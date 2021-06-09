from eva.features import OS_ID, OS_LIKE, UnsupportedOS
from eva.features import append_python_libraries, remove_python_libraries
from eva.features import install_system_packages

from eva.tools import val_to_boolean

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
            raise UnsupportedOS
    append_python_libraries(python_libs)


def remove():
    remove_python_libraries(python_libs)
