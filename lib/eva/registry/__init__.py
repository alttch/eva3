PFX = 'eva3'

import platform
import logging
import sys

from eva.tools import ShellConfigFile
from yedb import YEDB, FieldNotFound

from pathlib import Path

from pyaltt2.config import Config

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
        except (KeyError, ValueError, FieldNotFound):
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


def config_get(key, **kwargs):
    return Config(key_get(key, **kwargs))


@safe
def key_get(key, default=KeyError):
    try:
        return db.key_get(key=f'{PFX}/{SYSTEM_NAME}/{key}')
    except KeyError:
        if default is KeyError:
            raise
        else:
            return default


@safe
def key_get_field(key, field, default=KeyError):
    try:
        return db.key_get_field(key=f'{PFX}/{SYSTEM_NAME}/{key}', field=field)
    except KeyError:
        if default is KeyError:
            raise
        else:
            return default


@safe
def key_get_recursive(key):
    return db.key_get_recursive(key=f'{PFX}/{SYSTEM_NAME}/{key}')


@safe
def key_increment(key):
    return db.key_increment(key=f'{PFX}/{SYSTEM_NAME}/{key}')


@safe
def key_decrement(key):
    return db.key_increment(key=f'{PFX}/{SYSTEM_NAME}/{key}')


@safe
def get_subkeys(key):
    _key = f'{PFX}/{SYSTEM_NAME}/{key}'
    l = len(_key) + 1
    return {k[l:]: v for k, v in db.key_get_recursive(key=_key)}


@safe
def key_set(key, value, **kwargs):
    return db.key_set(key=f'{PFX}/{SYSTEM_NAME}/{key}', value=value, **kwargs)


@safe
def key_set_field(key, field, value, **kwargs):
    return db.key_set_field(key=f'{PFX}/{SYSTEM_NAME}/{key}',
                            field=field,
                            value=value,
                            **kwargs)


@safe
def key_delete(key):
    return db.key_delete(key=f'{PFX}/{SYSTEM_NAME}/{key}')


@safe
def key_delete_field(key, field, **kwargs):
    return db.key_delete_field(key=f'{PFX}/{SYSTEM_NAME}/{key}',
                               field=field,
                               **kwargs)


@safe
def key_as_dict(key, **kwargs):
    return db.key_as_dict(key=f'{PFX}/{SYSTEM_NAME}/{key}', **kwargs)


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
