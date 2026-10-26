#!/bin/sh
# Build current upstream MC with the emcx patches and install system-wide.
set -eu
umask 022

fail() { printf 'emcx installer: %s\n' "$*" >&2; exit 1; }
need_value() { [ "$#" -ge 2 ] && [ -n "$2" ] || fail "Missing value for $1"; }
usage() {
    cat <<'EOF'
Usage: sh install.sh [OPTIONS]

Install dependencies, compile upstream master with emcx patches, and install.
  --dry-run             Show the distribution, dependencies and plan; no writes
  --prefix PATH         System installation prefix (default: /usr/local)
  --jobs N              Parallel build jobs (default: up to 4)
  --source-dir PATH     Use emcx patches/tools from an existing checkout
  --project-ref REF     emcx Git branch/tag/commit (default: main)
  --upstream-ref REF    MC Git branch/tag/commit (default: master)
  --no-deps             Use already installed build dependencies
  --enable-epel         Enable CRB and EPEL on RHEL-compatible systems (9+)
  --keep-build          Keep the temporary source/build directory on success
  -h, --help            Show this help

Run as your normal user; sudo is used for dependencies and system installation.
Root shells can also run the installer. User profiles are left in place.
Rerun the same command to update. NixOS uses the declarative flake package.
EOF
}

prefix=/usr/local
jobs=
source_dir=
project_ref=main
upstream_ref=master
dry_run=0
no_deps=0
keep_build=0
enable_epel=0
work=
while [ "$#" -gt 0 ]; do
    case "$1" in
        --dry-run) dry_run=1; shift ;;
        --prefix) need_value "$@"; prefix=$2; shift 2 ;;
        --jobs) need_value "$@"; jobs=$2; shift 2 ;;
        --source-dir) need_value "$@"; source_dir=$2; shift 2 ;;
        --project-ref) need_value "$@"; project_ref=$2; shift 2 ;;
        --upstream-ref) need_value "$@"; upstream_ref=$2; shift 2 ;;
        --no-deps) no_deps=1; shift ;;
        --enable-epel) enable_epel=1; shift ;;
        --keep-build) keep_build=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) fail "Unknown option: $1 (use --help)" ;;
    esac
done

