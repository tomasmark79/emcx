# Real TUI tests run explicitly, outside the build sandbox.
{ pkgs, mc }:
let
  moveFaults = pkgs.runCommandCC "mc-move-test-faults" { } ''
    mkdir -p $out/lib
    $CC -Wall -Wextra -Werror -shared -fPIC ${./tests/move_faults.c} -ldl \
      -o $out/lib/move-faults.so
  '';
in
pkgs.writeShellApplication {
  name = "mc-tests";
  runtimeInputs = [
    pkgs.python3
    pkgs.tmux
    pkgs.util-linux
    pkgs.coreutils
    pkgs.unzip
    pkgs.zip
  ];
  text = ''
    export MC_TEST_BINARY=${mc}/bin/mc
    export MC_TEST_HELPER=${../misc/mc-clipboard.py}
    export MC_TEST_UZIP=${mc}/libexec/mc/extfs.d/uzip
    export MC_TEST_MOVE_FAULTS=${moveFaults}/lib/move-faults.so
    python3 ${./tests}/move_abort.py
    python3 ${./tests/zip_cache.py}
    exec python3 ${./tests/run.py} "$@"
  '';
}
