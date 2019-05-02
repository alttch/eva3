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


class UC_CLI(GenericCLI, ControllerCLI):

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
                if code: return True
                result = set()
                for v in data:
                    result.add(v[fld])
                return list(result)
            else:
                return ['sensor:', 'unit:']

    class ComplItemOIDType(object):

        def __call__(self, prefix, **kwargs):
            return ['unit:', 'sensor:'] if prefix.find(':') == -1 else True

    class ComplItemGroup(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            if not hasattr(kwargs.get('parsed_args'),
                           'p') or not kwargs.get('parsed_args').p:
                return True
            code, data = self.cli.call(
                ['state', '-p', kwargs.get('parsed_args').p])
            if code: return True
            result = set()
            for v in data:
                result.add(v['group'])
            return list(result)

    class ComplItemGroupList(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            opts = []
            if hasattr(kwargs.get('parsed_args'), 'p'):
                p = kwargs.get('parsed_args').p
                if p:
                    opts = ['-p', p]
            code, data = self.cli.call(['list'] + opts)
            if code: return True
            result = set()
            for v in data:
                result.add(v['group'])
            return list(result)

    class ComplUnit(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call('state -p unit')
            if code: return True
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
            if code: return True
            result = set()
            for v in data:
                result.add(v['group'])
            return list(result)

    class ComplDeviceTPL(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call('device templates')
            if code: return True
            for v in data:
                yield v['name']

    class ComplItemProp(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call(
                ['config', 'props',
                 kwargs.get('parsed_args').i])
            if code: return True
            result = list(data.keys())
            return result

    class ComplModBusProto(object):

        def __call__(self, prefix, **kwargs):
            return ['tcp:', 'udp:', 'rtu:', 'ascii:',
                    'binary:'] if prefix.find(':') == -1 else True

    class ComplModBus(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call('modbus list')
            if code: return True
            result = set()
            for v in data:
                result.add(v['id'])
            return list(result)

    class ComplOWFS(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call('owfs list')
            if code: return True
            result = set()
            for v in data:
                result.add(v['id'])
            return list(result)

    class ComplPHI(ComplGeneric):

        def __init__(self, cli, for_driver=False):
            self.for_driver = for_driver
            super().__init__(cli)

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call('phi list')
            if code: return True
            result = set()
            for v in data:
                result.add(v['id'] + (':' if self.for_driver else ''))
            return list(result)

    class ComplDriver(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call('driver list')
            if code: return True
            result = set()
            for v in data:
                result.add(v['id'])
            return list(result)

    class ComplPHIMods(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call('phi mods')
            if code: return True
            result = set()
            for v in data:
                result.add(v['mod'])
            return list(result)

    class ComplLPIMods(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call('lpi mods')
            if code: return True
            result = set()
            for v in data:
                result.add(v['mod'])
            return list(result)

    class ComplPHIMods(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call('phi mods')
            if code: return True
            result = set()
            for v in data:
                result.add(v['mod'])
            return list(result)

    class ComplPHITestCMD(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call(
                ['phi', 'test',
                 kwargs.get('parsed_args').i, 'help'])
            if code or not isinstance(data, dict): return True
            result = set()
            result.add('self')
            for d in data.keys():
                result.add(d)
            result.add('help')
            return result

    class ComplPHIExecCMD(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call(
                ['phi', 'exec',
                 kwargs.get('parsed_args').i, 'help'])
            if code or not isinstance(data, dict): return True
            result = set()
            result.add('self')
            for d in data.keys():
                result.add(d)
            result.add('help')
            return result

    def prepare_result_data(self, data, api_func, itype):
        if api_func == 'list_device_tpl':
            for d in data:
                d['type'] = d['type'] + ' device template'
                return data
            return result
        if api_func == 'get_modbus_slave_data':
            for d in data:
                rtps = {
                    'h': 'holding',
                    'i': 'input',
                    'd': 'd.input',
                    'c': 'coil'
                }
                rtype = rtps.get(d['addr'][0])
                addr = int(d['addr'][1:])
                d['addr'] = addr
                d['reg'] = rtype
                d['addr_hex'] = hex(addr)
                d['hex'] = hex(d['value'])
            return data
        if itype not in ['owfs', 'action', 'driver', 'phi', 'lpi']:
            return super().prepare_result_data(data, api_func, itype)
        result = []
        for d in data.copy():
            if api_func == 'scan_owfs_bus':
                if 'attrs' in d: del d['attrs']
            elif itype == 'action':
                from datetime import datetime
                d['time'] = datetime.fromtimestamp(
                    d['time']['created']).isoformat()
            elif itype == 'driver':
                if 'phi' in d:
                    d['phi_mod'] = d['phi'].get('mod')
                    del d['phi']
                    try:
                        del d['phi']['help']
                    except:
                        pass
            elif itype == 'phi':
                if 'equipment' in d and isinstance(d['equipment'], list):
                    d['equipment'] = ', '.join(d['equipment'])
            elif itype == 'lpi':
                if 'logic' in d and isinstance(d['logic'], list):
                    d['logic'] = ', '.join(d['logic'])
            result.append(d)
        return result

    def process_result(self, result, code, api_func, itype, a):
        if api_func == 'state_history' and \
                isinstance(result, dict):
            self.print_tdf(result, 't')
            return 0
        else:
            return super().process_result(result, code, api_func, itype, a)

    def prepare_run(self, api_func, params, a):
        if api_func == 'load_driver':
            try:
                import re
                params['p'], params['i'] = re.split('[.:]', params['i'])
            except:
                self.print_err("Invalid driver ID")
                return 98
        elif api_func == 'put_phi_mod':
            try:
                import requests
                # if a._uri[-3:] != '.py':
                # raise Exception('Not a PHI mod')
                params['m'] = '.'.join(a._uri.split('/')[-1].split('.')[:-1])
                r = requests.get(a._uri, timeout=self.timeout)
                if r.status_code != 200:
                    raise Exception('Download error')
                params['c'] = r.text
            except:
                self.print_err('Download error: %s' % a._uri)
                return 97
        return super().prepare_run(api_func, params, a)

    def prepare_result_dict(self, data, api_func, itype):
        if api_func != 'status_controller':
            return super().prepare_result_dict(data, api_func, itype)
        return self.prepare_controller_status_dict(data)

    def setup_parser(self):
        super().setup_parser()
        self.enable_controller_management_functions('uc')

    def add_functions(self):
        super().add_functions()
        self.add_uc_common_functions()
        self.add_uc_action_functions()
        self.add_uc_edit_functions()
        self.add_uc_configure_functions()
        self.add_uc_device_functions()
        self.add_uc_modbus_functions()
        self.add_uc_owfs_functions()
        self.add_uc_driver_functions()

    def add_uc_common_functions(self):
        sp_state = self.sp.add_parser('state', help='Get item state')
        sp_state.add_argument(
            'i',
            help='Item ID (specify either ID or item type)',
            metavar='ID',
            nargs='?').completer = self.ComplItemOID(self)
        sp_state.add_argument(
            '-p',
            '--type',
            help='Item type',
            metavar='TYPE',
            dest='p',
            choices=['unit', 'sensor', 'U', 'S'])
        sp_state.add_argument(
            '-g', '--group', help='Item group', metavar='GROUP',
            dest='g').completer = self.ComplItemGroup(self)
        sp_state.add_argument(
            '-y',
            '--full',
            help='Full information about item',
            dest='_full',
            action='store_true')

        sp_history = self.sp.add_parser(
            'history', help='Get item state history')
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

        sp_update = self.sp.add_parser('update', help='Update item state')
        sp_update.add_argument(
            'i', help='Item ID',
            metavar='ID').completer = self.ComplItemOID(self)
        sp_update.add_argument(
            '-s',
            '--status',
            help='Item status',
            metavar='STATUS',
            type=int,
            dest='s')
        sp_update.add_argument(
            '-v', '--value', help='Item value', metavar='VALUE', dest='v')

    def add_uc_action_functions(self):
        ap_action = self.sp.add_parser('action', help='Unit actions')

        sp_action = ap_action.add_subparsers(
            dest='_func', metavar='func', help='Action commands')

        sp_action_enable = sp_action.add_parser(
            'enable', help='Enable unit actions')
        sp_action_enable.add_argument(
            'i', help='Unit ID', metavar='ID').completer = self.ComplUnit(self)

        sp_action_disable = sp_action.add_parser(
            'disable', help='Disable unit actions')
        sp_action_disable.add_argument(
            'i', help='Unit ID', metavar='ID').completer = self.ComplUnit(self)

        sp_action_exec = sp_action.add_parser(
            'exec', help='Execute unit action')
        sp_action_exec.add_argument(
            'i', help='Unit ID', metavar='ID').completer = self.ComplUnit(self)
        sp_action_exec.add_argument('s', help='New status', metavar='STATUS')
        sp_action_exec.add_argument(
            '-v', '--value', help='New value', metavar='VALUE', dest='v')
        sp_action_exec.add_argument(
            '-p',
            '--priority',
            help='Action priority',
            metavar='PRIORITY',
            type=int,
            dest='p')
        sp_action_exec.add_argument(
            '-w',
            '--wait',
            help='Wait for complete',
            metavar='SEC',
            type=float,
            dest='w')
        sp_action_exec.add_argument(
            '-q',
            '--queue-timeout',
            help='Max queue timeout',
            metavar='SEC',
            type=float,
            dest='q')
        sp_action_exec.add_argument(
            '-u', '--uuid', help='Custom action uuid', metavar='UUID', dest='u')

        sp_action_toggle = sp_action.add_parser(
            'toggle', help='Execute unit toggle action')
        sp_action_toggle.add_argument(
            'i', help='Unit ID', metavar='ID').completer = self.ComplUnit(self)
        sp_action_toggle.add_argument(
            '-p',
            '--priority',
            help='Action priority',
            metavar='PRIORITY',
            type=int,
            dest='p')
        sp_action_toggle.add_argument(
            '-w',
            '--wait',
            help='Wait for complete',
            metavar='SEC',
            type=float,
            dest='w')
        sp_action_toggle.add_argument(
            '-q',
            '--queue-timeout',
            help='Max queue timeout',
            metavar='SEC',
            type=float,
            dest='q')
        sp_action_toggle.add_argument(
            '-u', '--uuid', help='Custom action uuid', metavar='UUID', dest='u')

        sp_action_terminate = sp_action.add_parser(
            'terminate', help='Terminate unit action')
        sp_action_terminate.add_argument(
            'i', help='Unit ID', metavar='ID',
            nargs='?').completer = self.ComplUnit(self)
        sp_action_terminate.add_argument(
            '-u', '--uuid', help='Action uuid', metavar='UUID', dest='u')

        sp_action_qclean = sp_action.add_parser(
            'clear', help='Clean up unit action queue')
        sp_action_qclean.add_argument(
            'i', help='Unit ID', metavar='ID').completer = self.ComplUnit(self)

        sp_action_kill = sp_action.add_parser(
            'kill', help='Terminate action and clean queue')
        sp_action_kill.add_argument(
            'i', help='Unit ID', metavar='ID').completer = self.ComplUnit(self)

        sp_action_result = sp_action.add_parser(
            'result', help='Get unit action results')
        sp_action_result.add_argument(
            '-i', '--id', help='Unit ID', metavar='ID',
            dest='i').completer = self.ComplUnit(self)
        sp_action_result.add_argument(
            '-u', '--uuid', help='Action UUID', metavar='UUID', dest='u')
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

    def add_uc_edit_functions(self):
        ap_edit = self.sp.add_parser('edit', help='Edit scripts and templates')

        sp_edit = ap_edit.add_subparsers(
            dest='_func', metavar='func', help='Edit commands')

        sp_edit_action = sp_edit.add_parser(
            'action', help='Edit item action script')
        sp_edit_action.add_argument(
            'i', help='Item ID', metavar='ID').completer = self.ComplUnit(self)

        sp_edit_update = sp_edit.add_parser(
            'update', help='Edit item update script')
        sp_edit_update.add_argument(
            'i', help='Item ID',
            metavar='ID').completer = self.ComplItemOID(self)

        sp_edit_tpl = sp_edit.add_parser(
            'template', help='Edit device template')
        sp_edit_tpl.add_argument(
            'i', help='Template name',
            metavar='TPL').completer = self.ComplDeviceTPL(self)

    def add_uc_configure_functions(self):
        sp_list = self.sp.add_parser('list', help='List items')
        sp_list.add_argument(
            '-p',
            '--type',
            help='Filter by type',
            metavar='TYPE',
            dest='p',
            choices=['unit', 'sensor', 'mu', 'U', 'S'])
        sp_list.add_argument(
            '-g', '--group', help='Filter by group', metavar='GROUP',
            dest='g').completer = self.ComplItemGroupList(self)

        ap_config = self.sp.add_parser('config', help='Item configuration')
        sp_config = ap_config.add_subparsers(
            dest='_func', metavar='func', help='Configuration commands')

        sp_config_get = sp_config.add_parser('get', help='Get item config')
        sp_config_get.add_argument(
            'i', help='Item ID',
            metavar='ID').completer = self.ComplItemOID(self)

        sp_config_save = sp_config.add_parser('save', help='Save item config')
        sp_config_save.add_argument(
            'i', help='Item ID',
            metavar='ID').completer = self.ComplItemOID(self)

        sp_list_props = sp_config.add_parser(
            'props', help='List item config props')
        sp_list_props.add_argument(
            'i', help='Item ID',
            metavar='ID').completer = self.ComplItemOID(self)

        sp_set_prop = sp_config.add_parser('set', help='Set item config prop')
        sp_set_prop.add_argument(
            'i', help='Item ID',
            metavar='ID').completer = self.ComplItemOID(self)
        sp_set_prop.add_argument(
            'p', help='Config property',
            metavar='PROP').completer = self.ComplItemProp(self)
        sp_set_prop.add_argument('v', help='Value', metavar='VAL', nargs='?')
        sp_set_prop.add_argument(
            '-y',
            '--save',
            help='Save item config after set',
            dest='_save',
            action='store_true')

        ap_create = self.sp.add_parser('create', help='Create new item')
        ap_create.add_argument(
            'i', help='Item OID (type:group/id)',
            metavar='OID').completer = self.ComplItemOIDType()
        ap_create.add_argument(
            '-y',
            '--save',
            help='Save item config after creation',
            dest='_save',
            action='store_true')

        ap_clone = self.sp.add_parser('clone', help='Clone items')
        sp_clone = ap_clone.add_subparsers(
            dest='_func', metavar='func', help='Cloning commands')

        sp_clone_item = sp_clone.add_parser('item', help='Clone single item')
        sp_clone_item.add_argument(
            'i', help='Item ID',
            metavar='ID').completer = self.ComplItemOID(self)
        sp_clone_item.add_argument(
            'n', help='New item ID (short)', metavar='ID')
        sp_clone_item.add_argument(
            '-g',
            '--group',
            help='Group for new item',
            metavar='GROUP',
            dest='g')
        sp_clone_item.add_argument(
            '-y',
            '--save',
            help='Save item config after cloning',
            dest='_save',
            action='store_true')

        sp_clone_group = sp_clone.add_parser(
            'group', help='Clone group of the items')
        sp_clone_group.add_argument(
            'g', help='Source group',
            metavar='SRC_GROUP').completer = self.ComplItemGroupList(self)
        sp_clone_group.add_argument(
            'n', help='Target group', metavar='TGT_GROUP')
        sp_clone_group.add_argument(
            '-p',
            '--source-prefix',
            help='Source items prefix',
            dest='p',
            metavar='SRC_PFX')
        sp_clone_group.add_argument(
            '-r',
            '--target-prefix',
            help='Target items prefix',
            dest='r',
            metavar='TGT_PFX')
        sp_clone_group.add_argument(
            '-y',
            '--save',
            help='Save items config after cloning',
            dest='_save',
            action='store_true')

        ap_destroy = self.sp.add_parser('destroy', help='Delete item')
        ap_destroy.add_argument(
            'i', help='Item ID', metavar='ID',
            nargs='?').completer = self.ComplItemOID(self)
        ap_destroy.add_argument(
            '-g',
            '--group',
            help='Destroy group of items',
            metavar='GROUP',
            dest='g').completer = self.ComplItemGroupList(self)

    def add_uc_device_functions(self):
        ap_device = self.sp.add_parser('device', help='Device management')
        sp_device = ap_device.add_subparsers(
            dest='_func', metavar='func', help='Device commands')

        sp_device_templates = sp_device.add_parser(
            'templates', help='List device templates')

        sp_device_create = sp_device.add_parser(
            'deploy', help='Deploy device with a template')
        sp_device_create.add_argument(
            't',
            help='Template name (file=runtime/tpl/<TPL>.yml|json)',
            metavar='TPL').completer = self.ComplDeviceTPL(self)
        sp_device_create.add_argument(
            '-c',
            '--config',
            help='Template vars, comma separated',
            metavar='VARS',
            dest='c')
        sp_device_create.add_argument(
            '-y',
            '--save',
            help='Save items config after creation',
            dest='_save',
            action='store_true')

        sp_device_update = sp_device.add_parser(
            'update', help='Update device item props with a template')
        sp_device_update.add_argument(
            't',
            help='Template name (file=runtime/tpl/<TPL>.yml|json)',
            metavar='TPL').completer = self.ComplDeviceTPL(self)
        sp_device_update.add_argument(
            '-c',
            '--config',
            help='Template vars, comma separated',
            metavar='VARS',
            dest='c')
        sp_device_update.add_argument(
            '-y',
            '--save',
            help='Save items config after creation',
            dest='_save',
            action='store_true')

        sp_device_destroy = sp_device.add_parser(
            'undeploy', help='Undeploy device with a template')
        sp_device_destroy.add_argument(
            't',
            help='Template name (file=runtime/tpl/<TPL>.yml|json)',
            metavar='TPL').completer = self.ComplDeviceTPL(self)
        sp_device_destroy.add_argument(
            '-c',
            '--config',
            help='Template vars, comma separated',
            metavar='VARS',
            dest='c')

    def add_uc_modbus_functions(self):
        ap_modbus = self.sp.add_parser('modbus', help='ModBus ports')
        sp_modbus = ap_modbus.add_subparsers(
            dest='_func', metavar='func', help='ModBus port commands')

        sp_modbus_list = sp_modbus.add_parser('list', help='List defined ports')
        sp_modbus_create = sp_modbus.add_parser(
            'create', help='Create (define) new port')
        sp_modbus_create.add_argument('i', help='Port ID', metavar='ID')
        sp_modbus_create.add_argument(
            'p',
            help=
            'Port parameters (proto:port/host:params, ' + \
                    'e.g. tcp:192.168.11.11:502 or rtu:/dev/ttyS0:9600:8:E:1)',
            metavar='PARAMS').completer = self.ComplModBusProto()
        sp_modbus_create.add_argument(
            '-l',
            '--lock',
            help='Lock port on operations',
            action='store_true',
            dest='l')
        sp_modbus_create.add_argument(
            '-t',
            '--timeout',
            help='Port timeout',
            metavar='SEC',
            type=float,
            dest='t')
        sp_modbus_create.add_argument(
            '-r',
            '--retries',
            help='Operation retry attempts',
            metavar='RETRIES',
            type=int,
            dest='r')
        sp_modbus_create.add_argument(
            '-d',
            '--delay',
            help='Delay between operations',
            metavar='SEC',
            type=float,
            dest='d')
        sp_modbus_create.add_argument(
            '-y',
            '--save',
            help='save configuration on success load',
            dest='_save',
            action='store_true')
        sp_modbus_test = sp_modbus.add_parser('test', help='Test defined port')
        sp_modbus_test.add_argument(
            'i', help='Port ID',
            metavar='ID').completer = self.ComplModBus(self)
        sp_modbus_destroy = sp_modbus.add_parser(
            'destroy', help='Destroy (undefine) port')
        sp_modbus_destroy.add_argument(
            'i', help='Port ID',
            metavar='ID').completer = self.ComplModBus(self)

        ap_modbus_slave = self.sp.add_parser(
            'modbus-slave', help='ModBus slave')
        sp_modbus_slave = ap_modbus_slave.add_subparsers(
            dest='_func', metavar='func', help='ModBus slave commands')
        sp_modbus_slave_get = sp_modbus_slave.add_parser(
            'get', help='Get Modbus slave register values')
        sp_modbus_slave_get.add_argument(
            'i',
            help='Regiser address(es), comma ' +
            'separated, predicated by type (h, c, i, d), range may be ' +
            'specified. e.g. h1000-1010,c10-15',
            metavar='REGISTERS')

    def add_uc_owfs_functions(self):
        ap_owfs = self.sp.add_parser('owfs', help='OWFS buses')
        sp_owfs = ap_owfs.add_subparsers(
            dest='_func', metavar='func', help='OWFS bus commands')

        sp_owfs_list = sp_owfs.add_parser('list', help='List defined buses')
        sp_owfs_create = sp_owfs.add_parser(
            'create', help='Create (define) new bus')
        sp_owfs_create.add_argument('i', help='Bus ID', metavar='ID')
        sp_owfs_create.add_argument(
            'n',
            help='Bus location (e.g. i2c=/dev/i2c-1:ALL or localhost:4304)',
            metavar='LOCATION')
        sp_owfs_create.add_argument(
            '-l',
            '--lock',
            help='Lock bus on operations',
            action='store_true',
            dest='l')
        sp_owfs_create.add_argument(
            '-t',
            '--timeout',
            help='Bus timeout',
            metavar='SEC',
            type=float,
            dest='t')
        sp_owfs_create.add_argument(
            '-r',
            '--retries',
            help='Operation retry attempts',
            metavar='RETRIES',
            type=int,
            dest='r')
        sp_owfs_create.add_argument(
            '-d',
            '--delay',
            help='Delay between operations',
            metavar='SEC',
            type=float,
            dest='d')
        sp_owfs_create.add_argument(
            '-y',
            '--save',
            help='save configuration on success load',
            dest='_save',
            action='store_true')
        sp_owfs_test = sp_owfs.add_parser('test', help='Test defined bus')
        sp_owfs_test.add_argument(
            'i', help='Bus ID', metavar='ID').completer = self.ComplOWFS(self)
        sp_owfs_scan = sp_owfs.add_parser('scan', help='Scan defined bus')
        sp_owfs_scan.add_argument(
            'i', help='Bus ID', metavar='ID').completer = self.ComplOWFS(self)
        sp_owfs_scan.add_argument(
            '-n', '--path', help='Equipment path', metavar='PATH', dest='n')
        sp_owfs_scan.add_argument(
            '-p',
            '--type',
            help='Equipment types (e.g. DS18S20,DS2405), comma separated',
            metavar='TYPE',
            dest='p')
        sp_owfs_scan.add_argument(
            '-a',
            '--attr',
            help='Equipment attributes (e.g. temperature, PIO, ' +
            'comma separated)',
            metavar='ATTRIBUTES',
            dest='a')
        sp_owfs_scan.add_argument(
            '-A',
            '--has-all',
            help='Equipment should have all attributes',
            action='store_true',
            dest='_has_all')
        sp_owfs_scan.add_argument(
            '-y',
            '--full',
            help='Get attribute values',
            action='store_true',
            dest='_full')
        sp_owfs_destroy = sp_owfs.add_parser(
            'destroy',
            help='Destroy (undefine) bus. Warning: if I2C bus is destroyed, ' +
            'controller must be restarted before it can be created again')
        sp_owfs_destroy.add_argument(
            'i', help='Bus ID', metavar='ID').completer = self.ComplOWFS(self)

    def add_uc_driver_functions(self):
        ap_phi = self.sp.add_parser('phi', help='PHI (Physical interface)')
        ap_lpi = self.sp.add_parser(
            'lpi', help='LPI (Logical to physical interface)')
        ap_driver = self.sp.add_parser('driver', help='Drivers ( PHI + LPI )')

        sp_phi = ap_phi.add_subparsers(
            dest='_func', metavar='func', help='PHI commands')
        sp_lpi = ap_lpi.add_subparsers(
            dest='_func', metavar='func', help='LPI commands')
        sp_driver = ap_driver.add_subparsers(
            dest='_func', metavar='func', help='Driver commands')

        sp_phi_list = sp_phi.add_parser('list', help='List loaded PHIs')
        sp_phi_list.add_argument(
            '-y',
            '--full',
            help='Full information about PHI',
            dest='_full',
            action='store_true')
        sp_driver_list = sp_driver.add_parser(
            'list', help='List loaded drivers')
        sp_driver_list.add_argument(
            '-y',
            '--full',
            help='Full information about driver',
            dest='_full',
            action='store_true')

        sp_phi_get = sp_phi.add_parser('get', help='Get loaded PHI info')
        sp_phi_get.add_argument(
            'i', help='PHI ID',
            metavar='PHI_ID').completer = self.ComplPHI(self)

        sp_phi_set = sp_phi.add_parser('set', help='Set PHI config prop')
        sp_phi_set.add_argument(
            'i', help='PHI ID',
            metavar='PHI ID').completer = self.ComplPHI(self)
        sp_phi_set.add_argument('p', help='Config property', metavar='PROP')
        sp_phi_set.add_argument('v', help='Value', nargs='?', metavar='VAL')
        sp_phi_set.add_argument(
            '-y',
            '--save',
            help='Save PHI config after set',
            dest='_save',
            action='store_true')

        sp_phi_mods = sp_phi.add_parser('mods', help='List available PHI mods')
        sp_lpi_mods = sp_lpi.add_parser('mods', help='List available LPI mods')

        sp_phi_test = sp_phi.add_parser('test', help='Send test call to PHI')
        sp_phi_test.add_argument(
            'i', help='PHI ID',
            metavar='PHI_ID').completer = self.ComplPHI(self)
        sp_phi_test.add_argument(
            'c', help='PHI test command',
            metavar='CMD').completer = self.ComplPHITestCMD(self)

        sp_phi_exec = sp_phi.add_parser('exec', help='Send exec call to PHI')
        sp_phi_exec.add_argument(
            'i', help='PHI ID',
            metavar='PHI_ID').completer = self.ComplPHI(self)
        sp_phi_exec.add_argument(
            'c', help='PHI exec command',
            metavar='CMD').completer = self.ComplPHIExecCMD(self)
        sp_phi_exec.add_argument(
            'a', help='Command arguments', metavar='ARGS', nargs='?')

        sp_driver_get = sp_driver.add_parser(
            'get', help='Get loaded driver info')
        sp_driver_get.add_argument(
            'i', help='Driver ID',
            metavar='DRIVER_ID').completer = self.ComplDriver(self)

        sp_driver_set = sp_driver.add_parser(
            'set', help='Set driver config prop (driver can not be default)')
        sp_driver_set.add_argument(
            'i', help='DRIVER ID',
            metavar='DRIVER ID').completer = self.ComplDriver(self)
        sp_driver_set.add_argument('p', help='Config property', metavar='PROP')
        sp_driver_set.add_argument('v', help='Value', nargs='?', metavar='VAL')
        sp_driver_set.add_argument(
            '-y',
            '--save',
            help='Save driver config after set',
            dest='_save',
            action='store_true')

        sp_phi_load = sp_phi.add_parser('load', help='Load PHI')
        sp_phi_load.add_argument('i', help='PHI ID', metavar='PHI_ID')
        sp_phi_load.add_argument(
            'm', help='PHI module',
            metavar='PHI_MOD').completer = self.ComplPHIMods(self)
        sp_phi_load.add_argument(
            '-c',
            '--config',
            help='PHI configuration values, comma separated',
            dest='c',
            metavar='CONFIG')
        sp_phi_load.add_argument(
            '-y',
            '--save',
            help='save configuration on success load',
            dest='_save',
            action='store_true')

        sp_driver_load = sp_driver.add_parser('load', help='Load driver')
        sp_driver_load.add_argument(
            'i', help='Driver ID (PHI_ID.LPI_ID)',
            metavar='PHI_ID.LPI_ID').completer = self.ComplPHI(
                self, for_driver=True)
        sp_driver_load.add_argument(
            'm', help='LPI module',
            metavar='LPI_MOD').completer = self.ComplLPIMods(self)
        sp_driver_load.add_argument(
            '-c',
            '--config',
            help='driver configuration values, comma separated',
            dest='c',
            metavar='CONFIG')
        sp_driver_load.add_argument(
            '-y',
            '--save',
            help='save configuration on success load',
            dest='_save',
            action='store_true')

        sp_phi_unload = sp_phi.add_parser('unload', help='Unload PHI')
        sp_phi_unload.add_argument(
            'i', help='PHI ID',
            metavar='PHI_ID').completer = self.ComplPHI(self)

        sp_driver_unload = sp_driver.add_parser('unload', help='Unload driver')
        sp_driver_unload.add_argument(
            'i', help='Driver ID',
            metavar='DRIVER_ID').completer = self.ComplDriver(self)

        sp_driver_assign = sp_driver.add_parser(
            'assign', help='Set for the item (action & update)')
        sp_driver_assign.add_argument(
            'i', help='Item ID',
            metavar='ID').completer = self.ComplItemOID(self)
        sp_driver_assign.add_argument(
            'd', help='Driver ID',
            metavar='DRIVER_ID').completer = self.ComplDriver(self)
        sp_driver_assign.add_argument(
            '-c',
            '--config',
            help='item driver config (ports etc.)',
            dest='c',
            metavar='CONFIG')
        sp_driver_assign.add_argument(
            '-y',
            '--save',
            help='save configuration',
            dest='_save',
            action='store_true')

        sp_driver_unassign = sp_driver.add_parser(
            'unassign',
            help='Unassign from the item ' +
            '(set action, update and driver_config to null)')
        sp_driver_unassign.add_argument(
            'i', help='Item ID',
            metavar='ID').completer = self.ComplItemOID(self)
        sp_driver_unassign.add_argument(
            '-y',
            '--save',
            help='save configuration',
            dest='_save',
            action='store_true')

        sp_phi_modinfo = sp_phi.add_parser('modinfo', help='PHI module info')
        sp_phi_modinfo.add_argument(
            'm', help='PHI module',
            metavar='PHI_MOD').completer = self.ComplPHIMods(self)

        sp_lpi_modinfo = sp_lpi.add_parser('modinfo', help='LPI module info')
        sp_lpi_modinfo.add_argument(
            'm', help='LPI module',
            metavar='LPI_MOD').completer = self.ComplLPIMods(self)

        sp_phi_modhelp = sp_phi.add_parser('modhelp', help='PHI module help')
        sp_phi_modhelp.add_argument(
            'm', help='PHI module',
            metavar='PHI_MOD').completer = self.ComplPHIMods(self)
        sp_phi_modhelp.add_argument(
            'c',
            help='Help context (cfg, get, set)',
            metavar='CONTEXT',
            choices=['cfg', 'get', 'set'])

        sp_lpi_modhelp = sp_lpi.add_parser('modhelp', help='LPI module help')
        sp_lpi_modhelp.add_argument(
            'm', help='LPI module',
            metavar='LPI_MOD').completer = self.ComplLPIMods(self)
        sp_lpi_modhelp.add_argument(
            'c',
            help='Help context (cfg, action, update)',
            metavar='CONTEXT',
            choices=['cfg', 'action', 'update'])

        sp_phi_download = sp_phi.add_parser(
            'download', help='Download and put PHI')
        sp_phi_download.add_argument(
            '_uri', help='Module HTTP URI', metavar='URI')
        sp_phi_download.add_argument(
            '-y',
            '--force',
            help='force put even if module file already exist',
            dest='_force',
            action='store_true')

        sp_phi_unlink = sp_phi.add_parser(
            'unlink', help='Unlink PHI (delete mod file)')
        sp_phi_unlink.add_argument(
            'm', help='PHI module',
            metavar='PHI_MOD').completer = self.ComplPHIMods(self)

    def edit_action(self, props):
        if self.apiuri:
            self.print_local_only()
            return self.local_func_result_failed
        code, data = self.call(args=['config', 'props', props.get('i')])
        if code or not isinstance(data, dict):
            return self.local_func_result_failed
        if not 'action_exec' in data:
            self.print_err('no actions available for this item type')
            return self.local_func_result_failed
        action_file = data.get('action_exec') if data.get(
            'action_exec') else props.get('i').split('/')[-1]
        if action_file.startswith('|'):
            self.print_err('Action is set to driver: ' + action_file[1:])
            return self.local_func_result_failed
        fname = '{}/xc/uc/{}'.format(dir_runtime, action_file) if \
                not action_file.startswith('/') else action_file
        if action_file.find('/') != -1:
            action_dir = '/'.join(fname.split('/')[:-1])
            if os.system('mkdir -p ' + action_dir):
                return self.local_func_result_failed
        editor = os.environ.get('EDITOR', 'vi')
        if os.system(editor + ' ' + fname):
            return self.local_func_result_failed
        try:
            os.chmod(fname, 0o755)
        except:
            self.print_err('Unable to set action file permissions: ' + fname)
            return self.local_func_result_failed
        if not os.path.isfile(fname):
            self.print_err('Action script not created: ' + fname)
            return self.local_func_result_failed
        return self.local_func_result_ok

    def edit_update(self, props):
        if self.apiuri:
            self.print_local_only()
            return self.local_func_result_failed
        code, data = self.call(args=['config', 'props', props.get('i')])
        if code or not isinstance(data, dict):
            return self.local_func_result_failed
        if not 'update_exec' in data:
            self.print_err('no updates available for this item type')
            return self.local_func_result_failed
        update_file = data.get('update_exec') if data.get(
            'update_exec') else props.get('i').split('/')[-1] + '_update'
        if update_file.startswith('|'):
            self.print_err('Update is set to driver: ' + update_file[1:])
            return self.local_func_result_failed
        fname = '{}/xc/uc/{}'.format(dir_runtime, update_file) if \
                not update_file.startswith('/') else update_file
        if update_file.find('/') != -1:
            update_dir = '/'.join(fname.split('/')[:-1])
            if os.system('mkdir -p ' + update_dir):
                return self.local_func_result_failed
        editor = os.environ.get('EDITOR', 'vi')
        if os.system(editor + ' ' + fname):
            return self.local_func_result_failed
        try:
            os.chmod(fname, 0o755)
        except:
            self.print_err('Unable to set update file permissions: ' + fname)
            return self.local_func_result_failed
        if not os.path.isfile(fname):
            self.print_err('Update script not created: ' + fname)
            return self.local_func_result_failed
        return self.local_func_result_ok

    def edit_tpl(self, props):
        import jinja2
        import jsonpickle
        import yaml
        try:
            yaml.warnings({'YAMLLoadWarning': False})
        except:
            pass

        tpl_decoder = {
            'json': jsonpickle.decode,
            'yml': yaml.load,
            'yaml': yaml.load
        }
        if self.apiuri:
            self.print_local_only()
            return self.local_func_result_failed
        tpl = props.get('i')
        if not tpl:
            return self.local_func_result_failed
        for ext in ['yml', 'yaml', 'json']:
            fname = '{}/tpl/{}.{}'.format(dir_runtime, tpl, ext)
            if os.path.isfile(fname):
                break
            fname = None
        if not fname:
            self.print_err('Template file not found')
            return self.local_func_result_failed
        editor = os.environ.get('EDITOR', 'vi')
        if os.system(editor + ' ' + fname):
            return self.local_func_result_failed
        try:
            t = jinja2.Environment(loader=jinja2.BaseLoader).from_string(
                open(fname).read())
            tpl_decoder.get(ext)(t.render())
        except Exception as e:
            self.print_err('Unable to validate template. ' + str(e))
            return self.local_func_result_failed
        return self.local_func_result_ok


_me = 'EVA ICS UC CLI version %s' % __version__

prog = os.path.basename(__file__)[:-3]
if prog == 'eva-shell': prog = 'eva uc'

cli = UC_CLI('uc', _me, prog=prog)

_api_functions = {
    'history': 'state_history',
    'action:exec': 'action',
    'action:result': 'result',
    'action:enable': 'enable_actions',
    'action:disable': 'disable_actions',
    'action:terminate': 'terminate',
    'action:clear': 'q_clean',
    'action:kill': 'kill',
    'config:get': 'get_config',
    'config:save': 'save_config',
    'config:props': 'list_props',
    'config:set': 'set_prop',
    'clone:item': 'clone',
    'device:templates': 'list_device_tpl',
    'device:deploy': 'deploy_device',
    'device:update': 'update_device',
    'device:undeploy': 'undeploy_device',
    'modbus:list': 'list_modbus_ports',
    'modbus:create': 'create_modbus_port',
    'modbus:destroy': 'destroy_modbus_port',
    'modbus:test': 'test_modbus_port',
    'modbus-slave:get': 'get_modbus_slave_data',
    'owfs:list': 'list_owfs_buses',
    'owfs:create': 'create_owfs_bus',
    'owfs:destroy': 'destroy_owfs_bus',
    'owfs:test': 'test_owfs_bus',
    'owfs:scan': 'scan_owfs_bus',
    'phi:list': 'list_phi',
    'phi:get': 'get_phi',
    'phi:set': 'set_phi_prop',
    'phi:mods': 'list_phi_mods',
    'phi:test': 'test_phi',
    'phi:exec': 'exec_phi',
    'phi:load': 'load_phi',
    'phi:unload': 'unload_phi',
    'phi:unlink': 'unlink_phi_mod',
    'phi:download': 'put_phi_mod',
    'phi:modinfo': 'modinfo_phi',
    'phi:modhelp': 'modhelp_phi',
    'lpi:mods': 'list_lpi_mods',
    'lpi:modinfo': 'modinfo_lpi',
    'lpi:modhelp': 'modhelp_lpi',
    'driver:list': 'list_drivers',
    'driver:get': 'get_driver',
    'driver:set': 'set_driver_prop',
    'driver:load': 'load_driver',
    'driver:unload': 'unload_driver',
    'driver:assign': 'assign_driver',
    'driver:unassign': 'assign_driver',
    'edit:action': cli.edit_action,
    'edit:update': cli.edit_update,
    'edit:template': cli.edit_tpl
}

_pd_cols = {
    'state': ['oid', 'action_enabled', 'status', 'value', 'nstatus', 'nvalue'],
    'state_': [
        'oid', 'action_enabled', 'description', 'location', 'status', 'value',
        'nstatus', 'nvalue'
    ],
    'result': [
        'time', 'uuid', 'priority', 'item_oid', 'nstatus', 'nvalue', 'exitcode',
        'status'
    ],
    'list': ['oid', 'description'],
    'get_modbus_slave_data': ['reg', 'addr', 'addr_hex', 'value', 'hex'],
    'list_modbus_ports':
    ['id', 'params', 'lock', 'timeout', 'retries', 'delay'],
    'list_owfs_buses':
    ['id', 'location', 'lock', 'timeout', 'retries', 'delay'],
    'list_phi_': ['id', 'mod', 'description', 'version'],
    'list_drivers_':
    ['id', 'mod', 'phi_id', 'phi_mod', 'description', 'version'],
    'list_drivers': ['id', 'mod', 'phi_id'],
    'list_phi_mods': ['mod', 'equipment', 'description', 'version', 'api'],
    'list_lpi_mods': ['mod', 'logic', 'description', 'version', 'api'],
    'modhelp_lpi': ['name', 'type', 'required', 'help'],
    'modhelp_phi': ['name', 'type', 'required', 'help']
}

_pd_idx = {
    'state': 'oid',
    'list': 'oid',
    'list_device_tpl': 'name',
    'result': 'time',
    'list_phi_mods': 'mod',
    'list_lpi_mods': 'mod'
}

_fancy_indentsp = {
    'list_props': 26,
    'get_phi': 14,
    'get_driver': 12,
    'load_phi': 14,
    'load_driver': 12
}

_always_json = ['get_config']

cli.always_json += _always_json
cli.always_print += ['action', 'action_toggle', 'cmd']
cli.arg_sections += [
    'action', 'config', 'clone', 'device', 'modbus', 'owfs', 'phi', 'lpi',
    'driver', 'modbus-slave'
]
cli.api_cmds_timeout_correction = ['cmd', 'action']
cli.set_api_functions(_api_functions)
cli.set_pd_cols(_pd_cols)
cli.set_pd_idx(_pd_idx)
cli.set_fancy_indentsp(_fancy_indentsp)
code = cli.run()
sys.exit(code)
