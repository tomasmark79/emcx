#!/usr/bin/env python3
"""Export Modern customizations after merging the desired upstream revision."""

from pathlib import Path
import subprocess
import sys


root = Path(__file__).resolve().parent.parent
base = sys.argv[1] if len(sys.argv) > 1 else "upstream/master"
paths = ["configure.ac", "m4.include", "lib", "misc", "src", "version.sh"]
conflicts = subprocess.check_output(
    ["git", "diff", "--name-only", "--diff-filter=U"], cwd=root, text=True
)
if conflicts.strip():
    raise SystemExit("Resolve and stage all merge conflicts before exporting the patch.")
patch = subprocess.check_output(
    ["git", "diff", "--binary", base, "--", *paths], cwd=root
)
if not patch:
    raise SystemExit("No Modern customizations found; check the upstream revision.")
target = root / "nix/patches/modern.patch"
target.parent.mkdir(exist_ok=True)
target.write_bytes(patch)
print(f"Updated {target.relative_to(root)} against {base}")
