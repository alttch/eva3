from __future__ import print_function

__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"

import argparse
# to be compatible with argcomplete
import getopt
import sys
import os
import io
import rapidtables
from eva.client import apiclient
from eva.gcli import GCLI

from collections import OrderedDict
from pathlib import Path

say_bye = True
readline_processing = True if \
        not os.environ.get('EVA_CLI_DISABLE_HISTORY') else False
parent_shell_name = None
shells_available = []

shell_switch_to = None
shell_switch_to_extra_args = None
shell_back_interactive = False

completer_stream = io.BytesIO()

default_errors = {
    apiclient.result_not_found: 'Object not found',
    apiclient.result_forbidden: 'Forbidden',
    apiclient.result_api_error: 'API error',
    apiclient.result_unknown_error: 'Unknown error',
    apiclient.result_not_ready: 'API not ready',
    apiclient.result_func_unknown: 'API function is not supported by server',
    apiclient.result_server_error: 'Server error',
    apiclient.result_server_timeout: 'Server timeout',
    apiclient.result_bad_data: 'Bad data',
    apiclient.result_invalid_params: 'Invalid function params',
    apiclient.result_already_exists: 'resource already exists',
    apiclient.result_busy: 'resource is in use'
}

dir_eva = Path(__file__).absolute().parents[3].as_posix()


class ComplGeneric(object):

    def __init__(self, cli):
        # self.cli = cli if cli.interactive else None
        self.cli = cli


class ComplCVAR(ComplGeneric):

    def __call__(self, prefix, **kwargs):
        code, data = self.cli.call('cvar list')
        if code:
            return True
        return data.keys()


class ComplKey(ComplGeneric):

    def __call__(self, prefix, **kwargs):
        code, data = self.cli.call('key list')
        if code:
            return True
        for v in data:
            yield v['key_id']


class ComplKeyDynamic(ComplGeneric):

    def __call__(self, prefix, **kwargs):
        code, data = self.cli.call('key list')
        if code:
            return True
        for v in data:
            if v.get('dynamic'):
                yield v['key_id']


class ComplKeyProp(ComplGeneric):

    def __call__(self, prefix, **kwargs):
        code, data = self.cli.call(
            ['key', 'props', kwargs.get('parsed_args').i])
        if code:
            return True
        result = list(data.keys())
        return result


class ComplUser(ComplGeneric):

    def __call__(self, prefix, **kwargs):
        code, data = self.cli.call('user list')
        if code:
            return True
        for v in data:
            yield v['user']


class ComplToken(ComplGeneric):

    def __call__(self, prefix, **kwargs):
        code, data = self.cli.call('user tokens')
        if code:
            return True
        for v in data:
            yield v['token']


class ComplCoreScript(ComplGeneric):

    def __call__(self, prefix, **kwargs):
        import glob
        result = []
        files = glob.glob(f'{dir_eva}/xc/{self.cli.product}/cs/*.py')
        for f in files:
            if os.path.isfile(f):
                result.append(os.path.basename(f[:-3]))
        return result


