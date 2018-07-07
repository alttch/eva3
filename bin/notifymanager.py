__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "3.1.0"

import sys
import os
import logging
import getopt

logging.basicConfig(level=logging.WARNING)

dir_lib = os.path.dirname(os.path.realpath(__file__)) + '/../lib'
sys.path.append(dir_lib)

import eva.core
import eva.apikey

from eva.tools import print_json

eva.core.set_product(os.environ['EVA_PRODUCT'], '-1')


def usage():
    print()
    print('EVA notifier manager version %s for %s' %
          (eva.core.version, eva.core.product_code.upper()))
    print()
    print("Usage: %s-notifier <command> [args]" % eva.core.product_code)
    print("""
Available commands:

    list                    list notifiers
    test <-i id>            test specified notifier
    disable <-i id>         disable specified notifier
    enable <-i id>          enable specified notifier

Create notifier:

    create <-i id> <-p type> [-s space] [-t timeout] [args] [-y]

        -p  type (http, http-post, mqtt, db)
        -i  notifier id
        -s  notification space
        -t  timeout
        -y  enable notifier right after creation

    arguments for http notifiers:

        -u  notification uri, required
        -k  notification key

    arguments for mqtt notifiers:
    
        -h  mqtt host, required
        -P  mqtt port, optional
        -A  mqtt authentication (-A username:password)

    arguments for db notifiers:

        -h  database file
        -k  time to keep item state records (in seconds)

Configure notifier:

    get_config <-i id>      get notifier config

    list_props <-i id>      get notifier properties available to set

    set_prop <-i id> <-p property> [-v value]
                            set notifier property, if value is not specified,
                            set property to the default value

                            To set MQTT QoS (Q = 0, 1 or 2)

                            -p qos -v Q          set all QoS subjects
                            -p qos.<subject> -v Q  set specified QoS subject,
                                                 where subject can be: state,
                                                 log or action

    subscribe <-p subject> [args]
                            subscribe notifier to the specified subject,
                            subscription will override the previous one

                            -p log [-L level]    subscribe to the log messages
                                                 of the specified level:

                                                 10 debug
                                                 20 info (default)
                                                 30 warning
                                                 40 error
                                                 50 critical

                            -p state [args]     subscribe to state changes,

                                                 -v for item types (i.e.
                                                 -v unit, sensor, lvar) or
                                                 -v '#' for all item types,

                                                 -g for item groups, comma
                                                 separated(you may also use
                                                 '#' or other mqtt-style
                                                 wildcards)

                                                 -I for the individual items
                                                 which are not in the specified
                                                 groups (i.e. -I item1,item2)

                            -p action [args]     subscribe to action status,
                                                 params are the same as for
                                                 status subscription, plus

                                                 -a for action status
                                                 '#' for all, or
                                                 -a status1,status2.... where
                                                 status can be:

                                                 created,pending,queued,refused
                                                 dead,canceled,ignored,running,
                                                 failed,terminated,completed

                                                 -v type for item types
                                                 (-v '#' for all item types)

                                                 -g for item groups (you
                                                 may also use '#' or other
                                                 mqtt-style wildcards)

                                                 -I for the individual items
                                                 which are not in the specified
                                                 groups (i.e. -I item1,item2)


    unsubscribe [-p subject]
                            unsubscribe from notification subject,
                            if no subject specified, notifier will be
                            unsubscribed from everything

    destroy <-i id>         destroy notifier
    """)


eva.apikey.load()

notifier_id = None
notifier_type = None
prop = None
value = None
notify_key = None
uri = None
host = None
port = None
space = None
timeout = None
username = None
password = None
items = []
groups = []
astatus = []
log_level = None

enable = False

notifier_status = {True: 'Enabled', False: 'Disabled'}

try:
    func = sys.argv[1]
    o, a = getopt.getopt(sys.argv[2:], 'i:p:u:h:P:k:s:t:A:v:I:g:a:L:y')
    for i, v in o:
        if i == '-i':
            notifier_id = v
        elif i == '-p':
            notifier_type = v
            prop = v
        elif i == '-u':
            uri = v
        elif i == '-P':
            port = int(v)
        elif i == '-h':
            host = v
        elif i == '-k':
            notify_key = v
        elif i == '-s':
            space = v
        elif i == '-t':
            timeout = float(v)
        elif i == '-A':
            username, password = v.split(':')
        elif i == '-v':
            value = v
        elif i == '-I':
            items = v.split(',')
        elif i == '-g':
            groups = v.split(',')
        elif i == '-a':
            astatus = v.split(',')
        elif i == '-L':
            log_level = int(v)
        elif i == '-y':
            enable = True
except:
    usage()
    sys.exit(99)

