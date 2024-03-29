__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.2"

PFX = 'eva3'

import platform
import logging
import sys

from eva.tools import ShellConfigFile

from pathlib import Path

from pyaltt2.config import Config

EVA_DIR = Path(__file__).parents[3].absolute()
DEFAULTS_DIR = Path(__file__).parent / 'defaults'
SCHEMA = Path(__file__).parent / 'schema.yml'
VENV_SCHEMA = Path(__file__).parent / 'schema-venv.yml'

config_file = EVA_DIR / 'etc/eva_config'

if config_file.exists():
    with ShellConfigFile(config_file.as_posix()) as cf:
        try:
            socket_path = cf.get('YEDB_SOCKET', EVA_DIR / 'var/registry.sock')
            SYSTEM_NAME = cf.get('SYSTEM_NAME', platform.node())
            timeout = float(cf.get("YEDB_TIMEOUT", 5))
        except Exception as e:
            from neotermcolor import cprint
            cprint(f'REGISTRY CONFIGURATION: {e}', color='red', attrs='bold')
            raise
else:
    socket_path = EVA_DIR / 'var/registry.sock'
    timeout = 5
    SYSTEM_NAME = platform.node()

from yedb import YEDB, FieldNotFound, SchemaValidationError
db = YEDB(socket_path, timeout=timeout)

from functools import wraps


def raise_critical(e):
    if 'eva.core' in sys.modules:
        import eva.core
        if isinstance(e, SchemaValidationError):
            logging.error(f'Schema validation error {e}')
            raise
        else:
            logging.critical('REGISTRY SERVER ERROR')
            eva.core.log_traceback()
            eva.core.critical()
            raise
    else:
        from neotermcolor import cprint
        cprint('REGISTRY SERVER ERROR', color='red', attrs='bold')
        raise


def safe(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (KeyError, ValueError, FieldNotFound):
            raise
        except Exception as e:
            raise_critical(e)

    return wrapper


def config_get(key, **kwargs):
    """
    Get key as configuration object
    """
    return Config(key_get(key, **kwargs), read_file=None)


def safe_purge():
    """
    Purge database, keep broken keys
    """
    return db.safe_purge()


@safe
def key_get(key, default=KeyError):
    """
    Get key
    """
    try:
        return db.key_get(key=f'{PFX}/{SYSTEM_NAME}/{key}')
    except KeyError:
        if default is KeyError:
            raise
        else:
            return default


@safe
def key_get_field(key, field, default=KeyError):
    """
    Get key field
    """
    try:
        return db.key_get_field(key=f'{PFX}/{SYSTEM_NAME}/{key}', field=field)
    except (KeyError, FieldNotFound) as e:
        if default is KeyError:
            raise KeyError(str(e))
        else:
            return default


@safe
def key_get_recursive(key):
    """
    Get keys recursive as [(key, value)] list
    """
    _key = f'{PFX}/{SYSTEM_NAME}/{key}'
    l = len(_key) + 1
    try:
        for k, v in db.key_get_recursive(key=_key):
            yield k[l:], v
    except (KeyError, ValueError, FieldNotFound):
        raise
    except Exception as e:
        raise_critical(e)


@safe
def key_increment(key):
    """
    Increment key value
    """
    return db.key_increment(key=f'{PFX}/{SYSTEM_NAME}/{key}')


@safe
def key_decrement(key):
    """
    Decrement key value
    """
    return db.key_increment(key=f'{PFX}/{SYSTEM_NAME}/{key}')


@safe
def get_subkeys(key):
    """
    Get keys recursive as a dict
    """
    _key = f'{PFX}/{SYSTEM_NAME}/{key}'
    l = len(_key) + 1
    return {k[l:]: v for k, v in db.key_get_recursive(key=_key)}


@safe
def key_set(key, value, **kwargs):
    """
    Set key
    """
    return db.key_set(key=f'{PFX}/{SYSTEM_NAME}/{key}', value=value, **kwargs)


@safe
def key_set_field(key, field, value, **kwargs):
    """
    Set key field
    """
    return db.key_set_field(key=f'{PFX}/{SYSTEM_NAME}/{key}',
                            field=field,
                            value=value,
                            **kwargs)


@safe
def key_delete(key):
    """
    Delete key
    """
    return db.key_delete(key=f'{PFX}/{SYSTEM_NAME}/{key}')


@safe
def key_delete_recursive(key):
    """
    Delete keys recursive
    """
    return db.key_delete_recursive(key=f'{PFX}/{SYSTEM_NAME}/{key}')


@safe
def key_delete_field(key, field, **kwargs):
    """
    Delete key field
    """
    return db.key_delete_field(key=f'{PFX}/{SYSTEM_NAME}/{key}',
                               field=field,
                               **kwargs)


@safe
def key_import(key, fh):
    """
    Import key from stream or file
    """
    import yaml
    if isinstance(fh, str):
        with open(fh) as f:
            data = f.read()
    else:
        data = fh.read()
    key_set(key, yaml.safe_load(data))


@safe
def key_as_dict(key, **kwargs):
    """
    Work with key as with a dict

    with key_as_dict(key): ...
    """
    return db.key_as_dict(key=f'{PFX}/{SYSTEM_NAME}/{key}', **kwargs)


def init_defaults(skip_existing=True):
    import yaml
    import os
    key_delete('data/info')
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
    version = os.popen(f'{EVA_DIR}/sbin/eva-tinyapi -V').read().strip()
    build = int(os.popen(f'{EVA_DIR}/sbin/eva-tinyapi -B').read().strip())
    key_set('data/info', {'version': __version__, 'build': build})


def import_schema():
    import yaml
    with VENV_SCHEMA.open() as fh:
        key = f'.schema/{PFX}/{SYSTEM_NAME}/config/venv'
        logging.info(f'Importing schema {key}')
        db.key_set(key=f'{key}', value=yaml.safe_load(fh))
    with SCHEMA.open() as fh:
        data = yaml.safe_load(fh)
    for k, v in data.items():
        key = f'.schema/{PFX}/{SYSTEM_NAME}/{k}'
        logging.info(f'Importing schema {key}')
        db.key_set(key=f'{key}', value=v)
