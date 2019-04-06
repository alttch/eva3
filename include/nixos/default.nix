with import <nixpkgs> {};
stdenv.mkDerivation {
  name = "evaics";

  buildInputs = [
    pkgs.jq
    pkgs.curl
    pkgs.bash
    pkgs.python3
    pkgs.python3Packages.pandas
  ];

  shellHook = ''
    PATH=/opt/eva/bin:$PATH
'';
}
