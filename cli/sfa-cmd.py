__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2020 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.3.2"

import sys
import os

from pathlib import Path

dir_eva = Path(__file__).absolute().parents[1].as_posix()
dir_lib = dir_eva + '/lib'
sys.path.insert(0, dir_lib)

from eva.client.cli import GenericCLI
from eva.client.cli import ControllerCLI
from eva.client.cli import LECLI
from eva.client.cli import ComplGeneric
from eva.client.cli import ComplUser
from eva.client.cli import ComplKey

import eva.client.cli


class SFA_CLI(GenericCLI, ControllerCLI, LECLI):

    @staticmethod
    def dict_safe_get(d, key, default):
        if d is None:
            return default
        result = d.get(key)
        return default if result is None else result

    class ComplItemOID(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            p = None
            if hasattr(kwargs.get('parsed_args'), 'p'):
                p = kwargs.get('parsed_args').p
                fld = 'full_id'
            if not p and prefix.find(':') != -1:
                p = prefix.split(':', 1)[0]
                fld = 'oid'
            if p:
                code, data = self.cli.call(['state', '-p', p])
                if code:
                    return True
                result = set()
                for v in data:
                    result.add(v[fld])
                return list(result)
            else:
                return ['sensor:', 'unit:', 'lvar:']

    class ComplItemGroup(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            if not hasattr(kwargs.get('parsed_args'),
                           'p') or not kwargs.get('parsed_args').p:
                return True
            code, data = self.cli.call(
                ['state', '-p', kwargs.get('parsed_args').p])
            if code:
                return True
            result = set()
            for v in data:
                result.add(v['group'])
            return list(result)

    class ComplUnit(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call('state -p unit')
            if code:
                return True
            result = set()
            for v in data:
                if prefix.startswith('unit:'):
                    result.add(v['oid'])
                else:
                    if v['full_id'].startswith(prefix):
                        result.add(v['full_id'])
            if not result:
                result.add('unit:')
            return list(result)

    class ComplUnitGroup(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call('state -p unit')
            if code:
                return True
            result = set()
            for v in data:
                result.add(v['group'])
            return list(result)

    class ComplLVAR(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call('state -p lvar')
            if code:
                return True
            result = set()
            for v in data:
                if prefix.startswith('lvar:'):
                    result.add(v['oid'])
                else:
                    if v['full_id'].startswith(prefix):
                        result.add(v['full_id'])
            if not result:
                result.add('lvar:')
            return list(result)

    class ComplMacro(ComplGeneric):

        def __init__(self, cli, field='full_id'):
            self.field = field
            super().__init__(cli)

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call('macro list')
            if code:
                return True
            result = set()
            for v in data:
                result.add(v[self.field])
            return list(result)

    class ComplMacroGroup(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call('macro list')
            if code:
                return True
            result = set()
            for v in data:
                result.add(v['group'])
            return list(result)

    class ComplCycleGroup(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call('cycle list')
            if code:
                return True
            result = set()
            for v in data:
                result.add(v['group'])
            return list(result)

    class ComplController(ComplGeneric):

        def __init__(self, cli, allow_all=False):
            super().__init__(cli)
            self.allow_all = allow_all

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call('controller list')
            if code:
                return True
            result = set()
            if self.allow_all:
                result.add('all')
            for v in data:
                result.add(v['full_id'])
            return list(result)

    class ComplControllerProp(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call(
                ['controller', 'props',
                 kwargs.get('parsed_args').i])
            if code:
                return True
            result = list(data.keys())
            return result

    class ComplRemoteGroup(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            opts = []
            if not kwargs.get('ignore_p') and hasattr(kwargs.get('parsed_args'),
                                                      'p'):
                p = kwargs.get('parsed_args').p
                if p:
                    opts = ['-p', p]
            code, data = self.cli.call(['remote'] + opts)
            if code:
                return True
            result = set()
            for v in data:
                result.add(v['group'])
            return list(result)

    def prepare_run(self, api_func, params, a):
        if api_func in ['set_controller_prop']:
            if params.get('p') and params['p'].find('=') != -1:
                params['p'], params['v'] = params['p'].split('=', 1)
        if api_func == 'state_history':
            if params['c']:
                params['g'] = 'chart'
        return super().prepare_run(api_func, params, a)

    def prepare_result_data(self, data, api_func, itype):
        if api_func not in [
                'state', 'list_macros', 'list_cycles', 'list_controllers',
                'result'
        ] and itype not in ['action']:
            return super().prepare_result_data(data, api_func, itype)
        result = []
        for d in data.copy():
            if itype == 'action' or api_func == 'result':
                from datetime import datetime
                d['time'] = datetime.fromtimestamp(
                    d['time']['created']).isoformat()
            if api_func == 'list_controllers':
                d['type'] = 'static' if d['static'] else 'dynamic'
                d['proto'] += '/' + ('mqtt' if d.get('mqtt_update') else 'ws')
            if api_func in ['list_macros', 'list_cycles', 'list_controllers']:
                d['id'] = d['full_id']
            if api_func == 'list_cycles':
                d['int'] = d['interval']
                d['iter'] = d['iterations']
                d['status'] = ['stopped', 'running', 'stopping'][d['status']]
            elif itype == 'state':
                try:
                    from datetime import datetime
                    d['set'] = datetime.fromtimestamp(d['set_time']).isoformat()
                    if d['expires']:
                        if d['status'] == 0:
                            d['exp_in'] = 'S'
                        else:
                            try:
                                if d['status'] == -1:
                                    raise Exception('expired')
                                import time
                                exp_in = d['set_time'] + \
                                        d['expires'] - time.time()
                                if exp_in <= 0:
                                    raise Exception('expired')
                                d['exp_in'] = '{:.1f}'.format(exp_in)
                            except Exception as e:
                                d['exp_in'] = 'E'
                    else:
                        d['exp_in'] = '-'
                except:
                    pass
            result.append(d)
        return result

    def process_result(self, result, code, api_func, itype, a):
        if api_func == 'state_history' and \
                isinstance(result, dict) and 'content_type' not in result:
            self.print_tdf(result,
                           't',
                           plot=a._bars,
                           plot_field=a.x if a.x else 'value')
            return 0
        else:
            return super().process_result(result, code, api_func, itype, a)

    def prepare_result_dict(self, data, api_func, itype):
        if api_func == 'status_controller':
            return self.prepare_controller_status_dict(data)
        elif api_func == 'result' and 'created' in data:
            from datetime import datetime
            for x in data.keys():
                data[x] = '{:.7f} | {}'.format(data[x],
                                               datetime.fromtimestamp(data[x]))
            return super().prepare_result_dict(data, api_func, itype)
        else:
            return super().prepare_result_dict(data, api_func, itype)

    def setup_parser(self):
        super().setup_parser()
        self.enable_controller_management_functions('sfa')
        self.enable_le_functions()

    def add_functions(self):
        super().add_functions()
        self.add_sfa_common_functions()
        self.add_sfa_remote_functions()
        self.add_sfa_action_functions()
        self.add_sfa_macro_functions()
        self.add_sfa_cycle_functions()
        self.add_sfa_edit_functions()
        self.add_sfa_lvar_functions()
        self.add_sfa_notify_functions()
        self.add_sfa_supervisor_functions()
        self.add_sfa_controller_functions()
        self.add_sfa_cloud_functions()

    def add_sfa_common_functions(self):
        sp_state = self.sp.add_parser('state', help='Get item state')
        sp_state.add_argument('i',
                              help='Item ID (specify either ID or item type)',
                              metavar='ID',
                              nargs='?').completer = self.ComplItemOID(self)
        sp_state.add_argument(
            '-p',
            '--type',
            help='Item type',
            metavar='TYPE',
            dest='p',
            choices=['unit', 'sensor', 'lvar', 'U', 'S', 'LV'])
        sp_state.add_argument('-g',
                              '--group',
                              help='Item group',
                              metavar='GROUP',
                              dest='g').completer = self.ComplItemGroup(self)
        sp_state.add_argument('-y',
                              '--full',
                              help='Full information about item',
                              dest='_full',
                              action='store_true')

        sp_history = self.sp.add_parser('history',
                                        help='Get item state history')
        sp_history.add_argument(
            'i',
            help=
            'Item ID or multiple IDs (-w param is required), comma separated',
            metavar='ID').completer = self.ComplItemOID(self)
        sp_history.add_argument(
            '-a',
            '--notifier',
            help='Notifier to get history from (default: db_1)',
            metavar='NOTIFIER',
            dest='a')
        sp_history.add_argument('-s',
                                '--time-start',
                                help='Start time',
                                metavar='TIME',
                                dest='s')
        sp_history.add_argument('-e',
                                '--time-end',
                                help='End time',
                                metavar='TIME',
                                dest='e')
        sp_history.add_argument('-l',
                                '--limit',
                                help='Records limit (doesn\'t work with fill)',
                                metavar='N',
                                dest='l')
        sp_history.add_argument('-x',
                                '--prop',
                                help='Item state prop (status or value)',
                                metavar='PROP',
                                dest='x',
                                choices=['status', 'value', 'S', 'V'])
        sp_history.add_argument(
            '-w',
            '--fill',
            help='Fill (i.e. 1T - 1 min, 2H - 2 hours), requires start time',
            metavar='INTERVAL',
            dest='w')
        sp_history.add_argument('-c',
                                '--chart-options',
                                help='Chart options (generate image)',
                                metavar='OPTS',
                                dest='c')
        sp_history.add_argument('-B',
                                '--bar-chart',
                                help='Generate ascii bar chart',
                                action='store_true',
                                dest='_bars')

    def add_sfa_edit_functions(self):
        ap_edit = self.sp.add_parser('edit', help='Edit commands')

        sp_edit = ap_edit.add_subparsers(dest='_func',
                                         metavar='func',
                                         help='Edit commands')

        self._append_edit_pvt_and_ui(sp_edit)
        self._append_edit_common(sp_edit)

    def add_sfa_remote_functions(self):
        ap_remote = self.sp.add_parser('remote', help='List remote items')
        ap_remote.add_argument('-i',
                               '--controller',
                               help='Filter by controller ID',
                               metavar='CONTROLLER_ID',
                               dest='i').completer = self.ComplController(self)
        ap_remote.add_argument('-g',
                               '--group',
                               help='Filter by group',
                               metavar='GROUP',
                               dest='g').completer = self.ComplRemoteGroup(self)
        ap_remote.add_argument(
            '-p',
            '--type',
            help='Filter by type',
            metavar='TYPE',
            dest='p',
            choices=['unit', 'sensor', 'lvar', 'U', 'S', 'LV'])

    def add_sfa_action_functions(self):
        ap_action = self.sp.add_parser('action', help='Unit actions')

        sp_action = ap_action.add_subparsers(dest='_func',
                                             metavar='func',
                                             help='Action commands')

        sp_action_enable = sp_action.add_parser('enable',
                                                help='Enable unit actions')
        sp_action_enable.add_argument(
            'i', help='Unit ID', metavar='ID').completer = self.ComplUnit(self)

        sp_action_disable = sp_action.add_parser('disable',
                                                 help='Disable unit actions')
        sp_action_disable.add_argument(
            'i', help='Unit ID', metavar='ID').completer = self.ComplUnit(self)

        sp_action_exec = sp_action.add_parser('exec',
                                              help='Execute unit action')
        sp_action_exec.add_argument(
            'i', help='Unit ID', metavar='ID').completer = self.ComplUnit(self)
        sp_action_exec.add_argument('s', help='New status', metavar='STATUS')
        sp_action_exec.add_argument('-v',
                                    '--value',
                                    help='New value',
                                    metavar='VALUE',
                                    dest='v')
        sp_action_exec.add_argument('-p',
                                    '--priority',
                                    help='Action priority',
                                    metavar='PRIORITY',
                                    type=int,
                                    dest='p')
        sp_action_exec.add_argument('-w',
                                    '--wait',
                                    help='Wait for complete',
                                    metavar='SEC',
                                    type=float,
                                    dest='w')
        sp_action_exec.add_argument('-q',
                                    '--queue-timeout',
                                    help='Max queue timeout',
                                    metavar='SEC',
                                    type=float,
                                    dest='q')
        sp_action_exec.add_argument('-u',
                                    '--uuid',
                                    help='Custom action uuid',
                                    metavar='UUID',
                                    dest='u')

        sp_action_toggle = sp_action.add_parser(
            'toggle', help='Execute unit toggle action')
        sp_action_toggle.add_argument(
            'i', help='Unit ID', metavar='ID').completer = self.ComplUnit(self)
        sp_action_toggle.add_argument('-p',
                                      '--priority',
                                      help='Action priority',
                                      metavar='PRIORITY',
                                      type=int,
                                      dest='p')
        sp_action_toggle.add_argument('-w',
                                      '--wait',
                                      help='Wait for complete',
                                      metavar='SEC',
                                      type=float,
                                      dest='w')
        sp_action_toggle.add_argument('-q',
                                      '--queue-timeout',
                                      help='Max queue timeout',
                                      metavar='SEC',
                                      type=float,
                                      dest='q')
        sp_action_toggle.add_argument('-u',
                                      '--uuid',
                                      help='Custom action uuid',
                                      metavar='UUID',
                                      dest='u')

        sp_action_terminate = sp_action.add_parser('terminate',
                                                   help='Terminate unit action')
        sp_action_terminate.add_argument(
            'i', help='Unit ID', metavar='ID',
            nargs='?').completer = self.ComplUnit(self)
        sp_action_terminate.add_argument('-u',
                                         '--uuid',
                                         help='Action uuid',
                                         metavar='UUID',
                                         dest='u')

        sp_action_qclean = sp_action.add_parser(
            'clear', help='Clean up unit action queue')
        sp_action_qclean.add_argument(
            'i', help='Unit ID', metavar='ID').completer = self.ComplUnit(self)

        sp_action_kill = sp_action.add_parser(
            'kill', help='Terminate action and clean queue')
        sp_action_kill.add_argument(
            'i', help='Unit ID', metavar='ID').completer = self.ComplUnit(self)

        sp_action_result = sp_action.add_parser('result',
                                                help='Get unit action results')
        sp_action_result.add_argument(
            '-i',
            '--id',
            help='Unit ID (specify either unit ID or action UUID)',
            metavar='ID',
            dest='i').completer = self.ComplUnit(self)
        sp_action_result.add_argument('-u',
                                      '--uuid',
                                      help='Action UUID',
                                      metavar='UUID',
                                      dest='u')
        sp_action_result.add_argument(
            '-g', '--group', help='Unit group', metavar='GROUP',
            dest='g').completer = self.ComplUnitGroup(self)
        sp_action_result.add_argument(
            '-s',
            '--state',
            help='Action state (Q, R, F: queued, running, finished)',
            metavar='STATE',
            dest='s',
            choices=['queued', 'running', 'finished', 'Q', 'R', 'F'])

    def add_sfa_macro_functions(self):
        ap_macro = self.sp.add_parser('macro', help='Macro functions')
        sp_macro = ap_macro.add_subparsers(dest='_func',
                                           metavar='func',
                                           help='Macro commands')

        sp_macro_list = sp_macro.add_parser('list', help='List macros')
        sp_macro_list.add_argument(
            '-g', '--group', help='Filter by group', metavar='GROUP',
            dest='g').completer = self.ComplMacroGroup(self)

        sp_macro_run = sp_macro.add_parser('run', help='Execute macro')
        sp_macro_run.add_argument(
            'i', help='Macro ID',
            metavar='ID').completer = self.ComplMacro(self)
        sp_macro_run.add_argument('-a',
                                  '--args',
                                  help='Macro arguments',
                                  metavar='ARGS',
                                  dest='a')
        sp_macro_run.add_argument(
            '--kwargs',
            help='Macro keyword arguments (name=value), comma separated',
            metavar='ARGS',
            dest='kw')
        sp_macro_run.add_argument('-p',
                                  '--priority',
                                  help='Action priority',
                                  metavar='PRIORITY',
                                  type=int,
                                  dest='p')
        sp_macro_run.add_argument('-w',
                                  '--wait',
                                  help='Wait for complete',
                                  metavar='SEC',
                                  type=float,
                                  dest='w')
        sp_macro_run.add_argument('-u',
                                  '--uuid',
                                  help='Custom action uuid',
                                  metavar='UUID',
                                  dest='u')

        sp_macro_result = sp_macro.add_parser(
            'result', help='Get macro execution results')
        sp_macro_result.add_argument(
            '-i',
            '--id',
            help='Macro ID (specify either macro ID or action UUID)',
            metavar='ID',
            dest='i').completer = self.ComplMacro(self, 'oid')
        sp_macro_result.add_argument('-u',
                                     '--uuid',
                                     help='Action UUID',
                                     metavar='UUID',
                                     dest='u')
        sp_macro_result.add_argument(
            '-g', '--group', help='Macro group', metavar='GROUP',
            dest='g').completer = self.ComplMacroGroup(self)
        sp_macro_result.add_argument(
            '-s',
            '--state',
            help='Action state (Q, R, F: queued, running, finished)',
            metavar='STATE',
            dest='s',
            choices=['queued', 'running', 'finished', 'Q', 'R', 'F'])

    def add_sfa_cycle_functions(self):
        ap_cycle = self.sp.add_parser('cycle', help='Cycle functions')
        sp_cycle = ap_cycle.add_subparsers(dest='_func',
                                           metavar='func',
                                           help='Cycle commands')

        sp_cycle_list = sp_cycle.add_parser('list', help='List cycles')
        sp_cycle_list.add_argument(
            '-g', '--group', help='Filter by group', metavar='GROUP',
            dest='g').completer = self.ComplCycleGroup(self)

    def add_sfa_lvar_functions(self):
        sp_set = self.sp.add_parser('set', help='Set LVar state')
        sp_set.add_argument('i', help='LVar ID',
                            metavar='ID').completer = self.ComplLVAR(self)
        sp_set.add_argument('-s',
                            '--status',
                            help='LVar status',
                            metavar='STATUS',
                            type=int,
                            dest='s')
        sp_set.add_argument('-v',
                            '--value',
                            help='LVar value',
                            metavar='VALUE',
                            dest='v')

        sp_reset = self.sp.add_parser('reset', help='Reset LVar state')
        sp_reset.add_argument('i', help='LVar ID',
                              metavar='ID').completer = self.ComplLVAR(self)

        sp_clear = self.sp.add_parser('clear', help='Clear LVar state')
        sp_clear.add_argument('i', help='LVar ID',
                              metavar='ID').completer = self.ComplLVAR(self)

        sp_toggle = self.sp.add_parser('toggle', help='Toggle LVar state')
        sp_toggle.add_argument('i', help='LVar ID',
                               metavar='ID').completer = self.ComplLVAR(self)

    def add_sfa_notify_functions(self):
        ap_notify = self.sp.add_parser('notify',
                                       help='Notify connected clients')
        sp_notify = ap_notify.add_subparsers(
            dest='_func', metavar='func', help='Client notification commands')

        sp_notify_reload = sp_notify.add_parser(
            'reload', help='Ask connected clients to reload the interface')
        sp_notify_reload = sp_notify.add_parser(
            'restart',
            help=
            'Notify connected clients about the server restart ' + \
                    'without actual restarting'
        )

    def add_sfa_supervisor_functions(self):
        ap_supervisor = self.sp.add_parser('supervisor',
                                           help='Supervisor functions')
        sp_supervisor = ap_supervisor.add_subparsers(dest='_func',
                                                     metavar='func',
                                                     help='Supervisor commands')

        sp_supervisor_lock = sp_supervisor.add_parser(
            'lock', help='Set supervisor lock')
        sp_supervisor_lock.add_argument(
            '-u', '--user', help='Lock owner user', dest='u',
            metavar='LOGIN').completer = ComplUser(self)
        sp_supervisor_lock.add_argument('-p',
                                        '--user-type',
                                        help='Lock owner user type (e.g. msad)',
                                        metavar='TYPE',
                                        dest='p')
        sp_supervisor_lock.add_argument('-a',
                                        '--key-id',
                                        help='Lock owner API key (ID)',
                                        metavar='ID',
                                        dest='a').completer = ComplKey(self)
        sp_supervisor_lock.add_argument(
            '-l',
            '--lock-scope',
            help='Lock scope (default: all supervisors)',
            choices=['u', 'k'],
            metavar='SCOPE',
            dest='l')
        sp_supervisor_lock.add_argument(
            '-c',
            '--unlock-scope',
            help='Unlock scope (default: all supervisors)',
            choices=['u', 'k'],
            metavar='SCOPE',
            dest='c')

        sp_supervisor_unlock = sp_supervisor.add_parser(
            'unlock', help='Clear supervisor lock')

        sp_supervisor_message = sp_supervisor.add_parser(
            'message', help='Send broadcast message')
        sp_supervisor_message.add_argument('m',
                                           help='Message text',
                                           metavar='Text to send')
        sp_supervisor_message.add_argument(
            '-u', '--user', help='Sender user', dest='u',
            metavar='LOGIN').completer = ComplUser(self)
        sp_supervisor_message.add_argument('-a',
                                           '--key-id',
                                           help='Sender API key',
                                           metavar='ID',
                                           dest='a').completer = ComplKey(self)

    def add_sfa_controller_functions(self):
        ap_controller = self.sp.add_parser(
            'controller', help='Connected controllers functions')
        sp_controller = ap_controller.add_subparsers(dest='_func',
                                                     metavar='func',
                                                     help='Controller commands')

        sp_controller_list = sp_controller.add_parser(
            'list', help='List connected controllers')

        sp_controller_test = sp_controller.add_parser(
            'test', help='Test connected controller')
        sp_controller_test.add_argument(
            'i', help='Controller ID',
            metavar='ID').completer = self.ComplController(self)

        sp_controller_matest = sp_controller.add_parser(
            'ma-test', help='Test connected controller cloud management API')
        sp_controller_matest.add_argument(
            'i', help='Controller ID',
            metavar='ID').completer = self.ComplController(self)

        sp_controller_list_props = sp_controller.add_parser(
            'props', help='List controller config props')
        sp_controller_list_props.add_argument(
            'i', help='Controller ID',
            metavar='ID').completer = self.ComplController(self)

        sp_controller_set_prop = sp_controller.add_parser(
            'set', help='Set controller config prop')
        sp_controller_set_prop.add_argument(
            'i', help='Controller ID',
            metavar='ID').completer = self.ComplController(self)
        sp_controller_set_prop.add_argument(
            'p', help='Config property',
            metavar='PROP').completer = self.ComplControllerProp(self)
        sp_controller_set_prop.add_argument('v',
                                            help='Value',
                                            metavar='VAL',
                                            nargs='?')
        sp_controller_set_prop.add_argument(
            '-y',
            '--save',
            help='Save controller config after set',
            dest='_save',
            action='store_true')

        sp_controller_reload = sp_controller.add_parser(
            'reload', help='Reload items from the connected controller')
        sp_controller_reload.add_argument(
            'i', help='Controller ID (or "all")',
            metavar='ID').completer = self.ComplController(self, allow_all=True)

        sp_controller_append = sp_controller.add_parser(
            'append', help='Connect controller')
        sp_controller_append.add_argument(
            'u', help='Controller API URI (http[s]://host:port)', metavar='URI')
        sp_controller_append.add_argument('-a',
                                          '--api-key',
                                          help='API key',
                                          metavar='KEY',
                                          dest='a')
        sp_controller_append.add_argument('-x',
                                          '--api-masterkey',
                                          help='API masterkey',
                                          metavar='MASTERKEY',
                                          dest='x')
        sp_controller_append.add_argument('-g',
                                          '--group',
                                          help='Force controller type group',
                                          metavar='GROUP',
                                          choices=['uc', 'lm'],
                                          dest='g')
        sp_controller_append.add_argument(
            '-m',
            '--mqtt',
            help='Local MQTT notifier ID for data exchange',
            metavar='NOTIFIER_ID',
            dest='m')
        sp_controller_append.add_argument(
            '-s',
            '--ssl-verify',
            help='Verify remote cert for SSL connections',
            metavar='SSL_VERIFY',
            dest='s',
            choices=[0, 1])
        sp_controller_append.add_argument('-t',
                                          '--timeout',
                                          help='API timeout',
                                          metavar='SEC',
                                          dest='t',
                                          type=float)
        sp_controller_append.add_argument(
            '-y',
            '--save',
            help='Save controller config after connection',
            dest='_save',
            action='store_true')

        sp_controller_enable = sp_controller.add_parser(
            'enable', help='Enable connected controller')
        sp_controller_enable.add_argument(
            'i', help='Controller ID',
            metavar='ID').completer = self.ComplController(self)
        sp_controller_enable.add_argument(
            '-y',
            '--save',
            help='Save controller config after set',
            dest='_save',
            action='store_true')

        sp_controller_disable = sp_controller.add_parser(
            'disable', help='Disable connected controller')
        sp_controller_disable.add_argument(
            'i', help='Controller ID',
            metavar='ID').completer = self.ComplController(self)
        sp_controller_disable.add_argument(
            '-y',
            '--save',
            help='Save controller config after set',
            dest='_save',
            action='store_true')

        sp_controller_remove = sp_controller.add_parser(
            'remove', help='Remove connected controller')
        sp_controller_remove.add_argument(
            'i', help='Controller ID',
            metavar='ID').completer = self.ComplController(self)

        sp_controller_rescan = sp_controller.add_parser(
            'upnp-rescan', help='Rescan controllers via UPnP')

    def add_sfa_cloud_functions(self):
        ap_cloud = self.sp.add_parser(
            'cloud',
            help='Cloud functions (requires cloud_manager=yes in sfa.ini)')
        sp_cloud = ap_cloud.add_subparsers(dest='_func',
                                           metavar='func',
                                           help='Cloud management commands')

        sp_cloud_deploy = sp_cloud.add_parser(
            'deploy', help='Deploy items and configuration from file')
        sp_cloud_deploy.add_argument('f', help='Deploy file',
                                     metavar='FILE').completer = self.ComplGlob(
                                         ['*.yml', '*.yaml'])
        sp_cloud_deploy.add_argument(
            '-y',
            '--save',
            help='Save controllers\' configurations after deploy',
            dest='_save',
            action='store_true')
        sp_cloud_deploy.add_argument('-u',
                                     '--undeploy',
                                     help='Undeploy old configuration first',
                                     dest='und',
                                     action='store_true')
        sp_cloud_deploy.add_argument('-s',
                                     '--skip',
                                     help='Skip existing items',
                                     dest='skip',
                                     action='store_true')
        sp_cloud_deploy.add_argument(
            '-c',
            '--config',
            help='Template vars, comma separated',
            metavar='VARS',
            dest='c',
        )
        sp_cloud_deploy.add_argument(
            '-T',
            '--test',
            help='Test configuration without deployment',
            dest='test',
            action='store_true')

        sp_cloud_undeploy = sp_cloud.add_parser(
            'undeploy', help='Undeploy items and configuration from file')
        sp_cloud_undeploy.add_argument(
            'f', help='Deploy file',
            metavar='FILE').completer = self.ComplGlob(['*.yml', '*.yaml'])
        sp_cloud_undeploy.add_argument('-d',
                                       '--delete-files',
                                       help='Delete uploaded remote files',
                                       dest="del_files",
                                       action="store_true")
        sp_cloud_undeploy.add_argument(
            '-y',
            '--save',
            help='Save controllers\' configurations after undeploy',
            dest='_save',
            action='store_true')
        sp_cloud_undeploy.add_argument(
            '-c',
            '--config',
            help='Template vars, comma separated',
            metavar='VARS',
            dest='c',
        )

    # cloud management

    def deploy(self, props):
        from eva.client import apiclient
        if props.get('und'):
            code, result = self.undeploy(props)
            if code != apiclient.result_ok:
                return code, result
        return self._deploy_undeploy(props, und=False)

    def undeploy(self, props):
        from eva.client import apiclient
        return self._deploy_undeploy(props,
                                     und=True,
                                     del_files=props.get('del_files', False))

    @staticmethod
    def _read_uri(fname, dirname=None, file_read_mode='r'):
        target = (dirname + '/' + fname) if dirname else fname
        if target.startswith('http://') or target.startswith('https://'):
            import requests
            result = requests.get(target)
            if not result.ok:
                raise Exception('http code {}'.format(result.status_code))
            return result.text if file_read_mode == 'r' else result.content
        else:
            with open(target, file_read_mode) as fd:
                return fd.read()

    def _deploy_undeploy(self, props, und=False, del_files=False):
        import yaml
        try:
            yaml.warnings({'YAMLLoadWarning': False})
        except:
            pass
        from eva.client import apiclient
        test_mode = props.get('test')
        try:
            try:
                import jinja2
                import importlib
                from eva.tools import dict_from_str
                fname = props.get('f')
                v = props.get('c')
                if v:
                    v = dict_from_str(v)
                else:
                    v = {}
                dirname = os.path.dirname(fname)
                tpl = jinja2.Template(self._read_uri(fname))
                tpl.globals['import_module'] = importlib.import_module
                ys = tpl.render(v)
                if test_mode:
                    self.print_debug('-' * 3)
                    self.print_debug(ys)
                    self.print_debug('-' * 3)
                cfg = yaml.load(ys)
            except Exception as e:
                raise Exception('Unable to parse {}: {}'.format(fname, e))
            api = props['_api']
            from functools import partial
            call = partial(api.call,
                           timeout=props.get('_timeout', self.default_timeout),
                           _debug=props.get('_debug'))
            code, test = call('test')
            if code != apiclient.result_ok or not test.get('ok'):
                raise Exception(
                    'SFA API is inaccessible, code: {}'.format(code))
            if not test.get('acl', {}).get('master'):
                self.print_err('Masterkey is required')
            if not test.get('cloud_manager'):
                raise Exception(
                    'SFA is not Cloud Manager. Enable feature in sfa.ini first')
            print('Checking deployment config...')
            for c in cfg.keys() if cfg else []:
                if c not in [
                        'controller', 'unit', 'sensor', 'lvar', 'lmacro',
                        'lcycle', 'dmatrix_rule', 'job'
                ]:
                    raise Exception('Invalid config section: {}'.format(c))
            for c, v in self.dict_safe_get(cfg, 'controller', {}).items():
                if v:
                    for k, vv in self.dict_safe_get(v, 'phi', {}).items():
                        if vv:
                            if 'module' not in vv:
                                raise Exception(
                                    'Controller ' + \
                                            '{}, PHI {}: module is not defined'.
                                    format(c, k))
            # check basic items
            controllers = set()
            controllers_fm_required = set()
            for x in [
                    'unit', 'sensor', 'lvar', 'lmacro', 'lcycle',
                    'dmatrix_rule', 'job'
            ]:
                for i, v in self.dict_safe_get(cfg, x, {}).items():
                    if not v or not 'controller' in v:
                        raise Exception(
                            'No controller specified for {} {}'.format(x, i))
                    if x in ['unit', 'sensor'
                            ] and not v['controller'].startswith('uc/'):
                        raise Exception('Invalid controller specified ' +
                                        'for {} {} (uc required)'.format(x, i))
                    if x in ['lvar', 'lmacro', 'lcycle', 'dmatrix_rule', 'job'
                            ] and not v['controller'].startswith('lm/'):
                        raise Exception('Invalid controller specified ' +
                                        'for {} {} (lm required)'.format(x, i))
                    controllers.add(v['controller'])
                    for p in ['action_exec', 'update_exec']:
                        if self.dict_safe_get(v, p, '').startswith('^'):
                            if not und:
                                try:
                                    self._read_uri(v[p][1:], dirname)
                                except:
                                    raise Exception(
                                        ('{} is defined as {} for {} {}, ' +
                                         'but file is not found').format(
                                             v[p][1:], p, x, i))
                            controllers_fm_required.add(v['controller'])
            print('Checking remote controllers...')
            for c, v in self.dict_safe_get(cfg, 'controller', {}).items():
                controllers.add(c)
                if v:
                    if 'upload-runtime' in v:
                        controllers_fm_required.add(c)
                        if not und:
                            for f in v['upload-runtime']:
                                fname, remote_file = f.split(':')
                                if '*' not in fname:
                                    try:
                                        self._read_uri(fname, dirname, 'rb')
                                    except:
                                        raise Exception(
                                            ('{}: {} unable to open ' +
                                             'file for upload').format(
                                                 c, fname))
                    if 'phi' in v:
                        for phi, phi_data in self.dict_safe_get(v, 'phi',
                                                                {}).items():
                            if 'src' in phi_data:
                                try:
                                    self._read_uri(fname, dirname, 'rb')
                                except:
                                    raise Exception(
                                        ('{}: {} unable to open ' +
                                         'file for upload').format(c, fname))
            macall = partial(call, 'management_api_call')
            for c in controllers:
                code, ctest = macall({'i': c, 'f': 'test'})
                if code == apiclient.result_not_found:
                    raise Exception('Controller {} not found'.format(c))
                code = ctest.get('code')
                ctest = ctest.get('data')
                if code == apiclient.result_not_ready:
                    raise Exception(
                        ('Controller {} management API not ready (no ' +
                         'master access from SFA)').format(c))
                if code == apiclient.result_forbidden:
                    raise Exception('Controller {} access forbidden'.format(c))
                if code != apiclient.result_ok:
                    raise Exception(
                        'Controller {} access error, code: {}'.format(c, code))
                if not ctest.get('acl', {}).get('master'):
                    raise Exception(
                        'Controller {} master access is not set up'.format(c))
                if c in controllers_fm_required and not ctest.get(
                        'file_management'):
                    raise Exception(
                        'Controller {} file management API is disabled'.format(
                            c))
            if test_mode:
                print('PASSED')
                return self.local_func_result_ok
            # ===== START =====
            print('Starting {}deployment of {}'.format('un' if und else '',
                                                       props['f']))
            # ===== BEFORE TASKS =====
            import time
            print('Executing commands in before-{}deploy...'.format(
                'un' if und else ''))

            def execute_custom_tasks(step):
                for c, v in self.dict_safe_get(cfg, 'controller', {}).items():
                    if v:
                        for a in self.dict_safe_get(
                                v, '{}-{}deploy'.format(step,
                                                        'un' if und else ''),
                            []):
                            if 'api' in a:
                                try:
                                    func = a['api']
                                    can_pass_err = a.get('_pass')
                                    params = a.copy()
                                    del params['api']
                                    try:
                                        del params['_pass']
                                    except:
                                        pass
                                except Exception as e:
                                    raise Exception(
                                        ('Controller {}, '
                                         'invalid before-{}deploy, {} {}'
                                        ).format(c, 'un' if und else '',
                                                 e.__class__.__name__, e))
                            else:
                                f = a['function']
                                if f == 'sleep':
                                    func = time.sleep
                                elif f == 'system':
                                    func = os.system
                                else:
                                    raise RuntimeError(
                                        f'function unsupported: {f}')
                                args = a.get('args', [])
                                kwargs = a.get('kwargs', {})
                                params = str(args) + ' ' + str(kwargs)
                            print(' -- {}: {} {}'.format(
                                '' if callable(func) else c,
                                func.__name__ if callable(func) else func,
                                params))
                            if callable(func):
                                func(*args, **kwargs)
                            else:
                                code = macall({
                                    'i': c,
                                    'f': func,
                                    'p': params
                                })[1].get('code')
                                if code != apiclient.result_ok:
                                    msg = f'API call failed, code {code}'
                                    if can_pass_err:
                                        self.print_warn(msg)
                                    else:
                                        raise Exception(msg)

            execute_custom_tasks('before')
            # ===== CALL DEPLOY/UNDEPLOY =====
            if not und:
                self._perform_deploy(props, cfg, macall, dirname)
            else:
                self._perform_undeploy(props, cfg, macall, del_files)
            # ===== AFTER TASKS =====
            print('Executing commands in after-{}deploy...'.format(
                'un' if und else ''))
            execute_custom_tasks('after')
            if props.get('save'):
                print('Saving configurations')
                for c in controllers:
                    print(' -- {}'.format(c))
                    code = macall({
                        'i': c,
                        'f': 'save',
                    })[1].get('code')
                    if code != apiclient.result_ok:
                        raise Exception('API call failed, code {}'.format(code))
            print('Reloading local SFA')
            for c in controllers:
                print(' -- {}'.format(c))
                code = call('reload_controller', {'i': c})[0]
                if code != apiclient.result_ok:
                    raise Exception('API call failed, code {}'.format(code))
        except Exception as e:
            self.print_err(e)
            return self.local_func_result_failed
        print()
        print('{}eployment completed for {}'.format('Und' if und else 'D',
                                                    props['f']))
        print('-' * 60)
        return self.local_func_result_ok

    @staticmethod
    def _get_files(f):
        result = []
        fname, remote_file = f.split(':')
        if '*' in fname:
            import glob
            for f in glob.glob(fname, recursive=True):
                if os.path.islink(f) or os.path.isfile(f):
                    if not remote_file.endswith('/'):
                        remote_file += '/'
                    if remote_file.startswith('/'):
                        remote_file = remote_file[1:]
                    if '/' in f:
                        fremote = f[fname.find('*'):]
                    else:
                        fremote = f
                    result.append((f, remote_file + fremote))
        else:
            if not remote_file or remote_file.endswith('/'):
                remote_file += os.path.basename(fname)
            if remote_file.startswith('/'):
                remote_file = remote_file[1:]
            result.append((fname, remote_file))
        return result

    def _perform_deploy(self, props, cfg, macall, dirname):

        skip_existing = props.get('skip')
        from eva.client import apiclient
        # ===== FILE UPLOAD =====
        print('Uploading files...')
        for c, v in self.dict_safe_get(cfg, 'controller', {}).items():
            if v:
                if 'upload-runtime' in v:
                    for f in v['upload-runtime']:
                        for fname, remote_file in self._get_files(f):
                            print(' -- {}: {} -> {}'.format(
                                c, fname, remote_file))
                            import base64
                            code = 0
                            code = macall({
                                'i': c,
                                'f': 'file_put',
                                'p': {
                                    'i':
                                        remote_file,
                                    'm':
                                        base64.b64encode(
                                            self._read_uri(
                                                fname, dirname, 'rb')).decode(),
                                    'b':
                                        True
                                }
                            })[1].get('code')
                            if code != apiclient.result_ok:
                                raise Exception(
                                    'File upload failed, API code {}'.format(
                                        code))
                            if os.access(fname, os.X_OK):
                                code = macall({
                                    'i': c,
                                    'f': 'file_set_exec',
                                    'p': {
                                        'i': remote_file,
                                        'e': 1
                                    }
                                })[1].get('code')
                                if code != apiclient.result_ok:
                                    raise Exception(
                                        'File set exec failed, API code {}'.
                                        format(code))
        # ===== CVARS =====
        print('Creating cvars...')
        for c, v in self.dict_safe_get(cfg, 'controller', {}).items():
            if v:
                for i, vv in self.dict_safe_get(v, 'cvar', {}).items():
                    print(' -- {}: {}={}'.format(c, i, vv))
                    code = macall({
                        'i': c,
                        'f': 'set_cvar',
                        'p': {
                            'i': i,
                            'v': vv
                        }
                    })[1].get('code')
                    if code != apiclient.result_ok:
                        raise Exception('API call failed, code {}'.format(code))
        # ===== PHI =====
        print('Loading PHIs...')
        for c, v in self.dict_safe_get(cfg, 'controller', {}).items():
            if v:
                for i, vv in self.dict_safe_get(v, 'phi', {}).items():
                    print(' -- {}: {} -> {}'.format(c, vv['module'], i))
                    if 'src' in vv:
                        print(' -- {}: {} -> {}'.format(c, vv['src'], i))
                        mod_source = self._read_uri(vv['src'])
                        code = macall({
                            'i': c,
                            'f': 'put_phi_mod',
                            'p': {
                                'm': vv['module'],
                                'c': mod_source,
                                'force': True
                            }
                        })[1].get('code')
                        if code != apiclient.result_ok:
                            raise Exception(
                                'API call failed, code {}'.format(code))
                    code = macall({
                        'i': c,
                        'f': 'load_phi',
                        'p': {
                            'i': i,
                            'm': vv['module'],
                            'c': vv.get('config')
                        }
                    })[1].get('code')
                    if code != apiclient.result_ok:
                        raise Exception('API call failed, code {}'.format(code))
        # ===== DRIVERS =====
        print('Loading drivers...')
        for c, v in self.dict_safe_get(cfg, 'controller', {}).items():
            if v:
                for i, vv in self.dict_safe_get(v, 'driver', {}).items():
                    print(' -- {}: {} -> {}'.format(c, vv['module'], i))
                    try:
                        phi_id, lpi_id = i.split('.')
                    except:
                        raise Exception('Invalid driver id: {}'.format(i))
                    code = macall({
                        'i': c,
                        'f': 'load_driver',
                        'p': {
                            'i': lpi_id,
                            'm': vv['module'],
                            'p': phi_id,
                            'c': vv.get('config')
                        }
                    })[1].get('code')
                    if code != apiclient.result_ok:
                        raise Exception('API call failed, code {}'.format(code))
        # ===== EXT =====
        print('Loading extensions...')
        for c, v in self.dict_safe_get(cfg, 'controller', {}).items():
            if v:
                for i, vv in self.dict_safe_get(v, 'ext', {}).items():
                    print(' -- {}: {} -> {}'.format(c, vv['module'], i))
                    code = macall({
                        'i': c,
                        'f': 'load_ext',
                        'p': {
                            'i': i,
                            'm': vv['module'],
                            'c': vv.get('config')
                        }
                    })[1].get('code')
                    if code != apiclient.result_ok:
                        raise Exception('API call failed, code {}'.format(code))
        # ===== ITEM AND MACRO CREATION =====
        for tp in ['unit', 'sensor', 'lvar', 'lmacro', 'lcycle']:
            print('Creating {}s...'.format(tp))
            for i, v in self.dict_safe_get(cfg, tp, {}).items():
                c = v.get('controller')
                print(' -- {}: {}:{}'.format(c, tp, i))
                item_props = v.copy()
                if 'controller' in item_props:
                    del item_props['controller']
                if 'driver' in item_props:
                    del item_props['driver']
                for p in item_props.copy():
                    if p.startswith('__'):
                        del item_props[p]
                if tp == 'lmacro':
                    tpc = 'macro'
                elif tp == 'lcycle':
                    tpc = 'cycle'
                else:
                    tpc = tp
                code = macall({
                    'i': c,
                    'f': 'create_' + tpc,
                    'p': {
                        'i': i
                    }
                })[1].get('code')
                if code != apiclient.result_ok:
                    if code == apiclient.result_already_exists and \
                            skip_existing:
                        print('    [skipped]')
                    else:
                        raise Exception('API call failed, code {}'.format(code))
                if 'driver' in v:
                    print('     - driver {} -> {}'.format(
                        v['driver'].get('id'), i))
                    code = macall({
                        'i': c,
                        'f': 'assign_driver',
                        'p': {
                            'i': i,
                            'd': v['driver'].get('id'),
                            'c': v['driver'].get('config')
                        }
                    })[1].get('code')
                    if code != apiclient.result_ok:
                        raise Exception(
                            'Driver assign API call failed, code {}'.format(
                                code))
                for prop, val in item_props.items():
                    if prop in ['action_exec', 'update_exec'
                               ] and val.startswith('^'):
                        file2u = val[1:]
                        val = os.path.basename(val[1:])
                    else:
                        file2u = None
                    prop = prop.replace('-', '_')
                    print('     - {} = {}'.format(prop, val))
                    if prop in ['status', 'value']:
                        if tp in ['unit', 'sensor']:
                            fn = 'update'
                        elif tp in ['lvar']:
                            fn = 'set'
                        else:
                            raise RuntimeError(
                                f'setting {prop} for {tp} is unsupported')
                        params = {'i': i}
                        if prop == 'status':
                            params['s'] = val
                        else:
                            params['v'] = val
                        if prop == 'value' and tp == 'sensor':
                            params['s'] = 1
                        code = macall({
                            'i': c,
                            'f': fn,
                            'p': params
                        })[1].get('code')
                    else:
                        code = macall({
                            'i':
                                c,
                            'f':
                                'set_{}prop'.format((
                                    tpc +
                                    '_') if tp in ['lmacro', 'lcycle'] else ''),
                            'p': {
                                'i': i,
                                'p': prop,
                                'v': val
                            }
                        })[1].get('code')
                    if code != apiclient.result_ok:
                        raise Exception('API call failed, code {}'.format(code))
                    if file2u:
                        remotefn = 'xc/{}/{}'.format(
                            'lm' if tp in ['lvar', 'lmacro'] else 'uc', val)
                        code = macall({
                            'i': c,
                            'f': 'file_put',
                            'p': {
                                'i': remotefn,
                                'm': self._read_uri(file2u, dirname)
                            }
                        })[1].get('code')
                        if code != apiclient.result_ok:
                            raise Exception(
                                'File upload failed, API code {}'.format(code))
                        if tp != 'lmacro':
                            code = macall({
                                'i': c,
                                'f': 'file_set_exec',
                                'p': {
                                    'i': remotefn,
                                    'e': 1
                                }
                            })[1].get('code')
                            if code != apiclient.result_ok:
                                raise Exception(
                                    'File set exec failed, API code {}'.format(
                                        code))
        # ===== RULE CREATION =====
        print('Creating decision rules...')
        for i, v in self.dict_safe_get(cfg, 'dmatrix_rule', {}).items():
            c = v.get('controller')
            print(' -- {}: {}'.format(c, i))
            rule_props = v.copy()
            if 'controller' in rule_props:
                del rule_props['controller']
            code = macall({
                'i': c,
                'f': 'create_rule',
                'p': {
                    'u': i,
                    'v': rule_props
                }
            })[1].get('code')
            if code != apiclient.result_ok:
                if code == apiclient.result_already_exists and skip_existing:
                    print('    [skipped]')
                else:
                    raise Exception('API call failed, code {}'.format(code))
        # ===== JOB CREATION =====
        print('Creating scheduled jobs...')
        for i, v in self.dict_safe_get(cfg, 'job', {}).items():
            c = v.get('controller')
            print(' -- {}: {}'.format(c, i))
            job_props = v.copy()
            if 'controller' in job_props:
                del job_props['controller']
            code = macall({
                'i': c,
                'f': 'create_job',
                'p': {
                    'u': i,
                    'v': job_props
                }
            })[1].get('code')
            if code != apiclient.result_ok:
                if code == apiclient.result_already_exists and skip_existing:
                    print('    [skipped]')
                else:
                    raise Exception('API call failed, code {}'.format(code))

    def _perform_undeploy(self, props, cfg, macall, del_files=False):
        from eva.client import apiclient
        # ===== JOB DELETION =====
        print('Deleting scheduled jobs...')
        for i, v in self.dict_safe_get(cfg, 'job', {}).items():
            c = v.get('controller')
            print(' -- {}: {}'.format(c, i))
            code = macall({
                'i': c,
                'f': 'destroy_job',
                'p': {
                    'i': i
                }
            })[1].get('code')
            if code == apiclient.result_not_found:
                self.print_warn('Job not found')
            elif code != apiclient.result_ok:
                raise Exception('API call failed, code {}'.format(code))
        # ===== RULE DELETION =====
        print('Deleting decision rules...')
        for i, v in self.dict_safe_get(cfg, 'dmatrix_rule', {}).items():
            c = v.get('controller')
            print(' -- {}: {}'.format(c, i))
            code = macall({
                'i': c,
                'f': 'destroy_rule',
                'p': {
                    'i': i
                }
            })[1].get('code')
            if code == apiclient.result_not_found:
                self.print_warn('Rule not found')
            elif code != apiclient.result_ok:
                raise Exception('API call failed, code {}'.format(code))
        # ===== ITEM AND MACRO DELETION =====
        for tp in ['lcycle', 'lmacro', 'lvar', 'sensor', 'unit']:
            print('Deleting {}s...'.format(tp))
            for i, v in self.dict_safe_get(cfg, tp, {}).items():
                c = v.get('controller')
                print(' -- {}: {}:{}'.format(c, tp, i))
                df = 'destroy'
                if tp == 'lvar':
                    df += '_lvar'
                elif tp == 'lmacro':
                    df += '_macro'
                elif tp == 'lcycle':
                    df += '_cycle'
                code = macall({'i': c, 'f': df, 'p': {'i': i}})[1].get('code')
                if code == apiclient.result_not_found:
                    self.print_warn('{} {} not found'.format(tp, i))
                elif code != apiclient.result_ok:
                    raise Exception('API call failed, code {}'.format(code))
                if del_files:
                    for prop, val in v.items():
                        if prop in ['action_exec', 'update_exec'
                                   ] and val.startswith('^'):
                            file2del = os.path.basename(val[1:])
                        else:
                            file2del = None
                        if file2del:
                            remotefn = 'xc/{}/{}'.format(
                                'lm' if tp in ['lvar', 'lmacro'] else 'uc',
                                file2del)
                            code = macall({
                                'i': c,
                                'f': 'file_unlink',
                                'p': {
                                    'i': remotefn,
                                }
                            })[1].get('code')
                            if code == apiclient.result_not_found:
                                self.print_warn(
                                    'file {} not found'.format(remotefn))
                            elif code != apiclient.result_ok:
                                raise Exception(
                                    'File deletion failed, API code {}'.format(
                                        code))
        # ===== EXT UNLOAD =====
        print('Unloading extensions...')
        for c, v in self.dict_safe_get(cfg, 'controller', {}).items():
            if v:
                for i, vv in self.dict_safe_get(v, 'ext', {}).items():
                    print(' -- {}: {}'.format(c, i))
                    code = macall({
                        'i': c,
                        'f': 'unload_ext',
                        'p': {
                            'i': i,
                        }
                    })[1].get('code')
                    if code == apiclient.result_not_found:
                        self.print_warn('Extension {} not found'.format(i))
                    elif code != apiclient.result_ok:
                        raise Exception('API call failed, code {}'.format(code))
        # ===== DRIVERS UNLOAD =====
        print('Unloading drivers...')
        for c, v in self.dict_safe_get(cfg, 'controller', {}).items():
            if v:
                for i, vv in self.dict_safe_get(v, 'driver', {}).items():
                    print(' -- {}: {}'.format(c, i))
                    code = macall({
                        'i': c,
                        'f': 'unload_driver',
                        'p': {
                            'i': i,
                        }
                    })[1].get('code')
                    if code == apiclient.result_not_found:
                        self.print_warn('Driver {} not found'.format(i))
                    elif code == apiclient.result_busy:
                        self.print_warn('Driver {} is in use'.format(i))
                    elif code != apiclient.result_ok:
                        raise Exception('API call failed, code {}'.format(code))
        # ===== PHI UNLOAD =====
        print('Unloading PHIs...')
        for c, v in self.dict_safe_get(cfg, 'controller', {}).items():
            if v:
                for i, vv in self.dict_safe_get(v, 'phi', {}).items():
                    print(' -- {}: {}'.format(c, i))
                    code = macall({
                        'i': c,
                        'f': 'unload_phi',
                        'p': {
                            'i': i,
                        }
                    })[1].get('code')
                    if code == apiclient.result_not_found:
                        self.print_warn('PHI {} not found'.format(i))
                    elif code == apiclient.result_busy:
                        self.print_warn('PHI {} is in use'.format(i))
                    elif code != apiclient.result_ok:
                        raise Exception('API call failed, code {}'.format(code))
        # ===== CVARS =====
        print('Deleting cvars...')
        for c, v in self.dict_safe_get(cfg, 'controller', {}).items():
            if v:
                for i, vv in self.dict_safe_get(v, 'cvar', {}).items():
                    print(' -- {}: {}'.format(c, i))
                    code = macall({
                        'i': c,
                        'f': 'set_cvar',
                        'p': {
                            'i': i
                        }
                    })[1].get('code')
                    if code == apiclient.result_not_found:
                        self.print_warn('CVAR {} not found'.format(i))
                    elif code != apiclient.result_ok:
                        raise Exception('API call failed, code {}'.format(code))
        # ===== FILE DELETION =====
        if del_files:
            print('Deleting uploaded files...')
            for c, v in self.dict_safe_get(cfg, 'controller', {}).items():
                if v:
                    if 'upload-runtime' in v:
                        for f in v['upload-runtime']:
                            for fname, remote_file in self._get_files(f):
                                if not remote_file or remote_file.endswith('/'):
                                    remote_file += os.path.basename(fname)
                                if remote_file.startswith('/'):
                                    remote_file = remote_file[1:]
                                print(' -- {}: {}'.format(c, remote_file))
                                code = macall({
                                    'i': c,
                                    'f': 'file_unlink',
                                    'p': {
                                        'i': remote_file,
                                    }
                                })[1].get('code')
                                if code == apiclient.result_not_found:
                                    self.print_warn(
                                        'file {} not found'.format(remote_file))
                                elif code != apiclient.result_ok:
                                    raise Exception(
                                        'File deletion failed, API code {}'.
                                        format(code))


_me = 'EVA ICS SFA CLI version %s' % __version__

prog = os.path.basename(__file__)[:-3]
if prog == 'eva-shell':
    prog = 'eva sfa'

cli = SFA_CLI('sfa', _me, prog=prog)

_api_functions = {
    'history': 'state_history',
    'action:exec': 'action',
    'action:result': 'result',
    'action:enable': 'enable_actions',
    'action:disable': 'disable_actions',
    'action:terminate': 'terminate',
    'action:clear': 'q_clean',
    'action:kill': 'kill',
    'remote': 'list_remote',
    'cycle:list': 'list_cycles',
    'macro:list': 'list_macros',
    'macro:run': 'run',
    'macro:result': 'result',
    'controller:list': 'list_controllers',
    'controller:test': 'test_controller',
    'controller:ma-test': 'matest_controller',
    'controller:props': 'list_controller_props',
    'controller:set': 'set_controller_prop',
    'controller:reload': 'reload_controller',
    'controller:append': 'append_controller',
    'controller:enable': 'enable_controller',
    'controller:disable': 'disable_controller',
    'controller:remove': 'remove_controller',
    'controller:upnp-rescan': 'upnp_rescan_controllers',
    'notify:reload': 'reload_clients',
    'notify:restart': 'notify_restart',
    'cloud:deploy': cli.deploy,
    'cloud:undeploy': cli.undeploy
}

_pd_cols = {
    'state': [
        'oid', 'action_enabled', 'status', 'value', 'nstatus', 'nvalue', 'set',
        'exp_in'
    ],
    'state_': [
        'oid', 'action_enabled', 'description', 'location', 'status', 'value',
        'nstatus', 'nvalue', 'set', 'expires', 'exp_in'
    ],
    'result': [
        'time', 'uuid', 'priority', 'item_oid', 'nstatus', 'nvalue', 'exitcode',
        'status'
    ],
    'list_remote': [
        'oid', 'description', 'controller_id', 'status', 'value', 'nstatus',
        'nvalue'
    ],
    'list_macros': ['id', 'description', 'action_enabled'],
    'list_cycles': [
        'id', 'description', 'controller_id', 'status', 'int', 'iter'
    ],
    'list_controllers': [
        'id', 'type', 'enabled', 'connected', 'managed', 'proto', 'version',
        'build', 'description'
    ]
}

_pd_idx = {'state': 'oid', 'result': 'time'}

_fancy_indentsp = {}

_always_json = []

cli.always_json += _always_json
cli.always_print += ['action', 'action_toggle', 'run', 'cmd']
cli.arg_sections += [
    'action', 'macro', 'cycle', 'notify', 'controller', 'cloud', 'supervisor'
]
cli.api_cmds_timeout_correction = ['cmd', 'action', 'run']
cli.set_api_functions(_api_functions)
cli.set_pd_cols(_pd_cols)
cli.set_fancy_indentsp(_fancy_indentsp)
code = cli.run()
eva.client.cli.subshell_exit_code = code
sys.exit(code)
