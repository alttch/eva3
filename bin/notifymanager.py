#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "3.1.0"

import sys
import os
from datetime import datetime

dir_lib = os.path.dirname(os.path.realpath(__file__)) + '/../lib'
sys.path.append(dir_lib)

import eva.core
from eva.client.cli import GenericCLI
from eva.tools import parse_host_port


class NotifierCLI(GenericCLI):

    def add_functions(self):
        super().add_functions()
        self.add_notifier_common_functions()

    def add_notifier_common_functions(self):
        ap_list = self.sp.add_parser('list', help='List notifiers')
        ap_create = self.sp.add_parser('create', help='Create notifier')
        ap_create.add_argument('i', help='Notifier ID', metavar='ID')
        ap_create.add_argument('p', help='Notifier properties: ' + \
                'json:http(s)://[key]@uri or ' + \
                'mqtt:[username:password]@host:[port] or ' + \
                'db:dbfile[:keeptime]', metavar='PROPS')
        ap_create.add_argument(
            '-s',
            '--space',
            help='Notification space',
            metavar='SPACE',
            dest='s')
        ap_create.add_argument(
            '-t',
            '--timeout',
            help='Notifier timeout',
            metavar='SEC',
            dest='t',
            type=float)
        ap_create.add_argument(
            '-y',
            '--enable',
            help='Enable notifier after creation',
            dest='y',
            action='store_true')
        ap_enable = self.sp.add_parser('enable', help='Enable notifier')
        ap_enable.add_argument('i', help='Notifier ID', metavar='NOTIFIER_ID')
        ap_disable = self.sp.add_parser('disable', help='Disable notifier')
        ap_disable.add_argument('i', help='Notifier ID', metavar='NOTIFIER_ID')
        ap_config = self.sp.add_parser('config', help='Get notifier config')
        ap_config.add_argument('i', help='Notifier ID', metavar='NOTIFIER_ID')
        ap_props = self.sp.add_parser('props', help='Get notifier properties')
        ap_props.add_argument('i', help='Notifier ID', metavar='NOTIFIER_ID')
        ap_set_prop = self.sp.add_parser('set', help='Set notifier property')
        ap_set_prop.add_argument('i', help='Notifier ID', metavar='NOTIFIER_ID')
        ap_set_prop.add_argument('p', help='Config property', metavar='PROP')
        ap_set_prop.add_argument('v', help='Value', metavar='VAL', nargs='?')
        ap_test = self.sp.add_parser('test', help='Test notifier')
        ap_test.add_argument('i', help='Notifier ID', metavar='NOTIFIER_ID')

        ap_unsubscribe = self.sp.add_parser(
            'unsubscribe', help='Unsubscribe notifier')
        ap_unsubscribe.add_argument(
            's',
            help='Notification subject (if empty - unsubscribe from all)',
            metavar='SUBJECT',
            nargs='?',
            choices=['log', 'state', 'action'])
        ap_unsubscribe.add_argument(
            'i', help='Notifier ID', metavar='NOTIFIER_ID')

        ap_subscribe = self.sp.add_parser(
            'subscribe', help='Subscribe notifier')
        sp_subscribe = ap_subscribe.add_subparsers(
            dest='_func',
            metavar='topic',
            help='Subscription topics, new topic subscription replaces previous'
        )

        sp_subscribe_log = sp_subscribe.add_parser(
            'log', help='Subscribe to log messages')
        sp_subscribe_log.add_argument(
            'i', help='Notifier ID', metavar='NOTIFIER_ID')
        sp_subscribe_log.add_argument(
            '-l',
            '--level',
            help='Log level (debug, info [default], warning, error or ' + \
                    'critical)',
            dest='l',
            metavar='LEVEL',
            default=20)

        sp_subscribe_state = sp_subscribe.add_parser(
            'state', help='Subscribe to state updates')
        sp_subscribe_state.add_argument(
            'i', help='Notifier ID', metavar='NOTIFIER_ID')
        sp_subscribe_state.add_argument(
            '-v',
            '--types',
            help=
            'Item types, comma separated (unit, sensor, lvar or # ' + \
                    '[default] for all)',
            dest='v',
            metavar='TYPE',
            default='#')
        sp_subscribe_state.add_argument(
            '-i',
            '--items',
            help='Item IDs, comma separated or # for all',
            dest='items',
            metavar='ITEMS')
        sp_subscribe_state.add_argument(
            '-g',
            '--groups',
            help='Item groups, comma separated or # for all',
            dest='g',
            metavar='GROUPS')

        sp_subscribe_action = sp_subscribe.add_parser(
            'action', help='Subscribe to action status')
        sp_subscribe_action.add_argument(
            'i', help='Notifier ID', metavar='NOTIFIER_ID')
        sp_subscribe_action.add_argument(
            '-a',
            '--action-status',
            help=
            'Action status, comma separated (created, pending, queued, ' + \
                    ' refused, dead, canceled, ignored, running, failed, '+ \
                    'terminated, completed or # [default] for all)',
            dest='a',
            metavar='TYPE',
            default='#')
        sp_subscribe_action.add_argument(
            '-v',
            '--types',
            help=
            'Item types, comma separated (unit, sensor, lvar or # [default]' + \
                    'for all)',
            dest='v',
            metavar='TYPE',
            default='#')
        sp_subscribe_action.add_argument(
            '-i',
            '--items',
            help='Item IDs, comma separated or # for all',
            dest='items',
            metavar='ITEMS')
        sp_subscribe_action.add_argument(
            '-g',
            '--groups',
            help='Item groups, comma separated or # for all',
            dest='g',
            metavar='GROUPS')

        ap_destroy = self.sp.add_parser('destroy', help='Destroy notifier')
        ap_destroy.add_argument('i', help='Notifier ID', metavar='NOTIFIER_ID')

    def create_notifier(self, params):
        n = self.get_notifier(params['i'], pass_errors=True)
        if n:
            self.print_err('notifier %s already exists' % params['i'])
            return self.local_func_result_failed
        notifier_id = params['i']
        p = params['p'].split(':')
        space = params.get('s')
        timeout = params.get('t')
        if len(p) < 2: return self.local_func_result_failed
        if p[0] in ['http', 'http-post', 'http-json', 'json']:
            u = (':'.join(p[1:])).split('/')
            if len(u) < 3: return self.local_func_result_failed
            if u[2].find('@') != -1:
                try:
                    notify_key, u[2] = u[2].split('@')
                except:
                    return self.local_func_result_failed
            else:
                notify_key = None
            uri = '/'.join(u)
            if p[0] == 'http':
                n = eva.notify.HTTPNotifier(
                    notifier_id=notifier_id,
                    uri=uri,
                    notify_key=notify_key,
                    space=space,
                    timeout=timeout)
            elif p[0] == 'http-post':
                n = eva.notify.HTTP_POSTNotifier(
                    notifier_id=notifier_id,
                    uri=uri,
                    notify_key=notify_key,
                    space=space,
                    timeout=timeout)
            else:
                n = eva.notify.HTTP_JSONNotifier(
                    notifier_id=notifier_id,
                    uri=uri,
                    notify_key=notify_key,
                    space=space,
                    timeout=timeout)
        elif p[0] == 'mqtt':
            _p = ':'.join(p[1:])
            if _p.find('@') != -1:
                auth = _p.split('@')[0]
                host = _p.split('@')[1]
                username = auth.split(':')[0]
                try:
                    password = auth.split(':')[1]
                except:
                    password = None
            else:
                username = None
                password = None
                host = _p
            host, port = parse_host_port(host)
            n = eva.notify.MQTTNotifier(
                notifier_id=notifier_id,
                host=host,
                port=port,
                username=username,
                password=password,
                space=space,
                timeout=timeout)
        elif p[0] == 'db':
            dbfile = p[1]
            if len(p) > 2:
                try:
                    keep = int(p[2])
                except:
                    return self.local_func_result_failed
            else:
                keep = None
            n = eva.notify.SQLiteNotifier(
                notifier_id=notifier_id, db=dbfile, keep=keep, space=space)
        else:
            self.print_err('notifier type unknown %s' % p[0])
            return self.local_func_result_failed
        n.enabled = True if params.get('y') else False
        eva.notify.append_notifier(n)
        eva.notify.save_notifier(notifier_id)
        return self.local_func_result_ok

    def list_notifiers(self, params):
        eva.notify.load(test=False, connect=False)
        result = []
        for i in sorted(
                sorted(eva.notify.get_notifiers(), key=lambda k: k.notifier_id),
                key=lambda k: k.notifier_type):
            n = {}
            n['id'] = i.notifier_id
            n['type'] = i.notifier_type
            n['enabled'] = i.enabled
            n['params'] = ''
            if isinstance(i, eva.notify.HTTPNotifier) or \
                    isinstance(i, eva.notify.HTTP_POSTNotifier) or \
                    isinstance(i, eva.notify.HTTP_JSONNotifier):
                n['params'] = 'uri: %s ' % i.uri
            elif isinstance(i, eva.notify.SQLiteNotifier):
                n['params'] = 'db: %s' % i.db
            elif isinstance(i, eva.notify.MQTTNotifier):
                if i.username is not None:
                    n['params'] = '%s%s@' % (i.username, ':*'
                                             if i.password else '')
                n['params'] += '%s:%u' % (i.host, i.port)
            result.append(n)
        return 0, result

    def get_notifier(self, notifier_id, pass_errors=False):
        try:
            n = eva.notify.load_notifier(notifier_id, test=False, connect=False)
            return n
        except:
            if not pass_errors:
                self.print_err('can not load notifier %s' % notifier_id)
            return None

    def test_notifier(self, params):
        n = self.get_notifier(params['i'])
        if n and n.test():
            n.disconnect()
            return self.local_func_result_ok
        else:
            return self.local_func_result_failed

    def destroy_notifier(self, params):
        n = self.get_notifier(params['i'])
        if n:
            notifier_fname = eva.core.format_cfg_fname('%s_notify.d/%s.json' % \
                (eva.core.product_code, params['i']), runtime = True)
            try:
                os.unlink(notifier_fname)
            except:
                self.print_err('unable to delete notifier config file')
                return self.local_func_result_failed
            return self.local_func_result_ok
        else:
            return self.local_func_result_failed

    def enable_notifier(self, params):
        return self.set_notifier_enable(params['i'], True)

    def disable_notifier(self, params):
        return self.set_notifier_enable(params['i'], False)

    def set_notifier_enable(self, notifier_id, e):
        n = self.get_notifier(notifier_id)
        if n:
            eva.notify.append_notifier(n)
            n.enabled = e
            eva.notify.save_notifier(notifier_id)
            return self.local_func_result_ok
        else:
            return self.local_func_result_failed

    def get_notifier_config(self, params):
        n = self.get_notifier(params['i'])
        return 0, n.serialize() if n else None

    def list_notifier_props(self, params):
        n = self.get_notifier(params['i'])
        return 0, n.serialize(props=True) if n else None

    def set_notifier_prop(self, params):
        n = self.get_notifier(params['i'])
        prop = params.get('p')
        value = params.get('v')
        if not n or not n.set_prop(prop, value):
            return self.local_func_result_failed
        eva.notify.append_notifier(n)
        c = n.serialize(props=True)
        if prop.find('.') == -1: v = c[prop]
        else:
            try:
                a, b = prop.split('.')
                v = c[a][b]
            except:
                v = 'null'
        print(
            self.colored(
                '%s.%s' % (params['i'], prop), color='blue', attrs=['bold']),
            end='')
        print(' = ', end='')
        print(self.colored(v, color='yellow'))
        eva.notify.save_notifier(params['i'])
        return self.local_func_result_ok

    def subscribe_notifier_log(self, params):
        level = params.get('l')
        if not level: level = 20
        else:
            try: level = int(level)
            except:
                try:
                    level = int(self.get_log_level_code(level))
                except:
                    self.print_err('Invalid log level: %s' % level)
                    return self.local_func_result_failed
        n = self.get_notifier(params['i'])
        if not n or not n.subscribe(subject='log', log_level=level):
            return self.local_func_result_failed
        eva.notify.append_notifier(n)
        eva.notify.save_notifier(params['i'])
        for d in n.serialize()['events']:
            if d['subject'] == 'log':
                return 0, d
        return self.local_func_result_failed

    def subscribe_notifier_state(self, params):
        n = self.get_notifier(params['i'])
        if not n or not n.subscribe(
                subject='state',
                item_types=params['v'].split(',') if params.get('v') else None,
                items=params['items'].split(',')
                if params.get('items') else None,
                groups=params['g'].split(',') if params.get('g') else None):
            return self.local_func_result_failed
        eva.notify.append_notifier(n)
        eva.notify.save_notifier(params['i'])
        for d in n.serialize()['events']:
            if d['subject'] == 'state':
                return 0, d
        return self.local_func_result_failed

    def subscribe_notifier_action(self, params):
        n = self.get_notifier(params['i'])
        if not n or not n.subscribe(
                subject='action',
                action_status=params['a'].split(',')
                if params.get('a') else None,
                item_types=params['v'].split(',') if params.get('v') else None,
                items=params['items'].split(',')
                if params.get('items') else None,
                groups=params['g'].split(',') if params.get('g') else None):
            return self.local_func_result_failed
        eva.notify.append_notifier(n)
        eva.notify.save_notifier(params['i'])
        for d in n.serialize()['events']:
            if d['subject'] == 'action':
                return 0, d
        return self.local_func_result_failed

    def unsubscribe_notifier(self, params):
        n = self.get_notifier(params['i'])
        if not n or not n.unsubscribe(params['s'] if params.get('s') else '#'):
            return self.local_func_result_failed
        eva.notify.append_notifier(n)
        eva.notify.save_notifier(params['i'])
        return self.local_func_result_ok


