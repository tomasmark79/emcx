"""Validate sudo-path configuration and rollback using temporary files only."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch


sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("sudo_path_helper", Path(__file__).parents[1] / "configure-sudo-path.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class SudoPathTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="emcx-sudo-test-")
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name) / "policy"
        self.target = self.directory / "emcx-source-path"
        for name, value in (("geteuid", 0),):
            mock = patch.object(helper.os, name, return_value=value)
            mock.start()
            self.addCleanup(mock.stop)
        mock = patch.object(helper.shutil, "which", return_value="/fake/visudo")
        mock.start()
        self.addCleanup(mock.stop)
        mock = patch.object(helper, "check_root_path")
        self.check_root_path = mock.start()
        self.addCleanup(mock.stop)

    def test_existing_path_needs_no_files_or_policy_changes(self):
        with patch.object(helper.subprocess, "run") as run:
            helper.configure("/usr/local", "/usr/local/bin:/usr/bin", self.directory)
            run.assert_not_called()
        self.assertFalse(self.directory.exists())
        self.check_root_path.assert_not_called()

    def test_new_dropin_preserves_path_entries_and_has_root_policy_permissions(self):
        with patch.object(helper.subprocess, "run"):
            helper.configure("/usr/local", "/sbin:/bin:/usr/sbin:/usr/bin", self.directory)
        self.assertIn('secure_path="/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/bin"', self.target.read_text())
        self.assertEqual(self.target.stat().st_mode & 0o777, 0o440)
        self.assertEqual(list(self.directory.iterdir()), [self.target])

    def test_invalid_paths_and_unmanaged_policy_are_not_overwritten(self):
        for path in ("relative:/bin", '/usr/bin:\"bad', "/usr/bin:\n/etc"):
            with self.assertRaises(RuntimeError):
                helper.configure("/usr/local", path, self.directory)
        self.assertFalse(self.directory.exists())
        self.directory.mkdir()
        self.target.write_text("# administrator policy\n")
        with patch.object(helper.subprocess, "run"), self.assertRaises(RuntimeError):
            helper.configure("/usr/local", "/usr/bin", self.directory)
        self.assertEqual(self.target.read_text(), "# administrator policy\n")

    def test_failed_complete_validation_restores_previous_state(self):
        previous = b'# Managed by the emcx source installer.\nDefaults secure_path="/bin"\n'
        for old in (None, previous):
            with self.subTest(existing_policy=old is not None):
                self.directory.mkdir(exist_ok=True)
                if old is not None:
                    self.target.write_bytes(old)
                checks = 0

                def validate(command, **kwargs):
                    nonlocal checks
                    if command[-1] == "-c":
                        checks += 1
                        if checks == 2:
                            raise subprocess.CalledProcessError(1, command)

                with patch.object(helper.subprocess, "run", side_effect=validate), self.assertRaises(subprocess.CalledProcessError):
                    helper.configure("/usr/local", "/usr/bin", self.directory)
                if old is None:
                    self.assertFalse(self.target.exists())
                else:
                    self.assertEqual(self.target.read_bytes(), old)
                self.assertEqual(list(self.directory.glob(".emcx-path-*")), [])


class TrustedPathTests(unittest.TestCase):
    def test_all_ancestors_must_be_root_owned_and_not_writable_by_other_users(self):
        for uid, mode, allowed in ((0, 0o40755, True), (1000, 0o40755, False),
                                   (0, 0o40775, False), (0, 0o41777, False)):
            with self.subTest(uid=uid, mode=mode):
                path = MagicMock()
                ancestor = MagicMock()
                path.parents = [ancestor]
                path.stat.return_value = SimpleNamespace(st_uid=0, st_mode=0o40755)
                ancestor.stat.return_value = SimpleNamespace(st_uid=uid, st_mode=mode)
                with patch.object(helper, "Path") as constructor:
                    constructor.return_value.resolve.return_value = path
                    if allowed:
                        helper.check_root_path("/opt/emcx/bin")
                    else:
                        with self.assertRaises(RuntimeError):
                            helper.check_root_path("/opt/emcx/bin")


if __name__ == "__main__":
    unittest.main(verbosity=2)
