"""Exercise upstream #4759 through F6, using disposable files across filesystems."""

import hashlib
import os
from pathlib import Path
import tempfile
import time
import unittest

from run import Session


class InterruptedMoveTests(unittest.TestCase):
    def setUp(self):
        self.source = tempfile.TemporaryDirectory(prefix=".mc-move-", dir=Path.home())
        self.addCleanup(self.source.cleanup)
        self.target = tempfile.TemporaryDirectory(prefix="mc-move-", dir="/dev/shm")
        self.addCleanup(self.target.cleanup)
        if os.stat(self.source.name).st_dev == os.stat(self.target.name).st_dev:
            self.skipTest("Requires home and /dev/shm on different filesystems")
        self.log = Path(self.source.name) / "attributes.log"
        self.session = Session(
            self.source.name, skin="dotname-light", right_directory=self.target.name,
            extra_env={
                "LD_PRELOAD": os.environ["MC_TEST_MOVE_FAULTS"],
                "MC_TEST_MOVE_SOURCE": str(Path(self.source.name) / "left"),
                "MC_TEST_MOVE_TARGET": self.target.name,
                "MC_TEST_MOVE_LOG": str(self.log),
            },
        )
        self.addCleanup(self.session.stop)
        self.session.wait(lambda t: self.session.file.name in t and "other.txt" in t,
                          "Initial panels did not open")

    def start_move(self, size, multiple=False):
        s = self.session
        with s.file.open("wb") as stream:
            stream.write(bytes(range(256)) * (size // 256))
        self.digest = hashlib.sha256(s.file.read_bytes()).digest()
        self.second = s.left / "z-second.txt"
        if multiple:
            self.second.write_text("Must remain untouched after Abort\n")
        s.keys("C-r", "Home", "Down")
        s.wait(lambda t: s.file.name in t, "Source file missing")
        if multiple:
            s.keys("*")
        s.keys("F6")
        s.wait(lambda t: "source mask:" in t, "Move dialog missing")
        s.keys("Enter")
        self.destination = s.right / s.file.name

    def finish(self):
        self.session.wait(
            lambda t: "Source" not in t and "Incomplete file" not in t
            and "source mask:" not in t,
            "Move did not finish",
        )

    def interrupt(self, button, keep=True, multiple=False):
        size = 8 * 1024 * 1024
        self.start_move(size, multiple=multiple)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if self.destination.exists() and self.destination.stat().st_size > 0:
                break
            time.sleep(.01)
        else:
            self.fail("Copy did not start\n" + self.session.screen())
        self.session.keys(button)
        self.session.wait(lambda t: "Incomplete file was retrieved" in t,
                          "Incomplete-file dialog missing")
        self.session.keys("M-k" if keep else "M-d")
        self.finish()
        self.assertTrue(self.session.file.exists(), "Interrupted F6 deleted the source")
        self.assertEqual(hashlib.sha256(self.session.file.read_bytes()).digest(), self.digest)
        if keep:
            self.assertGreater(self.destination.stat().st_size, 0)
            self.assertLess(self.destination.stat().st_size, size)
        else:
            self.assertFalse(self.destination.exists())
        self.assertFalse(self.log.exists(), "Incomplete file must not have ext2 flags applied")

    def test_skip_keep_preserves_source(self):
        self.interrupt("M-s")

    def test_abort_keep_preserves_source_and_remaining_file(self):
        self.interrupt("M-a", multiple=True)
        self.assertTrue(self.second.is_file())
        self.assertFalse((self.session.right / self.second.name).exists())

    def test_abort_delete_preserves_source(self):
        self.interrupt("M-a", keep=False)

    def test_completed_move_still_removes_source(self):
        self.start_move(64 * 1024)
        self.session.wait(lambda t: self.log.exists(), "Attribute failure was not exercised")
        self.finish()
        self.assertFalse(self.session.file.exists())
        self.assertEqual(hashlib.sha256(self.destination.read_bytes()).digest(), self.digest)


if __name__ == "__main__":
    unittest.main(verbosity=2)