if func == 'list':
    eva.notify.load(test=False, connect=False)
    print('%s %s %s %s' % ('Type'.ljust(15), 'ID'.ljust(15), 'Status'.ljust(12),
                           'Target'))
    print('-' * 78)
    for n in sorted(
            sorted(eva.notify.get_notifiers(), key=lambda k: k.notifier_id),
            key=lambda k: k.notifier_type):
        print(
            '%s %s %s' % (n.notifier_type.ljust(15), n.notifier_id.ljust(15),
                          notifier_status[n.enabled].ljust(12)),
            end='')
        if isinstance(n, eva.notify.HTTPNotifier) or \
                isinstance(n, eva.notify.HTTP_POSTNotifier):
            print(' %s' % n.uri, end='')
        elif isinstance(n, eva.notify.SQLiteNotifier):
            print(' %s' % n.db, end='')
        elif isinstance(n, eva.notify.MQTTNotifier):
            if n.username is not None and n.password is not None:
                print(' %s:%s@' % (n.username, n.password), end='')
            else:
                print(' ', end='')
            print('%s:%u' % (n.host, n.port), end='')
        print()
    print()
    sys.exit()
elif func == 'destroy':
    if notifier_id is None:
        print('notifier id not specified')
        sys.exit(1)
    notifier_fname = eva.core.format_cfg_fname('%s_notify.d/%s.json' % \
            (eva.core.product_code, notifier_id), runtime = True)
    try:
        os.unlink(notifier_fname)
        print('notifier %s destroyed' % notifier_id)
    except:
        print('notifier unknown: %s' % notifier_id)
        sys.exit(1)
    sys.exit()
elif func == 'create':
    eva.notify.load(test=False, connect=False)
    n = eva.notify.get_notifier(notifier_id)
    if n:
        print('notifier %s already exist' % notifier_id)
        sys.exit(1)
    if notifier_id is None:
        print('notifier id not specified')
        sys.exit(1)
    if notifier_type == 'http':
        if not uri:
            print('uri not specified')
            sys.exit(1)
        n = eva.notify.HTTPNotifier(
            notifier_id=notifier_id,
            uri=uri,
            notify_key=notify_key,
            space=space,
            timeout=timeout)
    elif notifier_type == 'http-post':
        if not uri:
            print('uri not specified')
            sys.exit(1)
        n = eva.notify.HTTP_POSTNotifier(
            notifier_id=notifier_id,
            uri=uri,
            notify_key=notify_key,
            space=space,
            timeout=timeout)
    elif notifier_type == 'mqtt':
        if not host:
            print('host not specified')
            sys.exit(1)
        n = eva.notify.MQTTNotifier(
            notifier_id=notifier_id,
            host=host,
            port=port,
            username=username,
            password=password,
            space=space,
            timeout=timeout)
    elif notifier_type == 'db':
        if not host:
            print('database is not specified')
            sys.exit(1)
        if notify_key:
            try:
                keep = int(notify_key)
            except:
                print('keep should be integer number (seconds)')
                sys.exit(1)
        else:
            keep = None
        n = eva.notify.SQLiteNotifier(
            notifier_id=notifier_id, db=host, keep=keep, space=space)
    else:
        if not notifier_type: print('notifier type not specified')
        else: print('notifier type unknown %s' % notifier_type)
        sys.exit(1)
    n.enabled = enable
    eva.notify.append_notifier(n)
    eva.notify.save_notifier(notifier_id)
    print('notifier %s created' % notifier_id)
    sys.exit()

if not notifier_id:
    usage()
    sys.exit(99)

try:
    n = eva.notify.load_notifier(notifier_id, test=False, connect=False)
except:
    print('can not load notifier %s' % notifier_id)
    sys.exit(1)

if func == 'get_config':
    print_json(n.serialize())
    sys.exit()
elif func == 'list_props':
    print_json(n.serialize(props=True))
    sys.exit()
elif func == 'test':
    if n.test(): print('notifier %s test passed' % notifier_id)
    else: print('notifier %s test FAILED' % notifier_id)
    n.disconnect()
    sys.exit(1)

eva.notify.append_notifier(n)

if func == 'disable':
    n.enabled = False
    eva.notify.save_notifier(notifier_id)
    print('notifier %s disabled' % notifier_id)
elif func == 'enable':
    n.enabled = True
    eva.notify.save_notifier(notifier_id)
    print('notifier %s enabled' % notifier_id)
elif func == 'set_prop':
    if not n.set_prop(prop, value):
        print('failed to set property')
        sys.exit(1)
    c = n.serialize(props=True)
    if prop.find('.') == -1: v = c[prop]
    else:
        try:
            a, b = prop.split('.')
            v = c[a][b]
        except:
            v = 'null'
    print('%s.%s = %s' % (notifier_id, prop, v))
    eva.notify.save_notifier(notifier_id)
elif func == 'unsubscribe':
    if prop is None: prop = '#'
    n.unsubscribe(prop.split(','))
    eva.notify.save_notifier(notifier_id)
    print('unsubscribed')
elif func == 'subscribe':
    if value:
        itypes = value.split(',')
    else:
        itypes = []
    if n.subscribe(
            subject=prop,
            items=items,
            groups=groups,
            item_types=itypes,
            action_status=astatus,
            log_level=log_level):
        eva.notify.save_notifier(notifier_id)
        for d in n.serialize()['events']:
            if d['subject'] == prop:
                print_json(d)
    else:
        print('subscribe error')
        sys.exit(2)
else:
    usage()
    sys.exit(99)
