__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "3.1.0"

import argparse
# to be compatible with argcomplete
import getopt
import importlib
import re
import sys
import os
import shlex
import readline
from datetime import datetime
from eva.client import apiclient
from eva.tools import print_json

class GenericCLI(object):

    def __init__(self, name):

        self.apikey = None
        self.apiuri = None
        self.api_func = None
        self.debug = False
        self.in_json = False
        self.default_timeout = 10
        self.timeout = self.default_timeout
        self.name = name
        self.pd = None
        self.argcomplete = None
        self.product = None
        self.ssl_verify = False
        self.always_json = []
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
        self.api_functions = self.common_api_functions
        self.common_pd_cols = {
            'list_keys': ['key_id', 'master', 'sysfunc', 'allow'],
            'log_get': ['time', 'host', 'p', 'level', 'message'],
            'log_get_':
            ['time', 'host', 'p', 'level', 'mod', 'thread', 'message']
        }
        self.pd_cols = self.common_pd_cols
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
        self.log_levels = {
            10: 'DEBUG',
            20: 'INFO',
            30: 'WARNING',
            40: 'ERROR',
            50: 'CRITICAL'
        }
        self.pd_idx = self.common_pd_idx
        self.common_fancy_tabsp = {'test': 14}
        self.fancy_tabsp = self.common_fancy_tabsp
        self.ap = argparse.ArgumentParser(description=self.name)
        self.add_primary_options()
        self.add_main_subparser()
        self.add_functions()
        self.load_argcomplete()

    def load_argcomplete(self):
        try:
            self.argcomplete = importlib.import_module('argcomplete')
        except:
            pass

    def get_log_level_name(self, level):
        l = self.log_levels.get(level)
        return l if l else level

    def get_log_level_code(self, name):
        if not isinstance(name, str): return name
        n = str.upper(name)
        for l, v in self.log_levels.items():
            if n[0] == v[0]: return l
        return None

    def add_primary_options(self):
        self.ap.add_argument(
            '-K',
            '--api-key',
            help=
            'master key, if no key specified, local master key will be used',
            dest='_api_key',
            metavar='KEY')
        self.ap.add_argument(
            '-U', '--api-url', help='API URL', dest='_api_uri', metavar='URL')
        self.ap.add_argument(
            '-T',
            '--api-timeout',
            help='API request timeout (in seconds)',
            type=float,
            default=self.default_timeout,
            dest='_timeout',
            metavar='TIMEOUT')
        self.ap.add_argument(
            '-J',
            '--json',
            help='print result as JSON',
            action='store_true',
            dest='_json',
            default=False)
        self.ap.add_argument(
            '-D',
            '--debug',
            help='enable debug messages',
            action='store_true',
            dest='_debug',
            default=False)

    def add_main_subparser(self):
        self.sp = self.ap.add_subparsers(
            dest='_type', metavar='command', help='command or type')

    def set_api_functions(self, fn_table={}):
        self.api_functions = {**self.common_api_functions, **fn_table}

    def set_pd_cols(self, pd_cols={}):
        self.pd_cols = {**self.common_pd_cols, **pd_cols}

    def set_pd_idx(self, pd_idx={}):
        self.pd_idx = {**self.common_pd_idx, **pd_idx}

    def set_fancy_tabsp(self, fancy_tabsp={}):
        self.fancy_tabsp = {**self.common_fancy_tabsp, **fancy_tabsp}

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

    def fancy_print_result(self, result, api_func, api_func_full, itype, tab=0):
        if result and isinstance(result, dict):
            rprinted = False
            h = None
            out = None
            err = None
            tabsp = self.fancy_tabsp.get(api_func)
            if not tabsp: tabsp = 10
            for v in sorted(result.keys()):
                if v == 'help':
                    if not not tab:
                        h = result[v]
                    else:
                        pass
                elif v == 'out' and not tab:
                    out = result[v]
                elif v == 'err' and not tab:
                    err = result[v]
                elif v != 'result':
                    if isinstance(result[v], dict):
                        if tab:
                            print(' ' * (tab * tabsp), end='>' * tab + ' ')
                        print(("{:>%u} : {}" % max(map(len, result))).format(
                            v, ''))
                        self.fancy_print_result(result[v], api_func,
                                                api_func_full, itype, tab + 1)
                    else:
                        if tab:
                            print(' ' * (tab * tabsp), end='>' * tab + ' ')
                        if isinstance(result[v], list):
                            _r = []
                            for vv in result[v]:
                                _r.append(str(vv))
                            _v = ', '.join(_r)
                        else:
                            _v = result[v]
                        print(("{:>%u} : {}" % max(map(len, result))).format(
                            v, _v))
                    rprinted = True
            if h:
                print('-' * 81)
                print(h.strip())
                rprinted = True
            if out:
                print('-' * 81)
                print('OUTPUT:')
                print(out.strip())
                rprinted = True
            if err:
                print('-' * 81)
                print('ERROR:')
                print(err.strip())
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
                print(idxcol + out[0][len(idxcol):])
                print('-' * len(out[0]))
                [print(re.sub('^NaN', '   ', o)) for o in out[2:]]
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
        self.add_primary_functions()
        self.add_cmd_functions()
        self.add_lock_functions()
        self.add_log_functions()
        self.add_cvar_functions()
        self.add_debug_functions()
        self.add_file_functions()
        self.add_key_functions()
        self.add_user_functions()

    def add_primary_functions(self):
        ap_test = self.sp.add_parser('test', help='API test')
        ap_save = self.sp.add_parser('save', help='Save item state and config')

    def add_cmd_functions(self):
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

    def add_lock_functions(self):
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

    def add_log_functions(self):
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
            '-l', '--level', help='Log level', metavar='LEVEL', dest='l')
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

    def add_cvar_functions(self):
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

    def add_debug_functions(self):
        ap_debug = self.sp.add_parser('debug', help='Debug control')
        ap_debug.add_argument(
            'debug',
            help='Debug mode (on/off)',
            metavar='MODE',
            choices=['on', 'off'])

    def add_file_functions(self):
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

    def add_key_functions(self):
        ap_key = self.sp.add_parser('key', help='API key management')
        sp_key = ap_key.add_subparsers(
            dest='_func', metavar='func', help='API key commands')

        sp_key_list = sp_key.add_parser('list', help='List API keys')

    def add_user_functions(self):
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
        return 0

    def run(self):
        batch_file = None
        stop_on_err = True
        interactive = False
        try:
            o, a = getopt.getopt(
                sys.argv[1:], '',
                ['exec-batch=', 'pass-batch-err', 'interactive'])
            for i, v in o:
                if i == '--exec-batch':
                    batch_file = v
                elif i == '--pass-batch-err':
                    stop_on_err = False
                elif i == '--interactive':
                    interactive = True
        except:
            pass
        if batch_file is not None:
            try:
                if batch_file != 'stdin':
                    cmds = [x.strip() for x in open(batch_file).readlines()]
                else:
                    cmds = [x.strip() for x in sys.stdin]
                for c in cmds:
                    print('>> ' + c)
                    try:
                        code = self.do_run(shlex.split(c))
                    except:
                        code = 90
                    print()
                    if code and stop_on_err: return code
            except:
                raise
                print('Unable to open %s' % batch_file)
                return 90
        elif not interactive:
            return self.do_run()
        else:
            while True:
                d = ''
                while d == '':
                    try:
                        d = shlex.split(input('>> '))
                    except:
                        raise
                        print('Bye')
                        return 0
                if d[0] in ['q', 'quit', 'exit', 'bye']:
                    print('Bye')
                    return 0
                elif d[0] == '?':
                    print('q for quit')
                    print('k for key display/set (k. for key reset)')
                    print('t for timeout display/set (t. for timeout reset)')
                    print('j for json mode (j. for normal mode)')
                    print('d for API debug mode (d. for normal mode)')
                    print('sh for a system shell')
                    print('top for display system processes')
                    print('or command to execute')
                elif d[0] == 'k.':
                    self.apikey = None
                    print('Key has been reset to default')
                elif d[0] == 'j':
                    self.in_json = True
                    print('JSON mode on')
                elif d[0] == 'j.':
                    self.in_json = False
                    print('JSON mode off')
                elif d[0] == 'd':
                    self.debug = True
                    print('API debug mode on')
                elif d[0] == 'd.':
                    self.debug = False
                    print('API debug mode off')
                elif d[0] == 't.':
                    self.timeout = self.default_timeout
                    print('timeout: %f' % self.timeout)
                elif d[0] == 'k':
                    if len(d) > 1:
                        self.apikey = d[1]
                    print('key: %s' % self.apikey
                          if self.apikey is not None else '<default>')
                elif d[0] == 't':
                    if len(d) > 1:
                        try:
                            self.timeout = float(d[1])
                        except:
                            print('Failed')
                    print('timeout: %f' % self.timeout)
                elif d[0] == 'top':
                    try:
                        os.system('top')
                    except:
                        print('Failed to run system "top" command')
                elif d[0] == 'sh':
                    print('Executing system shell')
                    shell = os.environ.get('SHELL')
                    if shell is None:
                        if os.path.isfile('/bin/bash'): shell = '/bin/bash'
                        else: shell = 'sh'
                    try:
                        os.system(shell)
                    except:
                        print('Failed to run system shell "%s"' % shell)
                elif d[0] == 'h':
                    try:
                        self.do_run(['-h'])
                    except:
                        pass
                else:
                    try:
                        opts = []
                        if self.apikey is not None:
                            opts += ['-K', self.apikey]
                        if self.timeout is not None:
                            opts += ['-T', str(self.timeout)]
                        if self.in_json:
                            opts += ['-J']
                        if self.debug:
                            opts += ['-D']
                        code = self.do_run(opts + d)
                        if self.debug: print('\nCode: %s' % code)
                    except:
                        pass
        return 0

    def do_run(self, args=None):
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
        debug = a._debug
        api_func = self.get_api_func(itype, func)
        if not api_func:
            self.ap.print_help()
            return 99
        self.apiuri = a._api_uri
        apikey = a._api_key
        if not self.apiuri:
            try:
                api = apiclient.APIClientLocal(self.product)
            except:
                print('Can not init API, %s.ini or %s_apikeys.ini missing?' %
                      (self.product, self.product))
                return 98
        else:
            api = apiclient.APIClient()
            api.set_uri(self.apiuri)
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
        code = self.prepare_run(api_func, params, a)
        if code: return code
        timeout = a._timeout
        if debug:
            print('API:', api._uri)
            print('API func:', api_func)
            print('timeout:', timeout)
            print('params', params)
        code, result = api.call(api_func, params, timeout, _debug=debug)
        if code != apiclient.result_ok and \
            code != apiclient.result_func_failed:
            if code == apiclient.result_not_found:
                print('Error: Object not found')
            elif code == apiclient.result_forbidden:
                print('Error: Forbidden')
            elif code == apiclient.result_api_error:
                print('Error: API error')
            elif code == apiclient.result_unknown_error:
                print('Error: Unknown error')
            elif code == apiclient.result_not_ready:
                print('Error: API not ready')
            elif code == apiclient.result_func_unknown:
                self.ap.print_help()
            elif code == apiclient.result_server_error:
                print('Error: Server error')
            elif code == apiclient.result_server_timeout:
                print('Error: Server timeout')
            elif code == apiclient.result_bad_data:
                print('Error: Bad data')
            elif code == apiclient.result_invalid_params:
                print('Error: invalid params')
            if debug:
                print('API result code: %u' % code)
            return code
        else:
            if a._json or api_func in self.always_json:
                print_json(result)
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
                print('FAILED')
                return 95
        elif code == apiclient.result_func_failed and \
                api_func not in self.always_print:
            print('FAILED')
            return code
        elif 'result' in result and api_func != 'test':
            print(result['result'])
            if result['result'] == 'ERROR':
                return apiclient.result_func_failed
        else:
            self.fancy_print_result(result, api_func, api_func_full, itype)
        return 0

    def print_tdf(self, result):
        self.import_pandas()
        # convert list to dict
        res = []
        for i in range(len(result['t'])):
            r = {}
            for k in result.keys():
                if k != 't':
                    r[k] = result[k][i]
                else:
                    r[k] = datetime.fromtimestamp(result[k][i]).isoformat()
            res.append(r)
        df = self.pd.DataFrame(res)
        df = df.set_index('t')
        df.index = self.pd.to_datetime(df.index, utc=False)
        out = df.to_string().split('\n')
        print('time' + out[0][4:])
        print('-' * len(out[0]))
        [print(o) for o in out[2:]]
