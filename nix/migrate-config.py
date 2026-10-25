#!/usr/bin/env python3
"""Copy an existing Midnight Commander profile into separate emcx directories."""

import argparse
import os
import re
from pathlib import Path
import shutil
import stat
import sys
import tempfile


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


def write_private_file(parent, prefix, data, suffix=""):
    fd, name = tempfile.mkstemp(dir=parent, prefix=prefix, suffix=suffix)
    path = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path


def migrate_hotlist(apply=False):
    home = Path.home()
    root = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
    if not root.is_absolute():
        raise RuntimeError("XDG configuration directory must be an absolute path")
    source = root / "mc/hotlist"
    if not os.path.lexists(source):
        source = home / ".mc/hotlist"
    if not source.is_file():
        raise RuntimeError(f"No Midnight Commander hotlist found: {source}")
    target = root / "emcx/hotlist"
    if target.parent.resolve() == source.parent.resolve():
        raise RuntimeError("The emcx profile points to the original mc profile; refusing to modify it")
    if os.path.lexists(target) and not target.is_file():
        raise RuntimeError(f"Target is not a regular hotlist file: {target}")
    data = source.read_bytes()
    previous = target.read_bytes() if target.is_file() else None
    if (previous == data and not target.is_symlink() and target.stat().st_nlink == 1):
        print("The emcx hotlist already matches the original MC hotlist.")
        return
    print(f"Copy {source} -> {target}")
    if previous is not None:
        print("The existing emcx hotlist will be backed up before replacement.")
    if not apply:
        print("Dry run. Close MC and emcx, then use --apply to import the hotlist.")
        return
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if previous is not None:
        backup = write_private_file(target.parent, "hotlist.before-import-", previous, ".bak")
        print(f"Backup: {backup}")
    staged = write_private_file(target.parent, ".hotlist-import-", data)
    try:
        os.replace(staged, target)
    finally:
        staged.unlink(missing_ok=True)
    print("Hotlist imported. Other emcx settings and the original mc profile are unchanged.")


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
            raise RuntimeError(f"Target already exists; refusing to overwrite: {target}. "
                               "Use --hotlist-only to import bookmarks into an existing profile.")
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
                updated = re.sub(rb"\bMC_(TMPDIR|SID|SKIN|KEYMAP|EXTFS_CACHE)\b",
                                 rb"EMCX_\1", updated)
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
    parser.add_argument("--apply", action="store_true", help="perform the import; default is a dry run")
    parser.add_argument("--hotlist-only", action="store_true",
                        help="import only bookmarks, backing up an existing emcx hotlist")
    args = parser.parse_args()
    try:
        if args.hotlist_only:
            migrate_hotlist(args.apply)
        else:
            migrate(args.apply)
    except (OSError, RuntimeError, shutil.Error) as error:
        print(f"emcx-migrate-config: {error}", file=sys.stderr)
        raise SystemExit(1)
