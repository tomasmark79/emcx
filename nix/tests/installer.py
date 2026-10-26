"""Installer planning and failure boundaries, without system modifications."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


INSTALLER = Path(__file__).resolve().parents[2] / "install.sh"
SHELL = shutil.which("sh")


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="emcx-installer-test-")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.release = self.base / "os-release"
        self.release.write_text('ID=debian\nPRETTY_NAME="Test Debian"\n')
        self.env = {**os.environ, "EMCX_OS_RELEASE_FILE": str(self.release),
                    "TMPDIR": str(self.base), "LC_ALL": "C"}

    def run_installer(self, *args):
        return subprocess.run([SHELL, str(INSTALLER), *args], env=self.env,
                              text=True, capture_output=True, timeout=10)

    def test_distributions_and_derivatives_have_a_read_only_plan(self):
        for identity, like, manager in (
            ("debian", "", "apt-get"), ("ubuntu", "debian", "apt-get"),
            ("linuxmint", "ubuntu debian", "apt-get"),
            ("fedora", "", "dnf"), ("arch", "", "pacman"),
            ("manjaro", "arch", "pacman"),
            ("opensuse-tumbleweed", "suse", "zypper"),
            ("opensuse-leap", "suse", "zypper"), ("alpine", "", "apk"),
            ("derivative", "ubuntu debian", "apt-get"),
        ):
            with self.subTest(distribution=identity):
                self.release.write_text(f'ID={identity}\nID_LIKE="{like}"\n')
                result = self.run_installer("--dry-run")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"Dependencies ({manager})", result.stdout)
                self.assertIn("upstream MC master", result.stdout)
                self.assertEqual(list(self.base.iterdir()), [self.release])

    def test_nixos_keeps_the_declarative_installation(self):
        self.release.write_text("ID=nixos\n")
        result = self.run_installer("--dry-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("environment.systemPackages", result.stderr)
        self.assertEqual(list(self.base.iterdir()), [self.release])

    def test_enterprise_repository_changes_require_an_explicit_option(self):
        self.release.write_text('ID=rocky\nVERSION_ID="9.6"\nID_LIKE="rhel centos fedora"\n')
        result = self.run_installer("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Dependencies (dnf)", result.stdout)
        self.assertIn("CRB/CodeReady Builder", result.stdout)
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--enable-epel", result.stderr)
        self.assertEqual(list(self.base.iterdir()), [self.release])
        result = self.run_installer("--dry-run", "--enable-epel")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Plan: enable the vendor build repository", result.stdout)

    def test_unsupported_distribution_stops_before_writes(self):
        self.release.write_text("ID=unknown\n")
        result = self.run_installer("--dry-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unsupported distribution", result.stderr)
        self.assertEqual(list(self.base.iterdir()), [self.release])

    def test_invalid_prefixes_and_arguments_are_rejected(self):
        cases = [("--prefix", value) for value in
                 ("/", "//", "/usr", "/nix/store/test", "relative", "/usr/../etc", "/tmp/a b")]
        cases += [("--jobs", "0"), ("--jobs", "-1"), ("--jobs", "two"),
                  ("--project-ref", "--upload-pack=bad"), ("--prefix",), ("--unknown",)]
        for args in cases:
            with self.subTest(arguments=args):
                result = self.run_installer(*args, "--dry-run")
                self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.base.iterdir()), [self.release])

    def test_dependency_failure_does_not_fetch_or_install_sources(self):
        fake_bin = self.base / "bin"
        fake_bin.mkdir()
        log = self.base / "commands"
        self.env["COMMAND_LOG"] = str(log)
        self.env["PATH"] = str(fake_bin) + os.pathsep + self.env["PATH"]
        for name, body in {
            "id": "echo 0\n",
            "apt-get": 'echo "apt-get $*" >> "$COMMAND_LOG"\n[ "$1" = update ] || exit 42\n',
            "git": 'echo "unexpected Git operation" >> "$COMMAND_LOG"\nexit 99\n',
        }.items():
            script = fake_bin / name
            script.write_text("#!/bin/sh\n" + body)
            script.chmod(0o755)
        result = self.run_installer()
        self.assertEqual(result.returncode, 42, result.stderr)
        self.assertNotIn("unexpected", log.read_text())
        self.assertEqual(list(self.base.glob("emcx-install.*")), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