class GenericCLI(GCLI):

    def __init__(self, product, name, prog=None, remote_api_enabled=True):
        self.product = product
        self.remote_api_enabled = remote_api_enabled
        super().__init__(name, prog)
        self.apikey = None
        self.apiuri = None
        self.in_json = False
        self.nodename = None
        self.default_timeout = 20
        self.timeout = self.default_timeout
        self.ssl_verify = False
        self.say_bye = say_bye
        self.readline_processing = readline_processing
        self._argcompleted = False
        if remote_api_enabled:
            self.always_print = ['cmd']
            self.common_api_functions = {
                'cvar:list': 'get_cvar',
                'cvar:get': 'get_cvar',
                'cvar:set': 'set_cvar',
                'cvar:delete': 'set_cvar',
                'debug': 'set_debug',
                'file:create': 'file_put',
                'file:upload': 'file_put',
                'file:mod': 'file_set_exec',
                'log:api': 'api_log_get',
                'key:list': 'list_keys',
                'key:create': 'create_key',
                'key:props': 'list_key_props',
                'key:set': 'set_key_prop',
                'key:regenerate': 'regenerate_key',
                'key:destroy': 'destroy_key',
                'user:list': 'list_users',
                'user:create': 'create_user',
                'user:password': 'set_user_password',
                'user:key': 'set_user_key',
                'user:destroy': 'destroy_user',
                'user:tokens': 'list_tokens',
                'user:drop-tokens': 'drop_tokens',
            }
            self.common_pd_cols = {
                'list_keys': [
                    'key_id', 'dynamic', 'master', 'sysfunc', 'allow'
                ],
                'list_corescript_mqtt_topics': ['topic', 'qos'],
                'list_users': ['user', 'key_id'],
                'list_tokens': [
                    'user', 'type', 'key_id', 'active', 'mode', 'token'
                ],
                'log_get': ['time', 'host', 'p', 'level', 'message'],
                'api_log_get': [
                    'time', 'gw', 'ip', 'auth', 'u', 'utp', 'ki', 'status',
                    'func', 'params'
                ],
                'log_get_': [
                    'time', 'host', 'p', 'level', 'mod', 'thread', 'message'
                ],
                'list_plugins': [
                    'name', 'version', 'ready', 'author', 'license'
                ]
            }
            self.arg_sections = ['log', 'cvar', 'file', 'key', 'user']
            self.common_fancy_indentsp = {'test': 14}
            self.fancy_indentsp = self.common_fancy_indentsp
        self.log_levels = {
            10: 'DEBUG',
            20: 'INFO',
            30: 'WARNING',
            40: 'ERROR',
            50: 'CRITICAL'
        }
        self.api_functions = self.common_api_functions
        self.api_cmds_timeout_correction = []
        self.setup_parser()
        import pwd
        dir_owner = os.stat(dir_eva + '/runtime').st_uid
        try:
            dir_owner = pwd.getpwuid(dir_owner).pw_name
        except KeyError:
            dir_owner = f'uid {dir_owner}'
        current_user = pwd.getpwuid(os.getuid()).pw_name
        if dir_owner != current_user:
            self.print_warn(f'EVA ICS seems to be configured to work under '
                            f'{dir_owner}, current CLI user: {current_user}')
            self.print_warn('This may cause serious permission problems')

    def get_prompt(self):
        if self.prompt:
            return self.prompt
        prompt = self.default_prompt
        ppeva = '' if not parent_shell_name else \
                self.colored(parent_shell_name,
                        'yellow', attrs=['bold'], rlsafe=True) + '/'
        if self.product:
            product_str = self.colored(self.product,
                                       'yellow',
                                       attrs=['bold'],
                                       rlsafe=True)
            host_str = ''
            if self.nodename:
                nodename = self.nodename
            else:
                import platform
                nodename = platform.node()
            if self.remote_api_enabled:
                try:
                    if not self.can_colorize():
                        raise Exception('no colors required')
                    cmd = []
                    if self.timeout:
                        cmd.append('-T')
                        cmd.append(str(self.timeout))
                    if self.apiuri:
                        cmd.append('-U')
                        cmd.append(self.apiuri)
                    if self.apikey:
                        cmd.append('-K')
                        cmd.append(self.apikey)
                    cmd.append('test')
                    code, result = self.execute_function(cmd,
                                                         return_result=True)
                    if code != apiclient.result_ok or \
                            not 'key_id' in result['acl']:
                        raise Exception('test failed')
                    h = result['acl']['key_id'] + '@' + result['system']
                    host_str = ':' + self.colored(
                        h, 'blue', attrs=['bold'], rlsafe=True)
                    if result['acl'].get('master'):
                        prompt = '# '
                except:
                    if self.apiuri:
                        h = ' ' + self.apiuri.replace('https://', '').replace(
                            'http://', '')
                    else:
                        h = ''
                    product_str = self.colored(self.product + ':' + nodename,
                                               'grey',
                                               attrs=['bold'],
                                               rlsafe=True)
                    host_str = self.colored(h,
                                            'grey',
                                            attrs=['bold'],
                                            rlsafe=True)
            else:
                product_str += self.colored(':' + nodename,
                                            'yellow',
                                            attrs=['bold'],
                                            rlsafe=True)
            prompt = '[%s%s]%s' % (ppeva + product_str, host_str, prompt)
        return prompt

    def print_interactive_help(self):
        super().print_interactive_help()
        if self.remote_api_enabled:
            print('a: show API params')
            print('c <host:port> [key] [timeout]: connect to remote API')
            print('k: key display/set (k. for key reset)')
            print('u: api uri display/set (u. for uri reset)')
            print('t: timeout display/set (t. for timeout reset)')
            print('d: toggle client debug mode')
            print()
            print('sh: start system shell')
            print('top: display system processes')
            print('w: display uptime and who is online')
            print('date: display system date and time')
            print()

    def parse_primary_args(self):
        super().parse_primary_args()
        try:
            if self.remote_api_enabled:
                o, a = getopt.getopt(sys.argv[1:], 'F:U:K:T', [
                    'client-ini-file=', 'exec-batch=', 'pass-batch-err',
                    'api-key=', 'api-url=', 'api-timeout='
                ])
                for i, v in o:
                    if i == '-U' or i == '--api-url':
                        self.apiuri = v
                    elif i == '-K' or i == '--api-key':
                        self.apikey = v
                    elif i == '-J' or i == '--json':
                        self.in_json = True
                    elif i == '-T' or i == '--api-timeout':
                        try:
                            self.timeout = float(v)
                        except:
                            pass
                    elif i == '-F' or i == '--client-ini-file':
                        c = self.parse_ini(v)
                        if 'uri' in c:
                            self.apiuri = c.get('uri')
                        if 'key' in c:
                            self.apikey = c.get('key')
                        if 'timeout' in c:
                            self.timeout = c.get('timeout')
                        if 'debug' in c:
                            self.debug = c.get('debug')
                        if 'json' in c:
                            self.in_json = c.get('json')
                        if 'raw' in c:
                            self.always_suppress_colors = c.get('raw')
        except:
            pass

    def parse_ini(self, fname):
        import configparser
        cfg = configparser.ConfigParser(inline_comment_prefixes=';')
        result = {}
        try:
            cfg.read(fname)
        except:
            self.print_err('unable to open %s' % fname)
            return {}
        try:
            result['uri'] = cfg.get(self.product, 'uri')
        except:
            pass
        try:
            result['key'] = cfg.get(self.product, 'key')
        except:
            pass
        try:
            result['timeout'] = float(cfg.get(self.product, 'timeout'))
        except:
            pass
        try:
            result['debug'] = cfg.get(self.product, 'debug') == 'yes'
        except:
            pass
        try:
            result['json'] = cfg.get(self.product, 'json') == 'yes'
        except:
            pass
        try:
            result['raw'] = cfg.get(self.product, 'raw') == 'yes'
        except:
            pass
        return result

    def get_log_level_name(self, level):
        l = self.log_levels.get(level)
        return l if l else level

    def get_log_level_code(self, name):
        if not isinstance(name, str):
            return name
        n = str.upper(name)
        for l, v in self.log_levels.items():
            if n[0] == v[0]:
                return l
        return name

    def format_log_str(self, r, res):
        if res['level'] == 'DEBUG':
            return self.colored(r, color='grey', attrs=['bold'])
        elif res['level'] == 'WARNING':
            return self.colored(r, color='yellow', attrs=[])
        elif res['level'] == 'ERROR':
            return self.colored(r, color='red', attrs=[])
        elif res['level'] == 'CRITICAL':
            return self.colored(r, color='red', attrs=['bold'])
        else:
            return r

    def add_primary_options(self):
        if self.remote_api_enabled:
            self.ap.add_argument(
                '-K',
                '--api-key',
                help='API key, if no key specified, local master key is used',
                dest='_api_key',
                metavar='KEY')
            self.ap.add_argument('-U',
                                 '--api-url',
                                 help='API URL',
                                 dest='_api_uri',
                                 metavar='URL')
            self.ap.add_argument('-T',
                                 '--api-timeout',
                                 help='API request timeout (in seconds)',
                                 type=float,
                                 dest='_timeout',
                                 metavar='TIMEOUT')
            self.ap.add_argument('-D',
                                 '--debug',
                                 help='Enable debug messages',
                                 action='store_true',
                                 dest='_debug',
                                 default=False)
            self.ap.add_argument(
                '-F',
                '--client-ini-file',
                help='Read API client options from config file',
                dest='_ini_file',
                metavar='FILE')
        super().add_primary_options()

    def set_api_functions(self, fn_table={}):
        self.api_functions = self.common_api_functions.copy()
        self.append_api_functions(fn_table)

    def append_api_functions(self, fn_table={}):
        self.api_functions.update(fn_table)

    def set_pd_cols(self, pd_cols={}):
        self.pd_cols = self.common_pd_cols.copy()
        self.pd_cols.update(pd_cols)

    def set_fancy_indentsp(self, fancy_indentsp={}):
        self.fancy_indentsp = self.common_fancy_indentsp.copy()
        self.fancy_indentsp.update(fancy_indentsp)

    def prepare_result_data(self, data, api_func, itype):
        if api_func == 'log_get':
            result = []
            for d in data:
                from datetime import datetime
                d['host'] = d.pop('h')
                d['thread'] = d.pop('th')
                d['message'] = d.pop('msg')
                d['level'] = self.get_log_level_name(d.pop('l'))
                d['time'] = datetime.strftime(
                    datetime.fromtimestamp(d.pop('t')), '%Y-%m-%d %T')
                result.append(d)
            return result
        elif api_func == 'api_log_get':
            from datetime import datetime
            result = []
            for d in data:
                d['time'] = datetime.strftime(
                    datetime.fromtimestamp(d.pop('t')), '%Y-%m-%d %T')
                result.append(d)
            return result
        elif api_func == 'list_corescript_mqtt_topics':
            return sorted(data, key=lambda k: k['topic'])
        elif api_func == 'list_corescripts':
            import time
            result = []
            for d in data.copy():
                d['modified'] = time.ctime(d['modified'])
                result.append(d)
            return result
        elif api_func == 'list_tokens':
            from datetime import datetime
            for d in data:
                d['user'] = d.get('u', '')
                d['type'] = d.get('utp')
                d['key_id'] = d.get('ki')
                m = d.get('m')
                if m == 1:
                    d['mode'] = 'normal'
                elif m == 2:
                    d['mode'] = 'readonly'
                t = d.get('t')
                if t:
                    d['active'] = datetime.fromtimestamp(t).isoformat()
            return data
        else:
            return data

    def prepare_result_dict(self, data, api_func, itype):
        return data

    def fancy_print_result(self,
                           result,
                           api_func,
                           itype,
                           indent=0,
                           print_ok=True,
                           a=None):
        if result and isinstance(result, dict):
            _result = self.prepare_result_dict(result, api_func, itype)
            rprinted = False
            h = None
            out = None
            err = None
            indentsp = self.fancy_indentsp.get(api_func)
            if not indentsp:
                indentsp = 10
            for v in sorted(_result.keys()):
                if v == 'ok' and api_func not in ['test']:
                    continue
                if v == 'help':
                    if not indent:
                        h = _result[v]
                    else:
                        pass
                elif v == 'out' and not indent:
                    out = _result[v]
                elif v == 'err' and not indent:
                    err = _result[v]
                elif v != '_result':
                    if isinstance(_result[v], dict):
                        if indent:
                            print(' ' * (indent * indentsp),
                                  end=self.colored('>' * indent) + ' ')
                        print(((self.colored(
                            '{:>%u} ', color='blue', attrs=['bold']) +
                                self.colored(':') +
                                self.colored('  {}', color='yellow')) %
                               max(map(len, _result))).format(v, ''))
                        self.fancy_print_result(_result[v],
                                                api_func,
                                                itype,
                                                indent + 1,
                                                a=a)
                    else:
                        if indent:
                            print(' ' * (indent * indentsp),
                                  end=self.colored('>' * indent) + ' ')
                        if isinstance(_result[v], list):
                            _r = []
                            for vv in _result[v]:
                                _r.append(str(vv))
                            _v = ', '.join(_r)
                        else:
                            _v = _result[v]
                        print(((self.colored(
                            '{:>%u} ', color='blue', attrs=['bold']) +
                                self.colored(':') +
                                self.colored(' {}', color='yellow')) %
                               max(map(len, _result))).format(v, _v))
                    rprinted = True
            if h:
                print(self.colored('-' * 81, color='grey'))
                print(h.strip())
                rprinted = True
            if out is not None and out != '':
                print(self.colored('-' * 81, color='grey'))
                print(self.colored('OUTPUT:', color='blue'))
                if isinstance(out, list) or isinstance(out, dict):
                    self.print_json(out)
                else:
                    print(str(out).strip())
                rprinted = True
            if err is not None and err != '':
                print(self.colored('-' * 81, color='grey'))
                print(self.colored('ERROR:', color='red'))
                if isinstance(err, list) or isinstance(err, dict):
                    self.print_json(err)
                else:
                    print(str(err).strip())
                rprinted = True
            if not rprinted and not indent and print_ok:
                print('OK')
        elif result and isinstance(result, list):
            table = []
            func = api_func + self.cur_api_func_is_full
            for r in self.prepare_result_data(result, api_func, itype):
                t = OrderedDict()
                if func in self.pd_cols:
                    for c in self.pd_cols[func]:
                        t[c] = self.list_to_str(r.get(c)).replace('\n', ' ')
                else:
                    for i, c in r.items():
                        t[i] = self.list_to_str(c).replace('\n', ' ')
                table.append(t)
            if table:
                header, rows = rapidtables.format_table(
                    table,
                    rapidtables.FORMAT_GENERATOR,
                    max_column_width=120 if api_func == 'log_get' and
                    (not a or a._full_display is False) else None)
                print(self.colored(header, color='blue', attrs=[]))
                print(self.colored('-' * len(header), color='grey', attrs=[]))
                for r, res in zip(rows, table):
                    r = self.format_log_str(r,
                                            res) if api_func == 'log_get' else r
                    print(r)
            else:
                print('no data')
        elif result:
            print(result)

    def add_functions(self):
        if self.remote_api_enabled:
            self._add_primary_functions()
            self._add_cmd_functions()
            self._add_lock_functions()
            self._add_log_functions()
            self._add_cvar_functions()
            self._add_debug_functions()
            self._add_file_functions()
            self._add_key_functions()
            self._add_user_functions()

    def _add_primary_functions(self):
        ap_test = self.sp.add_parser('test', help='API test')
        ap_save = self.sp.add_parser('save', help='Save item state and config')

    def _add_cmd_functions(self):
        ap_cmd = self.sp.add_parser('cmd', help='Execute remote command')
        ap_cmd.add_argument('c', help='Command to execute', metavar='CMD')
        ap_cmd.add_argument('-a',
                            '--args',
                            help='Command arguments',
                            metavar='ARGS',
                            dest='a')
        ap_cmd.add_argument('-w',
                            '--wait',
                            help='Wait for command finish',
                            metavar='SEC',
                            type=float,
                            dest='w')
        ap_cmd.add_argument('-t',
                            '--timeout',
                            help='Command timeout',
                            metavar='SEC',
                            type=float,
                            dest='t')

    def _add_lock_functions(self):
        ap_lock = self.sp.add_parser('lock', help='acquire lock')
        ap_lock.add_argument('l', help='Lock ID', metavar='ID')
        ap_lock.add_argument('-t',
                             '--timeout',
                             help='Max acquire wait time',
                             metavar='SEC',
                             type=float,
                             dest='t')
        ap_lock.add_argument('-e',
                             '--expires',
                             help='Lock expire time',
                             metavar='SEC',
                             type=float,
                             dest='e')
        ap_unlock = self.sp.add_parser('unlock', help='release lock')
        ap_unlock.add_argument('l', help='Lock ID', metavar='ID')

    def _add_log_functions(self):
        ap_log = self.sp.add_parser('log', help='Log functions')
        sp_log = ap_log.add_subparsers(dest='_func',
                                       metavar='func',
                                       help='Log commands')
        sp_log_debug = sp_log.add_parser('debug', help='Send debug message')
        sp_log_debug.add_argument('m', help='Message', metavar='MSG')
        sp_dump = self.sp.add_parser('dump', help='Dump memory (for debugging)')
        sp_dump.add_argument('-s',
                             '--support-request',
                             help='Prepare support request',
                             action='store_true',
                             dest='_sr')
        sp_log_info = sp_log.add_parser('info', help='Send info message')
        sp_log_info.add_argument('m', help='Message', metavar='MSG')
        sp_log_warning = sp_log.add_parser('warning',
                                           help='Send warning message')
        sp_log_warning.add_argument('m', help='Message', metavar='MSG')
        sp_log_error = sp_log.add_parser('error', help='Send error message')
        sp_log_error.add_argument('m', help='Message', metavar='MSG')
        sp_log_critical = sp_log.add_parser('critical',
                                            help='Send critical message')
        sp_log_critical.add_argument('m', help='Message', metavar='MSG')
        sp_log_get = sp_log.add_parser('get', help='Get system log messages')
        sp_log_get.add_argument('l',
                                help='Log level',
                                metavar='LEVEL',
                                nargs='?')
        sp_log_get.add_argument('-t',
                                '--seconds',
                                help='Get records for the last SEC seconds',
                                metavar='SEC',
                                dest='t')
        sp_log_get.add_argument('-n',
                                '--limit',
                                help='Limit records to',
                                metavar='LIMIT',
                                dest='n')
        sp_log_get.add_argument('-y',
                                '--full',
                                help='Display full log records',
                                dest='_full_display',
                                action='store_true')
        sp_log_get.add_argument('-x',
                                '--regex',
                                help='Filter by regex',
                                metavar='REGEX',
                                dest='x')
        sp_log_get.add_argument('-f',
                                '--follow',
                                help='Follow log until C-c',
                                dest='_follow',
                                action='store_true')

        sp_log_api = sp_log.add_parser('api', help='Get API call log')
        sp_log_api.add_argument('-s',
                                '--time-start',
                                help='Start time',
                                metavar='TIME',
                                dest='s')
        sp_log_api.add_argument('-e',
                                '--time-end',
                                help='End time',
                                metavar='TIME',
                                dest='e')
        sp_log_api.add_argument('-n',
                                '--limit',
                                help='Records limit (doesn\'t work with fill)',
                                metavar='N',
                                dest='n')
        sp_log_api.add_argument('-f',
                                '--filter',
                                help='Filter (field=value[,field=value...])',
                                metavar='FILTER',
                                dest='f')

    def _add_cvar_functions(self):
        ap_cvar = self.sp.add_parser('cvar', help='CVAR functions')
        sp_cvar = ap_cvar.add_subparsers(dest='_func',
                                         metavar='func',
                                         help='CVAR commands')
        sp_cvar_all = sp_cvar.add_parser('list', help='List all CVARS')
        sp_cvar_get = sp_cvar.add_parser('get', help='Get CVAR value')
        sp_cvar_get.add_argument('i', help='CVAR ID',
                                 metavar='ID').completer = ComplCVAR(self)
        sp_cvar_set = sp_cvar.add_parser('set', help='Set CVAR value')
        sp_cvar_set.add_argument('i', help='CVAR ID',
                                 metavar='ID').completer = ComplCVAR(self)
        sp_cvar_set.add_argument('v', help='Value', metavar='VALUE')
        sp_cvar_delete = sp_cvar.add_parser('delete', help='Delete CVAR')
        sp_cvar_delete.add_argument('i', help='CVAR ID',
                                    metavar='ID').completer = ComplCVAR(self)

    def _add_debug_functions(self):
        ap_debug = self.sp.add_parser('debug', help='Debug control')
        ap_debug.add_argument('debug',
                              help='Debug mode (on/off)',
                              metavar='MODE',
                              choices=['on', 'off'])

    def _add_file_functions(self):
        ap_file = self.sp.add_parser('file',
                                     help='File management in runtime folder')
        sp_file = ap_file.add_subparsers(dest='_func',
                                         metavar='func',
                                         help='File commands')

        sp_file_get = sp_file.add_parser('get', help='Download file')
        sp_file_get.add_argument(
            'i',
            help='File name (relative to runtime, without / in the beginning)',
            metavar='REMOTE_FILE')
        # sp_file_get.add_argument(
        # '_fname', help='Local file name', metavar='LOCAL_FILE')

        sp_file_upload = sp_file.add_parser('upload', help='Upload file')
        sp_file_upload.add_argument('_fname',
                                    help='Local file name',
                                    metavar='LOCAL_FILE')
        sp_file_upload.add_argument(
            'i',
            help='File name (relative to runtime, without / in the beginning)',
            metavar='REMOTE_FILE')

        sp_file_create = sp_file.add_parser(
            'create', help='Create file with a content given in a command line')
        sp_file_create.add_argument(
            'i',
            help='File name (relative to runtime, without / in the beginning)',
            metavar='REMOTE_FILE')
        sp_file_create.add_argument('m', help='File content', metavar='CONTENT')

        sp_file_mod = sp_file.add_parser('mod', help='Set file exec mode')
        sp_file_mod.add_argument(
            'i',
            help='File name (relative to runtime, without / in the beginning)',
            metavar='REMOTE_FILE')
        sp_file_mod.add_argument(
            'e',
            help='Exec mode (0 - disabled [0644], 1 - enabled [0755])',
            metavar='MODE')

        sp_file_unlink = sp_file.add_parser('unlink', help='Delete remote file')
        sp_file_unlink.add_argument(
            'i',
            help='File name (relative to runtime, without / in the beginning)',
            metavar='REMOTE_FILE')

    def _add_key_functions(self):
        ap_key = self.sp.add_parser(
            'key', help='API key management (dynamic keys only)')
        sp_key = ap_key.add_subparsers(dest='_func',
                                       metavar='func',
                                       help='API key commands')

        sp_key_list = sp_key.add_parser('list', help='List API keys')

        sp_key_create = sp_key.add_parser('create', help='Create new API key')
        sp_key_create.add_argument('i', help='API key ID', metavar='ID')
        sp_key_create.add_argument('-y',
                                   '--save',
                                   help='Save key after creation',
                                   dest='_save',
                                   action='store_true')

        sp_key_props = sp_key.add_parser('props', help='List API key props')
        sp_key_props.add_argument(
            'i', help='API key ID',
            metavar='ID').completer = ComplKeyDynamic(self)

        sp_key_set_prop = sp_key.add_parser('set', help='Set API key prop')
        sp_key_set_prop.add_argument(
            'i', help='API key ID',
            metavar='ID').completer = ComplKeyDynamic(self)
        sp_key_set_prop.add_argument(
            'p', help='Config property',
            metavar='PROP').completer = ComplKeyProp(self)
        sp_key_set_prop.add_argument('v',
                                     help='Value',
                                     metavar='VAL',
                                     nargs='?')
        sp_key_set_prop.add_argument('-y',
                                     '--save',
                                     help='Save key config after set',
                                     dest='_save',
                                     action='store_true')

        sp_key_regenerate = sp_key.add_parser('regenerate',
                                              help='Regenerate API key')
        sp_key_regenerate.add_argument(
            'i', help='API key ID',
            metavar='ID').completer = ComplKeyDynamic(self)
        sp_key_regenerate.add_argument('-y',
                                       '--save',
                                       help='Save key after regeneration',
                                       dest='_save',
                                       action='store_true')

        sp_key_delete = sp_key.add_parser('destroy', help='Delete API key')
        sp_key_delete.add_argument(
            'i', help='API key ID',
            metavar='ID').completer = ComplKeyDynamic(self)

    def _add_user_functions(self):
        ap_user = self.sp.add_parser('user', help='user management')
        sp_user = ap_user.add_subparsers(dest='_func',
                                         metavar='func',
                                         help='user commands')

        sp_user_list = sp_user.add_parser('list', help='List users')

        sp_user_create = sp_user.add_parser('create', help='Create new user')
        sp_user_create.add_argument('u', help='User login', metavar='LOGIN')
        sp_user_create.add_argument('p',
                                    help='User password',
                                    metavar='PASSWORD')
        sp_user_create.add_argument(
            'a',
            help='API key ID or multiple, comma separated',
            metavar='APIKEY_ID').completer = ComplKey(self)

        sp_user_password = sp_user.add_parser('password',
                                              help='Change password for user')
        sp_user_password.add_argument(
            'u', help='User login', metavar='LOGIN').completer = ComplUser(self)
        sp_user_password.add_argument('p',
                                      help='User password',
                                      metavar='PASSWORD')

        sp_user_key = sp_user.add_parser('key', help='Change API key for user')
        sp_user_key.add_argument('u', help='User login',
                                 metavar='LOGIN').completer = ComplUser(self)
        sp_user_key.add_argument('a',
                                 help='API key ID or multiple, comma separated',
                                 metavar='APIKEY_ID').completer = ComplKey(self)

        sp_user_destroy = sp_user.add_parser('destroy', help='Delete user')
        sp_user_destroy.add_argument(
            'u', help='User login', metavar='LOGIN').completer = ComplUser(self)

        sp_user_list_tokens = sp_user.add_parser(
            'tokens', help='List active session tokens')
        sp_user_drop_tokens = sp_user.add_parser(
            'drop-tokens', help='Drop active session token(s)')
        sp_user_drop_tokens.add_argument('a',
                                         help='Session token',
                                         metavar='TOKEN',
                                         nargs='?').completer = ComplToken(self)
        sp_user_drop_tokens.add_argument(
            '-u', '--user', dest='u', help='User login',
            metavar='LOGIN').completer = ComplUser(self)
        sp_user_drop_tokens.add_argument(
            '-i', '--key-id', dest='i', help='API key ID',
            metavar='APIKEY_ID').completer = ComplKey(self)

    def start_interactive(self, reset_sst=True):
        if reset_sst:
            globals()['shell_switch_to'] = None
        super().start_interactive()

    def prepare_run(self, api_func, params, a):
        if api_func == 'file_put' and a._func == 'upload':
            try:
                with open(a._fname) as fd:
                    params['m'] = fd.read()
            except:
                print('Unable to open %s' % a._fname)
                return 97
        elif api_func == 'install_pkg':
            try:
                from eva.tools import read_uri, dict_from_str
                params['i'] = Path(a._fname).stem
                params['m'] = read_uri(fname=a._fname,
                                       file_read_mode='rb',
                                       b64=True)
                try:
                    params['o'] = dict_from_str(params['o'])
                except:
                    pass
            except:
                print('Unable to open %s' % a._fname)
                return 97
        elif api_func == 'log_get':
            params['l'] = self.get_log_level_code(params['l'])
            if params.get('n') is None:
                params['n'] = 50
        return 0

    def run(self):
        if self.batch_file is not None:
            try:
                if self.batch_file and self.batch_file != 'stdin' and \
                        self.batch_file != '-':
                    with open(self.batch_file) as fd:
                        cmds = [x.strip() for x in fd.readlines()]
                else:
                    cmds = [x.strip() for x in ';'.join(sys.stdin).split(';')]
                for c in cmds:
                    if c:
                        print(self.get_prompt() + c)
                        try:
                            import shlex
                            code = self.execute_function(shlex.split(c))
                            self.suppress_colors = False
                        except:
                            code = 90
                        if code and self.batch_stop_on_err:
                            return code
            except:
                print('Unable to open %s' % self.batch_file)
                return 90
        elif not self.interactive:
            try:
                return self.execute_function()
            except Exception as e:
                self.print_err(e)
        else:
            # interactive mode
            self.start_interactive()
            import shlex
            import distutils.spawn
            while True:
                parsed = None
                while True:
                    try:
                        parsed = shlex.split(input(self.get_prompt()))
                    except EOFError:
                        print()
                        self.finish_interactive()
                        return 0
                    except KeyboardInterrupt:
                        print()
                        pass
                    except:
                        self.print_err('parse error')
                    if parsed:
                        break
                    self.setup_parser()
                cmds = [[]]
                cix = 0
                full_cmds = []
                cmd_title = ''
                for p in parsed:
                    if p == ';':
                        cmds.append([])
                        cix += 1
                    else:
                        if p.endswith(';'):
                            cmds[cix].append(p[:-1])
                            cmds.append([])
                            cix += 1
                        else:
                            cmds[cix].append(p)
                clear_screen = False
                repeat_delay = 0
                for i in range(0, len(cmds)):
                    d = cmds[i]
                    if i and i < len(cmds):
                        print()
                    if not d:
                        continue
                    if d[0] in ['q', 'quit', 'exit', 'bye'] or \
                            (d[0] in ['..', '/'] and parent_shell_name):
                        self.finish_interactive()
                        return 0
                    if parent_shell_name and (d[0] in shells_available or
                                              (d[0].startswith('/') and
                                               d[0][1:] in shells_available)):
                        ss = d[0][1:] if d[0].startswith('/') else d[0]
                        if len(d) > 1:
                            globals()['shell_switch_to_extra_args'] = d[1:]
                        globals()['shell_switch_to'] = ss
                        globals()['shell_back_interactive'] = True
                        self.finish_interactive()
                        return 0
                    if (d[0] == 'k.' or
                            d[0] == 'c.') and self.remote_api_enabled:
                        self.apikey = None
                        print('Key has been reset to default')
                    if (d[0] == 'u.' or
                            d[0] == 'c.') and self.remote_api_enabled:
                        self.apiuri = None
                        print('API uri has been reset to default')
                    if (d[0] == 't.' or
                            d[0] == 'c.') and self.remote_api_enabled:
                        self.timeout = self.default_timeout
                        print('timeout: %.2f' % self.timeout)
                    if (d[0] == 'k' or d[0] == 'c') and self.remote_api_enabled:
                        try:
                            self.apikey = d[1 if d[0] == 'k' else 2]
                        except:
                            pass
                        print('key: %s' % self.apikey if self.
                              apikey is not None else '<default>')
                    if (d[0] == 'u' or d[0] == 'c') and self.remote_api_enabled:
                        try:
                            self.apiuri = d[1]
                        except:
                            pass
                        print('API uri: %s' % self.apiuri if self.
                              apiuri is not None else '<default>')
                    if (d[0] == 't' or d[0] == 'c') and self.remote_api_enabled:
                        try:
                            self.timeout = float(d[1 if d[0] == 't' else 3])
                        except:
                            pass
                        print('timeout: %.2f' % self.timeout)
                    elif d[0] == 'a' and self.remote_api_enabled:
                        print('API uri: %s' % (self.apiuri if self.apiuri
                                               is not None else '<default>'))
                        print('key: %s' % (self.apikey if self.apikey
                                           is not None else '<default>'))
                        print('JSON mode ' + ('on' if self.in_json else 'off'))
                        print('Client debug mode ' +
                              ('on' if self.debug else 'off'))
                        print('timeout: %.2f' % self.timeout)

                    elif d[0] == 'j':
                        self.in_json = not self.in_json
                        print('JSON mode ' + ('on' if self.in_json else 'off'))
                    elif d[0] == 'r':
                        self.always_suppress_colors = \
                                not self.always_suppress_colors
                        print('Raw mode ' +
                              ('on' if self.always_suppress_colors else 'off'))
                    elif d[0] == 'd' and self.remote_api_enabled:
                        self.debug = not self.debug
                        print('Client debug mode ' +
                              ('on' if self.debug else 'off'))
                    elif d[0] == 'top':
                        try:
                            top = distutils.spawn.find_executable('htop')
                            if not top:
                                top = 'top'
                            if os.system(top):
                                raise Exception('exec error')
                        except:
                            self.print_err('Failed to run system "%s" command' %
                                           top)
                    elif d[0] == 'w':
                        try:
                            if os.system('w'):
                                raise Exception('exec error')
                        except:
                            self.print_err('Failed to run system "w" command')
                    elif d[0] == 'date':
                        try:
                            if os.system('date'):
                                raise Exception('exec error')
                        except:
                            self.print_err(
                                'Failed to run system "date" command')
                    elif d[0] == 'cls':
                        try:
                            if os.system('clear'):
                                raise Exception('exec error')
                        except:
                            self.print_err(
                                'Failed to run system "clear" command')
                    elif d[0] == 'sh':
                        print('Executing system shell')
                        shell = os.environ.get('SHELL')
                        if shell is None:
                            shell = distutils.spawn.find_executable('bash')
                            if not shell:
                                shell = 'sh'
                        try:
                            os.system(shell)
                        except:
                            self.print_err('Failed to run system shell "%s"' %
                                           shell)
                    elif d[0] in ['?', 'h', 'help']:
                        self.print_interactive_help()
                        try:
                            self.execute_function(['-h'])
                        except:
                            pass
                        self.setup_parser()
                    elif d[0] not in [
                            'k', 'u', 'c', 't', 'k.', 'u.', 'c.', 't.'
                    ]:
                        try:
                            opts = []
                            if self.remote_api_enabled:
                                if self.apikey is not None:
                                    opts += ['-K', self.apikey]
                                if self.apiuri is not None:
                                    opts += ['-U', self.apiuri]
                                if self.timeout is not None:
                                    opts += ['-T', str(self.timeout)]
                                if self.debug:
                                    opts += ['-D']
                            if self.in_json:
                                opts += ['-J']
                            clear_screen = False
                            if ' |' in d[-1] and not d[-1].startswith(' |'):
                                cmd = d[-1].split(' |')
                                cmd[-1] = '|' + cmd[-1]
                                d.pop(-1)
                                d.extend(cmd)
                            if d[-1][0] == '|':
                                try:
                                    c = d[-1][1:]
                                    if c[0] == 'c':
                                        c = c[1:]
                                        clear_screen = True
                                    repeat_delay = float(c)
                                    if repeat_delay < 0:
                                        raise Exception
                                except:
                                    repeat_delay = None
                                d = d[:-1]
                            else:
                                repeat_delay = None
                        except:
                            pass
                        full_cmds.append(opts + d)
                        if cmd_title:
                            cmd_title += '; '
                        cmd_title += ' '.join(d)
                try:
                    while True:
                        import time
                        start_time = time.time()
                        if clear_screen:
                            os.system('clear')
                            if repeat_delay:
                                print(time.ctime() + '  ' + \
                                    self.colored(
                                        '{}'.format(cmd_title),
                                        color='yellow') + \
                                    '  (interval {} sec)'.format(
                                        repeat_delay))
                        for i in range(len(full_cmds)):
                            code = self.execute_function(full_cmds[i])
                            if i < len(full_cmds) - 1:
                                print()
                        if self.debug:
                            self.print_debug('\nCode: %s' % code)
                        if not repeat_delay:
                            break
                        time_to_sleep = repeat_delay - \
                                time.time() + start_time
                        if time_to_sleep > repeat_delay:
                            time_to_sleep = repeat_delay
                        if time_to_sleep > 0:
                            time.sleep(time_to_sleep)
                        if not clear_screen:
                            print()
                except (KeyboardInterrupt, SystemExit):
                    continue
                except Exception as e:
                    self.print_err(e)
                self.suppress_colors = False
        return 0

    def log_tail(self, params):
        try:
            import websocket, msgpack, threading
            from eva.types import CT_MSGPACK
            import eva.client.apiclient

            ping_msg = eva.client.apiclient.pack_msgpack({'s': 'ping'})

            log_level_id = self.get_log_level_code(params['l'])

            if log_level_id is None:
                log_level_id = 20

            if not isinstance(log_level_id, int):
                self.print_err(f'Invalid log level: {log_level_id}')
                raise RuntimeError

            def format_log_msg(msg, full=False):
                from datetime import datetime
                msg['level'] = msg['lvl'].upper()
                s = datetime.strftime(datetime.fromtimestamp(
                    msg['t']), '%Y-%m-%d %T') + ' ' + msg['h'] + '  ' + msg[
                        'level'] + ' ' + msg['p'] + ' ' + msg['msg']
                s = s if full else s[:120].replace('\n', ' ').replace('\r', '')
                return self.format_log_str(s, msg)

            api = params.get('_api')
            uri = api._uri
            apikey = api._key
            timeout = api._timeout

            n = params.get('n')
            x = params.get('x')

            if x:
                import re
                rgx = re.compile(f'.*{x}.*', re.IGNORECASE)
            else:
                rgx = None

            if uri.startswith('https://'):
                ws_uri = 'wss' + uri[5:]
            elif uri.startswith('http://'):
                ws_uri = 'ws' + uri[4:]
            else:
                ws_uri = 'ws://' + uri

            ws = websocket.create_connection(
                f'{ws_uri}/ws?k={apikey}&c={CT_MSGPACK}', timeout=timeout)
            ws.settimeout(timeout * 2)

            def pinger():
                import time
                while True:
                    try:
                        ws.send(ping_msg, opcode=0x02)
                        time.sleep(timeout if timeout < 5 else 5)
                    except:
                        break

            threading.Thread(target=pinger, daemon=True).start()

            try:
                ws.send(eva.client.apiclient.pack_msgpack({
                    's': 'log',
                    'l': log_level_id
                }),
                        opcode=0x02)
                code, data = api.call('log_get', {
                    'l': log_level_id,
                    'n': n,
                    'x': x
                })
                if code != eva.client.apiclient.result_ok:
                    raise Exception
                for d in data:
                    print(
                        format_log_msg(d,
                                       full=self.cur_api_func_is_full == '_'))
                while True:
                    frame = ws.recv_frame()
                    if frame:
                        data = msgpack.loads(frame.data, raw=False)
                        if data.get('s') == 'log':
                            for d in data['d']:
                                if rgx is None or re.match(rgx, d['msg']):
                                    print(
                                        format_log_msg(
                                            d,
                                            full=self.cur_api_func_is_full ==
                                            '_'))
            finally:
                ws.close()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            return self.local_func_result_failed
        return self.local_func_result_ok

    def call(self, args=None):
        opts = []
        if self.remote_api_enabled:
            if self.apikey is not None:
                opts += ['-K', self.apikey]
            if self.apiuri is not None:
                opts += ['-U', self.apiuri]
            if self.timeout is not None:
                opts += ['-T', str(self.timeout)]
        if isinstance(args, list):
            _args = args
        else:
            import shlex
            _args = shlex.split(args)
        return self.execute_function(args=opts + _args, return_result=True)

    def execute_function(self, args=None, return_result=False):
        self.suppress_colors = False
        if os.environ.get('_ARGCOMPLETE') and not self._argcompleted:
            ostream = completer_stream
            ostream.seek(0)
            ostream.truncate()
        else:
            ostream = None
        if self.argcomplete and not self._argcompleted:
            self._argcompleted = True
            self.argcomplete.autocomplete(self.ap,
                                          exit_method=sys.exit,
                                          output_stream=ostream,
                                          default_completer=self.argcomplete.
                                          completers.SuppressCompleter())
        try:
            p = args if args else (sys.argv[1:] if len(sys.argv) > 1 else [])
            if p and p[0] in shells_available:
                self.subshell_extra_args = p[1:] if len(p) > 1 else []
                a = self.ap.parse_args([p[0]])
            else:
                a, self.subshell_extra_args = self.ap.parse_known_args(args)
        except:
            return 99
        params = vars(a).copy()
        itype = a._type
        for p in params.copy().keys():
            if p[0] == '_':
                del params[p]
        if not itype:
            self.ap.print_help()
            return 99
        func = getattr(a, '_func', None)
        if itype in self.arg_sections and func is None:
            try:
                self.ap.parse_args([itype, '--help'])
            except:
                return 96
        if getattr(a, '_ini_file', None):
            c = self.parse_ini(a._ini_file)
        else:
            c = {}
        if 'raw' in c:
            self.suppress_colors = c.get('raw')
        else:
            self.suppress_colors = a._raw
        if 'debug' in c:
            debug = c.get('debug')
        else:
            debug = False
        if getattr(a, '_debug', False):
            debug = a._debug
        api_func = self.get_api_func(itype, func)
        if not api_func:
            self.ap.print_help()
            return 99
        if 'uri' in c:
            apiuri = c.get('uri')
        else:
            apiuri = None
        if getattr(a, '_api_uri', None):
            apiuri = a._api_uri
        if 'key' in c:
            apikey = c.get('key')
        else:
            apikey = None
        if getattr(a, '_api_key', None):
            apikey = a._api_key
        if self.remote_api_enabled:
            if not apiuri:
                try:
                    api = apiclient.APIClientLocal(self.product)
                except:
                    print('Can not init API')
                    import traceback
                    traceback.print_exc()
                    return 98
            else:
                api = apiclient.APIClient()
                api.set_uri(apiuri)
                api.set_product(self.product)
            if apikey is not None:
                api.set_key(apikey)
            api.ssl_verify(self.ssl_verify)
        else:
            api = None
        self.cur_api_func_is_full = ''
        self.cur_api_func_follow = False
        if getattr(a, '_full', False):
            params['full'] = 1
            self.cur_api_func_is_full = '_'
        if getattr(a, '_has_all', False):
            params['has_all'] = 1
        elif getattr(a, '_full_display', False):
            self.cur_api_func_is_full = '_'
        elif getattr(a, '_full_display', False):
            self.cur_api_func_is_full = '_'
        if getattr(a, '_save', False):
            params['save'] = 1
        if getattr(a, '_force', False):
            params['force'] = 1
        if getattr(a, '_follow', False):
            self.cur_api_func_follow = True
        code = self.prepare_run(api_func, params, a)
        if code:
            return code
        if 'timeout' in c:
            timeout = c.get('timeout')
        else:
            timeout = self.default_timeout
        if hasattr(a, '_timeout') and a._timeout:
            timeout = a._timeout
            wait = params.get('w')
            if a._timeout == float(self.default_timeout) and \
                wait is not None and \
                (itype in self.api_cmds_timeout_correction or \
                func in self.api_cmds_timeout_correction) and \
                wait + 2 > self.default_timeout:
                timeout = wait + 2
        self.last_api_call_params = params
        if debug and self.remote_api_enabled:
            self.print_debug('API: %s' % api._uri)
            self.print_debug('API func: %s' % api_func)
            self.print_debug('timeout: %.2f' % timeout)
            self.print_debug('params %s' % params)
        if api_func == 'log_get' and self.cur_api_func_follow:
            api_func = self.log_tail
        if isinstance(api_func, str) and self.remote_api_enabled:
            code, result = api.call(api_func, params, timeout, _debug=debug)
        else:
            params['_api'] = api
            params['_timeout'] = timeout
            params['_debug'] = debug
            params['_func'] = func
            code, result = api_func(params)
        if api_func == 'dump' and code == apiclient.result_ok:
            if a._sr:
                f = result['file']
                try:
                    if c.get('json') or a._json or api_func in self.always_json:
                        ss = ' > /dev/null 2>&1'
                    else:
                        ss = ''
                    code = os.system(
                        f'cd {dir_eva}/var && {dir_eva}/bin/prepare-sr {f} {ss}'
                    )
                    if code != 0:
                        return self.local_func_result_failed
                    else:
                        result['file'] = f + '.sr'
                finally:
                    os.unlink(f)
        if return_result:
            return code, result
        if not isinstance(api_func, str):
            api_func = api_func.__name__
        if code != apiclient.result_ok:
            if debug and self.remote_api_enabled:
                self.print_debug('API result code: %u' % code)
            if code < 100:
                if 'error' not in result:
                    self.print_err('Error: ' +
                                   default_errors.get(code, 'Operation failed'))
                else:
                    self.print_failed_result(result)
            if code == apiclient.result_func_unknown and not debug:
                self.ap.print_help()
            if code > 100:
                code -= 100
            return code
        else:
            if a._output_file and code == apiclient.result_ok:
                try:
                    self.write_result(result, a._output_file)
                except Exception as e:
                    self.print_err(e)
                    return 9
            elif c.get('json') or a._json or api_func in self.always_json:
                # hack for features, remove when subshells will be merged
                if '--quiet' not in sys.argv:
                    self.print_json(result)
            else:
                return self.process_result(result, code, api_func, itype, a)
        return 0

    def write_result(self, obj, out_file):
        if not isinstance(obj, dict) or \
                ('content_type' not in obj and 'data' not in obj):
            with open(out_file, 'w') as fd:
                fd.write(self.format_json(obj))
        else:
            data = obj['data']
            if obj['content_type'] in ['image/svg+xml', 'text/plain']:
                if isinstance(out_file, str):
                    with open(out_file, 'w') as fd:
                        fd.write(data)
                else:
                    out_file.write(data)
            else:
                import base64
                data = base64.b64decode(data)
                if isinstance(out_file, str):
                    with open(out_file, 'wb') as fd:
                        fd.write(data)
                else:
                    out_file.buffer.write(data)

    def process_result(self, result, code, api_func, itype, a):
        if code != apiclient.result_ok:
            self.print_failed_result(result)
        if isinstance(result, dict) and 'content_type' in result:
            if sys.stdout.isatty():
                self.print_err('File received, output file must be specified')
                return apiclient.result_invalid_params
            else:
                self.write_result(result, sys.stdout)
        else:
            self.fancy_print_result(result,
                                    api_func,
                                    itype,
                                    print_ok=code == apiclient.result_ok,
                                    a=a)
        return code

    def watch_item(self, oid, interval, rows, prop, chart_type='bar'):

        import time
        import datetime

        vals = []
        to_clear = 0

        old_width = 0
        old_height = 0

        limit = rows

        limit_auto_set = rows is None

        def _append(label, value, limit):
            if chart_type == 'bar':
                vals.append((label, value))
            else:
                if isinstance(value, float):
                    vals.append(value)
                else:
                    try:
                        v = float(value)
                    except:
                        v = 0
                    vals.append(v)
            while len(vals) > limit:
                vals.pop(0)

        next_step = time.monotonic() + interval
        try:
            while True:
                if chart_type == 'bar':
                    label = datetime.datetime.now().strftime('%T.%f')[:-5]
                else:
                    label = datetime.datetime.now().isoformat()
                width, height = os.get_terminal_size(0)
                if limit is None:
                    if chart_type == 'bar':
                        limit = height - 2
                    else:
                        limit = width - 12
                if width != old_width or height != old_height:
                    os.system('clear')
                    if chart_type == 'bar':
                        print(self.colored(oid, color='yellow'))
                    old_width, old_height = width, height
                    if limit_auto_set:
                        if chart_type == 'bar':
                            limit = height - 2
                        else:
                            rows = height - 6
                elif chart_type == 'bar':
                    for t in range(to_clear):
                        sys.stdout.write('\033[F\033[K')
                elif chart_type == 'line':
                    os.system('clear')
                code, data = self.call(['state', '-i', oid])
                if code:
                    self.print_err(data.get('error', ''))
                    return self.local_func_result_failed
                else:
                    v = data.get(prop)
                    if isinstance(v, str):
                        try:
                            v = int(v)
                        except:
                            try:
                                v = float(v)
                            except:
                                v = None
                if chart_type == 'bar':
                    _append(label, v, limit)
                    self.plot_bar_chart(vals)
                    to_clear = len(vals)
                else:
                    _append(label, v, width)
                    max_value_width = 0
                    for z in vals:
                        i = len(str(z))
                        if i > max_value_width:
                            max_value_width = i
                    while len(vals) > width - (max_value_width if
                                               max_value_width > 7 else 7) - 5:
                        vals.pop(0)
                    max_value_width += 2
                    print(
                        f'{self.colored(oid, color="yellow")} '
                        f'{self.colored(label, color="cyan")}: ',
                        end='')
                    if v is None:
                        print(self.colored('NaN', color='magenta'))
                    else:
                        print(self.colored(v, color='green', attrs='bold'))
                    self.plot_line_chart(vals, rows, max_value_width)
                t = time.perf_counter()
                sleep_to = next_step - t
                if sleep_to > 0:
                    time.sleep(sleep_to)
                    next_step += interval
                else:
                    next_step = t
        except KeyboardInterrupt:
            return

    def print_tdf(self, result_in, time_field, plot=False, plot_field='value'):
        if not result_in.get(time_field):
            return
        result = result_in.copy()
        if plot:
            # convert list to plot data
            res = []
            for i in range(len(result[time_field])):
                k = result.get(time_field)
                t = None
                v = None
                for k in result.keys():
                    if k == time_field:
                        # from datetime import datetime
                        # t = datetime.strftime(
                        # datetime.fromtimestamp(result[k][i]),
                        # '%Y-%m-%d %T,%f %z')[:-3]
                        t = result[k][i]
                    elif k == plot_field:
                        v = result[k][i]
                        if isinstance(v, str):
                            try:
                                v = int(result[k][i])
                            except:
                                try:
                                    v = float(result[k][i])
                                except:
                                    v = None
                res.append((t, v))
            self.plot_bar_chart(res)
            return
        # convert list to dict
        res = []
        for i in range(len(result[time_field])):
            r = OrderedDict()
            k = result.get(time_field)
            for k in result.keys():
                if k != time_field:
                    try:
                        r[k] = result[k][i]
                    except:
                        r[k] = ''
                else:
                    # from datetime import datetime
                    # t = datetime.strftime(datetime.fromtimestamp(result[k][i]),
                    # '%Y-%m-%d %T,%f')[:-3]
                    t = result[k][i]
            rt = OrderedDict()
            rt['time'] = t
            rt.update(r)
            res.append(rt)
        if res:
            header, rows = rapidtables.format_table(
                res, fmt=rapidtables.FORMAT_GENERATOR_COLS)
            print(self.colored('  '.join(header), color='blue'))
            print(
                self.colored('-' * sum([(len(x) + 2) for x in header]),
                             color='grey'))
            for cols in rows:
                for i, c in enumerate(cols):
                    print(self.colored(c, color='yellow' if not i else 'cyan') +
                          ('  ' if i < len(cols) - 1 else ''),
                          end='')
                print()

    def print_local_only(self):
        self.print_err('This function is available for local controller only')


