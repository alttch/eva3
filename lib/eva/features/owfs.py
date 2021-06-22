from eva.features import OS_ID, OS_LIKE, UnsupportedOS
from eva.features import append_python_libraries, remove_python_libraries
from eva.features import install_system_packages, build_system_package
from eva.features import val_to_boolean

from pathlib import Path

python_libs = ['onewire==0.2']


def setup(python_lib_only=None):
    if python_lib_only is not None:
        python_lib_only = val_to_boolean(python_lib_only)
    if not python_lib_only:
        if OS_ID in ['rhel', 'centos']:
            raise UnsupportedOS(kb='KB00003')
        elif OS_LIKE == 'debian':
            install_system_packages(['libow-dev'])
        elif OS_LIKE == 'fedora':
            install_system_packages(['owfs-libs', 'owfs-devel'])
        else:
            if not Path('/usr/include/owcapi.h').exists() and not Path(
                    '/usr/local/include/owcapi.h').exists():
                build_system_package(
                    src=
                    'https://github.com/owfs/owfs/releases/download/v3.2p4/owfs-3.2p4.tar.gz',
                    sha256=
                    'af0a5035f3f3df876ca15aea13486bfed6b3ef5409dee016db0be67755c35fcc',
                    tdir='owfs-3.2p4',
                    configure_args=[
                        '--prefix=/usr', '--disable-owtcl', '--disable-owphp',
                        '--disable-owpython', '--disable-zero',
                        '--disable-owshell', '--disable-owhttpd',
                        '--disable-owftpd', '--disable-owserver',
                        '--disable-owperl', '--disable-owtap',
                        '--disable-owmon', '--disable-owexternal'
                    ],
                    update_ld=True)
    append_python_libraries(python_libs)


def remove():
    remove_python_libraries(python_libs)
