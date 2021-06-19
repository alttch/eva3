from eva.features import OS_ID, OS_LIKE, UnsupportedOS
from eva.features import append_python_libraries, remove_python_libraries
from eva.features import install_system_packages

python_libs = ['python3-netsnmp==1.1a1']


def setup():
    if OS_LIKE == 'debian':
        install_system_packages(['libsnmp-dev'])
    elif OS_LIKE == 'fedora':
        install_system_packages(['net-snmp-devel'])
    elif OS_LIKE == 'alpine':
        install_system_packages(['net-snmp-dev'])
    else:
        raise UnsupportedOS
    append_python_libraries(python_libs)


def remove():
    remove_python_libraries(python_libs)
