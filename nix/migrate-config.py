#!/usr/bin/env python3
"""Copy an existing Midnight Commander profile into separate emcx directories."""

import argparse
import os
import re
from pathlib import Path
import shutil
import stat
import sys


def copy_profile(source, target, copied):
    """Materialize external links and keep directory cycles inside the new profile."""
    info = source.stat()
    if stat.S_ISDIR(info.st_mode):
        identity = (info.st_dev, info.st_ino)
        if identity in copied:
            target.symlink_to(os.path.relpath(copied[identity], target.parent),
                              target_is_directory=True)
            return
        copied[identity] = target
        target.mkdir(exist_ok=True)
        for child in source.iterdir():
            copy_profile(child, target / child.name, copied)
        shutil.copystat(source, target)
    elif stat.S_ISREG(info.st_mode):
        shutil.copy2(source, target)
    else:
        raise RuntimeError(f"Unsupported profile entry: {source}")


def migrate(apply=False):
    home = Path.home()
    roots = [
        Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")),
        Path(os.environ.get("XDG_DATA_HOME", home / ".local/share")),
    ]
    if any(not root.is_absolute() for root in roots):
        raise RuntimeError("XDG configuration and data directories must be absolute paths")
    roots = list(dict.fromkeys(roots))
    plans = [(root / "mc", root / "emcx") for root in roots if (root / "mc").is_dir()]
    if not plans:
        print("No Midnight Commander configuration or data found.")
        return
    for source, target in plans:
        if os.path.lexists(target):
            raise RuntimeError(f"Target already exists; refusing to overwrite: {target}")
        print(f"Copy {source} -> {target}")
    if not apply:
        print("Dry run. Use --apply to copy. The original mc profile is retained.")
        return
    created = []
    try:
        for source, target in plans:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.mkdir(mode=0o700)
            created.append(target)
            copy_profile(source, target, {})
            menu = target / "menu"
            if menu.is_file():
                text = menu.read_bytes()
                updated = re.sub(rb"(?<![\w./-])mc-clipboard(?![\w.-])", b"emcx-clipboard", text)
                if updated != text:
                    menu.chmod(menu.stat().st_mode | 0o200)
                    menu.write_bytes(updated)
            target.chmod(0o700)
    except Exception:
        for target in reversed(created):
            shutil.rmtree(target)
        raise
    print("Copied successfully. The original mc profile and cache are unchanged.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="copy profiles; default is a dry run")
    args = parser.parse_args()
    try:
        migrate(args.apply)
    except (OSError, RuntimeError, shutil.Error) as error:
        print(f"emcx-migrate-config: {error}", file=sys.stderr)
        raise SystemExit(1)
