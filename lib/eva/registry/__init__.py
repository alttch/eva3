PFX = 'eva3'

import platform

from eva.tools import ShellConfigFile
from yedb import YEDB

from pathlib import Path

EVA_DIR = Path(__file__).parents[3].absolute()

config_file = EVA_DIR / 'etc/eva_config'

if config_file.exists():
    with ShellConfigFile(config_file.as_posix()) as cf:
        socket_path = cf.get('SOCKET', EVA_DIR / 'var/registry.sock')
        SYSTEM_NAME = cf.get('SYSTEM_NAME', platform.node())


db = YEDB(socket_path)


def key_get(name):
    return db.key_get(key=f'{PFX}/{SYSTEM_NAME}/{name}')


def key_get_recursive(name):
    return db.key_get_recursive(
        key=f'{PFX}/{SYSTEM_NAME}/{name}')


def key_set(name, value, **kwargs):
    return db.key_set(key=f'{PFX}/{SYSTEM_NAME}/{name}',
                      value=value,
                      **kwargs)
