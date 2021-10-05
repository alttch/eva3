__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.2"

import sys
import os
import argparse
import textwrap
from datetime import datetime

from pathlib import Path
sys.path.insert(0, (Path(__file__).absolute().parents[1] / 'lib').as_posix())

import eva.core
import eva.notify
import eva.registry

from eva.client.cli import GenericCLI
from eva.client.cli import ControllerCLI
from eva.client.cli import ComplGeneric

from pyaltt2 import logs

import logging

logs.init(formatter=logging.Formatter('%(message)s'),
          level=logging.WARNING,
          tracebacks=True)


class NotifierCLI(GenericCLI, ControllerCLI):

    class ComplNProto(object):

        def __call__(self, prefix, **kwargs):
            return [
                    'mqtt:', 'gcpiot:', 'json:',
                    'db:', 'influxdb:', 'prometheus:'] if \
                    prefix and prefix.find(':') == -1 else True

    class ComplN(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call('list')
            if code:
                return True
            result = set()
            for v in data:
                result.add(v['id'])
            return list(result)

    class ComplNProp(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call(['props', kwargs.get('parsed_args').i])
            if code:
                return True
            result = list(data.keys())
            return result

    def setup_parser(self):
        super().setup_parser()
        self.enable_controller_management_functions(eva.core.product.code)

    def prepare_run(self, *args, **kwargs):
        from pyaltt2 import logs
        logs.config.colorize = self.can_colorize()

    def prepare_result_dict(self, data, api_func, itype):
        if api_func != 'status_controller':
            return super().prepare_result_dict(data, api_func, itype)
        return self.prepare_controller_status_dict(data)

    def add_functions(self):
        import eva.core
        import eva.notify
        super().add_functions()
        self.add_notifier_common_functions()

    def add_notifier_common_functions(self):
        ap_list = self.sp.add_parser('list', help='List notifiers')
        ap_create = self.sp.add_parser(
            'create',
            help='Create notifier',
            formatter_class=argparse.RawTextHelpFormatter)
        ap_create.add_argument('i', help='Notifier ID', metavar='ID')
        ap_create.add_argument('p',
                               help=textwrap.dedent('''
        Notifier properties:
            json:http(s)://[key]@uri[#jsonrpc|#list]
            mqtt:[username:password]@host:[port]
            gcpiot:project_id/region/registry
            db:db_uri
            timescaledb:db_uri
            udp:host:port
            influxdb:http(s)://uri#[org/]database
            prometheus:'''),
                               metavar='PROPS').completer = self.ComplNProto()
        ap_create.add_argument('-s',
                               '--space',
                               help='Notification space',
                               metavar='SPACE',
                               dest='s')
        ap_create.add_argument('-t',
                               '--timeout',
                               help='Notifier timeout',
                               metavar='SEC',
                               dest='t',
                               type=float)
        ap_create.add_argument('-y',
                               '--enable',
                               help='Enable notifier after creation',
                               dest='y',
                               action='store_true')
        ap_enable = self.sp.add_parser('enable', help='Enable notifier')
        ap_enable.add_argument(
            'i', help='Notifier ID',
            metavar='NOTIFIER_ID').completer = self.ComplN(self)
        ap_disable = self.sp.add_parser('disable', help='Disable notifier')
        ap_disable.add_argument(
            'i', help='Notifier ID',
            metavar='NOTIFIER_ID').completer = self.ComplN(self)
        ap_config = self.sp.add_parser('config', help='Get notifier config')
        ap_config.add_argument(
            'i', help='Notifier ID',
            metavar='NOTIFIER_ID').completer = self.ComplN(self)
        ap_props = self.sp.add_parser('props', help='Get notifier properties')
        ap_props.add_argument(
            'i', help='Notifier ID',
            metavar='NOTIFIER_ID').completer = self.ComplN(self)
        ap_set_prop = self.sp.add_parser('set', help='Set notifier property')
        ap_set_prop.add_argument(
            'i', help='Notifier ID',
            metavar='NOTIFIER_ID').completer = self.ComplN(self)
        ap_set_prop.add_argument(
            'p', help='Config property',
            metavar='PROP').completer = self.ComplNProp(self)
        ap_set_prop.add_argument('v', help='Value', metavar='VAL', nargs='?')
        ap_test = self.sp.add_parser('test', help='Test notifier')
        ap_test.add_argument(
            'i', help='Notifier ID',
            metavar='NOTIFIER_ID').completer = self.ComplN(self)

        ap_subscribe = self.sp.add_parser('subscribe',
                                          help='Subscribe notifier')
        sp_subscribe = ap_subscribe.add_subparsers(
            dest='_func',
            metavar='topic',
            help='Subscription topics, new topic subscription replaces previous'
        )

        sp_subscribe_log = sp_subscribe.add_parser(
            'log', help='Subscribe to log messages')
        sp_subscribe_log.add_argument(
            'i', help='Notifier ID',
            metavar='NOTIFIER_ID').completer = self.ComplN(self)
        sp_subscribe_log.add_argument(
            '-l',
            '--level',
            help='Log level (debug, info [default], warning, error or ' + \
                    'critical)',
            dest='l',
            metavar='LEVEL',
            default=20)

        sp_subscribe_server = sp_subscribe.add_parser(
            'server', help='Subscribe to server events')
        sp_subscribe_server.add_argument(
            'i', help='Notifier ID',
            metavar='NOTIFIER_ID').completer = self.ComplN(self)

        sp_subscribe_state = sp_subscribe.add_parser(
            'state', help='Subscribe to state updates')
        sp_subscribe_state.add_argument(
            'i', help='Notifier ID',
            metavar='NOTIFIER_ID').completer = self.ComplN(self)
        sp_subscribe_state.add_argument(
            '-p',
            '--types',
            help=
            'Item types, comma separated (unit, sensor, lvar or # ' + \
                    '[default] for all)',
            dest='p',
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
            'i', help='Notifier ID',
            metavar='NOTIFIER_ID').completer = self.ComplN(self)
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
            '-p',
            '--types',
            help=
            'Item types, comma separated (unit, sensor, lvar or # [default]' + \
                    'for all)',
            dest='p',
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

        ap_unsubscribe = self.sp.add_parser('unsubscribe',
                                            help='Unsubscribe notifier')
        ap_unsubscribe.add_argument(
            's',
            help='Notification subject (if empty - unsubscribe from all)',
            metavar='SUBJECT',
            nargs='?',
            choices=['log', 'state', 'action', 'server'])
        ap_unsubscribe.add_argument(
            'i', help='Notifier ID',
            metavar='NOTIFIER_ID').completer = self.ComplN(self)

        ap_destroy = self.sp.add_parser('destroy', help='Destroy notifier')
        ap_destroy.add_argument(
            'i', help='Notifier ID',
            metavar='NOTIFIER_ID').completer = self.ComplN(self)

    def create_notifier(self, params):
        n = self.get_notifier(params['i'], pass_errors=True)
        if n:
            self.print_err('notifier %s already exists' % params['i'])
            return self.local_func_result_failed
        notifier_id = params['i']
        p = params['p'].split(':')
        space = params.get('s')
        timeout = params.get('t')
        if len(p) < 2:
            return self.local_func_result_failed
        if p[0] == 'json':
            u = (':'.join(p[1:])).split('/')
            if len(u) < 3:
                return self.local_func_result_failed
            if u[2].find('@') != -1:
                try:
                    notify_key, u[2] = u[2].split('@')
                except:
                    return self.local_func_result_failed
            else:
                notify_key = None
            uri = '/'.join(u)
            if uri.find('#') != -1:
                uri, method = uri.split('#', 1)
            else:
                method = None
            n = eva.notify.HTTP_JSONNotifier(notifier_id=notifier_id,
                                             uri=uri,
                                             method=method,
                                             notify_key=notify_key,
                                             space=space,
                                             timeout=timeout)
        elif p[0] == 'influxdb':
            u = (':'.join(p[1:])).split('/')
            if len(u) < 3:
                return self.local_func_result_failed
            uri = '/'.join(u)
            if uri.find('#') != -1:
                uri, db = uri.split('#', 1)
            else:
                self.print_err('database not specified')
                return self.local_func_result_failed
            if '/' in db:
                org, db = db.split('/', 1)
                api_version = 2
            else:
                org = None
                api_version = 1
            n = eva.notify.InfluxDB_Notifier(notifier_id=notifier_id,
                                             uri=uri,
                                             db=db,
                                             org=org,
                                             api_version=api_version,
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
            from eva.tools import parse_host_port
            host, port = parse_host_port(host)
            n = eva.notify.MQTTNotifier(notifier_id=notifier_id,
                                        host=host,
                                        port=port,
                                        username=username,
                                        password=password,
                                        space=space,
                                        timeout=timeout)
        elif p[0] == 'db':
            db_uri = ':'.join(p[1:])
            n = eva.notify.SQLANotifier(notifier_id=notifier_id,
                                        db_uri=db_uri,
                                        keep=None,
                                        space=space)
        elif p[0] == 'timescaledb':
            db_uri = ':'.join(p[1:])
            n = eva.notify.TimescaleNotifier(notifier_id=notifier_id,
                                             db_uri=db_uri,
                                             keep=None,
                                             space=space)
        elif p[0] == 'udp':
            if len(p) > 3:
                return self.local_func_result_failed
            try:
                port = int(p[2])
            except:
                return self.local_func_result_failed
            n = eva.notify.UDPNotifier(notifier_id=notifier_id,
                                       host=p[1],
                                       port=port)
        elif p[0] == 'gcpiot':
            try:
                project, region, registry = ':'.join(p[1:]).split('/')
            except:
                return self.local_func_result_failed
            n = eva.notify.GCP_IoT(notifier_id=notifier_id,
                                   project=project,
                                   region=region,
                                   registry=registry,
                                   timeout=timeout)
        elif p[0] == 'prometheus':
            n = eva.notify.PrometheusNotifier(notifier_id=notifier_id)
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
        for i in sorted(sorted(eva.notify.get_notifiers(),
                               key=lambda k: k.notifier_id),
                        key=lambda k: k.notifier_type):
            n = {}
            n['id'] = i.notifier_id
            n['type'] = i.notifier_type
            n['enabled'] = i.enabled
            n['params'] = ''
            if isinstance(i, eva.notify.HTTP_JSONNotifier):
                method = getattr(i, 'method', None)
                n['params'] = 'uri: {}{} '.format(
                    i.uri, ('#{}'.format(method) if method else ''))
            elif isinstance(i, eva.notify.SQLANotifier) or isinstance(i, eva.notify.TimescaleNotifier):
                n['params'] = 'db: %s' % i.db_uri
            elif isinstance(i, eva.notify.InfluxDB_Notifier):
                n['params'] = 'uri: {}, db: {}, api: v{}'.format(
                    i.uri, i.db if i.api_version == 1 else f'{i.org}/{i.db}',
                    i.api_version)
            elif isinstance(i, eva.notify.GCP_IoT):
                n['params'] = '{}/{}/{}'.format(i.project, i.region, i.registry)
            elif isinstance(i, eva.notify.UDPNotifier):
                n['params'] = '{}:{} ({})'.format(i.host, i.port, i.fmt)
            elif isinstance(i, eva.notify.MQTTNotifier):
                if i.username is not None:
                    n['params'] = '%s%s@' % (i.username,
                                             ':*' if i.password else '')
                n['params'] += '%s:%u' % (i.host, i.port)
                if i.space is not None and i.space != '':
                    n['params'] += '/' + i.space
            result.append(n)
        return 0, sorted(result, key=lambda k: k['id'])

    def get_notifier(self, notifier_id, pass_errors=False):
        try:
            n = eva.notify.load_notifier(notifier_id, test=False, connect=False)
            n.test_only_mode = True
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
            try:
                eva.registry.key_delete(
                    f'config/{eva.core.product.code}/notifiers/{params["i"]}')
                return self.local_func_result_ok
            except Exception as e:
                self.print_err('unable to delete notifier {params["i"]} config')
                return self.local_func_result_failed
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
        return (0, n.serialize()) if n else self.local_func_result_failed

    def list_notifier_props(self, params):
        n = self.get_notifier(params['i'])
        return (0,
                n.serialize(props=True)) if n else self.local_func_result_failed

    def set_notifier_prop(self, params):
        n = self.get_notifier(params['i'])
        prop = params.get('p')
        value = params.get('v')
        if not value and '=' in prop:
            prop, value = prop.split('=', 1)
        if not n or not n.set_prop(prop, value):
            return self.local_func_result_failed
        eva.notify.append_notifier(n)
        c = n.serialize(props=True)
        if prop.find('.') == -1:
            v = c[prop]
        else:
            try:
                a, b = prop.split('.')
                v = c[a][b]
            except:
                v = 'null'
        print(self.colored('%s.%s' % (params['i'], prop),
                           color='blue',
                           attrs=['bold']),
              end='')
        print(' = ', end='')
        print(self.colored(v, color='yellow'))
        eva.notify.save_notifier(params['i'])
        return self.local_func_result_ok

    def subscribe_notifier_log(self, params):
        level = params.get('l')
        if not level:
            level = 20
        else:
            try:
                level = int(level)
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

    def subscribe_notifier_server(self, params):
        n = self.get_notifier(params['i'])
        if not n or not n.subscribe(subject='server'):
            return self.local_func_result_failed
        eva.notify.append_notifier(n)
        eva.notify.save_notifier(params['i'])
        for d in n.serialize()['events']:
            if d['subject'] == 'server':
                return 0, d
        return self.local_func_result_failed

    def subscribe_notifier_state(self, params):
        n = self.get_notifier(params['i'])
        if not n or not n.subscribe(
                subject='state',
                item_types=params['p'].split(',') if params.get('p') else None,
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
                item_types=params['p'].split(',') if params.get('p') else None,
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


try:
    product
except:
    product = os.environ['EVA_PRODUCT']

eva.core.set_product(product, '-1')

_me = 'EVA ICS Notification System Manager CLI for %s version %s' % (
    product.upper(), __version__)

cli = NotifierCLI('%s_notifier' % product,
                  _me,
                  remote_api_enabled=False,
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
    'subscribe:server': cli.subscribe_notifier_server,
    'subscribe:state': cli.subscribe_notifier_state,
    'subscribe:action': cli.subscribe_notifier_action
}

_pd_cols = {'list_notifiers': ['id', 'type', 'enabled', 'params']}

_pd_idx = {}

_fancy_indentsp = {}

_always_json = ['get_notifier_config']

cli.ap.prog = '%s-notifier' % product
cli.always_json += _always_json
cli.arg_sections += ['subscribe']
cli.set_api_functions(_api_functions)
cli.set_pd_cols(_pd_cols)
cli.set_fancy_indentsp(_fancy_indentsp)
code = cli.run()
eva.client.cli.subshell_exit_code = code
sys.exit(code)
