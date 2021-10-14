from eva.features import restart_controller
from eva.features import InvalidParameter
from eva.features import is_enabled
from eva.features import val_to_boolean

import eva.registry

import platform


def setup(smtp=None,
          default_from=None,
          ssl=None,
          tls=None,
          login=None,
          password=None):
    if not smtp:
        raise InvalidParameter
    if not default_from:
        default_from = f'eva@{platform.node()}'
    config = {'smtp': smtp, 'from': default_from}
    config['ssl'] = val_to_boolean(ssl) or False
    config['tls'] = val_to_boolean(tls) or False
    config['login'] = str(login) if login else None
    config['password'] = str(password) if password else None
    eva.registry.key_set('config/common/mailer', config)
    for c in ['uc', 'lm', 'sfa']:
        if is_enabled(c):
            restart_controller(c)


def remove():
    eva.registry.key_delete('config/common/mailer')
