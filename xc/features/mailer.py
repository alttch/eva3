from eva.features import restart_controller
from eva.features import InvalidParameter
from eva.features import ConfigFile
from eva.features import is_enabled

from eva.tools import val_to_boolean

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
    ssl = val_to_boolean(ssl)
    tls = val_to_boolean(tls)
    if ssl:
        config['ssl'] = 'yes'
    if tls:
        config['tls'] = 'yes'
    if login:
        config['login'] = login
    if password:
        config['password'] = password
    for c in ['uc', 'lm', 'sfa']:
        if is_enabled(c):
            with ConfigFile(f'{c}.ini') as fh:
                fh.replace_section('mailer', config)
                restart_controller(c)


def remove():
    for c in ['uc', 'lm', 'sfa']:
        if is_enabled(c):
            with ConfigFile(f'{c}.ini') as fh:
                fh.remove_section('mailer')
                restart_controller(c)
