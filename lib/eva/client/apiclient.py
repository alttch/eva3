__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "3.1.0"

import os
import configparser
import requests
import jsonpickle

version = __version__

result_ok = 0
result_not_found = 1
result_forbidden = 2
result_api_error = 3
result_unknown_error = 4
result_not_ready = 5
result_func_unknown = 6
result_server_error = 7
result_server_timeout = 8
result_bad_data = 9
result_func_failed = 10
result_invalid_params = 11

_sysapi_uri = '/sys-api/'

_sysapi_func = [
    'cmd', 'lock', 'unlock', 'log_rotate', 'log_debug', 'log_info',
    'log_warning', 'log_error', 'log_critical', 'log_get', 'notifiers',
    'enable_notifier', 'disable_notifier', 'save', 'get_cvar', 'set_cvar',
    'set_debug', 'file_unlink', 'file_get', 'file_put', 'file_set_exec',
    'create_user', 'set_user_password', 'set_user_key', 'destroy_user',
    'list_keys', 'list_users', 'dump'
]

_sysapi_func_cr = [
    'lock', 'unlock', 'log_rotate', 'log_debug', 'log_info', 'log_warning',
    'log_error', 'log_critical', 'save', 'set_debug', 'set_cvar', 'file_unlink',
    'file_put', 'file_set_exec', 'create_user', 'set_user_password',
    'set_user_key', 'destroy_user', 'dump'
]

_sysapi_func_ce = ['cmd']

_api_func = {
    'uc': {
        'uri':
        '/uc-api/',
        'func': [
            'test', 'state', 'state_history', 'groups', 'update', 'action',
            'action_toggle', 'result', 'terminate', 'q_clean', 'kill',
            'disable_actions', 'enable_actions', 'get_config', 'save_config',
            'list', 'list_props', 'set_prop', 'create_unit', 'create_sensor',
            'create_mu', 'create_device', 'update_device', 'clone',
            'clone_group', 'destroy', 'destroy_device', 'login', 'logout',
            'load_phi', 'unload_phi', 'load_driver', 'unload_driver',
            'list_phi', 'list_drivers', 'get_phi', 'get_driver', 'test_phi'
        ],
        'cr': [
            'update', 'terminate', 'kill', 'q_clean', 'disable_actions',
            'enable_actions', 'save_config', 'set_prop', 'create_unit',
            'create_sensor', 'create_mu', 'create_device', 'update_device',
            'clone', 'clone_group', 'destroy', 'destroy_device', 'login',
            'logout', 'unload_phi', 'remove_driver'
        ],
        'ce': ['action', 'action_toggle']
    },
    'lm': {
        'uri':
        '/lm-api/',
        'func': [
            'test', 'state', 'state_history', 'groups', 'groups_macro', 'set',
            'reset', 'clear', 'toggle', 'run', 'result', 'get_config',
            'save_config', 'list', 'list_remote', 'list_controllers',
            'list_macros', 'create_macro', 'destroy_macro', 'append_controller',
            'remove_controller', 'list_props', 'list_macro_props',
            'list_controller_props', 'set_prop', 'set_macro_prop',
            'set_controller_prop', 'reload_controller', 'create_lvar',
            'destroy_lvar', 'list_rules', 'list_rule_props', 'set_rule_prop',
            'create_rule', 'destroy_rule', 'login', 'logout'
        ],
        'cr': [
            'set', 'reset', 'clear', 'toggle', 'save_config', 'set_prop',
            'set_macro_prop', 'set_controller_prop', 'create_macro',
            'destroy_macro', 'append_controller', 'remove_controller',
            'reload_controller', 'create_lvar', 'destroy_lvar', 'set_rule_prop',
            'create_rule', 'destroy_rule', 'login', 'logout'
        ],
        'ce': ['run']
    },
    'sfa': {
        'uri':
        '/sfa-api/',
        'func': [
            'test', 'state', 'state_all', 'state_history', 'groups', 'action',
            'action_toggle', 'result', 'terminate', 'kill', 'q_clean',
            'disable_actions', 'enable_actions', 'set', 'reset', 'toggle',
            'clear', 'list_macros', 'groups_macro', 'run', 'list_controllers',
            'append_controller', 'remove_controller', 'list_controller_props',
            'set_controller_prop', 'reload_controller', 'list_remote',
            'list_rule_props', 'set_rule_prop', 'login', 'logout',
            'reload_clients', 'notify_restart'
        ],
        'cr': [
            'terminate', 'kill', 'q_clean', 'disable_actions', 'enable_actions',
            'set', 'reset', 'toggle', 'clear', 'set_controller_prop',
            'append_controller', 'remove_controller', 'reload_controller',
            'set_rule_prop', 'login', 'logout', 'reload_clients'
        ],
        'ce': ['action', 'action_toggle', 'run']
    }
}


