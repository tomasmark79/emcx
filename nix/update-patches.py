#!/usr/bin/env python3
"""Export functional changes separately from the checked-in identity patch."""

from pathlib import Path
import subprocess
import sys
import os
import tempfile


root = Path(__file__).resolve().parent.parent
base = sys.argv[1] if len(sys.argv) > 1 else "upstream/master"
paths = ["configure.ac", "m4.include", "lib", "misc", "src", "contrib", "version.sh"]
conflicts = subprocess.check_output(
    ["git", "diff", "--name-only", "--diff-filter=U"], cwd=root, text=True
)
if conflicts.strip():
    raise SystemExit("Resolve and stage all merge conflicts before exporting the patch.")
identity = root / "nix/patches/identity.patch"
# Use a temporary index so neither the working tree nor its staging is changed.
with tempfile.TemporaryDirectory(prefix="emcx-patches-") as directory:
    env = {**os.environ, "GIT_INDEX_FILE": str(Path(directory) / "index")}
    subprocess.run(["git", "read-tree", "HEAD"], cwd=root, env=env, check=True)
    subprocess.run(["git", "add", "--", *paths], cwd=root, env=env, check=True)
    subprocess.run(
        ["git", "apply", "--cached", "--reverse", "--whitespace=nowarn", str(identity)],
        cwd=root, env=env, check=True,
    )
    patch = subprocess.check_output(
        ["git", "diff", "--cached", "--binary", base, "--", *paths], cwd=root, env=env
    )
if not patch:
    raise SystemExit("No functional customizations found; check the upstream revision.")
target = root / "nix/patches/features.patch"
target.parent.mkdir(exist_ok=True)
target.write_bytes(patch)
print(f"Updated {target.relative_to(root)} against {base}")
