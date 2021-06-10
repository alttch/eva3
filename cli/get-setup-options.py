__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.3.3"

import sys
import os
import getopt

from pathlib import Path
sys.path.insert(0, (Path(__file__).absolute().parents[1] / 'lib').as_posix())

os.environ['EVA_DIR'] = Path(__file__).absolute().parents[1].as_posix()

import eva.core
import eva.notify
import eva.api
import eva.apikey

try:
    product_code = sys.argv[1]
except:
    print("no product provided")
    sys.exit(1)

eva.core.init()
eva.core.set_product(product_code, '-1')

eva.core.load(initial=True, check_pid=False, omit_plugins=True)
eva.core.start(init_db_only=True)

eva.apikey.load(load_from_db=True)
eva.notify.load(test=False, connect=False)

print('MASTERKEY=' + (eva.apikey.get_masterkey(
) if eva.apikey.get_masterkey() is not None else ''))
print('REMOTES=', end='')
if eva.apikey.get_masterkey():
    print(','.join(
        eva.apikey.keys.get(eva.apikey.get_masterkey()).serialize().get(
            'hosts_allow', '')))
else:
    print('')
key = eva.apikey.key_by_id('default')
print('DEFAULTKEY=' + (key if key is not None else ''))
key = eva.apikey.key_by_id('operator')
print('OPKEY=' + (key if key is not None else ''))
n = eva.notify.get_notifier('eva_1')
if n:
    data = n.serialize()
    print('MQTT_HOST=' + data.get('host', ''))
    print('MQTT_PORT=' + str(data.get('port', '')))
    print('MQTT_USER=' + data.get('username', ''))
    print('MQTT_PASSWORD=' + data.get('password', ''))
    print('MQTT_SPACE=' + data.get('space', ''))
    print('MQTT_CAFILE=' + data.get('ca_certs', ''))
    print('MQTT_CERT=' + data.get('certfile', ''))
    print('MQTT_KEY=' + data.get('keyfile', ''))
    print('MQTT_NO_RETAIN=' + ('' if data.get('retain_enabled') else '1'))
    print('MQTT_ANNOUNCE_ENABLED=' +
          ('1' if data.get('announce_interval', 0) > 0 else '0'))
