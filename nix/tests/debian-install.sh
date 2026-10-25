#!/usr/bin/env bash
# Run only inside a disposable Debian container with the checkout at /source.
set -euo pipefail

if [[ ! -f /.dockerenv || $(id -u) != 0 || ! -d /source/.git ]]; then
    echo 'Use a disposable root Debian container with a read-only checkout mounted at /source.' >&2
    exit 1
fi

export DEBIAN_FRONTEND=noninteractive
export TERM=xterm-256color
apt-get update
apt-get install -y --no-install-recommends \
    build-essential autoconf automake autopoint gettext libtool pkg-config \
    libglib2.0-dev libslang2-dev libssh2-1-dev libext2fs-dev libzip-dev \
    python3 libglib2.0-bin wl-clipboard unzip zip git sudo ca-certificates

cp -a /source /build
git config --global --add safe.directory /build
cd /build
./autogen.sh
./configure --prefix=/usr/local
make -j"${EMCX_BUILD_JOBS:-2}"
make install
python3 nix/finalize-install.py /usr/local
install -m755 nix/migrate-config.py /usr/local/bin/emcx-migrate-config

test "$(command -v emcx)" = /usr/local/bin/emcx
emcx --version
test -r /usr/local/libexec/emcx/emcx.sh
test -r /usr/local/libexec/emcx/emcx-wrapper.sh

useradd --create-home --shell /bin/bash emcx-test
printf '%s\n' 'emcx-test ALL=(root) NOPASSWD: /usr/local/bin/emcx' > /etc/sudoers.d/emcx-test
chmod 0440 /etc/sudoers.d/emcx-test
runuser -u emcx-test -- env HOME=/home/emcx-test bash --noprofile --norc -c '
    test "$(command -v emcx)" = /usr/local/bin/emcx
    emcx --version
    sudo -n emcx --version
    shopt -s expand_aliases
    source /usr/local/libexec/emcx/emcx.sh
    test "$(type -t emcx)" = alias
    eval "emcx --version"
'

mkdir -p /root/.config/mc /home/emcx-test/.config/mc
printf '%s\n' 'ENTRY "Root files" URL "/root"' > /root/.config/mc/hotlist
printf '%s\n' 'ENTRY "User files" URL "/home/emcx-test"' > /home/emcx-test/.config/mc/hotlist
chown -R emcx-test:emcx-test /home/emcx-test/.config
emcx-migrate-config --hotlist-only --apply
runuser -u emcx-test -- env HOME=/home/emcx-test emcx-migrate-config --hotlist-only --apply
cmp /root/.config/mc/hotlist /root/.config/emcx/hotlist
cmp /home/emcx-test/.config/mc/hotlist /home/emcx-test/.config/emcx/hotlist
if cmp -s /root/.config/emcx/hotlist /home/emcx-test/.config/emcx/hotlist; then
    echo 'User and root hotlists unexpectedly match.' >&2
    exit 1
fi

printf 'Native install passed (%s): user, root, sudo, Bash wrapper and separate hotlists.\n' "$(uname -m)"
