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

## Install

On Debian/Ubuntu, Fedora, Arch, openSUSE or Alpine, download and run the source
installer as your normal user:

```sh
curl -fsSL https://raw.githubusercontent.com/tomasmark79/emcx/main/install.sh -o emcx-install.sh && sh emcx-install.sh
```

It installs dependencies, builds current upstream `master` with our patches,
and installs into `/usr/local`, including `sudo emcx`. Rerun the same command
to update. [Installer options and supported distributions](#native-source-builds).
For NixOS, use the [declarative flake package](#nix-and-nixos).

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

[`install.sh`](install.sh) contains the distribution detection, dependency lists
and build/install pipeline. It runs on POSIX `/bin/sh`, including Alpine's ash.
The download command needs `curl`; an existing checkout can run
`sh install.sh` directly. Administrator access is needed for dependencies and
the system installation. Root shells are also supported.

| Distribution family | Package manager |
|---|---|
| Debian, Ubuntu, Mint, Pop!_OS, Kali, Raspberry Pi OS | `apt-get` |
| Fedora | `dnf` |
| RHEL, Rocky, AlmaLinux, CentOS Stream, Oracle Linux (9+) | `dnf`, with the repository option below |
| Arch, Manjaro, EndeavourOS | `pacman` |
| openSUSE Tumbleweed and Leap | `zypper` |
| Alpine | `apk` |

Other derivatives are detected through `ID_LIKE` in `/etc/os-release`.
Enterprise Linux needs its vendor CRB/CodeReady Builder repository and EPEL for
the build dependencies. Enabling those repositories requires an explicit option:

```sh
sh emcx-install.sh --enable-epel
```

RHEL must already be registered with access to CodeReady Builder. Use
`--no-deps` instead to use dependencies provided by your administrator.
Arch should already be up to date: the installer uses `pacman -S --needed`,
following Arch's [guidance against partial upgrades](https://wiki.archlinux.org/title/System_maintenance#Partial_upgrades_are_unsupported).
It does not refresh Arch's database or force a complete system upgrade.

Preview the installation or choose build options:

```sh
sh emcx-install.sh --dry-run
sh emcx-install.sh --jobs 2
sh emcx-install.sh --prefix /opt/emcx
sh install.sh --source-dir "$PWD" --no-deps
```

The default `/usr/local` prefix provides the system-wide command. A custom
prefix needs its `bin` directory added to the user's and root's PATH as needed.
`--project-ref` and `--upstream-ref` can pin source revisions; both default to
the current branches. The build reports the exact upstream commit and a version
containing its date/hash and our patch hash. A patch conflict stops the build.
Failed builds are retained for inspection; `--keep-build` also retains successes.

Compilation and manual-page finalization happen in a temporary directory before
installation. The staged payload uses emcx names, preserves existing MC manuals,
and is installed with root ownership. Existing user/root profiles and hotlists
are retained. Import bookmarks separately with
`emcx-migrate-config --hotlist-only` and then `--hotlist-only --apply`, as
[described above](#commands-and-configuration).

If sudo's `secure_path` omits the installation's `bin` directory (as on RHEL
defaults), the installer adds it through `/etc/sudoers.d/emcx-source-path`.
The drop-in preserves existing entries and is checked with `visudo` before and
after installation. Hosts that already include the directory need no change.
New sudo-path entries must have root-owned ancestors without group/other write
access; a private or shared writable build prefix is not suitable for this.

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

## Development and validation

```bash
nix build .#emcx
nix run .#emcx-tests
nix build .#checks.x86_64-linux.coexistence
nix flake check --all-systems --no-build --no-update-lock-file
python3 nix/tests/installer.py
python3 nix/tests/sudo_path.py
```

Tests use disposable profiles and files, their own tmux servers, and user
namespaces for root-mode checks. They do not access a NAS or the real desktop
clipboard. The coexistence check installs emcx and upstream MC into one Nix
environment, including both sets of manual pages.

To check the source installer in a disposable container (including the normal
user, root, `sudo emcx`, the shell wrapper and preservation of MC files/profiles):

```bash
docker run --rm --platform linux/amd64 \
  --mount type=bind,src="$PWD",dst=/source,readonly \
  debian:bookworm sh /source/nix/tests/source-install.sh
```

The same test supports `ubuntu:24.04`, `fedora:latest`, `archlinux:base`,
`opensuse/tumbleweed:latest`, `alpine:latest`, and `rockylinux:9`. It installs dependencies and
changes sudo rules only inside the disposable container. ARM builds can be
tested natively on ARM; no cross-compilation is required by the installer.

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
