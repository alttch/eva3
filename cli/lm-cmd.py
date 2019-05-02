__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.2"

import sys
import os

dir_lib = os.path.dirname(os.path.realpath(__file__)) + '/../lib'
dir_runtime = os.path.realpath(
    os.path.dirname(os.path.realpath(__file__)) + '/../runtime')
sys.path.append(dir_lib)

from eva.client.cli import GenericCLI
from eva.client.cli import ControllerCLI
from eva.client.cli import ComplGeneric


class LM_CLI(GenericCLI, ControllerCLI):

    class ComplLVAR(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call('state -p lvar')
            if code: return True
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

    class ComplItemOIDType(object):

        def __call__(self, prefix, **kwargs):
            return ['lvar:'] if prefix.find(':') == -1 else True

    class ComplLVARGroup(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call('state -p lvar')
            if code: return True
            result = set()
            for v in data:
                result.add(v['group'])
            return list(result)

    class ComplLVARProp(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call(
                ['config', 'props',
                 kwargs.get('parsed_args').i])
            if code: return True
            result = list(data.keys())
            return result

    class ComplMacro(ComplGeneric):

        def __init__(self, cli, with_common=False):
            self.with_common = with_common
            super().__init__(cli)

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call('macro list')
            if code: return True
            result = set()
            for v in data:
                result.add(v['id'])
                result.add(v['full_id'])
            if self.with_common:
                result.add('common.py')
            return list(result)

    class ComplCycle(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call('cycle list')
            if code: return True
            result = set()
            for v in data:
                result.add(v['id'])
                result.add(v['full_id'])
            return list(result)

    class ComplMacroGroup(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call('macro list')
            if code: return True
            result = set()
            for v in data:
                result.add(v['group'])
            return list(result)

    class ComplCycleGroup(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call('cycle list')
            if code: return True
            result = set()
            for v in data:
                result.add(v['group'])
            return list(result)

    class ComplMacroProp(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call(
                ['macro', 'props',
                 kwargs.get('parsed_args').i])
            if code: return True
            result = list(data.keys())
            return result

    class ComplCycleProp(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call(
                ['cycle', 'props',
                 kwargs.get('parsed_args').i])
            if code: return True
            result = list(data.keys())
            return result

    class ComplExt(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call('ext list')
            if code: return True
            result = set()
            for v in data:
                result.add(v['id'])
            return list(result)

    class ComplExtMods(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call('ext mods')
            if code: return True
            result = set()
            for v in data:
                result.add(v['mod'])
            return list(result)

    class ComplController(ComplGeneric):

        def __init__(self, cli, allow_all=False):
            super().__init__(cli)
            self.allow_all = allow_all

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call('controller list')
            if code: return True
            result = set()
            if self.allow_all:
                result.add('all')
            for v in data:
                result.add(v['id'])
                result.add(v['full_id'])
            return list(result)

    class ComplControllerProp(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call(
                ['controller', 'props',
                 kwargs.get('parsed_args').i])
            if code: return True
            result = list(data.keys())
            return result

    class ComplRemoteGroup(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            opts = []
            if not kwargs.get('ignore_p') and hasattr(
                    kwargs.get('parsed_args'), 'p'):
                p = kwargs.get('parsed_args').p
                if p:
                    opts = ['-p', p]
            code, data = self.cli.call(['remote'] + opts)
            if code: return True
            result = set()
            for v in data:
                result.add(v['group'])
            return list(result)

    class ComplRule(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call('rule list')
            if code: return True
            result = set()
            for v in data:
                result.add(v['id'])
            return list(result)

    class ComplRuleProp(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call(
                ['rule', 'props', kwargs.get('parsed_args').i])
            if code: return True
            result = list(data.keys())
            result.append('oid')
            return result

    class ComplRulePropVal(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            p = kwargs.get('parsed_args').p
            if p == 'macro':
                return self.cli.ComplMacro(self.cli)(prefix, **kwargs)
            if p == 'for_initial':
                return ['skip', 'only', 'any']
            if p == 'for_item_type':
                return ['unit', 'sensor', 'lvar', '#']
            if p == 'for_prop':
                return ['status', 'value', '#']
            if p == 'for_item_group':
                kwargs['ignore_p'] = True
                result = self.cli.ComplRemoteGroup(self.cli)(prefix, **kwargs)
                result += self.cli.ComplLVARGroup(self.cli)(prefix, **kwargs)
                result.append('#')
                return result
            if p in ['for_oid', 'oid']:
                if prefix.find(':') == -1:
                    return ['unit:', 'sensor:', 'lvar:']
                if prefix.startswith('lvar:'):
                    code, data = self.cli.call('state -p lvar')
                else:
                    code, data = self.cli.call('remote')
                if code: return True
                for d in data:
                    yield d['oid'] + '/status'
                    yield d['oid'] + '/value'
            return True

    class ComplJob(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call('job list')
            if code: return True
            result = set()
            for v in data:
                result.add(v['id'])
            return list(result)

    class ComplJobProp(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call(
                ['job', 'props', kwargs.get('parsed_args').i])
            if code: return True
            result = list(data.keys())
            return result

    class ComplJobPropVal(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            p = kwargs.get('parsed_args').p
            if p == 'macro':
                return self.cli.ComplMacro(self.cli)(prefix, **kwargs)
            return True

    class ComplCyclePropVal(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            p = kwargs.get('parsed_args').p
            if p in ['macro', 'on_error']:
                return self.cli.ComplMacro(self.cli)(prefix, **kwargs)
            return True

    def fancy_print_result(self, result, api_func, itype, tab=0, print_ok=True):
        if api_func == 'list_rules':
            self.print_list_rules(result)
        elif api_func == 'list_jobs':
            self.print_list_jobs(result)
        else:
            super().fancy_print_result(result, api_func, itype, tab, print_ok)

    def print_list_rules(self, result):
        if not result:
            print('no data')
            return
        self.import_pandas()
        data2 = []
        data3 = []
        for r in result:
            args = []
            kwargs = []
            for o in r['macro_args']:
                args.append('\'' + o + '\'')
            if r.get('macro_kwargs'):
                for i, v in r['macro_kwargs'].items():
                    kwargs.append('{}=\'{}\''.format(i, v))
            m = ''
            if r['for_prop'] == 'status' and \
                isinstance(r['in_range_max'], float) and \
                r['in_range_min'] is None and \
                r['in_range_max'] == -1 and \
                r['in_range_max_eq']:
                m = ' (expire)'
            elif r['for_prop'] == 'status' and \
                isinstance(r['in_range_min'], float) and \
                isinstance(r['in_range_max'], float) and \
                r['in_range_min'] == 1 and \
                r['in_range_max'] == 1 and \
                r['in_range_min_eq'] and \
                r['in_range_max_eq']:
                m = ' (set)'
            if r['macro']:
                macro = r['macro'] + '(' + ', '.join(args)
                if kwargs:
                    macro += ', ' + ', '.join(kwargs)
                macro += ')'
            else:
                macro = ''
            data2.append({'for_oid': r['for_oid'], 'macro': macro})
            data3.append({
                'id':
                r['id'],
                'E':
                self.bool2yn(r['enabled']),
                'Prio':
                r['priority'],
                'Condition':
                r['condition'] + m,
                'Initial':
                r['for_initial'] if r['for_initial'] else 'any',
                'Chillout':
                '%.2f/%.2f' % (r['chillout_time'], r['chillout_ends_in']),
                'Brk':
                self.bool2yn(r['break_after_exec']),
                'Description':
                r['description']
            })
        df2 = self.pd.DataFrame(data2)
        df2.set_index('for_oid', inplace=True)
        df3 = self.pd.DataFrame(data3)
        df3 = df3.ix[:, [
            'id',
            'E',
            'Prio',
            'Condition',
            'Initial',
            'Chillout',
            'Brk',
            'Description',
        ]]
        df3.set_index('id', inplace=True)
        out2 = df2.to_string().split('\n')
        out3 = df3.to_string().split('\n')
        print(self.colored(out3[0], color='blue'))
        print(self.colored('-' * max(len(out2[0]), len(out3[0])), color='grey'))
        for i in range(0, len(data2)):
            print(out3[i + 2])
            print(' ' + out2[i + 2])
            print()

    def print_list_jobs(self, result):
        if not result:
            print('no data')
            return
        self.import_pandas()
        data2 = []
        data3 = []
        for r in result:
            args = []
            kwargs = []
            for o in r['macro_args']:
                args.append('\'' + o + '\'')
            if r.get('macro_kwargs'):
                for i, v in r['macro_kwargs'].items():
                    kwargs.append('{}=\'{}\''.format(i, v))
            if r['macro']:
                macro = r['macro'] + '(' + ', '.join(args)
                if kwargs:
                    macro += ', ' + ', '.join(kwargs)
                macro += ')'
            else:
                macro = ''
            data2.append({'every': ('every {}'.format(r['every'])) if r['every'] else '', 'macro': macro})
            data3.append({
                'id':
                r['id'],
                'E':
                self.bool2yn(r['enabled']),
                'Description':
                r['description'],
                'Last':
                r['last']
            })
        df2 = self.pd.DataFrame(data2)
        df2.set_index('every', inplace=True)
        df3 = self.pd.DataFrame(data3)
        df3 = df3.ix[:, [
            'id',
            'E',
            'Description',
            'Last'
        ]]
        df3.set_index('id', inplace=True)
        out2 = df2.to_string().split('\n')
        out3 = df3.to_string().split('\n')
        print(self.colored(out3[0], color='blue'))
        print(self.colored('-' * max(len(out2[0]), len(out3[0])), color='grey'))
        for i in range(0, len(data2)):
            print(out3[i + 2])
            print(' ' + out2[i + 2])
            print()

    def prepare_run(self, api_func, params, a):
        if api_func == 'set_rule_prop':
            if a._func in ['enable', 'disable']:
                params['p'] = 'enabled'
                params['v'] = 1 if a._func == 'enable' else 0
        elif api_func == 'set_job_prop':
            if a._func in ['enable', 'disable']:
                params['p'] = 'enabled'
                params['v'] = 1 if a._func == 'enable' else 0
        super().prepare_run(api_func, params, a)

    def prepare_result_data(self, data, api_func, itype):
        if api_func not in [
                'state', 'list_macros', 'list_cycles', 'list_controllers',
                'result'
        ]:
            return super().prepare_result_data(data, api_func, itype)
        result = []
        for d in data.copy():
            if api_func in ['list_macros', 'list_cycles', 'list_controllers']:
                d['id'] = d['full_id']
            if api_func == 'list_cycles':
                d['int'] = d['interval']
                d['iter'] = d['iterations']
                d['status'] = ['stopped', 'running', 'stopping'][d['status']]
            if api_func == 'list_controllers':
                d['type'] = 'static' if d['static'] else 'dynamic'
            elif api_func == 'result':
                from datetime import datetime
                d['time'] = datetime.fromtimestamp(
                    d['time']['created']).isoformat()
            elif itype == 'state':
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
                            exp_in = d['set_time'] + d['expires'] - time.time()
                            if exp_in <= 0:
                                raise Exception('expired')
                            d['exp_in'] = '{:.1f}'.format(exp_in)
                        except:
                            d['exp_in'] = 'E'
                else:
                    d['exp_in'] = '-'
            result.append(d)
        return result

    def process_result(self, result, code, api_func, itype, a):
        if api_func == 'state_history' and \
                isinstance(result, dict):
            self.print_tdf(result, 't')
            return 0
        if api_func == 'create_rule' and result and result.get(
                'result') == 'OK':
            del result['result']
        if api_func == 'create_job' and result and result.get(
                'result') == 'OK':
            del result['result']
        # if api_func == 'list_jobs':
            # for r in result:
                # args = []
                # kwargs = []
                # for o in r['macro_args']:
                    # args.append('\'' + o + '\'')
                # if r.get('macro_kwargs'):
                    # for i, v in r['macro_kwargs'].items():
                        # kwargs.append('{}=\'{}\''.format(i, v))
                # if r['macro']:
                    # macro = r['macro'] + '(' + ', '.join(args)
                    # if kwargs:
                        # macro += ', '  + ', '.join(kwargs)
                    # macro += ')'
                # else:
                    # macro = ''
                # r['macro'] = macro
        return super().process_result(result, code, api_func, itype, a)

    def prepare_result_dict(self, data, api_func, itype):
        if api_func != 'status_controller':
            return super().prepare_result_dict(data, api_func, itype)
        return self.prepare_controller_status_dict(data)

    def setup_parser(self):
        super().setup_parser()
        self.enable_controller_management_functions('lm')

    def add_functions(self):
        super().add_functions()
        self.add_lm_common_functions()
        self.add_lm_configure_functions()
        self.add_lm_remote_functions()
        self.add_lm_macro_functions()
        self.add_lm_cycle_functions()
        self.add_lm_edit_functions()
        self.add_lm_rule_functions()
        self.add_lm_job_functions()
        self.add_lm_ext_functions()
        self.add_lm_controller_functions()

    def add_lm_common_functions(self):
        sp_state = self.sp.add_parser('state', help='Get LVar state')
        sp_state.add_argument(
            'i', help='LVar ID', metavar='ID',
            nargs='?').completer = self.ComplLVAR(self)
        sp_state.add_argument(
            '-g', '--group', help='LVar group', metavar='GROUP',
            dest='g').completer = self.ComplLVARGroup(self)
        sp_state.add_argument(
            '-p',
            '--type',
            help='Item type',
            metavar='TYPE',
            dest='p',
            choices=['lvar', 'LV'])
        sp_state.add_argument(
            '-y',
            '--full',
            help='Full information about LVar',
            dest='_full',
            action='store_true')

        sp_history = self.sp.add_parser(
            'history', help='Get LVar state history')
        sp_history.add_argument(
            'i',
            help=
            'LVar ID or multiple IDs (-w param is required), comma separated',
            metavar='ID').completer = self.ComplLVAR(self)
        sp_history.add_argument(
            '-a',
            '--notifier',
            help='Notifier to get history from (default: db_1)',
            metavar='NOTIFIER',
            dest='a')
        sp_history.add_argument(
            '-s', '--time-start', help='Start time', metavar='TIME', dest='s')
        sp_history.add_argument(
            '-e', '--time-end', help='End time', metavar='TIME', dest='e')
        sp_history.add_argument(
            '-l',
            '--limit',
            help='Records limit (doesn\'t work with fill)',
            metavar='N',
            dest='l')
        sp_history.add_argument(
            '-x',
            '--prop',
            help='LVar state prop (status or value)',
            metavar='PROP',
            dest='x',
            choices=['status', 'value', 'S', 'V'])
        sp_history.add_argument(
            '-w',
            '--fill',
            help='Fill (i.e. 1T - 1 min, 2H - 2 hours), requires start time',
            metavar='INTERVAL',
            dest='w')

        sp_set = self.sp.add_parser('set', help='Set LVar state')
        sp_set.add_argument(
            'i', help='LVar ID', metavar='ID').completer = self.ComplLVAR(self)
        sp_set.add_argument(
            '-s',
            '--status',
            help='LVar status',
            metavar='STATUS',
            type=int,
            dest='s')
        sp_set.add_argument(
            '-v', '--value', help='LVar value', metavar='VALUE', dest='v')

        sp_reset = self.sp.add_parser('reset', help='Reset LVar state')
        sp_reset.add_argument(
            'i', help='LVar ID', metavar='ID').completer = self.ComplLVAR(self)

        sp_clear = self.sp.add_parser('clear', help='Clear LVar state')
        sp_clear.add_argument(
            'i', help='LVar ID', metavar='ID').completer = self.ComplLVAR(self)

        sp_toggle = self.sp.add_parser('toggle', help='Toggle LVar state')
        sp_toggle.add_argument(
            'i', help='LVar ID', metavar='ID').completer = self.ComplLVAR(self)

    def add_lm_configure_functions(self):
        sp_list = self.sp.add_parser('list', help='List LVars')
        sp_list.add_argument(
            '-g', '--group', help='Filter by group', metavar='GROUP',
            dest='g').completer = self.ComplLVARGroup(self)

        ap_config = self.sp.add_parser('config', help='LVar configuration')
        sp_config = ap_config.add_subparsers(
            dest='_func', metavar='func', help='Configuration commands')

        sp_config_get = sp_config.add_parser('get', help='Get LVar config')
        sp_config_get.add_argument(
            'i', help='LVar ID', metavar='ID').completer = self.ComplLVAR(self)

        sp_config_save = sp_config.add_parser('save', help='Save LVar config')
        sp_config_save.add_argument(
            'i', help='LVar ID', metavar='ID').completer = self.ComplLVAR(self)

        sp_list_props = sp_config.add_parser(
            'props', help='List LVar config props')
        sp_list_props.add_argument(
            'i', help='LVar ID', metavar='ID').completer = self.ComplLVAR(self)

        sp_set_prop = sp_config.add_parser('set', help='Set LVar config prop')
        sp_set_prop.add_argument(
            'i', help='LVar ID', metavar='ID').completer = self.ComplLVAR(self)
        sp_set_prop.add_argument(
            'p', help='Config property',
            metavar='PROP').completer = self.ComplLVARProp(self)
        sp_set_prop.add_argument('v', help='Value', metavar='VAL', nargs='?')
        sp_set_prop.add_argument(
            '-y',
            '--save',
            help='Save LVar config after set',
            dest='_save',
            action='store_true')

        ap_create = self.sp.add_parser('create', help='Create new LVar')
        ap_create.add_argument(
            'i', help='LVar ID or OID',
            metavar='OID').completer = self.ComplItemOIDType()
        ap_create.add_argument(
            '-y',
            '--save',
            help='Save LVar config after creation',
            dest='_save',
            action='store_true')

        ap_destroy = self.sp.add_parser('destroy', help='Delete LVar')
        ap_destroy.add_argument(
            'i', help='LVar ID', metavar='ID').completer = self.ComplLVAR(self)

    def add_lm_remote_functions(self):
        ap_remote = self.sp.add_parser('remote', help='List remote items')
        ap_remote.add_argument(
            '-i',
            '--controller',
            help='Filter by controller ID',
            metavar='CONTROLLER_ID',
            dest='i').completer = self.ComplController(self)
        ap_remote.add_argument(
            '-g', '--group', help='Filter by group', metavar='GROUP',
            dest='g').completer = self.ComplRemoteGroup(self)
        ap_remote.add_argument(
            '-p',
            '--type',
            help='Filter by type',
            metavar='TYPE',
            dest='p',
            choices=['unit', 'sensor', 'U', 'S'])

    def add_lm_macro_functions(self):
        ap_macro = self.sp.add_parser('macro', help='Macro functions')
        sp_macro = ap_macro.add_subparsers(
            dest='_func', metavar='func', help='Macro commands')

        sp_macro_get = sp_macro.add_parser('get', help='Get macro info')
        sp_macro_get.add_argument(
            'i', help='Macro ID',
            metavar='ID').completer = self.ComplMacro(self)

        sp_macro_list = sp_macro.add_parser('list', help='List macros')
        sp_macro_list.add_argument(
            '-g', '--group', help='Filter by group', metavar='GROUP',
            dest='g').completer = self.ComplMacroGroup(self)

        ap_macro_create = sp_macro.add_parser('create', help='Create new macro')
        ap_macro_create.add_argument('i', help='Macro ID', metavar='ID')
        ap_macro_create.add_argument(
            '-g', '--group', help='Macro group', metavar='GROUP',
            dest='g').completer = self.ComplMacroGroup(self)
        ap_macro_create.add_argument(
            '-y',
            '--save',
            help='Save macro config after creation',
            dest='_save',
            action='store_true')

        ap_edit = sp_macro.add_parser('edit', help='Edit macro code')
        ap_edit.add_argument(
            'i', help='Macro ID (common.py for common code)',
            metavar='ID').completer = self.ComplMacro(
                self, with_common=True)

        sp_macro_list_props = sp_macro.add_parser(
            'props', help='List macro config props')
        sp_macro_list_props.add_argument(
            'i', help='Macro ID',
            metavar='ID').completer = self.ComplMacro(self)

        sp_macro_set_prop = sp_macro.add_parser(
            'set', help='Set macro config prop')
        sp_macro_set_prop.add_argument(
            'i', help='Macro ID',
            metavar='ID').completer = self.ComplMacro(self)
        sp_macro_set_prop.add_argument(
            'p', help='Config property',
            metavar='PROP').completer = self.ComplMacroProp(self)
        sp_macro_set_prop.add_argument(
            'v', help='Value', metavar='VAL', nargs='?')
        sp_macro_set_prop.add_argument(
            '-y',
            '--save',
            help='Save macro config after set',
            dest='_save',
            action='store_true')

        sp_macro_run = sp_macro.add_parser('run', help='Execute macro')
        sp_macro_run.add_argument(
            'i', help='Macro ID',
            metavar='ID').completer = self.ComplMacro(self)
        sp_macro_run.add_argument(
            '-a', '--args', help='Macro arguments', metavar='ARGS', dest='a')
        sp_macro_run.add_argument(
            '--kwargs',
            help='Macro keyword arguments (name=value), comma separated',
            metavar='ARGS',
            dest='kw')
        sp_macro_run.add_argument(
            '-p',
            '--priority',
            help='Action priority',
            metavar='PRIORITY',
            type=int,
            dest='p')
        sp_macro_run.add_argument(
            '-w',
            '--wait',
            help='Wait for complete',
            metavar='SEC',
            type=float,
            dest='w')
        sp_macro_run.add_argument(
            '-q',
            '--queue-timeout',
            help='Max queue timeout',
            metavar='SEC',
            type=float,
            dest='q')
        sp_macro_run.add_argument(
            '-u', '--uuid', help='Custom action uuid', metavar='UUID', dest='u')

        sp_macro_result = sp_macro.add_parser(
            'result', help='Get macro execution results')
        sp_macro_result.add_argument(
            '-i', '--id', help='Macro ID', metavar='ID',
            dest='i').completer = self.ComplMacro(self)
        sp_macro_result.add_argument(
            '-u', '--uuid', help='Action UUID', metavar='UUID', dest='u')
        sp_macro_result.add_argument(
            '-g', '--group', help='Macros group', metavar='GROUP',
            dest='g').completer = self.ComplMacroGroup(self)
        sp_macro_result.add_argument(
            '-s',
            '--state',
            help='Action state (Q, R, F: queued, running, finished)',
            metavar='STATE',
            dest='s',
            choices=['queued', 'running', 'finished', 'Q', 'R', 'F'])

        ap_destroy = sp_macro.add_parser('destroy', help='Delete macro')
        ap_destroy.add_argument(
            'i', help='Macro ID',
            metavar='ID').completer = self.ComplMacro(self)

    def add_lm_cycle_functions(self):
        ap_cycle = self.sp.add_parser('cycle', help='Cycle functions')
        sp_cycle = ap_cycle.add_subparsers(
            dest='_func', metavar='func', help='Cycle commands')

        sp_cycle_get = sp_cycle.add_parser('get', help='Get cycle info')
        sp_cycle_get.add_argument(
            'i', help='Cycle ID',
            metavar='ID').completer = self.ComplCycle(self)

        sp_cycle_list = sp_cycle.add_parser('list', help='List cycles')
        sp_cycle_list.add_argument(
            '-g', '--group', help='Filter by group', metavar='GROUP',
            dest='g').completer = self.ComplCycleGroup(self)

        ap_cycle_create = sp_cycle.add_parser('create', help='Create new cycle')
        ap_cycle_create.add_argument('i', help='Cycle ID', metavar='ID')
        ap_cycle_create.add_argument(
            '-g', '--group', help='Cycle group', metavar='GROUP',
            dest='g').completer = self.ComplCycleGroup(self)
        ap_cycle_create.add_argument(
            '-y',
            '--save',
            help='Save cycle config after creation',
            dest='_save',
            action='store_true')

        sp_cycle_list_props = sp_cycle.add_parser(
            'props', help='List cycle config props')
        sp_cycle_list_props.add_argument(
            'i', help='Cycle ID',
            metavar='ID').completer = self.ComplCycle(self)

        sp_cycle_set_prop = sp_cycle.add_parser(
            'set', help='Set cycle config prop')
        sp_cycle_set_prop.add_argument(
            'i', help='Cycle ID',
            metavar='ID').completer = self.ComplCycle(self)
        sp_cycle_set_prop.add_argument(
            'p', help='Config property',
            metavar='PROP').completer = self.ComplCycleProp(self)
        sp_cycle_set_prop.add_argument(
            'v', help='Value', metavar='VAL',
            nargs='?').completer = self.ComplCyclePropVal(self)
        sp_cycle_set_prop.add_argument(
            '-y',
            '--save',
            help='Save cycle config after set',
            dest='_save',
            action='store_true')

        ap_start = sp_cycle.add_parser('start', help='Start cycle')
        ap_start.add_argument(
            'i', help='Cycle ID',
            metavar='ID').completer = self.ComplCycle(self)

        sp_cycle_stop = sp_cycle.add_parser('stop', help='Stop cycle')
        sp_cycle_stop.add_argument(
            'i', help='Cycle ID',
            metavar='ID').completer = self.ComplCycle(self)

        sp_cycle_stop = sp_cycle.add_parser(
            'reset', help='Reset cycle stats (avg)')
        sp_cycle_stop.add_argument(
            'i', help='Cycle ID',
            metavar='ID').completer = self.ComplCycle(self)

        ap_destroy = sp_cycle.add_parser('destroy', help='Delete cycle')
        ap_destroy.add_argument(
            'i', help='Cycle ID',
            metavar='ID').completer = self.ComplCycle(self)

    def add_lm_edit_functions(self):
        ap_edit = self.sp.add_parser('edit', help='Edit item scripts')

        sp_edit = ap_edit.add_subparsers(
            dest='_func', metavar='func', help='Edit commands')

        sp_edit_macro = sp_edit.add_parser('macro', help='Edit macro code')
        sp_edit_macro.add_argument(
            'i', help='Macro ID (common.py for common code)',
            metavar='ID').completer = self.ComplMacro(
                self, with_common=True)

    def add_lm_rule_functions(self):
        ap_rule = self.sp.add_parser('rule', help='Decision-making rules')
        sp_rule = ap_rule.add_subparsers(
            dest='_func', metavar='func', help='Rules commands')

        sp_rule_list = sp_rule.add_parser('list', help='List defined rules')

        sp_rule_get = sp_rule.add_parser('get', help='Get rule info')
        sp_rule_get.add_argument(
            'i', help='Rule ID', metavar='ID').completer = self.ComplRule(self)

        sp_rule_create = sp_rule.add_parser('create', help='Create new rule')
        sp_rule_create.add_argument(
            '-u',
            '--uuid',
            help='Rule UUID (generated if not specified)',
            dest='u',
            metavar='UUID')
        sp_rule_create.add_argument(
            '-y',
            '--save',
            help='Save rule config after set',
            dest='_save',
            action='store_true')

        sp_rule_enable = sp_rule.add_parser('enable', help='Enable rule')
        sp_rule_enable.add_argument(
            'i', help='Rule ID', metavar='ID').completer = self.ComplRule(self)
        sp_rule_enable.add_argument(
            '-y',
            '--save',
            help='Save rule config after set',
            dest='_save',
            action='store_true')

        sp_rule_disable = sp_rule.add_parser('disable', help='Disable rule')
        sp_rule_disable.add_argument(
            'i', help='Rule ID', metavar='ID').completer = self.ComplRule(self)
        sp_rule_disable.add_argument(
            '-y',
            '--save',
            help='Save rule config after set',
            dest='_save',
            action='store_true')

        sp_rule_list_props = sp_rule.add_parser(
            'props', help='List rule config props')
        sp_rule_list_props.add_argument(
            'i', help='Rule ID', metavar='ID').completer = self.ComplRule(self)

        sp_rule_set_prop = sp_rule.add_parser(
            'set', help='Set rule config prop')
        sp_rule_set_prop.add_argument(
            'i', help='Rule ID', metavar='ID').completer = self.ComplRule(self)
        sp_rule_set_prop.add_argument(
            'p', help='Config property',
            metavar='PROP').completer = self.ComplRuleProp(self)
        sp_rule_set_prop.add_argument(
            'v', help='Value', metavar='VAL',
            nargs='?').completer = self.ComplRulePropVal(self)
        sp_rule_set_prop.add_argument(
            '-y',
            '--save',
            help='Save rule config after set',
            dest='_save',
            action='store_true')

        sp_rule_destroy = sp_rule.add_parser('destroy', help='Delete rule')
        sp_rule_destroy.add_argument(
            'i', help='Rule ID', metavar='ID').completer = self.ComplRule(self)

    def add_lm_job_functions(self):
        ap_job = self.sp.add_parser('job', help='Scheduled jobs')
        sp_job = ap_job.add_subparsers(
            dest='_func', metavar='func', help='Jobs commands')

        sp_job_list = sp_job.add_parser('list', help='List defined jobs')

        sp_job_get = sp_job.add_parser('get', help='Get job info')
        sp_job_get.add_argument(
            'i', help='Job ID', metavar='ID').completer = self.ComplJob(self)

        sp_job_create = sp_job.add_parser('create', help='Create new job')
        sp_job_create.add_argument(
            '-u',
            '--uuid',
            help='Job UUID (generated if not specified)',
            dest='u',
            metavar='UUID')
        sp_job_create.add_argument(
            '-y',
            '--save',
            help='Save job config after set',
            dest='_save',
            action='store_true')

        sp_job_enable = sp_job.add_parser('enable', help='Enable job')
        sp_job_enable.add_argument(
            'i', help='Job ID', metavar='ID').completer = self.ComplJob(self)
        sp_job_enable.add_argument(
            '-y',
            '--save',
            help='Save job config after set',
            dest='_save',
            action='store_true')

        sp_job_disable = sp_job.add_parser('disable', help='Disable job')
        sp_job_disable.add_argument(
            'i', help='Job ID', metavar='ID').completer = self.ComplJob(self)
        sp_job_disable.add_argument(
            '-y',
            '--save',
            help='Save job config after set',
            dest='_save',
            action='store_true')

        sp_job_list_props = sp_job.add_parser(
            'props', help='List job config props')
        sp_job_list_props.add_argument(
            'i', help='Job ID', metavar='ID').completer = self.ComplJob(self)

        sp_job_set_prop = sp_job.add_parser(
            'set', help='Set job config prop')
        sp_job_set_prop.add_argument(
            'i', help='Job ID', metavar='ID').completer = self.ComplJob(self)
        sp_job_set_prop.add_argument(
            'p', help='Config property',
            metavar='PROP').completer = self.ComplJobProp(self)
        sp_job_set_prop.add_argument(
            'v', help='Value', metavar='VAL',
            nargs='?').completer = self.ComplJobPropVal(self)
        sp_job_set_prop.add_argument(
            '-y',
            '--save',
            help='Save job config after set',
            dest='_save',
            action='store_true')

        sp_job_destroy = sp_job.add_parser('destroy', help='Delete job')
        sp_job_destroy.add_argument(
            'i', help='Job ID', metavar='ID').completer = self.ComplJob(self)

    def add_lm_controller_functions(self):
        ap_controller = self.sp.add_parser(
            'controller', help='Connected UC controllers functions')
        sp_controller = ap_controller.add_subparsers(
            dest='_func', metavar='func', help='Controller commands')

        sp_controller_get = sp_controller.add_parser(
            'get', help='Get connected UC info')
        sp_controller_get.add_argument(
            'i', help='Controller ID',
            metavar='ID').completer = self.ComplController(self)

        sp_controller_list = sp_controller.add_parser(
            'list', help='List connected UCs')

        sp_controller_test = sp_controller.add_parser(
            'test', help='Test connected UC')
        sp_controller_test.add_argument(
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
        sp_controller_set_prop.add_argument(
            'v', help='Value', metavar='VAL', nargs='?')
        sp_controller_set_prop.add_argument(
            '-y',
            '--save',
            help='Save controller config after set',
            dest='_save',
            action='store_true')

        sp_controller_reload = sp_controller.add_parser(
            'reload', help='Reload items from the connected UC')
        sp_controller_reload.add_argument(
            'i', help='Controller ID (or "all")',
            metavar='ID').completer = self.ComplController(
                self, allow_all=True)

        sp_controller_append = sp_controller.add_parser(
            'append', help='Connect UC')
        sp_controller_append.add_argument(
            'u', help='Controller API URI (http[s]://host:port)', metavar='URI')
        sp_controller_append.add_argument(
            '-a', '--api-key', help='API key', metavar='KEY', dest='a')
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
        sp_controller_append.add_argument(
            '-t',
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
            'enable', help='Enable connected UC')
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
            'disable', help='Disable connected UC')
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
            'remove', help='Remove connected UC')
        sp_controller_remove.add_argument(
            'i', help='Controller ID',
            metavar='ID').completer = self.ComplController(self)

    def add_lm_ext_functions(self):
        ap_ext = self.sp.add_parser('ext', help='Macro extension functions')
        sp_ext = ap_ext.add_subparsers(
            dest='_func', metavar='func', help='Extension commands')

        sp_ext_list = sp_ext.add_parser('list', help='List loaded extensions')
        sp_ext_list.add_argument(
            '-y',
            '--full',
            help='full information about extension',
            dest='_full',
            action='store_true')

        sp_ext_get = sp_ext.add_parser('get', help='Get loaded extension info')
        sp_ext_get.add_argument(
            'i', help='EXT id',
            metavar='EXT_ID').completer = self.ComplExt(self)

        sp_ext_mods = sp_ext.add_parser(
            'mods', help='List available extension mods')

        sp_ext_load = sp_ext.add_parser('load', help='Load extension')
        sp_ext_load.add_argument(
            'i', help='Extension id',
            metavar='EXT_ID').completer = self.ComplExt(self)
        sp_ext_load.add_argument(
            'm', help='Extension module',
            metavar='EXT_MOD').completer = self.ComplExtMods(self)
        sp_ext_load.add_argument(
            '-c',
            '--config',
            help='Extension configuration values, comma separated',
            dest='c',
            metavar='CONFIG')
        sp_ext_load.add_argument(
            '-y',
            '--save',
            help='save configuration on success load',
            dest='_save',
            action='store_true')

        sp_ext_unload = sp_ext.add_parser('unload', help='Unload extension')
        sp_ext_unload.add_argument(
            'i', help='Extension id',
            metavar='EXT_ID').completer = self.ComplExt(self)

        sp_ext_modinfo = sp_ext.add_parser(
            'modinfo', help='Extension module info')
        sp_ext_modinfo.add_argument(
            'm', help='Extension module',
            metavar='EXT_MOD').completer = self.ComplExtMods(self)

        sp_ext_modhelp = sp_ext.add_parser(
            'modhelp', help='Extension module help')
        sp_ext_modhelp.add_argument(
            'm', help='Extension module',
            metavar='EXT_MOD').completer = self.ComplExtMods(self)
        sp_ext_modhelp.add_argument(
            'c',
            help='Help context (cfg, functions)',
            metavar='CONTEXT',
            choices=['cfg', 'functions'])

        sp_ext_set_prop = sp_ext.add_parser(
            'set', help='Set extension config prop')
        sp_ext_set_prop.add_argument(
            'i', help='EXT ID',
            metavar='EXT ID').completer = self.ComplExt(self)
        sp_ext_set_prop.add_argument(
            'p', help='Config property', metavar='PROP')
        sp_ext_set_prop.add_argument(
            'v', help='Value', nargs='?', metavar='VAL')
        sp_ext_set_prop.add_argument(
            '-y',
            '--save',
            help='Save ext config after set',
            dest='_save',
            action='store_true')

    def edit_macro(self, props):
        if self.apiuri:
            self.print_local_only()
            return self.local_func_result_failed
        if props.get('i') == 'common.py':
            macro_file = 'common.py'
        else:
            code, data = self.call(args=['macro', 'props', props.get('i')])
            if code or not isinstance(data, dict):
                return self.local_func_result_failed
            macro_file = data.get('action_exec') if data.get(
                'action_exec') else props.get('i').split('/')[-1] + '.py'
        fname = '{}/xc/lm/{}'.format(dir_runtime, macro_file) if \
                not macro_file.startswith('/') else macro_file
        if macro_file.find('/') != -1:
            macro_dir = '/'.join(fname.split('/')[:-1])
            if os.system('mkdir -p ' + macro_dir):
                return self.local_func_result_failed
        editor = os.environ.get('EDITOR', 'vi')
        if os.system(editor + ' ' + fname):
            return self.local_func_result_failed
        try:
            compile(open(fname).read(), fname, 'exec')
        except Exception as e:
            self.print_err('Macro code error: ' + str(e))
            return self.local_func_result_failed
        return self.local_func_result_ok


_me = 'EVA ICS LM CLI version %s' % __version__

cli = LM_CLI('lm', _me)

_api_functions = {
    'history': 'state_history',
    'config:get': 'get_config',
    'config:save': 'save_config',
    'config:props': 'list_props',
    'config:set': 'set_prop',
    'create': 'create_lvar',
    'destroy': 'destroy_lvar',
    'remote': 'list_remote',
    'cycle:list': 'list_cycles',
    'cycle:props': 'list_cycle_props',
    'cycle:set': 'set_cycle_prop',
    'cycle:create': 'create_cycle',
    'cycle:destroy': 'destroy_cycle',
    'cycle:start': 'start_cycle',
    'cycle:stop': 'stop_cycle',
    'cycle:reset': 'reset_cycle_stats',
    'cycle:get': 'get_cycle',
    'macro:list': 'list_macros',
    'macro:props': 'list_macro_props',
    'macro:set': 'set_macro_prop',
    'macro:create': 'create_macro',
    'macro:destroy': 'destroy_macro',
    'macro:run': 'run',
    'macro:result': 'result',
    'macro:get': 'get_macro',
    'rule:list': 'list_rules',
    'rule:create': 'create_rule',
    'rule:enable': 'set_rule_prop',
    'rule:disable': 'set_rule_prop',
    'rule:props': 'list_rule_props',
    'rule:set': 'set_rule_prop',
    'rule:destroy': 'destroy_rule',
    'rule:get': 'get_rule',
    'job:list': 'list_jobs',
    'job:create': 'create_job',
    'job:enable': 'set_job_prop',
    'job:disable': 'set_job_prop',
    'job:props': 'list_job_props',
    'job:set': 'set_job_prop',
    'job:destroy': 'destroy_job',
    'job:get': 'get_job',
    'controller:list': 'list_controllers',
    'controller:test': 'test_controller',
    'controller:props': 'list_controller_props',
    'controller:set': 'set_controller_prop',
    'controller:reload': 'reload_controller',
    'controller:append': 'append_controller',
    'controller:enable': 'enable_controller',
    'controller:disable': 'disable_controller',
    'controller:remove': 'remove_controller',
    'controller:get': 'get_controller',
    'ext:list': 'list_ext',
    'ext:get': 'get_ext',
    'ext:mods': 'list_ext_mods',
    'ext:load': 'load_ext',
    'ext:unload': 'unload_ext',
    'ext:modhelp': 'modhelp_ext',
    'ext:modinfo': 'modinfo_ext',
    'ext:set': 'set_ext_prop',
    'macro:edit': cli.edit_macro,
    'edit:macro': cli.edit_macro
}

_pd_cols = {
    'state': ['oid', 'status', 'value', 'set', 'exp_in'],
    'state_': [
        'oid', 'description', 'location', 'status', 'value', 'set', 'expires',
        'exp_in'
    ],
    'result': ['time', 'uuid', 'priority', 'item_oid', 'exitcode', 'status'],
    'list': ['oid', 'description'],
    'list_remote': [
        'oid', 'description', 'controller_id', 'status', 'value', 'nstatus',
        'nvalue'
    ],
    'list_macros': ['id', 'description', 'action_enabled'],
    'list_jobs': ['id', 'description', 'enabled', 'every', 'macro'],
    'list_cycles': ['id', 'description', 'status', 'int', 'iter', 'avg'],
    'list_controllers': [
        'id', 'type', 'enabled', 'connected', 'proto', 'version', 'build',
        'description'
    ],
    'list_ext_': ['id', 'mod', 'description', 'version'],
    'list_ext_mods': ['mod', 'description', 'version', 'api'],
    'modhelp_ext': ['name', 'type', 'required', 'help']
}

_pd_idx = {'state': 'oid', 'list': 'oid', 'result': 'time'}

_fancy_indentsp = {'list_props': 26}

_always_json = ['get_config']

cli.always_json += _always_json
cli.always_print += ['run', 'cmd']
cli.arg_sections += ['config', 'macro', 'cycle', 'rule', 'controller', 'ext']
cli.api_cmds_timeout_correction = ['run']
cli.set_api_functions(_api_functions)
cli.set_pd_cols(_pd_cols)
cli.set_pd_idx(_pd_idx)
cli.set_fancy_indentsp(_fancy_indentsp)
code = cli.run()
sys.exit(code)
