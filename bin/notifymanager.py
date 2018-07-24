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


class NotifierCLI(GenericCLI):

    def add_functions(self):
        super().add_functions()
        self.add_notifier_common_functions()

    def add_notifier_common_functions(self):
        ap_list = self.sp.add_parser('list', help='List notifiers')
        ap_test = self.sp.add_parser('test', help='Test notifier')
        ap_test.add_argument('i', help='Notifier ID', metavar='ID')
        ap_enable = self.sp.add_parser('enable', help='Enable notifier')
        ap_enable.add_argument('i', help='Notifier ID', metavar='ID')
        ap_disable = self.sp.add_parser('disable', help='Disable notifier')
        ap_disable.add_argument('i', help='Notifier ID', metavar='ID')
        ap_config = self.sp.add_parser('config', help='Get notifier config')
        ap_config.add_argument('i', help='Notifier ID', metavar='ID')
        ap_props = self.sp.add_parser('props', help='Get notifier properties')
        ap_props.add_argument('i', help='Notifier ID', metavar='ID')
        ap_set_prop = self.sp.add_parser('set', help='Set notifier property')
        ap_set_prop.add_argument('i', help='Notifier ID', metavar='ID')
        ap_set_prop.add_argument('p', help='Config property', metavar='PROP')
        ap_set_prop.add_argument('v', help='Value', metavar='VAL', nargs='?')

    def list_notifiers(self, params=None):
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
                if i.username is not None and i.password is not None:
                    n['params'] = '%s:%s@' % (i.username, i.password)
                n['params'] += '%s:%u' % (i.host, i.port)
            result.append(n)
        return 0, result

    def get_notifier(self, notifier_id):
        try:
            n = eva.notify.load_notifier(notifier_id, test=False, connect=False)
            return n
        except:
            self.print_err('can not load notifier %s' % notifier_id)
            return None

    def test_notifier(self, params=None):
        n = self.get_notifier(params['i'])
        if n and n.test():
            n.disconnect()
            return self.local_func_result_ok
        else:
            return self.local_func_result_failed

    def enable_notifier(self, params=None):
        return self.set_notifier_enable(params['i'], True)

    def disable_notifier(self, params=None):
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

    def get_notifier_config(self, params=None):
        n = self.get_notifier(params['i'])
        return 0, n.serialize() if n else None

    def list_notifier_props(self, params=None):
        n = self.get_notifier(params['i'])
        return 0, n.serialize(props=True) if n else None

    def set_notifier_prop(self, params=None):
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


product = os.environ['EVA_PRODUCT']

_me = 'EVA ICS Notification System Manager CLI for %s version %s' % (
    product.upper(), __version__)

cli = NotifierCLI('%s_notifier' % product, _me, remote_api=False)

_api_functions = {
    'list': cli.list_notifiers,
    'test': cli.test_notifier,
    'enable': cli.enable_notifier,
    'disable': cli.disable_notifier,
    'config': cli.get_notifier_config,
    'props': cli.list_notifier_props,
    'set': cli.set_notifier_prop
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
cli.set_api_functions(_api_functions)
cli.set_pd_cols(_pd_cols)
cli.set_pd_idx(_pd_idx)
cli.set_fancy_tabsp(_fancy_tabsp)
code = cli.run()
sys.exit(code)
