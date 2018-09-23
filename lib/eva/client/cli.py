__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "3.1.1"

import argparse
# to be compatible with argcomplete
import getopt
import importlib
import configparser
import re
import sys
import os
import shlex
import readline
import json
import jsonpickle
import copy
from termcolor import colored
from datetime import datetime
from eva.client import apiclient
from pygments import highlight, lexers, formatters

say_bye = True
parent_shell_name = None


class GenericCLI(object):

    def __init__(self, product, name, prog=None, remote_api=True):
        self.debug = False
        self.name = name
        self.product = product
        self.remote_api = remote_api
        self.pd = None
        self.argcomplete = None
        self.prompt = None
        self.apikey = None
        self.apiuri = None
        self.api_func = None
        self.in_json = False
        self.suppress_colors = False
        self.always_suppress_colors = False
        self.default_timeout = 10
        self.timeout = self.default_timeout
        self.ssl_verify = False
        self.always_json = []
        self.local_func_result_ok = (apiclient.result_ok, {'result': 'OK'})
        self.local_func_result_failed = (apiclient.result_func_failed, {
            'result': 'ERROR'
        })
        self.local_func_result_empty = (apiclient.result_ok, '')
        if remote_api:
            self.always_print = ['cmd']
            self.common_api_functions = {
                'cvar:all': 'get_cvar',
                'cvar:get': 'get_cvar',
                'cvar:set': 'set_cvar',
                'cvar:delete': 'set_cvar',
                'debug': 'set_debug',
                'file:create': 'file_put',
                'file:upload': 'file_put',
                'file:mod': 'file_set_exec',
                'key:list': 'list_keys',
                'user:list': 'list_users',
                'user:create': 'create_user',
                'user:password': 'set_user_password',
                'user:key': 'set_user_key',
                'user:destroy': 'destroy_user'
            }
            self.common_pd_cols = {
                'list_keys': ['key_id', 'master', 'sysfunc', 'allow'],
                'log_get': ['time', 'host', 'p', 'level', 'message'],
                'log_get_':
                ['time', 'host', 'p', 'level', 'mod', 'thread', 'message']
            }
            self.common_pd_idx = {
                'list_keys': 'key_id',
                'list_users': 'user',
                'state': 'oid',
                'list': 'oid',
                'log_get': 'time',
                'result': 'time',
                'list_phi_mods': 'mod',
                'list_lpi_mods': 'mod'
            }
            self.arg_sections = ['log', 'cvar', 'file', 'key', 'user']
            self.common_fancy_tabsp = {'test': 14}
        else:
            self.always_print = []
            self.common_api_functions = {}
            self.common_pd_cols = {}
            self.common_pd_idx = {}
            self.arg_sections = []
            self.common_fancy_tabsp = {}
        self.log_levels = {
            10: 'DEBUG',
            20: 'INFO',
            30: 'WARNING',
            40: 'ERROR',
            50: 'CRITICAL'
        }
        self.pd_cols = self.common_pd_cols
        self.api_functions = self.common_api_functions
        self.fancy_tabsp = self.common_fancy_tabsp
        self.pd_idx = self.common_pd_idx
        self.batch_file = None
        self.batch_stop_on_err = True
        self.prog_name = prog
        self.interactive = False
        self.parse_primary_args()
        self.setup_parser()

    def setup_parser(self):
        if not self.interactive and not self.batch_file:
            self.ap = argparse.ArgumentParser(
                description=self.name, prog=self.prog_name)
        else:
            self.ap = argparse.ArgumentParser(usage=argparse.SUPPRESS, prog='')
        self.add_primary_options()
        self.add_main_subparser()
        self.add_functions()
        self.load_argcomplete()

    def print_json(self, obj):
        j = self.format_json(obj)
        if not self.always_suppress_colors and not self.suppress_colors and \
                sys.stdout.isatty():
            j = highlight(j, lexers.JsonLexer(), formatters.TerminalFormatter())
        print(j)

    def format_json(self, obj, minimal=False, unpicklable=False):
        return json.dumps(json.loads(jsonpickle.encode(obj,
                unpicklable = unpicklable)), indent=4, sort_keys=True) \
                    if not minimal else \
                    jsonpickle.encode(obj, unpicklable = False)

    def get_prompt(self):
        if self.prompt: return self.prompt
        prompt = '> '
        if self.apiuri:
            h = ' ' + self.apiuri.replace('https://', '').replace('http://', '')
        else:
            h = ''
        ppeva = '' if not parent_shell_name else \
                self.colored(parent_shell_name, 'green', attrs=['bold']) + '/'
        if self.product:
            prompt = '[%s%s] %s' % (
                ppeva + self.colored(self.product, 'green', attrs=['bold']),
                self.colored(h, 'blue', attrs=['bold']), prompt)
        return prompt

    def colored(self, text, color=None, on_color=None, attrs=None):
        if self.suppress_colors or self.always_suppress_colors or \
                not sys.stdout.isatty():
            return str(text)
        return colored(text, color=color, on_color=on_color, attrs=attrs)

    def print_interactive_help(self):
        print('q: quit')
        print('j: toggle json mode')
        print('r: toggle raw mode (no colors)')
        print()
        if self.remote_api:
            print('a: show API params')
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
        print('or command to execute')
        print()

    def parse_primary_args(self):
        try:
            if self.remote_api:
                o, a = getopt.getopt(sys.argv[1:], 'F:U:K:T:JIR', [
                    'client-ini-file=', 'exec-batch=', 'pass-batch-err',
                    'interactive'
                ])
            else:
                o, a = getopt.getopt(
                    sys.argv[1:], 'JIR',
                    ['exec-batch=', 'pass-batch-err', 'interactive'])
            for i, v in o:
                if i == '--exec-batch':
                    self.batch_file = v
                elif i == '--pass-batch-err':
                    self.batch_stop_on_err = False
                elif i == '--interactive' or i == '-I':
                    self.interactive = True
                elif i == '-U':
                    self.apiuri = v
                elif i == '-K':
                    self.apikey = v
                elif i == '-J':
                    self.in_json = True
                elif i == '-R':
                    self.always_suppress_colors = True
                elif i == '-T':
                    try:
                        self.timeout = float(v)
                    except:
                        pass
                elif i == '-F' or i == '--client-ini-file':
                    c = self.parse_ini(v)
                    if 'uri' in c: self.apiuri = c.get('uri')
                    if 'key' in c: self.apikey = c.get('key')
                    if 'timeout' in c: self.timeout = c.get('timeout')
                    if 'debug' in c: self.debug = c.get('debug')
                    if 'json' in c: self.in_json = c.get('json')
                    if 'raw' in c: self.always_suppress_colors = c.get('raw')
        except:
            pass

    def parse_ini(self, fname):
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

    def load_argcomplete(self):
        try:
            self.argcomplete = importlib.import_module('argcomplete')
        except:
            pass

    def reset_argcomplete(self):
        if self.argcomplete:
            completer = self.argcomplete.CompletionFinder(self.ap)
            readline.set_completer_delims("")
            readline.set_completer(completer.rl_complete)
            readline.parse_and_bind("tab: complete")

    def print_err(self, s):
        print(self.colored(s, color='red', attrs=[]))

    def print_debug(self, s):
        print(self.colored(s, color='grey', attrs=['bold']))

    def get_log_level_name(self, level):
        l = self.log_levels.get(level)
        return l if l else level

    def get_log_level_code(self, name):
        if not isinstance(name, str): return name
        n = str.upper(name)
        for l, v in self.log_levels.items():
            if n[0] == v[0]: return l
        return name

    def format_log_str(self, s):
        if s.find(' DEBUG ') != -1:
            return self.colored(s, color='grey', attrs=['bold'])
        if s.find(' WARNING ') != -1:
            return self.colored(s, color='yellow', attrs=[])
        if s.find(' ERROR ') != -1:
            return self.colored(s, color='red', attrs=[])
        if s.find(' CRITICAL ') != -1:
            return self.colored(s, color='red', attrs=['bold'])
        return s

    def add_primary_options(self):
        if self.remote_api:
            self.ap.add_argument(
                '-K',
                '--api-key',
                help='API key, if no key specified, local master key is used',
                dest='_api_key',
                metavar='KEY')
            self.ap.add_argument(
                '-U',
                '--api-url',
                help='API URL',
                dest='_api_uri',
                metavar='URL')
            self.ap.add_argument(
                '-T',
                '--api-timeout',
                help='API request timeout (in seconds)',
                type=float,
                dest='_timeout',
                metavar='TIMEOUT')
            self.ap.add_argument(
                '-D',
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
        self.ap.add_argument(
            '-J',
            '--json',
            help='Print result as JSON',
            action='store_true',
            dest='_json',
            default=False)
        self.ap.add_argument(
            '-R',
            '--raw-output',
            help='Print raw result (no colors)',
            action='store_true',
            dest='_raw',
            default=False)
        if not self.interactive:
            self.ap.add_argument(
                '-I',
                '--interactive',
                help='Enter interactive (command prompt) mode',
                action='store_true',
                dest='__interactive',
                default=False)

    def add_main_subparser(self):
        self.sp = self.ap.add_subparsers(
            dest='_type', metavar='command', help='command or type')

    def set_api_functions(self, fn_table={}):
        self.api_functions = self.common_api_functions.copy()
        self.api_functions.update(fn_table)

    def set_pd_cols(self, pd_cols={}):
        self.pd_cols = self.common_pd_cols.copy()
        self.pd_cols.update(pd_cols)

    def set_pd_idx(self, pd_idx={}):
        self.pd_idx = self.common_pd_idx.copy()
        self.pd_idx.update(pd_idx)

    def set_fancy_tabsp(self, fancy_tabsp={}):
        self.fancy_tabsp = self.common_fancy_tabsp.copy()
        self.fancy_tabsp.update(fancy_tabsp)

    def get_api_func(self, itype, func):
        if func is None:
            f = self.api_functions.get(itype)
            return f if f else itype
        else:
            f = self.api_functions.get(itype + ':' + func)
            return f if f else itype + '_' + func

    def prepare_result_data(self, data, api_func, api_func_full, itype):
        if api_func == 'log_get':
            result = []
            for d in data:
                d['host'] = d.pop('h')
                d['thread'] = d.pop('th')
                d['message'] = d.pop('msg')
                d['level'] = self.get_log_level_name(d.pop('l'))
                d['time'] = datetime.fromtimestamp(d.pop('t')).isoformat()
                result.append(d)
            return result
        else:
            return data

    def prepare_result_dict(self, data, api_func, api_func_full, itype):
        return data

    def fancy_print_result(self, result, api_func, api_func_full, itype, tab=0):
        if result and isinstance(result, dict):
            _result=self.prepare_result_dict(result, api_func, api_func_full,
                                              itype)
            rprinted = False
            h = None
            out = None
            err = None
            tabsp = self.fancy_tabsp.get(api_func)
            if not tabsp: tabsp = 10
            for v in sorted(_result.keys()):
                if v == 'help':
                    if not tab:
                        h = _result[v]
                    else:
                        pass
                elif v == 'out' and not tab:
                    out = _result[v]
                elif v == 'err' and not tab:
                    err = _result[v]
                elif v != '_result':
                    if isinstance(_result[v], dict):
                        if tab:
                            print(
                                ' ' * (tab * tabsp),
                                end=self.colored('>' * tab) + ' ')
                        print(((self.colored(
                            '{:>%u} ', color='blue', attrs=['bold']) +
                                self.colored(':') + self.colored(
                                    '  {}', color='yellow')) % max(
                                        map(len, _result))).format(v, ''))
                        self.fancy_print_result(_result[v], api_func,
                                                api_func_full, itype, tab + 1)
                    else:
                        if tab:
                            print(
                                ' ' * (tab * tabsp),
                                end=self.colored('>' * tab) + ' ')
                        if isinstance(_result[v], list):
                            _r = []
                            for vv in _result[v]:
                                _r.append(str(vv))
                            _v = ', '.join(_r)
                        else:
                            _v = _result[v]
                        print(((self.colored(
                            '{:>%u} ', color='blue', attrs=['bold']) +
                                self.colored(':') + self.colored(
                                    ' {}', color='yellow')) % max(
                                        map(len, _result))).format(v, _v))
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
            if not rprinted and not tab:
                print('OK')
        elif result and isinstance(result, list):
            self.import_pandas()
            df = self.pd.DataFrame(
                data=self.prepare_result_data(result, api_func, api_func_full,
                                              itype))
            if api_func + api_func_full in self.pd_cols:
                cols = self.pd_cols[api_func + api_func_full]
            else:
                cols = list(df)
            df = df.ix[:, cols]
            try:
                idxcol = self.pd_idx.get(api_func)
                if idxcol is None: idxcol = 'id'
                if idxcol in list(df):
                    df.set_index(idxcol, inplace=True)
                else:
                    idxcol = list(df)[0]
                    df.set_index(list(df)[0], inplace=True)
                if idxcol == 'time':
                    df.index = self.pd.to_datetime(df.index, utc=False)
                out = df.fillna(' ').to_string().split('\n')
                print(
                    self.colored(
                        idxcol + out[0][len(idxcol):], color='blue', attrs=[]))
                print(self.colored('-' * len(out[0]), color='grey'))
                for o in out[2:]:
                    s = re.sub('^NaN', '   ', o)
                    if api_func == 'log_get': s = self.format_log_str(s)
                    print(s)
            except:
                raise
        elif result:
            print(result)

    def import_pandas(self):
        if not self.pd:
            self.pd = importlib.import_module('pandas')
            self.pd.set_option('display.expand_frame_repr', False)
            self.pd.options.display.max_colwidth = 90

    def add_functions(self):
        if self.remote_api:
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
        ap_cmd.add_argument(
            '-a', '--args', help='Command arguments', metavar='ARGS', dest='a')
        ap_cmd.add_argument(
            '-w',
            '--wait',
            help='Wait for command finish',
            metavar='SEC',
            type=float,
            dest='w')
        ap_cmd.add_argument(
            '-t',
            '--timeout',
            help='Command timeout',
            metavar='SEC',
            type=float,
            dest='t')

    def _add_lock_functions(self):
        ap_lock = self.sp.add_parser('lock', help='acquire lock')
        ap_lock.add_argument('l', help='Lock ID', metavar='ID')
        ap_lock.add_argument(
            '-t',
            '--timeout',
            help='Max acquire wait time',
            metavar='SEC',
            type=float,
            dest='t')
        ap_lock.add_argument(
            '-e',
            '--expires',
            help='Lock expire time',
            metavar='SEC',
            type=float,
            dest='e')
        ap_unlock = self.sp.add_parser('unlock', help='release lock')
        ap_unlock.add_argument('l', help='Lock ID', metavar='ID')

    def _add_log_functions(self):
        ap_log = self.sp.add_parser('log', help='Log functions')
        sp_log = ap_log.add_subparsers(
            dest='_func', metavar='func', help='Log commands')
        sp_log_rotate = sp_log.add_parser('rotate', help='Rotate logs')
        sp_log_debug = sp_log.add_parser('debug', help='Send debug message')
        sp_log_debug.add_argument('m', help='Message', metavar='MSG')
        sp_log_info = sp_log.add_parser('info', help='Send info message')
        sp_log_info.add_argument('m', help='Message', metavar='MSG')
        sp_log_warning = sp_log.add_parser(
            'warning', help='Send warning message')
        sp_log_warning.add_argument('m', help='Message', metavar='MSG')
        sp_log_error = sp_log.add_parser('error', help='Send error message')
        sp_log_error.add_argument('m', help='Message', metavar='MSG')
        sp_log_critical = sp_log.add_parser(
            'critical', help='Send critical message')
        sp_log_critical.add_argument('m', help='Message', metavar='MSG')
        sp_log_get = sp_log.add_parser('get', help='Get system log messages')
        sp_log_get.add_argument(
            'l', help='Log level', metavar='LEVEL', nargs='?')
        sp_log_get.add_argument(
            '-t',
            '--seconds',
            help='Get records for the last SEC seconds',
            metavar='SEC',
            dest='t')
        sp_log_get.add_argument(
            '-n', '--limit', help='Limit records to', metavar='LIMIT', dest='n')
        sp_log_get.add_argument(
            '-y',
            '--full',
            help='Display full log records',
            dest='_full_display',
            action='store_true')

    def _add_cvar_functions(self):
        ap_cvar = self.sp.add_parser('cvar', help='CVAR functions')
        sp_cvar = ap_cvar.add_subparsers(
            dest='_func', metavar='func', help='CVAR commands')
        sp_cvar_all = sp_cvar.add_parser('all', help='Get all CVARS')
        sp_cvar_get = sp_cvar.add_parser('get', help='Get CVAR value')
        sp_cvar_get.add_argument('i', help='CVAR ID', metavar='ID')
        sp_cvar_set = sp_cvar.add_parser('set', help='Set CVAR value')
        sp_cvar_set.add_argument('i', help='CVAR ID', metavar='ID')
        sp_cvar_set.add_argument('v', help='Value', metavar='VALUE')
        sp_cvar_delete = sp_cvar.add_parser('delete', help='Delete CVAR')
        sp_cvar_delete.add_argument('i', help='CVAR ID', metavar='ID')

    def _add_debug_functions(self):
        ap_debug = self.sp.add_parser('debug', help='Debug control')
        ap_debug.add_argument(
            'debug',
            help='Debug mode (on/off)',
            metavar='MODE',
            choices=['on', 'off'])

    def _add_file_functions(self):
        ap_file = self.sp.add_parser(
            'file', help='File management in runtime folder')
        sp_file = ap_file.add_subparsers(
            dest='_func', metavar='func', help='File commands')

        sp_file_get = sp_file.add_parser('get', help='Download file')
        sp_file_get.add_argument(
            'i',
            help='File name (relative to runtime, without / in the beginning)',
            metavar='REMOTE_FILE')
        sp_file_get.add_argument(
            '_fname', help='Local file name', metavar='LOCAL_FILE')

        sp_file_upload = sp_file.add_parser('upload', help='Upload file')
        sp_file_upload.add_argument(
            '_fname', help='Local file name', metavar='LOCAL_FILE')
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
        ap_key = self.sp.add_parser('key', help='API key management')
        sp_key = ap_key.add_subparsers(
            dest='_func', metavar='func', help='API key commands')

        sp_key_list = sp_key.add_parser('list', help='List API keys')

    def _add_user_functions(self):
        ap_user = self.sp.add_parser('user', help='user management')
        sp_user = ap_user.add_subparsers(
            dest='_func', metavar='func', help='user commands')

        sp_user_list = sp_user.add_parser('list', help='List users')

        sp_user_create = sp_user.add_parser('create', help='Create new user')
        sp_user_create.add_argument('u', help='User login', metavar='LOGIN')
        sp_user_create.add_argument(
            'p', help='User password', metavar='PASSWORD')
        sp_user_create.add_argument('a', help='API key ID', metavar='APIKEY_ID')

        sp_user_password = sp_user.add_parser(
            'password', help='Change password for user')
        sp_user_password.add_argument('u', help='User login', metavar='LOGIN')
        sp_user_password.add_argument(
            'p', help='User password', metavar='PASSWORD')

        sp_user_key = sp_user.add_parser('key', help='Change API key for user')
        sp_user_key.add_argument('u', help='User login', metavar='LOGIN')
        sp_user_key.add_argument('a', help='API key ID', metavar='APIKEY_ID')

        sp_user_destroy = sp_user.add_parser('destroy', help='Delete user')
        sp_user_destroy.add_argument('u', help='User login', metavar='LOGIN')

    def prepare_run(self, api_func, params, a):
        if api_func == 'file_put' and a._func == 'upload':
            try:
                params['m'] = ''.join(open(a._fname).readlines())
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
                if self.batch_file and self.batch_file != 'stdin':
                    cmds = [
                        x.strip() for x in open(self.batch_file).readlines()
                    ]
                else:
                    cmds = [x.strip() for x in ';'.join(sys.stdin).split(';')]
                for c in cmds:
                    print(self.get_prompt() + c)
                    try:
                        code = self.do_run(shlex.split(c))
                        self.suppress_colors = False
                    except:
                        code = 90
                    if code and self.batch_stop_on_err: return code
            except:
                print('Unable to open %s' % self.batch_file)
                return 90
        elif not self.interactive:
            return self.do_run()
        else:
            # interactive mode
            self.reset_argcomplete()
            while True:
                d = None
                while not d:
                    try:
                        d = shlex.split(input(self.get_prompt()))
                    except EOFError:
                        print()
                        if say_bye: print('Bye')
                        return 0
                    except:
                        self.print_err('parse error')
                if d[0] in ['q', 'quit', 'exit', 'bye']:
                    if say_bye: print('Bye')
                    return 0
                elif d[0] == 'a' and self.remote_api:
                    print('API uri: %s' % (self.apiuri
                                           if self.apiuri is not None else
                                           '<default>'))
                    print('key: %s' % (self.apikey if self.apikey is not None
                                       else '<default>'))
                    print('JSON mode ' + ('on' if self.in_json else 'off'))
                    print('Client debug mode ' +
                          ('on' if self.debug else 'off'))
                    print('timeout: %.2f' % self.timeout)
                elif d[0] == 'k.' and self.remote_api:
                    self.apikey = None
                    print('Key has been reset to default')
                elif d[0] == 'u.' and self.remote_api:
                    self.apiuri = None
                    print('API uri has been reset to default')
                elif d[0] == 'j':
                    self.in_json = not self.in_json
                    print('JSON mode ' + ('on' if self.in_json else 'off'))
                elif d[0] == 'r':
                    self.always_suppress_colors = \
                            not self.always_suppress_colors
                    print('Raw mode ' +
                          ('on' if self.always_suppress_colors else 'off'))
                elif d[0] == 'd' and self.remote_api:
                    self.debug = not self.debug
                    print('Client debug mode ' +
                          ('on' if self.debug else 'off'))
                elif d[0] == 't.' and self.remote_api:
                    self.timeout = self.default_timeout
                    print('timeout: %f' % self.timeout)
                elif d[0] == 'k' and self.remote_api:
                    if len(d) > 1:
                        self.apikey = d[1]
                    print('key: %s' % self.apikey
                          if self.apikey is not None else '<default>')
                elif d[0] == 'u' and self.remote_api:
                    if len(d) > 1:
                        self.apiuri = d[1]
                    print('API uri: %s' % self.apiuri
                          if self.apiuri is not None else '<default>')
                elif d[0] == 't' and self.remote_api:
                    if len(d) > 1:
                        try:
                            self.timeout = float(d[1])
                        except:
                            self.print_err('FAILED')
                    print('timeout: %f' % self.timeout)
                elif d[0] == 'top':
                    try:
                        top = '/usr/bin/htop' if os.path.isfile(
                            '/usr/bin/htop') else 'top'
                        if os.system(top): raise Exception('exec error')
                    except:
                        self.print_err(
                            'Failed to run system "%s" command' % top)
                elif d[0] == 'w':
                    try:
                        if os.system('w'): raise Exception('exec error')
                    except:
                        self.print_err('Failed to run system "w" command')
                elif d[0] == 'date':
                    try:
                        if os.system('date'): raise Exception('exec error')
                    except:
                        self.print_err('Failed to run system "date command')
                elif d[0] == 'sh':
                    print('Executing system shell')
                    shell = os.environ.get('SHELL')
                    if shell is None:
                        if os.path.isfile('/bin/bash'): shell = '/bin/bash'
                        else: shell = 'sh'
                    try:
                        os.system(shell)
                    except:
                        self.print_err(
                            'Failed to run system shell "%s"' % shell)
                elif d[0] in ['?', 'h', 'help']:
                    self.print_interactive_help()
                    try:
                        self.do_run(['-h'])
                    except:
                        pass
                else:
                    try:
                        opts = []
                        if self.remote_api:
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
                        code = self.do_run(opts + d)
                        self.suppress_colors = False
                        if self.debug: self.print_debug('\nCode: %s' % code)
                    except:
                        pass
        return 0

    def do_run(self, args=None):
        self.suppress_colors = False
        if self.argcomplete:
            self.argcomplete.autocomplete(self.ap)
        try:
            a = self.ap.parse_args(args)
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
        if hasattr(a, '_func'):
            func = a._func
        else:
            func = None
        if itype in self.arg_sections and func is None:
            try:
                self.ap.parse_args([itype, '--help'])
            except:
                return 96
        if hasattr(a, '_ini_file') and a._ini_file:
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
        if hasattr(a, '_debug') and a._debug: debug = a._debug
        api_func = self.get_api_func(itype, func)
        if not api_func:
            self.ap.print_help()
            return 99
        if 'uri' in c:
            apiuri = c.get('uri')
        else:
            apiuri = None
        if hasattr(a, '_api_uri') and a._api_uri: apiuri = a._api_uri
        if 'key' in c:
            apikey = c.get('key')
        else:
            apikey = None
        if hasattr(a, '_api_key') and a._api_key:
            apikey = a._api_key
        if self.remote_api:
            if not apiuri:
                try:
                    api = apiclient.APIClientLocal(self.product)
                except:
                    print('Can not init API, %s.ini or %s_apikeys.ini missing?'
                          % (self.product, self.product))
                    return 98
            else:
                api = apiclient.APIClient()
                api.set_uri(apiuri)
                api.set_product(self.product)
            if apikey is not None:
                api.set_key(apikey)
            api.ssl_verify(self.ssl_verify)
        if hasattr(a, '_full') and a._full:
            params['full'] = 1
            api_func_full = '_'
        elif hasattr(a, '_full_display') and a._full_display:
            api_func_full = '_'
        else:
            api_func_full = ''
        if hasattr(a, '_virtual') and a._virtual:
            params['virtual'] = 1
        if hasattr(a, '_save') and a._save:
            params['save'] = 1
        if hasattr(a, '_force') and a._force:
            params['force'] = 1
        code = self.prepare_run(api_func, params, a)
        if code: return code
        if 'timeout' in c:
            timeout = c.get('timeout')
        else:
            timeout = self.default_timeout
        if hasattr(a, '_timeout') and a._timeout: timeout = a._timeout
        if debug and self.remote_api:
            self.print_debug('API: %s' % api._uri)
            self.print_debug('API func: %s' % api_func)
            self.print_debug('timeout: %s' % timeout)
            self.print_debug('params %s' % params)
        if isinstance(api_func, str) and self.remote_api:
            code, result = api.call(api_func, params, timeout, _debug=debug)
        else:
            code, result = api_func(params)
        if not isinstance(api_func, str): api_func = api_func.__name__
        if code != apiclient.result_ok and \
            code != apiclient.result_func_failed:
            if code == apiclient.result_not_found:
                self.print_err('Error: Object not found')
            elif code == apiclient.result_forbidden:
                self.print_err('Error: Forbidden')
            elif code == apiclient.result_api_error:
                self.print_err('Error: API error')
            elif code == apiclient.result_unknown_error:
                self.print_err('Error: Unknown error')
            elif code == apiclient.result_not_ready:
                self.print_err('Error: API not ready')
            elif code == apiclient.result_func_unknown:
                self.ap.print_help()
            elif code == apiclient.result_server_error:
                self.print_err('Error: Server error')
            elif code == apiclient.result_server_timeout:
                self.print_err('Error: Server timeout')
            elif code == apiclient.result_bad_data:
                self.print_err('Error: Bad data')
            elif code == apiclient.result_invalid_params:
                self.print_err('Error: invalid params')
            if debug and self.remote_api:
                self.print_debug('API result code: %u' % code)
            return code
        else:
            if c.get('json') or a._json or api_func in self.always_json:
                self.print_json(result)
                if 'result' in result and result['result'] == 'ERROR':
                    return apiclient.result_func_failed
            else:
                return self.process_result(result, code, api_func,
                                           api_func_full, itype, a)
        return 0

    def process_result(self, result, code, api_func, api_func_full, itype, a):
        if api_func == 'file_get':
            try:
                open(a._fname, 'w').write(result['data'])
                print('OK')
            except:
                self.print_err('FAILED')
                return 95
        elif code == apiclient.result_func_failed and \
                api_func not in self.always_print:
            self.print_err('FAILED')
            return code
        elif result and 'result' in result and api_func != 'test':
            if result['result'] != 'ERROR':
                print(result['result'])
            else:
                self.print_err('FAILED')
            if result['result'] == 'ERROR':
                return apiclient.result_func_failed
        else:
            self.fancy_print_result(result, api_func, api_func_full, itype)
        return 0

    def print_tdf(self, result, time_field):
        self.import_pandas()
        # convert list to dict
        res = []
        for i in range(len(result[time_field])):
            r = {}
            for k in result.keys():
                if k != time_field:
                    r[k] = result[k][i]
                else:
                    r[k] = datetime.fromtimestamp(result[k][i]).isoformat()
            res.append(r)
        df = self.pd.DataFrame(res)
        df = df.set_index(time_field)
        df.index = self.pd.to_datetime(df.index, utc=False)
        out = df.to_string().split('\n')
        print(self.colored('time' + out[0][4:], color='blue', attrs=[]))
        print(self.colored('-' * len(out[0]), color='grey'))
        [print(o) for o in out[2:]]
