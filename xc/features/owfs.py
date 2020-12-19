from eva.features import OS_ID, OS_LIKE, UnsupportedOS
from eva.features import append_python_libraries, remove_python_libraries
from eva.features import install_system_packages

python_libs = ['onewire==0.2']


def setup():
    if OS_ID == 'rhel':
        raise UnsupportedOS
    elif OS_LIKE == 'debian':
        install_system_packages(['libow-dev'])
    elif OS_LIKE == 'fedora':
        install_system_packages(['owfs-libs', 'owfs-devel'])
    else:
        raise UnsupportedOS
    append_python_libraries(python_libs)


def remove():
    remove_python_libraries(python_libs)
