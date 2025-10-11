{
  description = "Facepager - An application for automated data retrieval on the web";

  inputs = {
    # Use nixpkgs-unstable
    # Note: PySide6 WebEngine support is not available on macOS in Nix
    # Users needing full WebEngine functionality should use traditional installers
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    # Generate outputs for common systems: x86_64-linux, aarch64-linux, x86_64-darwin, aarch64-darwin
    flake-utils.lib.eachDefaultSystem (system:
      let
        # Allow broken packages (qtwebengine is marked broken on macOS but may work)
        pkgs = import nixpkgs {
          inherit system;
          config.allowBroken = true;
        };
        facepager = pkgs.callPackage ./package.nix { };
      in
      {
        # Accessed through: inputs.facepager.packages.${system}.default
        packages = {
          default = facepager;
          facepager = facepager;
        };

        apps.default = {
          type = "app";
          program = "${facepager}/bin/facepager";
        };

        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            python311
            qt6.qtbase
            qt6.qtsvg
          ];
        };
      }
    );
}