product = os.environ['EVA_PRODUCT']

_me = 'EVA ICS Notification System Manager CLI for %s version %s' % (
    product.upper(), __version__)

cli = NotifierCLI(
    '%s_notifier' % product,
    _me,
    remote_api=False,
    prog='%s-notifier' % product)

_api_functions = {
    'list': cli.list_notifiers,
    'test': cli.test_notifier,
    'destroy': cli.destroy_notifier,
    'create': cli.create_notifier,
    'enable': cli.enable_notifier,
    'disable': cli.disable_notifier,
    'config': cli.get_notifier_config,
    'props': cli.list_notifier_props,
    'set': cli.set_notifier_prop,
    'unsubscribe': cli.unsubscribe_notifier,
    'subscribe:log': cli.subscribe_notifier_log,
    'subscribe:state': cli.subscribe_notifier_state,
    'subscribe:action': cli.subscribe_notifier_action
}

_pd_cols = {'list_notifiers': ['id', 'type', 'enabled', 'params']}

_pd_idx = {
    'list_keys': 'key_id',
    'list_users': 'user',
    'state': 'oid',
    'list': 'oid',
    'result': 'time',
    'list_phi_mods': 'mod',
    'list_lpi_mods': 'mod'
}

_fancy_tabsp = {'list_props': 26, 'get_phi': 14, 'get_driver': 12}

_always_json = ['get_notifier_config']

eva.core.set_product(product, '-1')
cli.ap.prog = '%s-notifier' % product
cli.always_json += _always_json
cli.arg_sections += ['subscribe']
cli.set_api_functions(_api_functions)
cli.set_pd_cols(_pd_cols)
cli.set_pd_idx(_pd_idx)
cli.set_fancy_tabsp(_fancy_tabsp)
code = cli.run()
sys.exit(code)
