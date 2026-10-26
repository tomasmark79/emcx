#!/bin/sh
# Integration test: disposable container only; never run on an installed system.
set -eu
[ -f /.dockerenv ] && [ "$(id -u)" -eq 0 ] && [ -f /source/install.sh ] || {
    echo 'Run in a disposable root container with the checkout mounted read-only at /source.' >&2
    exit 1
}
export TERM=xterm-256color
# shellcheck source=/dev/null
. /etc/os-release
case "$ID" in
    debian|ubuntu) apt-get update; DEBIAN_FRONTEND=noninteractive apt-get install -y sudo ;;
    fedora|rocky|almalinux|centos|rhel|ol) dnf install -y sudo shadow-utils util-linux ;;
    alpine) apk add --no-cache sudo shadow bash ;;
    arch) pacman -Syu --noconfirm sudo ;;
    opensuse*) zypper --non-interactive refresh; zypper --non-interactive install sudo shadow ;;
    *) echo "Test bootstrap not implemented: $ID" >&2; exit 1 ;;
esac
useradd --create-home --shell /bin/sh emcx-test
printf '%s\n' 'Defaults:emcx-test !targetpw' 'emcx-test ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers
mkdir -p /usr/local/bin /usr/local/share/man/man1 /home/emcx-test/.config/mc /home/emcx-test/.config/emcx
cp "$(command -v sleep)" /usr/local/bin/emcx
bash -c 'exec -a sleep /usr/local/bin/emcx 3600' &
old_pid=$!
trap 'kill "$old_pid" 2>/dev/null || true' 0
printf '%s\n' 'original upstream MC manual' > /usr/local/share/man/man1/mc.1
printf '%s\n' 'original MC bookmarks' > /home/emcx-test/.config/mc/hotlist
printf '%s\n' 'current emcx bookmarks' > /home/emcx-test/.config/emcx/hotlist
chown -R emcx-test:emcx-test /home/emcx-test/.config

case "$ID" in rocky|almalinux|centos|rhel|ol) extra=--enable-epel ;; *) extra= ;; esac
su -s /bin/sh emcx-test -c "sh /source/install.sh --source-dir /source --jobs 2 $extra"
kill -0 "$old_pid"
test "$(cat /usr/local/share/man/man1/mc.1)" = 'original upstream MC manual'
test "$(cat /home/emcx-test/.config/mc/hotlist)" = 'original MC bookmarks'
test "$(cat /home/emcx-test/.config/emcx/hotlist)" = 'current emcx bookmarks'
test "$(stat -c %u /usr/local/bin/emcx)" = 0
test "$(stat -c %u /usr/local/bin/emcx-migrate-config)" = 0
emcx --version
# Expanded by the user's child shell, after sourcing its wrapper.
# shellcheck disable=SC2016
su -s /bin/bash emcx-test -c '
    set -eu
    emcx --version
    sudo -n emcx --version
    shopt -s expand_aliases
    source /usr/local/libexec/emcx/emcx.sh
    test "$(type -t emcx)" = alias
    eval "emcx --version"
    emcx-migrate-config --hotlist-only --apply
'
test "$(cat /home/emcx-test/.config/emcx/hotlist)" = 'original MC bookmarks'
test "$(cat /home/emcx-test/.config/emcx/hotlist.before-import-*.bak)" = 'current emcx bookmarks'
printf 'Source installer passed: %s (%s), unprivileged build, root ownership, sudo, wrapper, preserved MC manual and profiles.\n' "$ID" "$(uname -m)"
