PFX = 'eva3'

import sys
import os
import eva.core

from eva.tools import ShellConfigFile
from yedb import YEDB

config_file = f'{eva.core.dir_etc}/eva_registry'
socket_path = f'{eva.core.dir_var}/registry.sock'

if os.path.exists(config_file):
    with ShellConfigFile(config_file) as cf:
        try:
            socket_path = cf.get('SOCKET')
        except KeyError:
            pass

db = YEDB(socket_path)


def key_get(name):
    return db.key_get(key=f'{PFX}/{eva.core.config.system_name}/{name}')


def key_get_recursive(name):
    return db.key_get_recursive(
        key=f'{PFX}/{eva.core.config.system_name}/{name}')


def key_set(name, value, **kwargs):
    return db.key_set(key=f'{PFX}/{eva.core.config.system_name}/{name}',
                      value=value,
                      **kwargs)
