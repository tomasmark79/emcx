{
  description = "Extended Commander — a terminal file manager based on Midnight Commander";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";
  inputs.mc-upstream = {
    url = "github:MidnightCommander/mc/master";
    flake = false;
  };

  outputs =
    { self, nixpkgs, mc-upstream }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      eachSystem = nixpkgs.lib.genAttrs systems;
    in
    {
      packages = eachSystem (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          emcx = pkgs.callPackage ./nix/package.nix { upstreamSource = mc-upstream; };
        in
        {
          inherit emcx;
          default = emcx;
        }
        // nixpkgs.lib.optionalAttrs pkgs.stdenv.hostPlatform.isLinux {
          emcx-tests = import ./nix/tests.nix { inherit pkgs emcx; };
        }
      );
      apps = eachSystem (system: {
        default = {
          type = "app";
          program = "${self.packages.${system}.emcx}/bin/emcx";
        };
      });
      checks = eachSystem (system:
        let pkgs = nixpkgs.legacyPackages.${system}; in {
          build = self.packages.${system}.emcx;
          coexistence = pkgs.buildEnv {
            name = "emcx-with-upstream-mc";
            paths = [ self.packages.${system}.emcx pkgs.mc ];
            extraOutputsToInstall = [ "man" ];
          };
        });
      devShells = eachSystem (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = pkgs.mkShell {
            inputsFrom = [ self.packages.${system}.emcx ];
            packages = [
              pkgs.python3
              pkgs.tmux
              pkgs.glib
            ]
            ++ pkgs.lib.optionals pkgs.stdenv.hostPlatform.isLinux [
              pkgs.util-linux
              pkgs.wl-clipboard
            ];
          };
        }
      );
    };
}
