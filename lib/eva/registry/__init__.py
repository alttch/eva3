PFX = 'eva3'

import platform
import logging
import sys

from eva.tools import ShellConfigFile
from yedb import YEDB

from pathlib import Path

EVA_DIR = Path(__file__).parents[3].absolute()
DEFAULTS_DIR = Path(__file__).parent / 'defaults'

config_file = EVA_DIR / 'etc/eva_config'

if config_file.exists():
    with ShellConfigFile(config_file.as_posix()) as cf:
        socket_path = cf.get('SOCKET', EVA_DIR / 'var/registry.sock')
        SYSTEM_NAME = cf.get('SYSTEM_NAME', platform.node())
else:
    socket_path = EVA_DIR / 'var/registry.sock'
    SYSTEM_NAME = platform.node()

db = YEDB(socket_path)

from functools import wraps


def safe(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (KeyError, ValueError):
            raise
        except:
            if 'eva.core' in sys.modules:
                import eva.core
                logging.crticial('REGISTRY SERVER ERROR')
                eva.core.critical()
            else:
                from neotermcolor import cprint
                cprint('REGISTRY SERVER ERROR', color='red', attrs='bold')
                raise

    return wrapper


@safe
def key_get(name, default=KeyError):
    try:
        return db.key_get(key=f'{PFX}/{SYSTEM_NAME}/{name}')
    except KeyError:
        if default is KeyError:
            raise
        else:
            return default


@safe
def key_get_field(name, field, default=KeyError):
    try:
        return db.key_get_field(key=f'{PFX}/{SYSTEM_NAME}/{name}', field=field)
    except KeyError:
        if default is KeyError:
            raise
        else:
            return default


@safe
def key_get_recursive(name):
    return db.key_get_recursive(key=f'{PFX}/{SYSTEM_NAME}/{name}')


@safe
def key_set(name, value, **kwargs):
    return db.key_set(key=f'{PFX}/{SYSTEM_NAME}/{name}', value=value, **kwargs)


@safe
def key_set_field(name, field, value, **kwargs):
    return db.key_set_field(key=f'{PFX}/{SYSTEM_NAME}/{name}',
                            field=field,
                            value=value,
                            **kwargs)


@safe
def key_as_dict(name, **kwargs):
    return db.key_as_dict(key=f'{PFX}/{SYSTEM_NAME}/{name}', **kwargs)


def init_defaults(skip_existing=True):
    import yaml
    l = len(DEFAULTS_DIR.as_posix()) + 1
    for f in DEFAULTS_DIR.glob('**/*.yml'):
        key = f.as_posix()[l:].rsplit('.', 1)[0]
        need_rewrite = True
        if skip_existing:
            try:
                key_get(key)
                need_rewrite = False
            except KeyError:
                pass
        if need_rewrite:
            with f.open() as fh:
                logging.info(f'Setting key {key} to defaults from {f}')
                data = yaml.safe_load(fh)
                key_set(key, data)
