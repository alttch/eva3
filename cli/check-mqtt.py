__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.1"

import sys
import argparse
import logging

logging.basicConfig(level=logging.DEBUG)

from pathlib import Path
sys.path.insert(0, (Path(__file__).absolute().parents[1] / 'lib').as_posix())

import eva.core
import eva.tools
import eva.notify
import eva.api

eva.core.set_product('test', -1)

_me = 'EVA ICS MQTT test version %s' % __version__

ap = argparse.ArgumentParser(description=_me)
ap.add_argument(help='MQTT user:pass@host:port/space',
                dest='_mqtt',
                metavar='MQTT')
ap.add_argument('--cafile', help='CA File', dest='_ca_file', metavar='FILE')
ap.add_argument('--cert', help='Cert file', dest='_cert_file', metavar='FILE')
ap.add_argument('--key', help='Key File', dest='_key_file', metavar='FILE')

try:
    import argcomplete
    argcomplete.autocomplete(ap)
except:
    pass

a = ap.parse_args()

if not a._mqtt:
    ap.print_usage()
    sys.exit(99)

if a._mqtt.find('@') != -1:
    try:
        mqa, mq = a._mqtt.split('@')
        user, password = mqa.split(':')
    except:
        ap.print_usage()
        sys.exit(99)
else:
    mq, user, password = a._mqtt, None, None

if mq.find('/') != -1:
    try:
        x = mq.split('/')
        mq = x[0]
        space = '/'.join(x[1:])
    except:
        ap.print_usage()
        sys.exit(99)
else:
    space = None

mqtt_host, mqtt_port = eva.tools.parse_host_port(mq, 1883)

n = eva.notify.MQTTNotifier(notifier_id='test',
                            host=mqtt_host,
                            port=mqtt_port,
                            space=space,
                            username=user if user else None,
                            password=password if password else None,
                            ca_certs=a._ca_file,
                            certfile=a._cert_file,
                            keyfile=a._key_file)

if n.test():
    print('OK')
else:
    print('FAILED')
    sys.exit(1)
