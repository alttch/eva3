with import <nixpkgs> {};
stdenv.mkDerivation {
  name = "evaics.setup";

  buildInputs = [
    pkgs.jq
    pkgs.curl
    pkgs.bash
    pkgs.gcc
    pkgs.pkgconfig
    pkgs.libffi
    pkgs.openssl
    pkgs.zlib
    pkgs.libjpeg
    pkgs.libow
    pkgs.python3
    pkgs.python3Packages.pandas
  ];

  shellHook = ''
    export SOURCE_DATE_EPOCH=315532800
'';
}
