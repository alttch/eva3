__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.2"

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
            params['t'] = 'iso'
            if params['c']:
                params['g'] = 'chart'
        if api_func == 'state_log':
            params['t'] = 'iso'
        return super().prepare_run(api_func, params, a)

    def prepare_result_data(self, data, api_func, itype):
        if api_func == 'state_log':
            if data:
                for v in data:
                    v['time'] = v['t']
                    del v['t']
        if api_func not in [
                'state', 'list_macros', 'list_cycles', 'list_controllers',
                'result'
        ] and itype not in ['action']:
            return super().prepare_result_data(data, api_func, itype)
        result = []
        for d in data.copy():
            if itype == 'action' or api_func == 'result':
                from datetime import datetime
                import pytz
                import time
                tz = pytz.timezone(time.tzname[0])
                d['time'] = datetime.fromtimestamp(d['time']['created'],
                                                   tz).isoformat()
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
                    import pytz
                    import time
                    tz = pytz.timezone(time.tzname[0])
                    d['set'] = datetime.fromtimestamp(d['set_time'],
                                                      tz).isoformat()
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
        elif api_func in ['result', 'run', 'action', 'action_toggle'
                         ] and 'created' in data:
            from datetime import datetime
            for x in data.keys():
                import pytz
                import time
                tz = pytz.timezone(time.tzname[0])
                data[x] = '{:.7f} | {}'.format(
                    data[x],
                    datetime.fromtimestamp(data[x], tz).isoformat())
            return super().prepare_result_dict(data, api_func, itype)
        else:
            return super().prepare_result_dict(data, api_func, itype)

    def setup_parser(self):
        super().setup_parser()
        self.full_management = True
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
        sp_history.add_argument(
            '-z',
            '--time-zone',
            help='Time zone (pytz, e.g. UTC or Europe/Prague)',
            metavar='ZONE',
            dest='z')
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
            help='Fill (i.e. 1T - 1 min, 2H - 2 hours), requires start time, '
            'value precision can be specified as e.g. 1T:2 for 2 digits'
            ' after comma',
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

        sp_slog = self.sp.add_parser('slog', help='Get item state log')
        sp_slog.add_argument('i',
                             help='Item ID or OID mask (type:group/#)',
                             metavar='ID').completer = self.ComplItemOID(self)
        sp_slog.add_argument('-a',
                             '--notifier',
                             help='Notifier to get slog from (default: db_1)',
                             metavar='NOTIFIER',
                             dest='a')
        sp_slog.add_argument('-s',
                             '--time-start',
                             help='Start time',
                             metavar='TIME',
                             dest='s')
        sp_slog.add_argument('-e',
                             '--time-end',
                             help='End time',
                             metavar='TIME',
                             dest='e')
        sp_slog.add_argument('-z',
                             '--time-zone',
                             help='Time zone (pytz, e.g. UTC or Europe/Prague)',
                             metavar='ZONE',
                             dest='z')
        sp_slog.add_argument('-l',
                             '--limit',
                             help='Records limit',
                             metavar='N',
                             dest='l')

        sp_watch = self.sp.add_parser('watch', help='Watch item state')
        sp_watch.add_argument('i',
                              help='Item ID (specify either ID or item type)',
                              metavar='ID').completer = self.ComplItemOID(self)
        sp_watch.add_argument('-r',
                              '--interval',
                              help='Watch interval (default: 1s)',
                              metavar='SEC',
                              default=1,
                              type=float,
                              dest='r')
        sp_watch.add_argument('-n',
                              '--rows',
                              help='Rows to plot',
                              metavar='NUM',
                              type=int,
                              dest='n')
        sp_watch.add_argument('-x',
                              '--prop',
                              help='State prop to use (default: value)',
                              choices=['status', 'value'],
                              metavar='PROP',
                              default='value',
                              dest='x')
        sp_watch.add_argument('-p',
                              '--chart-type',
                              help='Chart type',
                              choices=['bar', 'line'],
                              default='bar')

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
            help='Action state (Q, R, F, D: queued, running, finished, dead)',
            metavar='STATE',
            dest='s',
            choices=[
                'queued', 'running', 'finished', 'dead', 'Q', 'R', 'F', 'D'
            ])

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
        sp_cloud_deploy.add_argument('f',
                                     help='Deploy file ("-" for STDIN)',
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
            '--test',
            help='Test configuration without deployment',
            dest='test',
            action='store_true')

        sp_cloud_undeploy = sp_cloud.add_parser(
            'undeploy', help='Undeploy items and configuration from file')
        sp_cloud_undeploy.add_argument(
            'f', help='Deploy file ("-" for STDIN)',
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

        sp_cloud_update = sp_cloud.add_parser('update',
                                              help='Update cloud nodes')
        sp_cloud_update.add_argument(
            '--test',
            help='Test update plan without actual updating',
            dest='test',
            action='store_true')
        sp_cloud_update.add_argument(
            '-S',
            '--shutdown-delay',
            help='Controller shutdown delay before checking (default: 30 sec)',
            default=30,
            metavar='SEC',
            type=float,
            dest='s')
        sp_cloud_update.add_argument(
            '-C',
            '--check-timeout',
            help='Max node update duration (default: 60 sec)',
            default=60,
            metavar='SEC',
            type=float,
            dest='c')
        sp_cloud_update.add_argument('--YES',
                                     dest='y',
                                     help='Update without any prompts',
                                     action='store_true')

    # cloud management

    @staticmethod
    def _get_build():
        dir_sbin = dir_eva + '/sbin'
        with os.popen('{}/eva-tinyapi -B'.format(dir_sbin)) as p:
            data = p.read()
            return int(data.strip())

    @staticmethod
    def _get_version():
        dir_sbin = dir_eva + '/sbin'
        with os.popen('{}/eva-tinyapi -V'.format(dir_sbin)) as p:
            data = p.read()
            version = data.strip()
            int(version.split('.')[0])
            return version

    def cloud_update(self, params):
        from eva.client import apiclient
        from functools import partial
        debug = params.get('_debug')
        update_timeout = params.get('c')
        shutdown_delay = params.get('s')
        api = params['_api']
        call = partial(api.call,
                       timeout=params.get('_timeout', self.default_timeout),
                       _debug=params.get('_debug'))
        macall = partial(call, 'management_api_call')
        code, test = call('test')
        if code != apiclient.result_ok or not test.get('ok'):
            raise Exception('SFA API is inaccessible, code: {}'.format(code))
        my_build = self._get_build()
        my_version = self._get_version()
        print('Collecting data...')
        code, data = call('list_controllers')
        if code != apiclient.result_ok:
            raise Exception(
                'Unable to list controllers, API code: {}'.format(code))
        nodes = {}
        for c in data:
            if c['enabled'] and c['connected'] and c['managed'] and int(
                    c['build']) < my_build:
                if int(c['build']) < 2020121702:
                    if debug:
                        self.print_debug(
                            f'{c["oid"]} build is lower than 2020121702')
                    continue
                node = c['id']
                if node not in nodes:
                    if debug:
                        self.print_debug('ma-test ' + c['oid'])
                    code, result = call('matest_controller', {'i': c['oid']})
                    if code != apiclient.result_ok:
                        self.print_warn(
                            f'Skipping {c["full_id"]} (ma-test code {code})')
                    else:
                        nodes[node] = c['full_id']
        controllers = []
        for c in data:
            if c['enabled'] and c['connected']:
                node = c['id']
                if node in nodes:
                    controllers.append((c['full_id'], node))
        if not nodes:
            print('No update candidates found')
            return self.local_func_result_empty
        print()
        self.print_warn('make sure all nodes have either '
                        'the Internet connection or valid mirror setup')
        print('Update logs will be '
              'available on each node at EVA_DIR/log/update.log')
        print()
        print('Nodes to update:')
        for n, v in nodes.items():
            print(f' -- {n} -> via {v}')
        print(f'Controllers to check (have to be up in {update_timeout} sec):')
        for c in controllers:
            print(f' -- {c[0]}')
        if params.get('test'):
            return self.local_func_result_ok
        if not params.get('y'):
            print()
            try:
                u = input('Type ' +
                          self.colored('YES', color='red', attrs=['bold']) +
                          ' (uppercase) to update, or press ' +
                          self.colored('ENTER', color='white') + ' to abort > ')
            except:
                print()
                u = ''
            if u != 'YES':
                return self.local_func_result_empty
        print()
        print('Sending update node commands...')
        update_result = self.local_func_result_ok
        for n, v in nodes.items():
            print(f'{n}: ', end='', flush=True)
            try:
                code = macall({
                    'i': v,
                    'f': 'update_node',
                    'p': {
                        'v': f'{my_version}:{my_build}',
                        'y': 'YES'
                    }
                })[1].get('code')
                if code != apiclient.result_ok:
                    raise Exception(f'failed, code {code}')
                print('OK')
            except Exception as e:
                for c in controllers.copy():
                    if c[1] == n:
                        controllers.remove(c)
                self.print_err(e)
                update_result = self.local_func_result_failed

        pbar = ''
        import time

        def fancy_sleep(msg=''):
            nonlocal pbar
            if sys.stdout.isatty():
                pbar += '.'
                print(msg + pbar, end='', flush=True)
                if len(pbar) > 3:
                    print('\r', end='')
                    print(' ' * (4 + len(msg)), end='\r', flush=True)
                    print(msg, end='', flush=True)
                    pbar = ''
            time.sleep(1)
            if sys.stdout.isatty():
                print('\r', end='', flush=True)

        if controllers:
            for t in range(int(shutdown_delay)):
                fancy_sleep('Waiting for update')
            print()
            time_limit = time.perf_counter() + update_timeout
            pbar = ''
            while controllers and time.perf_counter() < time_limit:
                for c in controllers.copy():
                    if debug:
                        self.print_debug(c[0])
                    code, data = call('reload_controller', {'i': c[0]})
                    if code == apiclient.result_ok:
                        time.sleep(1)
                        code, data = call('get_controller', {'i': c[0]})
                        if int(data['build']) == my_build:
                            print(
                                self.colored(c[0] + ' -> OK',
                                             color='green',
                                             attrs='bold'))
                        else:
                            self.print_warn(
                                f'{c[0]} -> FAILED! (update not applied or '
                                'wrong build installed)')
                            update_result = self.local_func_result_failed
                        controllers.remove(c)
                if controllers:
                    fancy_sleep()
            else:
                if controllers:
                    for c, n in controllers:
                        self.print_err(f'CRITICAL: {c} NOT STARTED')
                        update_result = self.local_func_result_failed
        return update_result

    @staticmethod
    def _api_error(code):
        api_errors = {
            1: 'Resource not found',
            2: 'Access denied',
            3: 'API client error',
            4: 'Uknown error',
            5: 'API not ready',
            6: 'Function unknown',
            7: 'Server error',
            8: 'Server timeout',
            9: 'Invalid request data',
            10: 'Function failed, please read controller logs',
            11: 'Invalid function params',
            12: 'Resource already exists',
            13: 'Resource busy',
            14: 'Method not implemented',
            15: 'Token restricted'
        }
        error = api_errors.get(code, 'Unlisted error')
        return f'API call failed, code: {code} ({error})'

    @staticmethod
    def _read_stdin(props):
        if props.get('f') == '-':
            props['__stdin'] = sys.stdin.read()

    def deploy(self, props):
        from eva.client import apiclient
        self._read_stdin(props)
        if props.get('und'):
            code, result = self.undeploy(props, read_stdin=False)
            if code != apiclient.result_ok:
                return code, result
        return self._deploy_undeploy(props, und=False)

    def undeploy(self, props, read_stdin=True):
        from eva.client import apiclient
        if read_stdin:
            self._read_stdin(props)
        return self._deploy_undeploy(props,
                                     und=True,
                                     del_files=props.get('del_files', False))

    def _deploy_undeploy(self, props, und=False, del_files=False):
        import yaml
        try:
            yaml.warnings({'YAMLLoadWarning': False})
        except:
            pass
        from eva.client import apiclient
        from eva.tools import validate_schema
        from eva.tools import read_uri
        test_mode = props.get('test')
        try:
            try:
                import yaml
                from eva.tools import render_template
                fname = props.get('f')
                if fname == '-':
                    dirname = '.'
                    tplc = props['__stdin']
                else:
                    dirname = os.path.dirname(fname)
                    tplc = read_uri(fname)
                ys = render_template(tplc, props.get('c'), raw=True)
                if test_mode:
                    self.print_debug('-' * 3)
                    self.print_debug(ys)
                    self.print_debug('-' * 3)
                cfg = yaml.load(ys)
                validate_schema(cfg, 'deploy')
            except Exception as e:
                raise Exception('Unable to parse {}: {}'.format(fname, e))
            api = props['_api']
            from functools import partial
            timeout = props.get('_timeout', self.default_timeout)
            call = partial(api.call,
                           timeout=timeout,
                           _debug=props.get('_debug'))
            code, test = call('test')
            if code != apiclient.result_ok or not test.get('ok'):
                raise Exception('SFA API is inaccessible, ' +
                                self._api_error(code))
            if not test.get('acl', {}).get('master'):
                self.print_err('Masterkey is required')
            if not test.get('cloud_manager'):
                raise Exception(
                    'SFA is not Cloud Manager. Enable feature in sfa.ini first')
            print('Checking deployment config...')
            for c in cfg.keys() if cfg else []:
                if c.replace('-', '_') not in [
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
            ucs_to_reload = set()
            for x in [
                    'unit', 'sensor', 'lvar', 'lmacro', 'lcycle',
                    'dmatrix_rule', 'job'
            ]:
                for i, v in self.dict_safe_get(cfg, x, {}).items():
                    if not v or not 'controller' in v:
                        raise Exception(
                            'No controller specified for {} {}'.format(x, i))
                    if x in ['unit', 'sensor']:
                        if not v['controller'].startswith('uc/'):
                            raise Exception(
                                'Invalid controller specified ' +
                                'for {} {} (uc required)'.format(x, i))
                        else:
                            ucs_to_reload.add(v['controller'])
                    if x in ['lvar', 'lmacro', 'lcycle', 'dmatrix_rule', 'job'
                            ] and not v['controller'].startswith('lm/'):
                        raise Exception('Invalid controller specified ' +
                                        'for {} {} (lm required)'.format(x, i))
                    controllers.add(v['controller'])
                    for p in ['action_exec', 'update_exec']:
                        if self.dict_safe_get(v, p, '').startswith('^'):
                            if not und:
                                try:
                                    read_uri(v[p][1:], dirname, check_only=True)
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
                                        read_uri(fname,
                                                 dirname,
                                                 'rb',
                                                 check_only=True)
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
                                    read_uri(fname,
                                             dirname,
                                             'rb',
                                             check_only=True)
                                except:
                                    raise Exception(
                                        ('{}: {} unable to open ' +
                                         'file for upload').format(c, fname))
            macall = partial(call, 'management_api_call')
            for c in controllers:
                if c != 'local':
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
                        raise Exception(
                            'Controller {} access forbidden'.format(c))
                    if code != apiclient.result_ok:
                        raise Exception(f'Controller {c} ' +
                                        self._api_error(code))
                    if not ctest.get('acl', {}).get('master'):
                        raise Exception(
                            'Controller {} master access is not set up'.format(
                                c))
                    if c in controllers_fm_required and not ctest.get(
                            'file_management'):
                        raise Exception(
                            'Controller {} file management API is disabled'.
                            format(c))
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

            def _fmt_params(func, params):
                if isinstance(params, dict):
                    params = params.copy()
                    if func == 'install_pkg':
                        del params['m']
                return params

            def execute_custom_tasks(step):
                cs = self.dict_safe_get(cfg, 'controller', {}).copy()
                local = self.dict_safe_get(cs, 'local', {}).copy()
                if local:
                    lc = [('local', local)]
                    del cs['local']
                else:
                    lc = []
                cs_items = [(k, v) for k, v in cs.items()] + lc
                for c, v in cs_items:
                    if v:
                        for a in self.dict_safe_get(
                                v, '{}-{}deploy'.format(step,
                                                        'un' if und else ''),
                            []):
                            wait_online = False
                            if 'install-pkg' in a:
                                a['api'] = 'install_pkg'
                                fname = a['install-pkg']
                                a['i'] = Path(fname).stem
                                a['m'] = read_uri(fname,
                                                  dirname,
                                                  'rb',
                                                  b64=True)
                                del a['install-pkg']
                            if 'api' in a:
                                try:
                                    func = a['api']
                                    can_pass_err = a.get('_pass')
                                    custom_timeout = a.get('_timeout', timeout)
                                    params = a.copy()
                                    del params['api']
                                    for p in ['_pass', '_timeout']:
                                        try:
                                            del params[p]
                                        except:
                                            pass
                                    if func == 'reboot_controller':
                                        func = 'shutdown_core'
                                        wait = params.get('wait', 30)
                                        for p in ['wait']:
                                            try:
                                                del params[p]
                                            except:
                                                pass
                                        wait_online = True
                                except Exception as e:
                                    raise Exception(
                                        ('Controller {}, '
                                         'invalid before-{}deploy, {} {}'
                                        ).format(c, 'un' if und else '',
                                                 e.__class__.__name__, e))
                            elif 'cm-api' in a:
                                try:
                                    func = a['cm-api']
                                    can_pass_err = a.get('_pass')
                                    custom_timeout = a.get('_timeout', timeout)
                                    params = a.copy()
                                    del params['cm-api']
                                    for p in ['_pass', '_timeout']:
                                        try:
                                            del params[p]
                                        except:
                                            pass
                                    if func == 'reboot_controller':
                                        func = 'shutdown_core'
                                        wait = params.get('wait', 30)
                                        for p in ['wait']:
                                            try:
                                                del params[p]
                                            except:
                                                pass
                                        wait_online = True
                                except Exception as e:
                                    raise Exception(
                                        ('Controller {}, '
                                         'invalid before-{}deploy, {} {}'
                                        ).format(c, 'un' if und else '',
                                                 e.__class__.__name__, e))
                            else:
                                f = a['function']
                                expect_result = None
                                if f == 'sleep':
                                    func = time.sleep
                                elif f == 'system':
                                    func = os.system
                                    expect_result = 0
                                else:
                                    raise RuntimeError(
                                        f'function unsupported: {f}')
                                args = a.get('args', [])
                                kwargs = a.get('kwargs', {})
                                params = str(args) + ' ' + str(kwargs)
                            print(' -- {}: {} {}'.format(
                                '' if callable(func) else c,
                                func.__name__ if callable(func) else func,
                                _fmt_params(func, params)))
                            if callable(func):
                                result = func(*args, **kwargs)
                                if expect_result is not None and \
                                        result != expect_result:
                                    raise RuntimeError(
                                        f'function failed: {result: {result}}')
                            elif 'api' in a:
                                if c == 'local':
                                    code, data = api.call(
                                        func, params, timeout=custom_timeout)
                                else:
                                    result = macall({
                                        'i': c,
                                        'f': func,
                                        'p': params,
                                        't': custom_timeout
                                    })[1]
                                    code = result.get('code')
                                    data = result.get('data', {})
                                if code != apiclient.result_ok:
                                    msg = self._api_error(code)
                                    if can_pass_err and \
                                        code != apiclient.result_server_error:
                                        self.print_warn(msg)
                                    else:
                                        raise Exception(msg)
                                elif func in ['cmd', 'install_pkg'
                                             ] and data.get('exitcode'):
                                    msg = (f'API call failed, '
                                           f'stderr:\n{data.get("err")}')
                                    if can_pass_err and \
                                        code != apiclient.result_server_error:
                                        self.print_warn(msg)
                                    else:
                                        raise Exception(msg)
                            elif 'cm-api' in a:
                                code, data = api.call(func,
                                                      params,
                                                      timeout=custom_timeout)
                                if code != apiclient.result_ok:
                                    msg = self._api_error(code)
                                    if can_pass_err and \
                                        code != apiclient.result_server_error:
                                        self.print_warn(msg)
                                    else:
                                        raise Exception(msg)
                                elif func == 'cmd' and data.get('exitcode'):
                                    msg = (f'cmd call failed, '
                                           f'stderr:\n{data.get("err")}')
                                    if can_pass_err and \
                                        code != apiclient.result_server_error:
                                        self.print_warn(msg)
                                    else:
                                        raise Exception(msg)
                            else:
                                raise RuntimeError('Invalid section')
                            if wait_online:
                                prev_boot_id = data.get('boot_id', 0)
                                boot_id = prev_boot_id
                                if 'api' in a:
                                    cname = c
                                elif 'cm-api' in a:
                                    cname = 'local'
                                print(
                                    f'waiting controller {cname} back online '
                                    f'(max: {wait} sec)...',
                                    end='',
                                    flush=True)
                                time_to_wait = time.perf_counter() + wait
                                code = -1
                                while boot_id <= prev_boot_id:
                                    time.sleep(0.5)
                                    if time.perf_counter() > time_to_wait:
                                        print()
                                        raise RuntimeError('wait timeout')
                                    print('.', end='', flush=True)
                                    if 'api' in a:
                                        result = macall({
                                            'i': c,
                                            'f': 'test',
                                            'p': {},
                                            't': custom_timeout
                                        })[1]
                                        code = result.get('code')
                                        data = result.get('data', {})
                                    elif 'cm-api' in a:
                                        code, data = api.call(
                                            'test', timeout=custom_timeout)
                                    else:
                                        raise RuntimeError
                                    if code == apiclient.result_ok:
                                        boot_id = data.get('boot_id')
                                print()

            execute_custom_tasks('before')
            # ===== CALL DEPLOY/UNDEPLOY =====
            if not und:
                self._perform_deploy(props, cfg, call, macall, dirname)
            else:
                self._perform_undeploy(props, cfg, call, macall, del_files)
            # ===== AFTER TASKS =====
            print('Executing commands in after-{}deploy...'.format(
                'un' if und else ''))
            execute_custom_tasks('after')
            if props.get('save'):
                print('Saving configurations')
                for c in controllers:
                    print(' -- {}'.format(c))
                    if c == 'local':
                        code = call('save')[0]
                    else:
                        code = macall({
                            'i': c,
                            'f': 'save',
                        })[1].get('code')
                    if code != apiclient.result_ok:
                        self.print_warn(
                            'Unable to save: {self._api_error(code)}')
            if ucs_to_reload:
                print('Reloading LM PLCs')
                for c in controllers:
                    if c.startswith('lm/'):
                        print(f' -- {c}')
                        result = macall({
                            'i': c,
                            'f': 'list_controllers',
                        })[1]
                        code = result.get('code')
                        data = result.get('data')
                        if code != apiclient.result_ok:
                            raise Exception(self._api_error(code))
                        for d in data:
                            cid = d['full_id']
                            if cid in ucs_to_reload:
                                print(f'      {cid}')
                                code = macall({
                                    'i': c,
                                    'f': 'reload_controller',
                                    'p': {
                                        'i': cid
                                    }
                                })[1].get('code')
                                if code != apiclient.result_ok:
                                    raise Exception(self._api_error(code))
            print('Reloading local SFA')
            for c in controllers:
                if c != 'local':
                    print(' -- {}'.format(c))
                    code = call('reload_controller', {'i': c})[0]
                    if code != apiclient.result_ok:
                        raise Exception(self._api_error(code))
        except Exception as e:
            self.print_err(e)
            return self.local_func_result_failed
        print()
        print('{}eployment completed for {}'.format(
            'Und' if und else 'D',
            'STDIN' if props['f'] == '-' else props['f']))
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

    def _perform_deploy(self, props, cfg, call, macall, dirname):

        skip_existing = props.get('skip')
        from eva.client import apiclient
        from eva.tools import read_uri
        # ===== FILE UPLOAD =====
        print('Uploading files...')
        for c, v in self.dict_safe_get(cfg, 'controller', {}).items():
            if v:
                if 'upload-runtime' in v:
                    for f in v['upload-runtime']:
                        for fname, remote_file in self._get_files(f):
                            print(' -- {}: {} -> {}'.format(
                                c, fname, remote_file))
                            code = 0
                            code = macall({
                                'i': c,
                                'f': 'file_put',
                                'p': {
                                    'i':
                                        remote_file,
                                    'm':
                                        read_uri(fname, dirname, 'rb',
                                                 b64=True),
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
                        raise Exception(self._api_error(code))
        # ===== API Keys =====
        print('Creating API keys...')
        for c, v in self.dict_safe_get(cfg, 'controller', {}).items():
            if v:
                for i, vv in self.dict_safe_get(v, 'key', {}).items():
                    print(' -- {}: {}'.format(c, i))
                    if c == 'local':
                        code = call('create_key', {'i': i})[0]
                    else:
                        code = macall({
                            'i': c,
                            'f': 'create_key',
                            'p': {
                                'i': i
                            }
                        })[1].get('code')
                    if code != apiclient.result_ok:
                        if code == apiclient.result_already_exists and \
                                skip_existing:
                            print('    [skipped]')
                        else:
                            raise Exception(self._api_error(code))
                    for prop, value in vv.items():
                        print('     -- {}={}'.format(prop, value))
                        if c == 'local':
                            code = call('set_key_prop', {
                                'i': i,
                                'p': prop,
                                'v': value
                            })[0]
                        else:
                            code = macall({
                                'i': c,
                                'f': 'set_key_prop',
                                'p': {
                                    'i': i,
                                    'p': prop,
                                    'v': value
                                }
                            })[1].get('code')
                        if code != apiclient.result_ok:
                            raise Exception(self._api_error(code))
        print('Creating local users...')
        for c, v in self.dict_safe_get(cfg, 'controller', {}).items():
            if v:
                for i, vv in self.dict_safe_get(v, 'user', {}).items():
                    print(' -- {}: {}'.format(c, i))
                    if c == 'local':
                        code = call('create_user', {
                            'u': i,
                            'p': vv['password'],
                            'a': vv['key']
                        })[0]
                    else:
                        code = macall({
                            'i': c,
                            'f': 'create_user',
                            'p': {
                                'u': i,
                                'p': vv['password'],
                                'a': vv['key']
                            }
                        })[1].get('code')
                    if code != apiclient.result_ok:
                        if code == apiclient.result_already_exists and \
                                skip_existing:
                            print('    [skipped]')
                            for prop, value in vv.items():
                                print('     -- {}={}'.format(prop, value))
                                if c == 'local':
                                    code = call('user.set', {
                                        'u': i,
                                        'p': prop,
                                        'v': value
                                    })[0]

                                else:
                                    code = macall({
                                        'i': c,
                                        'f': 'user.set',
                                        'p': {
                                            'u': i,
                                            'p': prop,
                                            'v': value
                                        }
                                    })[1].get('code')
                                if code != apiclient.result_ok:
                                    raise Exception(self._api_error(code))
                        else:
                            raise Exception(self._api_error(code))
        # ===== PHI =====
        print('Loading PHIs...')
        for c, v in self.dict_safe_get(cfg, 'controller', {}).items():
            if v:
                for i, vv in self.dict_safe_get(v, 'phi', {}).items():
                    print(' -- {}: {} -> {}'.format(c, vv['module'], i))
                    if 'src' in vv:
                        print(' -- {}: {} -> {}'.format(c, vv['src'], i))
                        mod_source = read_uri(vv['src'])
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
                            raise Exception(self._api_error(code))
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
                        raise Exception(self._api_error(code))
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
                        raise Exception(self._api_error(code))
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
                        raise Exception(self._api_error(code))
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
                        raise Exception(self._api_error(code))
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
                        raise Exception('Driver assign ' +
                                        self._api_error(code))
                for prop, val in item_props.items():
                    if prop in ['action_exec', 'update_exec'
                               ] and val.startswith('^'):
                        file2u = val[1:]
                        val = os.path.basename(val[1:])
                    elif tp == 'lmacro' and prop == 'src':
                        prop = ''
                        file2u = val
                        val = os.path.basename(val)
                    else:
                        file2u = None
                    prop = prop.replace('-', '_')
                    if prop:
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
                            if val != 'update':
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
                    elif prop:
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
                        raise Exception(self._api_error(code))
                    if file2u:
                        if tp == 'lmacro' and 'action_exec' not in item_props:
                            fx = os.path.basename(file2u)
                            if '.' in fx:
                                ext = '.' + fx.rsplit('.', 1)[-1]
                            rf = f'{i}{ext}'
                        else:
                            rf = val
                        remotefn = 'xc/{}/{}'.format(
                            'lm' if tp in ['lvar', 'lmacro'] else 'uc', rf)
                        code = macall({
                            'i': c,
                            'f': 'file_put',
                            'p': {
                                'i': remotefn,
                                'm': read_uri(file2u, dirname)
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
        for i, v in self.dict_safe_get(
                cfg, 'dmatrix_rule', self.dict_safe_get(cfg, 'dmatrix-rule',
                                                        {})).items():
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
                    raise Exception(self._api_error(code))
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
                    raise Exception(self._api_error(code))
        # ===== Plugin deployment =====
        for c, v in self.dict_safe_get(cfg, 'controller', {}).items():
            if v:
                if 'plugins' in v:
                    print(f'Deploying plugins into {c}')
                for i, vv in self.dict_safe_get(v, 'plugins', {}).items():
                    print(' -- {}: {}'.format(c, i))
                    mod_source = read_uri(vv['src'])
                    code = macall({
                        'i': c,
                        'f': 'install_plugin',
                        'p': {
                            'i': i,
                            'm': mod_source,
                            'c': vv.get('config')
                        }
                    })[1].get('code')
                    if code != apiclient.result_ok:
                        if code == apiclient.result_already_exists and \
                                skip_existing:
                            print('    [skipped]')
                        else:
                            raise Exception(self._api_error(code))

    def _perform_undeploy(self, props, cfg, call, macall, del_files=False):
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
                raise Exception(self._api_error(code))
        # ===== RULE DELETION =====
        print('Deleting decision rules...')
        for i, v in self.dict_safe_get(
                cfg, 'dmatrix_rule', self.dict_safe_get(cfg, 'dmatrix-rule',
                                                        {})).items():
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
                raise Exception(self._api_error(code))
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
                    raise Exception(self._api_error(code))
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
                        raise Exception(self._api_error(code))
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
                        raise Exception(self._api_error(code))
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
                        raise Exception(self._api_error(code))
        print('Deleting local users...')
        for c, v in self.dict_safe_get(cfg, 'controller', {}).items():
            if v:
                for i, vv in self.dict_safe_get(v, 'user', {}).items():
                    print(' -- {}: {}'.format(c, i))
                    if c == 'local':
                        code = call('destroy_user', {'u': i})[0]
                    else:
                        code = macall({
                            'i': c,
                            'f': 'destroy_user',
                            'p': {
                                'u': i
                            }
                        })[1].get('code')
                    if code == apiclient.result_not_found:
                        self.print_warn('User {} not found'.format(i))
                    elif code != apiclient.result_ok:
                        raise Exception(self._api_error(code))
        print('Deleting API keys...')
        for c, v in self.dict_safe_get(cfg, 'controller', {}).items():
            if v:
                for i, vv in self.dict_safe_get(v, 'key', {}).items():
                    print(' -- {}: {}'.format(c, i))
                    if c == 'local':
                        code = call('destroy_key', {'i': i})[0]
                    else:
                        code = macall({
                            'i': c,
                            'f': 'destroy_key',
                            'p': {
                                'i': i
                            }
                        })[1].get('code')
                    if code == apiclient.result_not_found:
                        self.print_warn('API key {} not found'.format(i))
                    elif code != apiclient.result_ok:
                        raise Exception(self._api_error(code))
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
                        raise Exception(self._api_error(code))
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
        # ===== Plugin undeployment =====
        for c, v in self.dict_safe_get(cfg, 'controller', {}).items():
            if v:
                if 'plugins' in v:
                    print(f'Undeploying plugins from {c}')
                for i, vv in self.dict_safe_get(v, 'plugins', {}).items():
                    print(' -- {}: {}'.format(c, i))
                    code = macall({
                        'i': c,
                        'f': 'uninstall_plugin',
                        'p': {
                            'i': i
                        }
                    })[1].get('code')
                    if code == apiclient.result_not_found:
                        self.print_warn('Plugin {} not found'.format(i))
                    elif code != apiclient.result_ok:
                        raise Exception(
                            'Plugin undeployment failed, API code {}'.format(
                                code))

    def watch(self, props):
        self.watch_item(props['i'],
                        interval=props['r'],
                        rows=props['n'],
                        prop=props['x'],
                        chart_type=props['chart_type'])
        return self.local_func_result_empty


_me = 'EVA ICS SFA CLI version %s' % __version__

prog = os.path.basename(__file__)[:-3]
if prog == 'eva-shell':
    prog = 'eva sfa'

cli = SFA_CLI('sfa', _me, prog=prog)

_api_functions = {
    'watch': cli.watch,
    'history': 'state_history',
    'slog': 'state_log',
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
    'cloud:undeploy': cli.undeploy,
    'cloud:update': cli.cloud_update
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
    'state_log': ['time', 'oid', 'status', 'value'],
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
