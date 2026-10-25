# Extended Commander

*A terminal file manager based on Midnight Commander.*

Extended Commander (`emcx`) builds upstream Midnight Commander `master` with a
small set of functional and identity patches. It is an independent fork;
[report emcx issues here](https://github.com/tomasmark79/emcx/issues).
The original authors, license, and upstream documentation are preserved.

The package includes GIO trash actions, Wayland clipboard support, DotName light
and dark themes with root variants, live theme switching, Lynx-like navigation,
and direct ZIP streaming through libzip. Defaults work with a clean profile.
[Feature details, packaging, and tests](nix/README.md).

## Commands and configuration

| Command | Purpose |
|---|---|
| `emcx` | File manager |
| `emcx-edit` | Internal editor |
| `emcx-view` | File viewer |
| `emcx-diff` | File comparison |
| `emcx-clipboard` | Wayland clipboard helper |
| `emcx-migrate-config` | Copy an existing MC profile into separate emcx directories |

The Nix package installs no `mc`, `mcedit`, `mcview`, or `mcdiff` executable.
Commands, data, translations, and manual pages can coexist with upstream MC.
User configuration, data, and cache use the `emcx` directory under the standard
XDG locations, such as `~/.config/emcx`, `~/.local/share/emcx`, and `~/.cache/emcx`.
`EMCX_SKIN`, `EMCX_KEYMAP`, and `EMCX_TMPDIR` provide fork-specific overrides.
Internal configuration keys and profile formats remain compatible with MC.

To reuse an existing MC profile, close MC and emcx, then review and apply the copy
before the first emcx launch:

```bash
emcx-migrate-config
emcx-migrate-config --apply
```

Migration copies configuration and data, dereferences linked profiles and skins,
keeps directory cycles within the new profile, and updates bare `mc-clipboard`
commands and public `MC_*` environment variables in the copied user menu. It does not
modify the original profile or copy its cache. Existing emcx targets are never
overwritten. Review custom scripts containing absolute paths separately.

If emcx has already created a profile, import only the original MC hotlist:

```bash
emcx-migrate-config --hotlist-only
emcx-migrate-config --hotlist-only --apply
```

This copies bookmarks without changing other emcx settings. An existing hotlist
is backed up as `hotlist.before-import-*.bak` in the emcx configuration directory
before atomic replacement. The original MC hotlist is retained. A legacy
`~/.mc/hotlist` is also recognized when the XDG MC hotlist is absent.

## Nix and NixOS

Run without installing:

```bash
nix run github:tomasmark79/emcx
```

Install into a user profile (available to that user):

```bash
nix profile install github:tomasmark79/emcx#emcx
```

For NixOS, use the package from this flake. Keeping upstream as a separate root
input lets a configuration update it independently of our patch repository:

```nix
inputs.emcx = {
  url = "github:tomasmark79/emcx";
  inputs.nixpkgs.follows = "nixpkgs";
  inputs.mc-upstream.follows = "mc-upstream";
};
inputs.mc-upstream = {
  url = "github:MidnightCommander/mc/master";
  flake = false;
};
```

Add `emcx.packages.${pkgs.stdenv.hostPlatform.system}.emcx` to
`environment.systemPackages` in a module receiving the `emcx` input.
This is the system-wide NixOS installation: both the regular user and root can
run `emcx`, including `sudo emcx`. A user-profile installation or `nix run` does
not provide this system-wide command. No manual links into `/usr/bin` are needed.
The package supports Linux and macOS; the TUI test runner is Linux-only.

`flake.lock` records exact source revisions. `nix flake update mc-upstream`
selects the current upstream master; builds reuse that selection. Update the
`emcx` input to obtain new customizations. A conflicting upstream change fails
the build until the patches are updated; it does not silently use an old source.

To keep the shell in the directory visited in emcx, source its shell wrapper.
For Bash on NixOS:

```bash
alias emcx='. "$(dirname "$(readlink -f "$(type -P emcx)")")/../libexec/emcx/emcx-wrapper.sh"'
```

The wrapper path is resolved on each invocation, so package updates also work
in an already-open shell using this alias. Direct `nix run` cannot change the
parent shell's working directory.

## Themes

Switch themes with `Alt+Shift+T`. On macOS terminals, releasing `Esc` and then
pressing uppercase `T` is another way to send that shortcut. DotName identifies
our themes; it is not the application name.

## Native source builds

The checked-in source tree also includes the functional and identity changes.
On Debian (including ARM), install dependencies and build a system-wide copy
under `/usr/local`. This makes `emcx` available to the regular user and root,
including `sudo emcx`:

```bash
sudo apt install build-essential autoconf automake autopoint gettext libtool \
  pkg-config libglib2.0-dev libslang2-dev libssh2-1-dev libext2fs-dev libzip-dev \
  python3 libglib2.0-bin wl-clipboard unzip zip

git clone --branch main https://github.com/tomasmark79/emcx.git
cd emcx
./autogen.sh
./configure --prefix=/usr/local
make -j"$(nproc)"
sudo make install
sudo python3 nix/finalize-install.py /usr/local
sudo install -m755 nix/migrate-config.py /usr/local/bin/emcx-migrate-config

emcx --version
sudo emcx --version
```

The Python finalization step only renames manuals, and `install` only installs
the migration command. Neither imports your profile. To import your existing
MC bookmarks, close MC and emcx, then run these commands as your normal user:

```bash
emcx-migrate-config --hotlist-only
emcx-migrate-config --hotlist-only --apply
```

They can also be run directly from the checkout as
`python3 nix/migrate-config.py` with the same options, without rebuilding C.
To copy the entire original profile instead, use the full-profile migration
above before the first emcx invocation.

For Bash directory tracking, add this to your `~/.bashrc`:

```bash
source /usr/local/libexec/emcx/emcx.sh
```

When switching from a private installation, remove the earlier
`~/.local/opt/emcx/bin` PATH entry and its shell integration line. The system
installation also works without an alias; `sudo emcx` invokes the binary directly.
Root has its own profile. To import root's original MC bookmarks, close root's
MC/emcx sessions and run `sudo emcx-migrate-config --hotlist-only` followed by
`sudo emcx-migrate-config --hotlist-only --apply`. Run migration without sudo for
your own bookmarks. The installer does not copy one user's profile to another.

For an optional private installation, configure with
`--prefix="$HOME/.local/opt/emcx"`, run `make install` without sudo, and use that
prefix for the two Python/helper installation steps. Add its `bin` directory to
your PATH and source its `libexec/emcx/emcx.sh`. This variant is scoped to your
account; use the system installation above for `sudo emcx`.

The finalization step renames the installed upstream manuals for emcx.
Installing libzip after compilation does not enable ZIP streaming: configure
and rebuild with the library present. The Nix package includes it automatically.
Native builds use Git version information; Nix builds report the locked upstream
commit date/hash and a hash of the custom patches, with no manual version file.

## Development and validation

```bash
nix build .#emcx
nix run .#emcx-tests
nix build .#checks.x86_64-linux.coexistence
nix flake check --all-systems --no-build --no-update-lock-file
```

Tests use disposable profiles and files, their own tmux servers, and user
namespaces for root-mode checks. They do not access a NAS or the real desktop
clipboard. The coexistence check installs emcx and upstream MC into one Nix
environment, including both sets of manual pages.

To check the native Debian installation in a disposable container (including
the normal user, root, `sudo emcx`, the shell wrapper and separate hotlists):

```bash
docker run --rm --platform linux/arm64 \
  --mount type=bind,src="$PWD",dst=/source,readonly \
  debian:bookworm bash /source/nix/tests/debian-install.sh
```

An ARM64 run on an x86 host requires an already configured binfmt emulator.
Use `--platform linux/amd64` to test x86 Debian instead. The script installs
dependencies and changes sudo rules only inside the disposable container.

When updating the maintained native source tree:

```bash
git fetch upstream master
git merge upstream/master
# Resolve and stage source conflicts if necessary.
python3 nix/update-patches.py
nix flake update mc-upstream
nix run .#emcx-tests
```

`nix/patches/features.patch` contains our functional changes.
`nix/patches/identity.patch` contains the identity changes applied afterward.
The exporter reverses the identity patch in a temporary Git index before
exporting functional changes; it leaves the working tree and staging untouched.
Refresh the identity patch deliberately if upstream changes its affected code.
Keep changes local until reviewed and tested. See `COPYING` for the original
GNU GPL license and `AUTHORS` for upstream contributors.
