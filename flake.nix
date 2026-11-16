{
  description = "Ripley development environment and local runner";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "aarch64-darwin" "x86_64-darwin" "aarch64-linux" "x86_64-linux" ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
      pythonFor = pkgs: pkgs.python3.withPackages (ps: with ps; [
        flask flask-socketio requests beautifulsoup4 psutil pytest
        (buildPythonPackage {
          pname = "python-qbittorrent";
          version = "0.4.3";
          pyproject = true;
          src = pkgs.fetchurl {
            url = "https://files.pythonhosted.org/packages/86/25/a5ad35ad229c8016a8c98327495e649cb795be2fda63f8cace6c9a739af7/python-qbittorrent-0.4.3.tar.gz";
            sha256 = "4e22cf89890628b054a60aa4bd1161a68c2b0fad48ef0886fa4d325e69d3828a";
          };
          build-system = [ setuptools ];
          dependencies = [ requests ];
          pythonImportsCheck = [ "qbittorrent" ];
        })
      ]);
    in {
      packages = forAllSystems (system:
        let pkgs = import nixpkgs { inherit system; }; in {
          default = pkgs.writeShellApplication {
            name = "ripley";
            runtimeInputs = [ (pythonFor pkgs) ];
            text = ''
              export JCW_HOST="''${JCW_HOST:-127.0.0.1}"
              export JCW_PORT="''${JCW_PORT:-8080}"
              exec python ${self}/jcw.py
            '';
          };
        });
      devShells = forAllSystems (system:
        let pkgs = import nixpkgs { inherit system; }; in {
          default = pkgs.mkShell {
            packages = [ (pythonFor pkgs) ];
            JCW_HOST = "127.0.0.1";
            JCW_PORT = "8080";
          };
        });
    };
}