# copy of eva.tools.parse_host_port to avoid unnecesseary imports
def parse_host_port(hp):
    if hp.find(':') == -1: return (hp, None)
    try:
        host, port = hp.split(':')
        port = int(port)
    except:
        log_traceback()
        return (None, None)
    return (host, port)


class APIClient(object):

    def __init__(self):
        self._key = None
        self._uri = None
        self._timeout = 5
        self._product_code = 'sfa'
        self._ssl_verify = True

    def set_key(self, key):
        self._key = key

    def set_uri(self, uri):
        self._uri = uri

    def set_timeout(self, timeout):
        self._timeout = timeout

    def set_product(self, product):
        self._product_code = product

    def ssl_verify(self, v):
        self._ssl_verify = v

    def call(self,
             func,
             params=None,
             timeout=None,
             _return_raw=False,
             _api_uri=None,
             _debug=False):
        if not self._uri: return (result_not_ready, {})
        if timeout: t = timeout
        else: t = self._timeout
        api_uri = None
        check_result = False
        check_exitcode = False
        if not _api_uri:
            if self._product_code and \
                    self._product_code in _api_func and \
                    func in _api_func[self._product_code]['func']:
                api_uri = _api_func[self._product_code]['uri']
                if func in _api_func[self._product_code]['cr']:
                    check_result = True
                if func in _api_func[self._product_code]['ce']:
                    check_exitcode = True
            elif func in _sysapi_func:
                api_uri = _sysapi_uri
                if func in _sysapi_func_cr:
                    check_result = True
                if func in _sysapi_func_ce:
                    check_exitcode = True
            if not api_uri: return (result_func_unknown, {})
        else:
            api_uri = _api_uri
        if params:
            p = params.copy()
        else:
            p = {}
        if self._key is not None and 'k' not in p:
            p['k'] = self._key
        try:
            r = requests.post(
                self._uri + api_uri + func,
                data=p,
                timeout=t,
                verify=self._ssl_verify)
        except requests.Timeout:
            return (result_server_timeout, {}) if \
                    not _return_raw else (-1, {})
        except:
            if _debug:
                import traceback
                print(traceback.format_exc())
            return (result_server_error, {}) if \
                    not _return_raw else (-2, {})
        if _return_raw:
            return (r.status_code, r.text)
        if r.status_code != 200:
            if r.status_code == 403:
                return (result_forbidden, {})
            elif r.status_code == 404:
                return (result_not_found, {})
            elif r.status_code == 500:
                return (result_api_error, {})
            elif r.status_code == 400:
                return (result_invalid_params, {})
            else:
                return (result_unknown_error, {})
        try:
            result = jsonpickle.decode(r.text)
        except:
            if _debug:
                import traceback
                print(traceback.format_exc())
            return (result_bad_data, r.text)
        if (check_result and \
                (result is None or \
                    not 'result' in result or \
                    result['result'] != 'OK')) or \
                (check_exitcode and \
                    'exitcode' in result and \
                    result['exitcode']):
            return (result_func_failed, result)
        return (result_ok, result)


class APIClientLocal(APIClient):

    def __init__(self, product, dir_eva=None):
        super().__init__()
        if dir_eva is not None: _etc = dir_eva + '/etc'
        else:
            _etc = os.path.dirname(os.path.realpath(__file__)) + \
                    '/../../../etc'
        self._product_code = product
        cfg = configparser.ConfigParser(inline_comment_prefixes=';')
        cfg.readfp(open(_etc + '/' + product + '_apikeys.ini'))
        for s in cfg.sections():
            try:
                _master = (cfg.get(s, 'master') == 'yes')
                if _master:
                    try:
                        self._key = cfg.get(s, 'key')
                        break
                    except:
                        pass
            except:
                pass
        cfg = configparser.ConfigParser(inline_comment_prefixes=';')
        cfg.readfp(open(_etc + '/' + product + '.ini'))
        try:
            self._timeout = float(cfg.get('server', 'timeout'))
        except:
            pass
        try:
            h = cfg.get('webapi', 'listen')
            pfx = 'http://'
            default_port = 80
        except:
            try:
                h = cfg.get('webapi', 'ssl_listen')
                pfx = 'https://'
                default_port = 443
            except:
                h = None
        if h:
            try:
                host, port = parse_host_port(h)
                if host == '0.0.0.0': host = '127.0.0.1'
                if not port: port = default_port
                self._uri = pfx + host + ':' + str(port)
            except:
                pass
