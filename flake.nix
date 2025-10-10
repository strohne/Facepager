{
  description = "Facepager - An application for automated data retrieval on the web";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    # Generate outputs for common systems: x86_64-linux, aarch64-linux, x86_64-darwin, aarch64-darwin
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
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
            python310
            qt6.qtbase
            qt6.qtsvg
          ];
        };
      }
    );
}