class ControllerCLI(object):

    class ComplCSMQTT(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            code, data = self.cli.call(['corescript', 'mqtt-topics'])
            if code:
                return True
            return sorted([v['topic'] for v in data])

    def __init__(self):
        self.management_controller_id = None

    def start_controller(self, params):
        if self.apiuri:
            self.print_local_only()
            return self.local_func_result_failed
        self.exec_control_script('start')
        return self.local_func_result_ok

    def stop_controller(self, params):
        if self.apiuri:
            self.print_local_only()
            return self.local_func_result_failed
        self.exec_control_script('stop')
        return self.local_func_result_ok

    def restart_controller(self, params):
        if self.apiuri:
            self.print_local_only()
            return self.local_func_result_failed
        self.exec_control_script('restart')
        return self.local_func_result_ok

    def cleanup_controller(self, params):
        DB_CLEANUPS = {
            'uc': ['delete from state'],
        }
        if self.apiuri:
            self.print_local_only()
            return self.local_func_result_failed
        try:
            db_cleanup_queues = DB_CLEANUPS[self._management_controller_id]
        except KeyError:
            self.print_err('not implemented')
            return self.local_func_result_failed
        import eva.core
        import eva.registry
        from sqlalchemy import text as sql
        cfg = eva.registry.config_get(
            f'config/{self._management_controller_id}/main')
        db_file = cfg.get('server/db-file', default=None)
        try:
            db_uri = cfg.get('server/db')
        except LookupError:
            if db_file:
                db_uri = db_file
        db_uri = eva.core.format_db_uri(db_uri)
        db = eva.core.create_db_engine(db_uri)
        dbconn = db.connect()
        for q in db_cleanup_queues:
            dbconn.execute(sql(q))
        dbconn.close()
        return self.local_func_result_ok

    def launch_controller(self, params):
        if self.apiuri:
            self.print_local_only()
            return self.local_func_result_failed
        snl = '' if params.get('show_notifier_logs') else 'EVA_CORE_SNLSO=1 '
        raw = '' if self.can_colorize() else 'EVA_CORE_RAW_STDOUT=1 '
        os.system('EVA_CONTROLLER={} {}{}{}/_control launch{}'.format(
            self._management_controller_id, snl, raw, self.dir_sbin,
            ' debug' if params.get('_debug') else ''))
        return self.local_func_result_ok

    def status_controller(self, params):
        if self.apiuri:
            self.print_local_only()
            return self.local_func_result_failed
        out = self.exec_control_script('status', collect_output=True)
        result = {}
        try:
            result[self._management_controller_id] = out[0].strip().lower(
            ).find('running') != -1
        except:
            return self.local_func_result_failed
        return 0, result

    def exec_control_script(self, command, collect_output=False):
        cmd = '{}/eva-control {} {}'.format(self.dir_sbin, command,
                                            self._management_controller_id)
        if collect_output:
            with os.popen(cmd) as p:
                result = p.readlines()
            return result
        else:
            os.system(cmd)

    def prepare_controller_status_dict(self, data):
        result = {}
        for k, v in data.copy().items():
            result[k] = 'running' if v else 'stopped'
        return result

    def add_manager_control_functions(self):
        ap_corescript = self.sp.add_parser('corescript',
                                           help='Controller core scripts')
        sp_corescript = ap_corescript.add_subparsers(
            dest='_func', metavar='func', help='Core script commands')

        sp_delete = sp_corescript.add_parser('delete',
                                             help='Delete core script')
        sp_delete.add_argument('i', help='Core script name',
                               metavar='NAME').completer = ComplCoreScript(self)

        sp_edit = sp_corescript.add_parser('edit', help='Edit core script')
        sp_edit.add_argument('i', help='Core script name',
                             metavar='NAME').completer = ComplCoreScript(self)

        sp_list = sp_corescript.add_parser('list', help='List core scripts')

        sp_list_mqtt = sp_corescript.add_parser(
            'mqtt-topics', help='List subscribed mqtt topics')

        sp_sub_mqtt = sp_corescript.add_parser(
            'mqtt-subscribe', help='Subscribe core scripts to MQTT topic')
        sp_sub_mqtt.add_argument(
            't',
            help='MQTT topic (for default notifier) or <notifier_id>:<topic>',
            metavar='TOPIC')
        sp_sub_mqtt.add_argument('-q',
                                 '--qos',
                                 dest='q',
                                 help='MQTT QoS',
                                 metavar='QoS',
                                 type=int)
        sp_sub_mqtt.add_argument('-y',
                                 '--save',
                                 help='Save core script config after set',
                                 dest='_save',
                                 action='store_true')

        sp_unsub_mqtt = sp_corescript.add_parser(
            'mqtt-unsubscribe', help='Unsubscribe core scripts from MQTT topic')
        sp_unsub_mqtt.add_argument(
            't', help='MQTT topic',
            metavar='TOPIC').completer = self.ComplCSMQTT(self)
        sp_unsub_mqtt.add_argument('-y',
                                   '--save',
                                   help='Save core script config after set',
                                   dest='_save',
                                   action='store_true')

        sp_reload = sp_corescript.add_parser('reload',
                                             help='Reload core scripts')

        if 'corescript' not in self.arg_sections:
            self.arg_sections.append('corescript')

        ap_controller = self.sp.add_parser(
            'server', help='Controller server management functions')
        sp_controller = ap_controller.add_subparsers(dest='_func',
                                                     metavar='func',
                                                     help='Management commands')

        ap_start = sp_controller.add_parser('start',
                                            help='Start controller server')
        ap_stop = sp_controller.add_parser('stop',
                                           help='Stop controller server')
        ap_restart = sp_controller.add_parser('restart',
                                              help='Restart controller server')
        if self.remote_api_enabled:
            ap_reload = sp_controller.add_parser(
                'reload', help='Reload controller server')
        ap_status = sp_controller.add_parser(
            'status', help='Status of the controller server')
        ap_launch = sp_controller.add_parser(
            'launch', help='Launch controller server in foreground')
        ap_launch.add_argument('-n',
                               '--show-notifier-logs',
                               help='Show notifier event logs',
                               action='store_true')

        ap_plugins = sp_controller.add_parser('plugins',
                                              help='List loaded core plugins')
        ap_pkg_install = sp_controller.add_parser(
            'pkg-install', help='Install package tarball')
        ap_pkg_install.add_argument('_fname',
                                    help='Package file or URL',
                                    metavar='FILE').completer = self.ComplGlob(
                                        ['*.tgz', '*.tar.gz', '*.tar'])
        ap_pkg_install.add_argument('-o',
                                    '--options',
                                    dest='o',
                                    help='Package setup options',
                                    metavar='OPTS')
        ap_pkg_install.add_argument('-w',
                                    '--wait',
                                    metavar='SEC',
                                    default=1,
                                    dest='w',
                                    help='Wait until the package is installed')
        ap_cleanup = sp_controller.add_parser(
            'cleanup',
            help='Cleanup controller: remove non-critical DB entries etc.')

        self.append_api_functions({'server:plugins': 'list_plugins'})
        self.append_api_functions({'server:pkg-install': 'install_pkg'})

        if 'server' not in self.arg_sections:
            self.arg_sections.append('server')

    def _append_edit_common(self, parser):
        sp_edit_server_config = parser.add_parser(
            'server-config', help='Edit server configuration')
        sp_edit_plugin_config = parser.add_parser(
            'plugin-config', help='Edit plugin configuration')
        sp_edit_plugin_config.add_argument('i',
                                           help='Plugin name',
                                           metavar='NAME')
        sp_edit_corescript = parser.add_parser('corescript',
                                               help='Edit core script')
        sp_edit_corescript.add_argument(
            'i', help='Core script name',
            metavar='NAME').completer = ComplCoreScript(self)

    def edit_server_config(self, params):
        if self.apiuri:
            self.print_local_only()
            return self.local_func_result_failed
        code = os.system(f'AUTO_PREFIX=1 {self.dir_sbin}/eva-registry-cli '
                         f'edit config/{self._management_controller_id}/main')
        return self.local_func_result_empty if \
                not code else self.local_func_result_failed

    def edit_plugin_config(self, params):
        i = params['i']
        if self.apiuri:
            self.print_local_only()
            return self.local_func_result_failed
        code = os.system(
            f'AUTO_PREFIX=1 {self.dir_sbin}/eva-registry-cli '
            f'edit config/{self._management_controller_id}/plugins/{i}'
            f' --default {dir_eva}/lib/eva/'
            'registry/setup-defaults/config/plugin.yml')
        return self.local_func_result_empty if \
                not code else self.local_func_result_failed

    def edit_corescript(self, params):
        if self.apiuri:
            self.print_local_only()
            return self.local_func_result_failed
        editor = os.environ.get('EDITOR', 'vi')
        fname = params['i']
        if fname.endswith('.py'):
            fname = fname[:-3]
        fname = '{}/xc/{}/cs/{}.py'.format(dir_eva, self.product, fname)
        need_reload = not os.path.exists(fname)
        if os.system(f'{editor} {fname}'):
            return self.local_func_result_failed
        if not os.path.isfile(fname):
            return self.local_func_result_empty
        try:
            with open(fname) as fd:
                code = fd.read()
            compile(code, fname, 'exec')
        except Exception as e:
            self.print_err('Core script code error: ' + str(e))
            return self.local_func_result_failed
        if need_reload:
            return self.call(args=['corescript', 'reload'])
        else:
            return self.local_func_result_ok

    def delete_corescript(self, params):
        if self.apiuri:
            self.print_local_only()
            return self.local_func_result_failed
        fname = params['i']
        if fname.endswith('.py'):
            fname = fname[:-3]
        fname = '{}/xc/{}/cs/{}.py'.format(
            dir_eva, self.product,
            fname.replace('/', '').replace('..', ''))
        try:
            os.unlink(fname)
        except:
            print(f'Unable to delete core script file {fname}')
            return self.local_func_result_failed
        return self.call(args=['corescript', 'reload'])

    def list_corescripts(self, params):
        if self.apiuri:
            self.print_local_only()
            return self.local_func_result_failed
        import glob
        files = glob.glob('{}/xc/{}/cs/*.py'.format(
            dir_eva,
            self.product,
        ))
        result = []
        for f in files:
            result.append({
                'name': os.path.basename(f)[:-3],
                'modified': os.path.getmtime(f)
            })
        return 0, sorted(result, key=lambda k: k['name'])

    def enable_controller_management_functions(self, controller_id):
        if self.apiuri:
            return
        self.dir_sbin = dir_eva + '/sbin'
        self.dir_etc = dir_eva + '/etc'
        self.add_manager_control_functions()
        if controller_id:
            self._management_controller_id = controller_id
        self.append_api_functions({
            'server:start': self.start_controller,
            'server:stop': self.stop_controller,
            'server:cleanup': self.cleanup_controller,
            'server:restart': self.restart_controller,
            'server:status': self.status_controller,
            'server:reload': 'shutdown_core',
            'server:launch': self.launch_controller,
            'edit:server-config': self.edit_server_config,
            'edit:plugin-config': self.edit_plugin_config,
            'edit:corescript': self.edit_corescript,
            'corescript:list': self.list_corescripts,
            'corescript:edit': self.edit_corescript,
            'corescript:delete': self.delete_corescript,
            'corescript:reload': 'reload_corescripts',
            'corescript:mqtt-topics': 'list_corescript_mqtt_topics',
            'corescript:mqtt-subscribe': 'subscribe_corescripts_mqtt',
            'corescript:mqtt-unsubscribe': 'unsubscribe_corescripts_mqtt'
        })

    @staticmethod
    def bool2yn(b):
        return 'Y' if b else 'N'


class LECLI:

    class ComplPVT(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            import glob
            result = []
            files = glob.glob(
                '{}/pvt/**/*'.format(dir_eva), recursive=True) + glob.glob(
                    '{}/pvt/.**/*'.format(dir_eva), recursive=True)
            for f in files:
                if os.path.isfile(f):
                    result.append(f.split('/', dir_eva.count('/') + 2)[-1])
            return result

    class ComplUI(ComplGeneric):

        def __call__(self, prefix, **kwargs):
            import glob
            result = []
            exts = [
                'json', 'yml', 'yaml', 'js', 'html', 'js', 'j2', 'css', 'txt',
                'htm'
            ]
            hidden_dirs = ['apps', 'lib']
            files = glob.glob('{}/ui/**/*'.format(dir_eva),
                              recursive=True) + glob.glob(
                                  '{}/ui/.**/*'.format(dir_eva), recursive=True)
            for f in files:
                if os.path.isfile(f):
                    fname = f.rsplit('/', 1)[-1]
                    d = f.split('/', 5)[4]
                    if fname.find('.') != -1 and fname.rsplit(
                            '.', 1)[-1] in exts and not (
                                d in hidden_dirs and
                                os.path.isdir('{}/ui/{}'.format(dir_eva, d))):
                        result.append(f.split('/', dir_eva.count('/') + 2)[-1])
            return result

    def _append_edit_pvt_and_ui(self, parser):
        ap_edit_pvt = parser.add_parser('pvt', help='Edit PVT files')
        ap_edit_pvt.add_argument('f', help='File to edit',
                                 metavar='FILE').completer = self.ComplPVT(self)

        ap_edit_pvt = parser.add_parser('ui', help='Edit UI files')
        ap_edit_pvt.add_argument('f', help='File to edit',
                                 metavar='FILE').completer = self.ComplUI(self)

    def edit(self, params):
        if self.apiuri:
            self.print_local_only()
            return self.local_func_result_failed
        editor = os.environ.get('EDITOR', 'vi')
        code = os.system('{} {}/{}/{}'.format(editor, dir_eva, params['_func'],
                                              params['f']))
        return self.local_func_result_ok if \
                not code else self.local_func_result_failed

    def enable_le_functions(self):
        if not self.apiuri:
            self.append_api_functions({
                'edit:pvt': self.edit,
                'edit:ui': self.edit,
            })
