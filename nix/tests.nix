# Real TUI tests run explicitly, outside the build sandbox.
{ pkgs, emcx }:
let
  moveFaults = pkgs.runCommandCC "emcx-move-test-faults" { } ''
    mkdir -p $out/lib
    $CC -Wall -Wextra -Werror -shared -fPIC ${./tests/move_faults.c} -ldl \
      -o $out/lib/move-faults.so
  '';
in
pkgs.writeShellApplication {
  name = "emcx-tests";
  runtimeInputs = [
    pkgs.python3
    pkgs.bash
    pkgs.tmux
    pkgs.util-linux
    pkgs.coreutils
    pkgs.unzip
    pkgs.zip
  ];
  text = ''
    export EMCX_TEST_BINARY=${emcx}/bin/emcx
    export EMCX_TEST_HELPER=${../misc/mc-clipboard.py}
    export EMCX_TEST_MAN=${emcx.man}
    export EMCX_TEST_UZIP=${emcx}/libexec/emcx/extfs.d/uzip
    export EMCX_TEST_MOVE_FAULTS=${moveFaults}/lib/move-faults.so
    python3 ${./tests}/identity.py
    python3 ${./tests}/move_abort.py
    python3 ${./tests/zip_cache.py}
    exec python3 ${./tests/run.py} "$@"
  '';
}
