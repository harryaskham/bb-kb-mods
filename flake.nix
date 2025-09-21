{
  description = "Programmatic edits to zitaotech BB keyboard models";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    pyproject-nix = {
      url = "github:nix-community/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
      uv2nix,
      pyproject-nix,
      pyproject-build-systems,
      ...
    }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        inherit (nixpkgs) lib;
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python3;
        pythonBase = pkgs.callPackage pyproject-nix.build.packages {inherit python;};
        workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };
        overlay = workspace.mkPyprojectOverlay {sourcePreference = "wheel";};
        pythonSet =
          pythonBase.overrideScope (
            lib.composeManyExtensions [
              pyproject-build-systems.overlays.wheel
              overlay
            ]);
        venv = pythonSet.mkVirtualEnv "venv" workspace.deps.default;
        deps = with pkgs; [
          pkg-config
          stdenv.cc.cc
          stdenv.cc.cc.lib
          zlib.dev
          mypy
          ruff
        ];
      in rec {
        devShells = {
          default = pkgs.mkShell {
            packages = with pkgs; [ uv venv ];
            env = {
              UV_NO_SYNC = "1";
              UV_PYTHON_DOWNLOADS = "never";
            };
            propagatedBuildInputs = deps;
            shellHook = ''
              export LD_LIBRARY_PATH="${lib.makeLibraryPath deps}:$LD_LIBRARY_PATH"
              unset PYTHONPATH
              export REPO_ROOT=$(git rev-parse --show-toplevel)
            '';
          };
        };

        packages =
          let
            inherit (pkgs.callPackages pyproject-nix.build.util { }) mkApplication;
            bbkm = mkApplication {
              inherit venv;
              package = pythonSet.bb-kb-mods;
            };
          in {
            inherit bbkm;
            default = bbkm;
          };
      });
}
