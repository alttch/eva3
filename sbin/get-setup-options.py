#!/usr/bin/env python3

__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.0"

import sys
import os
import getopt

dir_lib = os.path.dirname(os.path.realpath(__file__)) + '/../lib'
sys.path.append(dir_lib)

os.environ['EVA_DIR'] = os.path.dirname(os.path.realpath(__file__)) + '/..'

import eva.sysapi
import eva.core
import eva.traphandler
import eva.udpapi
import eva.notify
import eva.api
import eva.apikey
import eva.uc.controller
import eva.uc.ucapi
import eva.logs

import eva.runner
import eva.wsapi

try:
    product_code = sys.argv[1]
except:
    print("no product provided")
    sys.exit(1)

eva.core.init()
eva.core.set_product(product_code, '-1')

eva.apikey.load(load_from_db=False)
eva.notify.load(test=False, connect=False)

print('MASTERKEY=' + (eva.apikey.get_masterkey()
                      if eva.apikey.get_masterkey() is not None else ''))
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
    print('MQTT_ANNOUNCE_ENABLED=' +
          ('1' if data.get('announce_interval', 0) > 0 else '0'))
