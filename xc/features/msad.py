from eva.features import OS_LIKE, UnsupportedOS, install_system_packages
from eva.features import append_python_libraries, remove_python_libraries
from eva.features import restart_controller

from eva.features import InvalidParameter
from eva.features import ConfigFile


def setup(host=None, domain=None, key_prefix='', ca=None):
    if not host or not domain:
        raise InvalidParameter
    if OS_LIKE == 'debian':
        install_system_packages(
            ['libsasl2-dev', 'libldap2-dev', 'libssl-dev'])
    elif OS_LIKE == 'fedora':
        install_system_packages(['openldap-devel', 'openssl-devel'])
    else:
        raise UnsupportedOS
    append_python_libraries(['easyad==1.0.9'])
    config = {'host': host, 'domain': domain}
    if key_prefix:
        config['key_prefix'] = key_prefix
    if ca:
        config['ca'] = ca
    with ConfigFile('sfa.ini') as fh:
        fh.replace_section('msad', config)
    restart_controller('sfa')


def remove():
    with ConfigFile('sfa.ini') as fh:
        fh.remove_section('msad')
    remove_python_libraries(['easyad==1.0.9'])
    restart_controller('sfa')
