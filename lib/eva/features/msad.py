from eva.features import OS_LIKE, UnsupportedOS, install_system_packages
from eva.features import append_python_libraries, remove_python_libraries
from eva.features import restart_controller, is_enabled

from eva.features import InvalidParameter, FunctionFailed

import eva.registry

python_libs = ['easyad==1.0.9']


def setup(host=None, domain=None, key_prefix='', ca=None, cache_time=None):
    if not is_enabled('sfa'):
        raise FunctionFailed('SFA is not enabled')
    if not host or not domain:
        raise InvalidParameter
    if cache_time:
        try:
            cache_time = int(cache_time)
        except:
            raise InvalidParameter('cache_time is not a number')
    if OS_LIKE == 'debian':
        install_system_packages(['libsasl2-dev', 'libldap2-dev', 'libssl-dev'])
    elif OS_LIKE == 'fedora':
        install_system_packages(['openldap-devel', 'openssl-devel'])
    elif OS_LIKE == 'alpine':
        install_system_packages(['openldap-dev'])
    else:
        raise UnsupportedOS
    append_python_libraries(python_libs)
    config = {'host': host, 'domain': domain}
    if key_prefix:
        config['key-prefix'] = key_prefix
    if ca:
        config['ca'] = ca
    if cache_time and cache_time > 0:
        config['cache-time'] = cache_time
    eva.registry.key_set_field('config/sfa/main', 'msad', config)
    restart_controller('sfa')


def remove():
    if not is_enabled('sfa'):
        raise FunctionFailed('SFA is not enabled')
    eva.registry.key_delete_field('config/sfa/main', 'msad')
    remove_python_libraries(python_libs)
    restart_controller('sfa')