case "$prefix" in /*) ;; *) fail 'The prefix must be an absolute path' ;; esac
case "$prefix" in /|/usr|/bin|/sbin|/etc|/nix|/nix/*|*[!A-Za-z0-9_./+-]*)
    fail 'Use a dedicated prefix such as /usr/local or /opt/emcx (without spaces)' ;;
esac
case "$prefix/" in *//*|*/../*|*/./*) fail 'The prefix cannot contain empty, . or .. components' ;; esac
prefix=${prefix%/}
if [ -z "$jobs" ]; then
    jobs=$(getconf _NPROCESSORS_ONLN 2>/dev/null || printf 2)
    [ "$jobs" -le 4 ] || jobs=4
fi
case "$jobs" in ''|*[!0-9]*|0) fail '--jobs must be a positive integer' ;; esac
for ref in "$project_ref" "$upstream_ref"; do
    case "$ref" in ''|-*|*[!A-Za-z0-9_./+-]*) fail "Invalid Git ref: $ref" ;; esac
done

# This override is also useful for derivative distributions and detection tests.
os_release=${EMCX_OS_RELEASE_FILE:-/etc/os-release}
[ -r "$os_release" ] || fail "Cannot read $os_release"
ID='' ID_LIKE='' PRETTY_NAME=''
# shellcheck source=/dev/null
. "$os_release"
[ "${ID:-}" != nixos ] || fail 'On NixOS add the emcx flake package to environment.systemPackages. See https://github.com/tomasmark79/emcx#nix-and-nixos'
family=
for candidate in "${ID:-}" ${ID_LIKE:-}; do
    case "$candidate" in
        debian|ubuntu|linuxmint|raspbian|pop|kali) family=debian ;;
        fedora) family=fedora ;;
        rhel|rocky|almalinux|centos|ol) family=enterprise ;;
        arch|manjaro|endeavouros) family=arch ;;
        opensuse*|suse|sles) family=suse ;;
        alpine) family=alpine ;;
    esac
    [ -z "$family" ] || break
done
[ -n "$family" ] || fail "Unsupported distribution: ${ID:-unknown}. See the native build instructions in README.md."

case "$family" in
    debian)
        manager=apt-get
        packages='build-essential autoconf automake autopoint gettext libtool pkg-config git ca-certificates libglib2.0-dev libslang2-dev libssh2-1-dev libext2fs-dev libzip-dev python3 libglib2.0-bin wl-clipboard unzip zip tar sudo'
        ;;
    fedora|enterprise)
        manager=dnf
        packages='gcc make autoconf automake gettext-devel libtool pkgconf-pkg-config git ca-certificates glib2-devel slang-devel libssh2-devel e2fsprogs-devel libzip-devel python3 glib2 wl-clipboard unzip zip tar sudo'
        ;;
    arch)
        manager=pacman
        packages='base-devel git ca-certificates glib2-devel slang libssh2 e2fsprogs libzip python gettext wl-clipboard unzip zip tar sudo'
        ;;
    suse)
        manager=zypper
        packages='gcc make autoconf automake gettext-tools libtool pkg-config git ca-certificates glib2-devel slang-devel libssh2-devel libext2fs-devel libzip-devel python3 glib2-tools wl-clipboard unzip zip tar sudo'
        ;;
    alpine)
        manager=apk
        packages='build-base autoconf automake gettext-dev libtool pkgconf git ca-certificates glib-dev slang-dev libssh2-dev e2fsprogs-dev libzip-dev python3 glib wl-clipboard unzip zip perl bash tar sudo'
        ;;
esac

printf 'Distribution: %s (%s)\nPrefix: %s\nBuild jobs: %s\n' "${PRETTY_NAME:-$ID}" "$family" "$prefix" "$jobs"
printf 'Dependencies (%s): %s\n' "$manager" "$packages"
printf 'Sources: emcx %s + upstream MC %s\n' "$project_ref" "$upstream_ref"
if [ "$family" = enterprise ]; then
    enterprise_major=${VERSION_ID:-}
    enterprise_major=${enterprise_major%%.*}
    case "$enterprise_major" in ''|*[!0-9]*) fail 'Cannot determine enterprise distribution version' ;; esac
    [ "$enterprise_major" -ge 9 ] || fail 'Enterprise distributions require version 9 or newer'
    printf '%s\n' 'Build dependencies require CRB/CodeReady Builder and Fedora EPEL repositories.'
    if [ "$enable_epel" -eq 1 ] && [ "$no_deps" -eq 0 ]; then
        printf '%s\n' 'Plan: enable the vendor build repository and install Fedora epel-release.'
    elif [ "$no_deps" -eq 0 ] && [ "$dry_run" -eq 0 ]; then
        fail 'Rerun with --enable-epel to enable these repositories, or --no-deps if dependencies are already installed'
    fi
fi
if [ "$dry_run" -eq 1 ]; then
    [ "$no_deps" -eq 1 ] || printf '%s\n' 'Plan: install build dependencies using the distribution package manager.'
    printf '%s\n' 'Plan: clone sources; apply features.patch and identity.patch; compile; stage and rename manuals; install files and migration helper; extend sudo PATH through a validated drop-in if needed.'
    exit 0
fi

as_root() {
    if [ "$(id -u)" -eq 0 ]; then "$@"; else sudo "$@"; fi
}
if [ "$(id -u)" -ne 0 ]; then
    command -v sudo >/dev/null 2>&1 || fail 'sudo is needed for the system installation; install sudo or run from a root shell'
    sudo -v
fi
if [ "$no_deps" -eq 0 ]; then
    command -v "$manager" >/dev/null 2>&1 || fail "Package manager not found: $manager"
    # Package names above are constants, intentionally split into arguments.
    # shellcheck disable=SC2086
    set -- $packages
    if [ "$family" = enterprise ] && [ "$enable_epel" -eq 1 ]; then
        as_root dnf install -y dnf-plugins-core
        case "$ID" in
            rhel)
                as_root subscription-manager repos --enable "codeready-builder-for-rhel-$enterprise_major-$(uname -m)-rpms"
                as_root dnf install -y "https://dl.fedoraproject.org/pub/epel/epel-release-latest-$enterprise_major.noarch.rpm"
                ;;
            ol)
                as_root dnf config-manager --set-enabled "ol${enterprise_major}_codeready_builder"
                as_root dnf install -y "oracle-epel-release-el$enterprise_major"
                ;;
            *)
                as_root dnf config-manager --set-enabled crb
                as_root dnf install -y epel-release
                ;;
        esac
    fi
    case "$family" in
        debian) as_root apt-get update; as_root apt-get install -y --no-install-recommends "$@" ;;
        fedora|enterprise) as_root dnf install -y "$@" ;;
        arch)
            # Do not create a partial upgrade with -Sy or force a system upgrade.
            as_root pacman -S --needed --noconfirm "$@" || fail 'Dependency installation failed. Update Arch with pacman -Syu, then rerun the installer.'
            ;;
        suse) as_root zypper --non-interactive refresh; as_root zypper --non-interactive install --no-recommends "$@" ;;
        alpine) as_root apk add --no-cache "$@" ;;
    esac
fi
for tool in git make python3 tar autoconf automake libtoolize pkg-config sudo; do
    command -v "$tool" >/dev/null 2>&1 || fail "Missing dependency: $tool"
done

work=$(mktemp -d "${TMPDIR:-/tmp}/emcx-install.XXXXXXXX")
cleanup() {
    result=$?
    trap - 0
    if [ "$result" -ne 0 ] || [ "$keep_build" -eq 1 ]; then
        printf 'Build directory retained: %s\n' "$work" >&2
    else
        rm -rf -- "$work"
    fi
    exit "$result"
}
trap cleanup 0
trap 'exit 130' 2
trap 'exit 143' 15

checkout() {
    url=$1 ref=$2 destination=$3
    git init -q "$destination"
    git -C "$destination" remote add origin "$url"
    git -C "$destination" fetch --depth 1 origin "$ref"
    git -C "$destination" checkout -q --detach FETCH_HEAD
}
if [ -n "$source_dir" ]; then
    source_dir=$(CDPATH='' cd -- "$source_dir" && pwd -P)
else
    source_dir=$work/emcx
    checkout https://github.com/tomasmark79/emcx.git "$project_ref" "$source_dir"
fi
for file in nix/patches/features.patch nix/patches/identity.patch nix/finalize-install.py nix/migrate-config.py nix/configure-sudo-path.py; do
    [ -f "$source_dir/$file" ] || fail "Missing installer asset: $source_dir/$file"
done
checkout https://github.com/MidnightCommander/mc.git "$upstream_ref" "$work/upstream"
for patch in features identity; do
    git -C "$work/upstream" apply --check "$source_dir/nix/patches/$patch.patch"
    git -C "$work/upstream" apply "$source_dir/nix/patches/$patch.patch"
done
upstream_commit=$(git -C "$work/upstream" rev-parse HEAD)
upstream_time=$(git -C "$work/upstream" show -s --format=%ct HEAD)
EMCX_VERSION=$(python3 - "$source_dir" "$upstream_commit" "$upstream_time" <<'PY'
import datetime, hashlib, sys
from pathlib import Path
root = Path(sys.argv[1]) / 'nix/patches'
digest = hashlib.sha256((root / 'features.patch').read_bytes() + (root / 'identity.patch').read_bytes()).hexdigest()[:7]
date = datetime.datetime.fromtimestamp(int(sys.argv[3]), datetime.timezone.utc).strftime('%Y-%m-%d')
print(f'unstable-{date}-{sys.argv[2][:7]}-{digest}')
PY
)
export EMCX_VERSION
printf 'Building Extended Commander %s\nUpstream commit: %s\n' "$EMCX_VERSION" "$upstream_commit"
cd "$work/upstream"
./autogen.sh
./configure --prefix="$prefix" --with-screen=slang
make -j"$jobs"
make DESTDIR="$work/stage" install
staged=$work/stage$prefix
python3 "$source_dir/nix/finalize-install.py" "$staged"
install -m755 "$source_dir/nix/migrate-config.py" "$staged/bin/emcx-migrate-config"
# Finalize before deployment so upstream MC manual names are never installed.
# Include files and symlinks, not shared directory entries. --unlink-first can
# then replace a running executable without trying to remove /usr/local/share.
python3 - "$staged" "$work/files" <<'PY'
import os, sys
from pathlib import Path
root = Path(sys.argv[1])
with open(sys.argv[2], 'wb') as manifest:
    for path in sorted(root.rglob('*')):
        if path.is_symlink() or path.is_file():
            manifest.write(os.fsencode(path.relative_to(root)) + b'\0')
        elif not path.is_dir():
            raise SystemExit(f'Unsupported staged entry: {path}')
PY
tar -C "$staged" --null --no-recursion -T "$work/files" -cf "$work/emcx.tar"
as_root mkdir -p "$prefix"
as_root tar --unlink-first --no-same-owner -xpf "$work/emcx.tar" -C "$prefix"
sudo_path=$(sudo -n /bin/sh -c 'printf "%s" "$PATH"')
case ":$sudo_path:" in
    *":$prefix/bin:"*) ;;
    *) as_root python3 "$source_dir/nix/configure-sudo-path.py" "$prefix" "$sudo_path" ;;
esac
sudo_path=$(sudo -n /bin/sh -c 'printf "%s" "$PATH"')
case ":$sudo_path:" in
    *":$prefix/bin:"*) ;;
    *) fail "sudo did not load the installation path; check /etc/sudoers.d/emcx-source-path" ;;
esac
TERM="${TERM:-xterm}" "$prefix/bin/emcx" --version
printf '\nInstalled: %s/bin/emcx\nBash directory tracking: source %s/libexec/emcx/emcx.sh\n' "$prefix" "$prefix"
printf 'Import existing MC bookmarks: %s/bin/emcx-migrate-config --hotlist-only\n' "$prefix"
printf '%s\n' 'Run the import again with --apply after closing MC/emcx. Root has a separate profile.'
