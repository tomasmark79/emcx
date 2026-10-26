#!/usr/bin/env python3
"""Add the source installation bindir to sudo's path when it is missing."""
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile


def check_root_path(bindir):
    path = Path(bindir).resolve(strict=True)
    for entry in (path, *path.parents):
        info = entry.stat()
        if info.st_uid != 0 or info.st_mode & 0o022 or not stat.S_ISDIR(info.st_mode):
            raise RuntimeError(f"sudo PATH needs root-owned directories without group/other write access: {entry}")


def configure(prefix, current_path, directory=Path("/etc/sudoers.d")):
    if os.geteuid() != 0:
        raise RuntimeError("sudo path configuration requires root")
    bindir = prefix.rstrip("/") + "/bin"
    paths = current_path.split(":")
    if bindir in paths:
        return
    if any(not path.startswith("/") or not re.fullmatch(r"[A-Za-z0-9_./+\-]+", path)
           for path in paths + [bindir]):
        raise RuntimeError("Cannot safely extend this sudo PATH; configure it manually")
    check_root_path(bindir)
    visudo = shutil.which("visudo", path="/usr/sbin:/sbin:" + os.environ.get("PATH", ""))
    if not visudo:
        raise RuntimeError("visudo is needed to validate sudo path configuration")
    subprocess.run([visudo, "-c"], check=True)
    directory = Path(directory)
    directory.mkdir(mode=0o755, exist_ok=True)
    target = directory / "emcx-source-path"
    header = b"# Managed by the emcx source installer.\n"
    previous = target.read_bytes() if target.exists() else None
    if previous is not None and not previous.startswith(header):
        raise RuntimeError(f"Refusing to replace administrator configuration: {target}")
    content = header + f'Defaults secure_path="{current_path}:{bindir}"\n'.encode()

    def replace(data):
        fd, name = tempfile.mkstemp(prefix=".emcx-path-", dir=directory)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
            os.chmod(name, 0o440)
            subprocess.run([visudo, "-cf", name], check=True)
            os.replace(name, target)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    replace(content)
    try:
        subprocess.run([visudo, "-c"], check=True)
    except Exception:
        if previous is None:
            target.unlink()
        else:
            replace(previous)
        raise
    print(f"Added {bindir} to sudo's secure_path in {target}")


if __name__ == "__main__":
    try:
        configure(*sys.argv[1:])
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
