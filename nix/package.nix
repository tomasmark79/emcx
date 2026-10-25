{
  lib,
  stdenv,
  mc,
  autoreconfHook,
  gettext,
  python3,
  glib,
  libzip,
  wl-clipboard,
  upstreamSource,
}:
mc.overrideAttrs (old: {
  version =
    lib.removeSuffix "\n" (builtins.readFile ../dotname/VERSION)
    + "-${upstreamSource.shortRev or "unknown"}";
  # Build upstream master directly, then apply only the Modern customizations.
  # The lock records the exact upstream revision for reproducible builds.
  src = upstreamSource;
  patches = [ ./patches/modern.patch ];
  buildInputs = (old.buildInputs or [ ]) ++ [ libzip ];
  nativeBuildInputs = (old.nativeBuildInputs or [ ]) ++ [
    autoreconfHook
    gettext
  ];
  postPatch =
    (old.postPatch or "")
    + ''
      mkdir -p dotname
      printf '%s\n' "$version" > dotname/VERSION
      substituteInPlace misc/mc-clipboard.py \
        --replace-fail '/usr/bin/env python3' '${python3}/bin/python3'
    ''
    + lib.optionalString stdenv.hostPlatform.isLinux ''
      substituteInPlace misc/mc-clipboard.py \
        --replace-fail '"wl-copy"' '"${wl-clipboard}/bin/wl-copy"'
    ''
    + ''
      substituteInPlace misc/mc-trash.menu \
        --replace-fail 'gio trash' '${glib.bin}/bin/gio trash'
    '';
  autoreconfPhase = ''
    runHook preAutoreconf
    ./autogen.sh
    runHook postAutoreconf
  '';
  meta = old.meta // {
    description = "Midnight Commander with trash actions, Wayland clipboard support, and DotName skins";
    homepage = "https://github.com/tomasmark79/mc";
    platforms = lib.platforms.linux ++ lib.platforms.darwin;
  };
})
