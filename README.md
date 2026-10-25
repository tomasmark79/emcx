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

To reuse an existing MC profile, first review the proposed copy:

```bash
emcx-migrate-config
emcx-migrate-config --apply
```

Migration copies configuration and data, dereferences linked profiles and skins,
keeps directory cycles within the new profile, and updates bare `mc-clipboard`
commands in the copied user menu. It does not
modify the original profile or copy its cache. Existing emcx targets are never
overwritten. Review custom scripts containing absolute paths separately.

## Nix and NixOS

Run without installing:

```bash
nix run github:tomasmark79/emcx
```

Install into a user profile:

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
The package supports Linux and macOS; the TUI test runner is Linux-only.

`flake.lock` records exact source revisions. `nix flake update mc-upstream`
selects the current upstream master; builds reuse that selection. Update the
`emcx` input to obtain new customizations. A conflicting upstream change fails
the build until the patches are updated; it does not silently use an old source.

To keep the shell in the directory visited in emcx, source its shell wrapper.
For Bash on Linux:

```bash
alias emcx='. "$(dirname "$(readlink -f "$(type -P emcx)")")/../libexec/emcx/emcx-wrapper.sh"'
```

The wrapper path is resolved on each invocation, so package updates also work
in an already-open shell using this alias. Direct `nix run` cannot change the
parent shell's working directory.

## Features in action

These recordings show the customizations before the project was renamed:

![File actions and themes](2026-10-07%2000-01-04.gif)

![Terminal file manager alongside the desktop](2026-10-07%2000-06-08.gif)

Switch themes with `Alt+Shift+T`. On macOS terminals, releasing `Esc` and then
pressing uppercase `T` is another way to send that shortcut. DotName identifies
our themes; it is not the application name.

## Native source builds

The checked-in source tree also includes the functional and identity changes.
On Debian, install the usual MC build dependencies plus libzip before building:

```bash
sudo apt install build-essential autoconf automake autopoint gettext libtool \
  pkg-config libglib2.0-dev libslang2-dev libssh2-1-dev libext2fs-dev libzip-dev

git clone --branch main https://github.com/tomasmark79/emcx.git
cd emcx
./autogen.sh
./configure --prefix="$HOME/.local/opt/emcx"
make -j"$(nproc)"
make install
python3 nix/finalize-install.py "$HOME/.local/opt/emcx"
install -m755 nix/migrate-config.py "$HOME/.local/opt/emcx/bin/emcx-migrate-config"
```

Use a dedicated prefix as shown, then add its `bin` directory to `PATH`.
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
