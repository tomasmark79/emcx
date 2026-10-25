"""Public command identity, separate profiles, migration and executable modes."""

import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

from run import BINARY, Session


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix=".emcx-identity-", dir=Path.home())
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.prefix = Path(BINARY).resolve().parent.parent
        self.env = {**os.environ, "HOME": str(self.base),
                    "XDG_CONFIG_HOME": str(self.base / "config"),
                    "XDG_DATA_HOME": str(self.base / "data"),
                    "XDG_CACHE_HOME": str(self.base / "cache"),
                    "TMPDIR": str(self.base), "LC_ALL": "C.UTF-8"}

    def test_public_commands_and_report_destination(self):
        names = {p.name for p in (self.prefix / "bin").iterdir()}
        self.assertEqual(names, {"emcx", "emcx-edit", "emcx-view", "emcx-diff",
                                 "emcx-clipboard", "emcx-migrate-config"})
        version = subprocess.check_output([BINARY, "--version"], env=self.env, text=True)
        self.assertTrue(version.startswith("Extended Commander "), version)
        help_text = subprocess.check_output([BINARY, "--help"], env=self.env, text=True)
        self.assertIn("https://github.com/tomasmark79/emcx/issues", help_text)
        self.assertNotIn("github.com/MidnightCommander/mc/issues", help_text)

    def test_profile_and_data_paths_are_separate(self):
        old = self.base / "config/mc"
        old.mkdir(parents=True)
        marker = old / "ini"
        marker.write_text("legacy profile must remain unchanged\n")
        paths = subprocess.check_output([BINARY, "-F"], env=self.env, text=True)
        self.assertIn("/share/emcx/", paths)
        self.assertIn("/libexec/emcx/", paths)
        self.assertIn("/etc/emcx/", paths)
        self.assertIn(str(self.base / "config/emcx"), paths)
        self.assertNotIn("/share/mc/", paths)
        self.assertNotIn("/libexec/mc/", paths)
        self.assertEqual(marker.read_text(), "legacy profile must remain unchanged\n")

    def test_shell_wrapper_launches_emcx(self):
        wrapper = self.prefix / "libexec/emcx/emcx-wrapper.sh"
        result = subprocess.run(["bash", "--noprofile", "--norc", "-c",
                                 '. "$1" --version', "test", str(wrapper)],
                                env=self.env, capture_output=True, text=True, check=True)
        self.assertTrue(result.stdout.startswith("Extended Commander "))

    def test_manual_names_do_not_shadow_mc(self):
        root = Path(os.environ["EMCX_TEST_MAN"]) / "share/man"
        files = {p.name for p in root.rglob("*") if p.is_file()}
        for name in ("emcx", "emcx-edit", "emcx-view", "emcx-diff"):
            self.assertTrue(name + ".1" in files or name + ".1.gz" in files, name)
        self.assertFalse(files & {"mc.1.gz", "mc.1", "mcedit.1.gz", "mcview.1.gz", "mcdiff.1.gz"})

    def test_executable_names_select_the_correct_modes(self):
        for mode in ("edit", "view", "diff"):
            with self.subTest(mode=mode):
                directory = self.base / mode
                first = directory / "left/file with spaces.txt"
                second = directory / "right/other.txt"
                args = [str(first)] + ([str(second)] if mode == "diff" else [])
                s = Session(directory, skin="dotname-light", args=args,
                            executable=str(self.prefix / "bin" / ("emcx-" + mode)),
                            panel_arguments=False)
                try:
                    s.wait(lambda t: "test content" in t, f"{mode} did not open file content")
                    if mode == "diff":
                        s.wait(lambda t: "second panel" in t, "Diff mode did not show both files")
                    else:
                        s.keys("End", "X", "F2")
                        if mode == "edit":
                            s.wait(lambda t: "Confirm save file:" in t, "Save confirmation missing")
                            s.keys("Enter")
                            deadline = time.monotonic() + 8
                            while time.monotonic() < deadline and "X" not in first.read_text():
                                time.sleep(.05)
                            self.assertIn("X", first.read_text(), "Editor mode did not save changes")
                        else:
                            self.assertEqual(first.read_text(), "test content\n")
                finally:
                    s.stop()

    def migrate(self, *args):
        return subprocess.run([str(self.prefix / "bin/emcx-migrate-config"), *args],
                              env=self.env, capture_output=True, text=True)

    def test_migration_copies_linked_profile_without_sharing_or_overwriting(self):
        old = self.base / "config/mc"
        old.mkdir(parents=True)
        (old / "ini").write_text("original settings\n")
        (old / "menu").write_text("c Copy path\n    mc-clipboard path %f\n    echo $MC_TMPDIR\n")
        data = self.base / "data"
        data.mkdir()
        (data / "mc").symlink_to(old, target_is_directory=True)
        self.assertEqual(self.migrate().returncode, 0)
        self.assertFalse((self.base / "config/emcx").exists())
        result = self.migrate("--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        for root in (self.base / "config", data):
            self.assertFalse((root / "emcx").is_symlink())
            self.assertEqual((root / "emcx/ini").read_text(), "original settings\n")
            self.assertIn("emcx-clipboard path", (root / "emcx/menu").read_text())
            self.assertIn("$EMCX_TMPDIR", (root / "emcx/menu").read_text())
        (self.base / "config/emcx/ini").write_text("new profile\n")
        self.assertNotEqual(self.migrate("--apply").returncode, 0)
        self.assertEqual((old / "ini").read_text(), "original settings\n")
        self.assertIn("mc-clipboard path", (old / "menu").read_text())
        self.assertEqual((self.base / "config/emcx/ini").read_text(), "new profile\n")

    def test_migration_directory_cycles_stay_inside_new_profile(self):
        old = self.base / "config/mc"
        old.mkdir(parents=True)
        (old / "ini").write_text("original settings\n")
        (old / "links").mkdir()
        (old / "links/mc").symlink_to(old, target_is_directory=True)
        skins = self.base / "external-skins"
        skins.mkdir()
        (skins / "theme.ini").write_text("original theme\n")
        (old / "skins").symlink_to(skins, target_is_directory=True)
        result = self.migrate("--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        new = self.base / "config/emcx"
        self.assertEqual((new / "links/mc").resolve(), new.resolve())
        self.assertFalse((new / "skins").is_symlink())
        (new / "links/mc/ini").write_text("new settings\n")
        (new / "skins/theme.ini").write_text("new theme\n")
        self.assertEqual((old / "ini").read_text(), "original settings\n")
        self.assertEqual((skins / "theme.ini").read_text(), "original theme\n")

    def test_migration_failure_cleans_only_its_new_targets(self):
        old = self.base / "config/mc"
        old.mkdir(parents=True)
        (old / "ini").write_text("original settings\n")
        data = self.base / "data/mc"
        data.mkdir(parents=True)
        (data / "broken").symlink_to(self.base / "missing")
        self.assertNotEqual(self.migrate("--apply").returncode, 0)
        self.assertFalse((self.base / "config/emcx").exists())
        self.assertFalse((self.base / "data/emcx").exists())
        self.assertEqual((old / "ini").read_text(), "original settings\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
