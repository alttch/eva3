from eva.features import InvalidParameter, dir_eva, FunctionFailed
from eva.features import restart_controller, val_to_boolean
from eva.features import append_python_libraries, is_enabled

import eva.registry

import os


def check_file(fname):
    if fname is None:
        raise InvalidParameter
    if not fname.startswith('/'):
        fname = f'{dir_eva}/etc/{fname}'
    if not os.path.isfile(fname) and not os.path.islink(fname):
        raise InvalidParameter(f'No such file: {fname}')


def setup(controller=None,
          cert=None,
          key=None,
          listen=None,
          module=None,
          chain=None,
          redirect=None):
    if controller not in ['uc', 'lm', 'sfa']:
        raise InvalidParameter
    if not is_enabled(controller):
        raise FunctionFailed(f'{controller} is not enebled')
    if listen is None or ':' not in listen:
        raise InvalidParameter
    if module is None:
        module = 'builtin'
    if module not in ['builtin', 'pyopenssl']:
        raise InvalidParameter
    if module == 'pyopenssl':
        append_python_libraries(['pyopenssl==20.0.1'])
    if redirect is not None:
        redirect = val_to_boolean(redirect)
        if redirect is None:
            raise InvalidParameter
    for f in [cert, key]:
        check_file(f)
    if chain:
        check_file(chain)
    cfg = f'config/{controller}/main'
    eva.registry.key_set_field(cfg, 'webapi/ssl-listen', listen)
    eva.registry.key_set_field(cfg, 'webapi/ssl-cert', cert)
    eva.registry.key_set_field(cfg, 'webapi/ssl-key', key)
    if module:
        eva.registry.key_set_field(cfg, 'webapi/ssl-module', module)
    if chain:
        eva.registry.key_set_field(cfg, 'webapi/ssl-chain', chain)
    if redirect is not None:
        eva.registry.key_set_field(cfg, 'webapi/ssl-force-redirect', redirect)
    restart_controller(controller)


def remove(controller=None):
    if controller not in ['uc', 'lm', 'sfa']:
        raise InvalidParameter
    if not is_enabled(controller):
        raise FunctionFailed(f'{controller} is not enebled')
    for field in [
            'ssl-listen', 'ssl-module', 'ssl-cert', 'ssl-key', 'ssl-chain',
            'ssl-force-redirect'
    ]:
        eva.registry.key_delete_field(f'config/{controller}/main',
                                      f'webapi/{field}')
    restart_controller(controller)
