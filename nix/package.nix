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
let
  customRevision = builtins.substring 0 7 (builtins.hashString "sha256"
    (builtins.readFile ./patches/features.patch + builtins.readFile ./patches/identity.patch));
  upstreamDate = upstreamSource.lastModifiedDate;
  date = "${builtins.substring 0 4 upstreamDate}-${builtins.substring 4 2 upstreamDate}-${builtins.substring 6 2 upstreamDate}";
  version = "unstable-${date}-${upstreamSource.shortRev}-${customRevision}";
in
mc.overrideAttrs (old: {
  inherit version;
  pname = "emcx";
  EMCX_VERSION = version;
  # Build upstream master directly, then apply functional and identity changes.
  # The lock records the exact upstream revision for reproducible builds.
  src = upstreamSource;
  patches = [ ./patches/features.patch ./patches/identity.patch ];
  buildInputs = (old.buildInputs or [ ]) ++ [ libzip ];
  nativeBuildInputs = (old.nativeBuildInputs or [ ]) ++ [
    autoreconfHook
    gettext
  ];
  postPatch =
    (old.postPatch or "")
    + ''
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
  postInstall = (old.postInstall or "") + ''
    ${python3}/bin/python3 ${./finalize-install.py} "$out" "$man"
    install -m755 ${./migrate-config.py} "$out/bin/emcx-migrate-config"
    substituteInPlace "$out/bin/emcx-migrate-config" \
      --replace-fail '/usr/bin/env python3' '${python3}/bin/python3'
  '';
  postFixup = builtins.replaceStrings [ "$out/bin/mc" ] [ "$out/bin/emcx" ] (old.postFixup or "");
  passthru = builtins.removeAttrs (old.passthru or { }) [ "updateScript" ];
  autoreconfPhase = ''
    runHook preAutoreconf
    ./autogen.sh
    runHook postAutoreconf
  '';
  meta = old.meta // {
    description = "A terminal file manager based on Midnight Commander";
    homepage = "https://github.com/tomasmark79/emcx";
    downloadPage = "https://github.com/tomasmark79/emcx";
    mainProgram = "emcx";
    platforms = lib.platforms.linux ++ lib.platforms.darwin;
  };
})
