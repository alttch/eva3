{ stdenv, fetchurl, pkgconfig }:

stdenv.mkDerivation {
  version = "3.2p1";
  name = "libow";

  src = fetchurl {
    url = "http://downloads.sourceforge.net/project/owfs/owfs/3.2p1/owfs-3.2p1.tar.gz";
    sha256 = "1sijb1s1n485gxkz798kbrwpdqyyfc6paznjgiqrm5invcjhn8ik";
  };

  nativeBuildInputs = [ pkgconfig ];

  meta = with stdenv.lib; {
    description = "1-Wire File System full library";
    homepage = http://owfs.org/;
    license = licenses.gpl2;
    platforms = platforms.unix;
  };

  configureFlags = [
      "--disable-owtcl"
      "--disable-owphp"
      "--disable-owpython"
      "--disable-zero"
      "--disable-owshell"
      "--disable-owhttpd"
      "--disable-owftpd"
      "--disable-owserver"
      "--disable-owperl"
      "--disable-owtcl"
      "--disable-owtap"
      "--disable-owmon"
      "--disable-owexternal"
    ];
}

