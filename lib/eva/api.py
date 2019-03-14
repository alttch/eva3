import ipdb
__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.1.2"

import cherrypy
import logging
import threading
import time
import math
import jsonpickle
from datetime import datetime
import dateutil
import pytz
import pandas as pd

import eva.core
from eva import apikey
from eva.tools import format_json
from eva.tools import parse_host_port
from eva.tools import parse_function_params
from eva.tools import InvalidParameter

from eva.exceptions import FunctionFailed
from eva.exceptions import ResourceNotFound
from eva.exceptions import AccessDenied

import eva.users
import eva.notify
import eva.benchmark

from pyaltt import g

from functools import wraps

from types import SimpleNamespace

default_port = 80
default_ssl_port = 443

config = SimpleNamespace(
    host='127.0.0.1',
    port=default_port,
    ssl_host=None,
    ssl_port=default_ssl_port,
    ssl_module=None,
    ssl_cert=None,
    ssl_key=None,
    ssl_chain=None,
    session_timeout=0,
    thread_pool=15,
    ei_enabled=False,
    use_x_real_ip=False)


class MethodNotFound(Exception):

    def __str__(self):
        msg = super().__str__()
        return msg if msg else 'API method not found'


def http_api_result(result, env):
    result = {'result': result}
    if env:
        result.update(env)
    return result


def http_api_result_ok(env=None):
    if hasattr(cherrypy.serving.request, 'json_rpc_payload'):
        result = {'ok': True}
        if env: result.update(env)
        return result
    else:
        return http_api_result('OK', env)


def http_api_result_error(env=None):
    cherrypy.serving.response.status = 500
    return http_api_result('ERROR', env)


def cp_forbidden_key():
    return cherrypy.HTTPError(403)


def cp_api_error(msg=None):
    return cherrypy.HTTPError(500, msg if msg else None)


def cp_api_404(msg=None):
    return cherrypy.HTTPError(404, msg if msg else None)


def cp_api_405(msg=None):
    return cherrypy.HTTPError(405, msg if msg else None)


def cp_bad_request(msg=None):
    return cherrypy.HTTPError(400, msg if msg else None)


def parse_api_params(params, names='', types='', defaults=None):
    if isinstance(names, str):
        n = 'k' + names
    elif isinstance(names, list):
        n = ['k'] + names
    elif isinstance(names, tuple):
        n = ('k',) + names
    else:
        raise InvalidParameter('API params parser error')
    result = parse_function_params(params, n, '.' + types, defaults)[1:]
    return result if len(result) > 1 else result[0]


def restful_parse_params(*args, **kwargs):
    k = kwargs.get('k')
    kind = None
    if args:
        ii = '/'.join(args[:-1])
        l = args[-1]
        if l.find('@') != -1:
            l, kind = l.split('@', 1)
        if ii: ii += '/'
        ii += l
    else:
        ii = None
    full = kwargs.get('full')
    save = kwargs.get('save')
    kind = kwargs.get('kind', kind)
    for_dir = cherrypy.request.path_info.endswith('/')
    if 'k' in kwargs: del kwargs['k']
    if 'save' in kwargs: del kwargs['save']
    if 'full' in kwargs: del kwargs['full']
    if 'kind' in kwargs: del kwargs['kind']
    return k, ii, full, save, kind, for_dir, kwargs


def generic_web_api_method(f):
    """
    convert function exceptions to web exceptions
    """

    @wraps(f)
    def do(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except InvalidParameter as e:
            eva.core.log_traceback()
            raise cp_bad_request(str(e))
        except TypeError as e:
            eva.core.log_traceback()
            raise cp_bad_request()
        except ResourceNotFound as e:
            # eva.core.log_traceback()
            raise cp_api_404(str(e))
        except MethodNotFound as e:
            raise cp_api_405(str(e))
        except FunctionFailed as e:
            eva.core.log_traceback()
            raise cp_api_error(str(e))

    return do


def standard_web_api_method(f):
    """
    Updates Allow and checks for method
    """

    @wraps(f)
    def do(*args, **kwargs):
        allow = ['GET', 'POST']
        cherrypy.serving.response.headers['Allow'] = ', '.join(allow)
        if cherrypy.serving.request.method not in allow:
            raise MethodNotFound('HTTP method not allowed')
        return f(*args, **kwargs)

    return do


def restful_api_method(f):
    """
    wrapper for restful API methods
    """

    @wraps(f)
    def do(c, rtp, *args, **kwargs):
        k, ii, full, save, kind, for_dir, props = restful_parse_params(
            *args, **kwargs)
        result = f(c, rtp, k, ii, full, kind, save, for_dir, props)
        if result is False:
            raise FunctionFailed
        if result is None:
            raise ResourceNotFound
        if f.__name__ == 'POST':
            if 'Location' in cherrypy.serving.response.headers:
                cherrypy.serving.response.status = 201
        return None if result is True else result

    return do


def cp_api_function(f):
    """
    wrapper for direct calling API
    """

    @wraps(f)
    def do(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
            if result is True:
                return http_api_result_ok()
            elif result is False:
                raise FunctionFailed
            elif result is None:
                raise ResourceNotFound
            else:
                return result
        except FunctionFailed as e:
            err = str(e)
            return http_api_result_error({'_error': err} if err else None)

    return do


def set_response_location(location):
    cherrypy.response.headers['Location'] = location


def update_config(cfg):
    try:
        config.host, config.port = parse_host_port(
            cfg.get('webapi', 'listen'), default_port)
        logging.debug('webapi.listen = %s:%u' % (config.host, config.port))
    except:
        eva.core.log_traceback()
        return False
    try:
        config.ssl_host, config.ssl_port = parse_host_port(
            cfg.get('webapi', 'ssl_listen'), default_ssl_port)
        try:
            config.ssl_module = cfg.get('webapi', 'ssl_module')
        except:
            config.ssl_module = 'builtin'
        config.ssl_cert = cfg.get('webapi', 'ssl_cert')
        if ssl_cert[0] != '/':
            config.ssl_cert = eva.core.dir_etc + '/' + config.ssl_cert
        ssl_key = cfg.get('webapi', 'ssl_key')
        if ssl_key[0] != '/':
            config.ssl_key = eva.core.dir_etc + '/' + config.ssl_key
        logging.debug(
            'webapi.ssl_listen = %s:%u' % (config.ssl_host, config.ssl_port))
        config.ssl_chain = cfg.get('webapi', 'ssl_chain')
        if config.ssl_chain[0] != '/':
            config.ssl_chain = eva.core.dir_etc + '/' + config.ssl_chain
    except:
        pass
    try:
        config.session_timeout = int(cfg.get('webapi', 'session_timeout'))
    except:
        pass
    logging.debug('webapi.session_timeout = %u' % config.session_timeout)
    try:
        config.thread_pool = int(cfg.get('webapi', 'thread_pool'))
    except:
        pass
    logging.debug('webapi.thread_pool = %u' % config.thread_pool)
    eva.core.db_pool_size = config.thread_pool
    try:
        config.ei_enabled = (cfg.get('webapi', 'ei_enabled') == 'yes')
    except:
        pass
    logging.debug('webapi.ei_enabled = %s' % ('yes' \
                                if config.ei_enabled else 'no'))
    try:
        config.use_x_real_ip = (cfg.get('webapi', 'x_real_ip') == 'yes')
    except:
        pass
    logging.debug('webapi.x_real_ip = %s' % ('yes' \
                                if config.use_x_real_ip else 'no'))
    return True


class API_Logger(object):

    def log_api_request(self, func, params, logger):
        msg = 'API request '
        auth = self.get_auth(func, params)
        info = self.prepare_info(func, params)
        if auth:
            msg += auth + ':'
        msg += func
        if info:
            msg += ', '
            if isinstance(info, list):
                msg += ' '.join(info)
            elif isinstance(info, dict):
                for i, v in info.items():
                    msg += '%s="%s" ' % (i, v)
            else:
                msg += info
        logger(msg)

    def __call__(self, func, params, logger):
        self.log_api_request(func.__name__, params.copy(), logger)

    def prepare_info(self, func, p):
        if not eva.core.development:
            if 'k' in p: del (p['k'])
            if func.startswith('set_'):
                try:
                    if p.get('p') in ['key', 'masterkey']: del p['v']
                except:
                    pass
        return p

    def get_auth(self, func, params):
        return apikey.key_id(k)


class HTTP_API_Logger(API_Logger):

    def get_auth(self, func, params):
        return http_remote_info(params.get('k'))


def cp_check_perm(api_key=None, path_info=None):
    try:
        api_check_perm(api_key=api_key, path_info=path_info)
    except AccessDenied:
        raise cp_forbidden_key()


def api_check_perm(api_key=None, path_info=None):
    k = api_key if api_key else cp_client_key()
    path = path_info if path_info is not None else \
            cherrypy.serving.request.path_info
    if k is not None: cherrypy.serving.request.params['k'] = k
    # pass login and info
    if path.endswith('/login') or path.endswith('/info'): return
    if apikey.check(k, ip=http_real_ip()): return
    raise AccessDenied


def http_real_ip(get_gw=False):
    if get_gw and hasattr(cherrypy.serving.request, '_eva_ics_gw'):
        return 'gateway/' + cherrypy.serving.request._eva_ics_gw
    if config.use_x_real_ip and 'X-Real-IP' in cherrypy.request.headers and \
            cherrypy.request.headers['X-Real-IP']!='':
        ip = cherrypy.request.headers['X-Real-IP']
    else:
        ip = cherrypy.request.remote.ip
    return ip


def http_remote_info(k=None):
    return '%s@%s' % (apikey.key_id(k), http_real_ip(get_gw=True))


def cp_json_pre():
    try:
        if cherrypy.request.headers.get('Content-Type') == 'application/json':
            cl = int(cherrypy.request.headers.get('Content-Length'))
            raw = cherrypy.request.body.read(cl).decode()
        elif 'X-JSON' in cherrypy.request.headers:
            raw = cherrypy.request.headers.get('X-JSON')
        else:
            return
        if raw:
            data = jsonpickle.decode(raw)
            if isinstance(data, dict) and not data.get('jsonrpc'):
                cherrypy.serving.request.params.update(jsonpickle.decode(raw))
            else:
                cherrypy.serving.request.json_rpc_payload = data
    except:
        raise cp_bad_request('invalid JSON data')
    return


def get_json_payload():
    if cherrypy.request.headers.get('Content-Type') == 'application/json':
        cl = int(cherrypy.request.headers.get('Content-Length'))
        raw = cherrypy.request.body.read(cl).decode()
    elif 'X-JSON' in cherrypy.request.headers:
        raw = cherrypy.request.headers.get('X-JSON')
    else:
        return None
    return jsonpickle.decode(raw) if raw else None


def cp_jsonrpc_pre():
    try:
        data = get_json_payload()
        if not data: raise Exception('no payload')
        cherrypy.serving.request.json_rpc_payload = data
    except:
        raise cp_bad_request('invalid JSON data')


def cp_nocache():
    headers = cherrypy.serving.response.headers
    headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    headers['Pragma'] = 'no-cache'
    headers['Expires'] = '0'


def log_d(f):

    @wraps(f)
    def do(*args, **kwargs):
        args[0].log_api_call(f, kwargs, logging.debug)
        return f(*args, **kwargs)

    return do


def log_i(f):

    @wraps(f)
    def do(*args, **kwargs):
        args[0].log_api_call(f, kwargs, logging.info)
        return f(*args, **kwargs)

    return do


def log_w(f):

    @wraps(f)
    def do(*args, **kwargs):
        args[0].log_api_call(f, kwargs, logging.warning)
        return f(*args, **kwargs)

    return do


class GenericAPI(object):

    @log_d
    def test(self, **kwargs):
        """
        test API/key and get system info

        Test can be executed with any valid API key of the controller the
        function is called to.

        Args:
            k: any valid API key

        Returns:
            JSON dict with system info and current API key permissions (for
            masterkey only { "master": true } is returned)
        """
        k = parse_function_params(kwargs, 'k', 'S')
        result = http_api_result_ok({
            'acl':
            apikey.serialized_acl(k),
            'system':
            eva.core.system_name,
            'time':
            time.time(),
            'version':
            eva.core.version,
            'product_name':
            eva.core.product_name,
            'product_code':
            eva.core.product_code,
            'product_build':
            eva.core.product_build,
            'uptime':
            int(time.time() - eva.core.start_time)
        })
        if eva.core.enterprise_layout is not None:
            result['layout'] = 'enterprise' if \
                    eva.core.enterprise_layout else 'simple'
        if apikey.check(k, master=True):
            result['file_management'] = \
                    eva.sysapi.config.api_file_management_allowed
        if apikey.check(k, sysfunc=True):
            result['debug'] = eva.core.debug
            result['setup_mode'] = eva.core.setup_mode
            result['db_update'] = eva.core.db_update
            result['polldelay'] = eva.core.polldelay
            if eva.core.development:
                result['development'] = True
            if eva.benchmark.enabled and eva.benchmark.intervals:
                intervals = []
                for k, v in eva.benchmark.intervals.items():
                    s = v.get('s')
                    e = v.get('e')
                    if s is None or e is None: continue
                    intervals.append(e - s)
                try:
                    result['benchmark_crt'] = sum(intervals) / float(
                        len(intervals))
                except:
                    result['benchmark_crt'] = -1
        return result

    # return version for embedded hardware
    @log_d
    def info(self):
        parse_api_params(params=kwargs)
        return {
            'platfrom': 'eva',
            'product': eva.core.product_code,
            'version': eva.core.version,
            'system': eva.core.system_name,
        }


def cp_json_handler(*args, **kwargs):
    value = cherrypy.serving.request._json_inner_handler(*args, **kwargs)
    if value or isinstance(value, list):
        return format_json(
            value, minimal=not eva.core.development).encode('utf-8')
    else:
        try:
            del cherrypy.serving.response.headers['Content-Type']
        except:
            pass
        cherrypy.serving.response.status = 204
        return None


def cp_jsonrpc_handler(*args, **kwargs):
    value = cherrypy.serving.request._json_inner_handler(*args, **kwargs)
    if value is None:
        cherrypy.serving.response.status = 202
        return
    else:
        return format_json(
            value, minimal=not eva.core.development).encode('utf-8')


def api_need_master(f):

    @wraps(f)
    def do(*args, **kwargs):
        if not eva.apikey.check(kwargs.get('k'), master=True):
            raise AccessDenied
        return f(*args, **kwargs)

    return do


def cp_client_key(_k=None):
    if _k: return _k
    k = cherrypy.request.headers.get('X-Auth-Key')
    if k: return k
    if 'k' in cherrypy.serving.request.params:
        k = cherrypy.serving.request.params['k']
    else:
        try:
            k = cherrypy.session.get('k')
        except:
            k = None
        if k is None:
            k = eva.apikey.key_by_ip_address(http_real_ip())
    return k


class GenericHTTP_API_abstract:

    def __init__(self):
        self.__exposed = {}
        self.log_api_call = HTTP_API_Logger()

    @generic_web_api_method
    @standard_web_api_method
    def __call__(self, *args, **kwargs):
        func = self._get_api_function(args)
        if func:
            return func(**kwargs)
        else:
            raise MethodNotFound

    def wrap_exposed(self, decorator):
        for k, v in self.__exposed.items():
            self.__exposed[k] = decorator(v)

    def _expose(self, f):
        if callable(f):
            self.__exposed[f.__name__] = f
        elif isinstance(f, str):
            self.__exposed[f] = getattr(self, f)
        elif isinstance(f, list):
            for func in f:
                self._expose(func)

    def _get_api_function(self, f):
        if isinstance(f, list) or isinstance(f, tuple):
            f = '.'.join(f)
        return self.__exposed.get(f)

    def expose_api_methods(self, api_id, set_api_uri=True):
        try:
            data = jsonpickle.decode(
                open('{}/eva/apidata/{}_data.json'.format(
                    eva.core.dir_lib, api_id)).read())
            self._expose(data['functions'])
            if set_api_uri:
                self.api_uri = data['uri']
        except:
            eva.core.critical()


class JSON_RPC_API_abstract(GenericHTTP_API_abstract):

    api_uri = '/jrpc'

    def __init__(self, api_uri=None):
        super().__init__()
        self._cp_config = api_cp_config.copy()
        if api_uri:
            self.api_uri = api_uri
        self._cp_config['tools.jsonrpc_pre.on'] = True
        self._cp_config['tools.json_out.handler'] = cp_jsonrpc_handler
        JSON_RPC_API_abstract.index.exposed = True

    def index(self, **kwargs):

        def format_error(code, msg):
            return {
                'jsonrpc': '2.0',
                'error': {
                    'code': code,
                    'message': str(msg)
                }
            }

        payload = getattr(cherrypy.serving.request, 'json_rpc_payload')
        result = []
        for pp in payload if isinstance(payload, list) else [payload]:
            if not isinstance(payload, dict) or not pp:
                raise cp_bad_request('Invalid JSON RPC payload')
            if pp.get('jsonrpc') != '2.0':
                raise cp_api_error('unsupported RPC protocol')
            req_id = pp.get('id')
            try:
                p = pp.get('params', {})
                method = pp.get('method')
                if not method: raise FunctionFailed('API method not defined')
                # allow API key from anywhere
                if 'k' not in p: p['k'] = kwargs.get('k')
                f = self._get_api_function(method)
                if not f:
                    raise MethodNotFound
                api_check_perm(api_key=p.get('k'), path_info='/' + method)
                r = {'jsonrpc': '2.0', 'result': f(**p), 'id': req_id}
            except MethodNotFound as e:
                r = format_error(6, e)
            except ResourceNotFound as e:
                r = format_error(1, e)
            except AccessDenied as e:
                r = format_error(2, e)
            except Exception as e:
                r = format_error(10, e)
            if req_id:
                r['id'] = req_id
                if isinstance(payload, list):
                    result.append(r)
                else:
                    result = r
        return result if result else None


class GenericHTTP_API_REST_abstract:

    exposed = True
    api_uri = '/r'

    def __call__(self, *args, **kwargs):
        raise cp_api_404()


class GenericHTTP_API(GenericAPI, GenericHTTP_API_abstract):

    exposed = True

    def __init__(self):
        super().__init__()
        self._cp_config = api_cp_config.copy()
        self._cp_config['tools.auth.on'] = True
        self._cp_config['tools.json_pre.on'] = True
        self._cp_config['tools.json_out.handler'] = cp_json_handler

        if config.session_timeout:
            self._cp_config.update({
                'tools.sessions.on':
                True,
                'tools.sessions.timeout':
                config.session_timeout
            })
            self._expose(['login', 'logout'])

        self._expose('test')

    def wrap_exposed(self):
        super().wrap_exposed(cp_api_function)

    @log_i
    def login(self, k, u=None, p=None):
        if not u and k:
            if k in apikey.keys:
                cherrypy.session['k'] = k
                return http_api_result_ok({'key': apikey.key_id(k)})
            else:
                cherrypy.session['k'] = ''
                raise AccessDenied
        key = eva.users.authenticate(u, p)
        if eva.apikey.check(apikey.key_by_id(key), ip=http_real_ip()):
            cherrypy.session['k'] = apikey.key_by_id(key)
            return http_api_result_ok({'key': key})
        cherrypy.session['k'] = ''
        raise AccessDenied('Login or password incorrect')

    @log_d
    def logout(self):
        cherrypy.session['k'] = ''
        return http_api_result_ok()


def mqtt_discovery_handler(notifier_id, d):
    logging.info(
        'MQTT discovery handler got info from %s' % notifier_id + \
        ' about %s, but no real handler registered' % d
    )


def mqtt_api_handler(notifier_id, data, callback):
    try:
        if not data or data[0] != '|':
            raise Exception('invalid data')
        pfx, api_key_id, d = data.split('|', 2)
        try:
            ce = apikey.key_ce(api_key_id)
            if ce is None:
                raise Exception('invalid key')
            d = ce.decrypt(d.encode()).decode()
            call_id, api_type, api_func, api_data = d.split('|', 3)
        except:
            logging.warning(
                'MQTT API: invalid api key in encrypted packet from ' +
                notifier_id)
            raise
            return
        app = cherrypy.serving.request.app = cherrypy.tree.apps.get(
            '/%s-api' % api_type)
        if not app: raise Exception("Invalid app")
        cherrypy.serving.request._eva_ics_gw = 'mqtt'
        try:
            cherrypy.serving.session = cherrypy.lib.sessions.RamSession()
            cherrypy.serving.response.status = None
            cherrypy.serving.request.run(
                'GET', '/{}-api/{}'.format(api_type, api_func), '', 'HTTP/1.0',
                [('X-JSON', api_data)], None)
        except:
            callback(call_id, '500|')
            raise Exception('API error')
        response = ce.encrypt(cherrypy.serving.response.body[0]).decode()
        for ww in range(10):
            if cherrypy.serving.response.status: break
            time.sleep(eva.core.sleep_step)
        if not cherrypy.serving.response.status:
            raise Exception('No response from API')
        callback(call_id,
                 cherrypy.serving.response.status.split()[0] + '|' + response)
    except:
        logging.warning('MQTT API: API call failed from ' + notifier_id)
        eva.core.log_traceback()
        return


def start():
    if not config.host: return False
    cherrypy.server.unsubscribe()
    logging.info('HTTP API listening at at %s:%s' % \
            (config.host, config.port))
    server1 = cherrypy._cpserver.Server()
    server1.socket_port = config.port
    server1._socket_host = config.host
    server1.thread_pool = config.thread_pool
    server1.subscribe()
    if config.ssl_host and config.ssl_module and \
            config.ssl_cert and config.ssl_key:
        logging.info('HTTP API SSL listening at %s:%s' % \
                (config.ssl_host, config.ssl_port))
        server_ssl = cherrypy._cpserver.Server()
        server_ssl.socket_port = config.ssl_port
        server_ssl._socket_host = config.ssl_host
        server_ssl.thread_pool = config.thread_pool
        server_ssl.ssl_certificate = config.ssl_cert
        server_ssl.ssl_private_key = config.ssl_key
        if config.ssl_chain:
            server_ssl.ssl_certificate_chain = config.ssl_chain
        if config.ssl_module:
            server_ssl.ssl_module = config.ssl_module
        server_ssl.subscribe()
    if not eva.core.development:
        cherrypy.config.update({'environment': 'production'})
        cherrypy.log.access_log.propagate = False
        cherrypy.log.error_log.propagate = False
    else:
        cherrypy.config.update({'global': {'engine.autoreload.on': False}})
    cherrypy.engine.start()


@eva.core.stop
def stop():
    cherrypy.engine.exit()


def init():
    cherrypy.tools.json_pre = cherrypy.Tool(
        'before_handler', cp_json_pre, priority=10)
    cherrypy.tools.jsonrpc_pre = cherrypy.Tool(
        'before_handler', cp_jsonrpc_pre, priority=10)
    cherrypy.tools.auth = cherrypy.Tool(
        'before_handler', cp_check_perm, priority=60)
    cherrypy.tools.nocache = cherrypy.Tool(
        'before_finalize', cp_nocache, priority=10)


def jsonify_error(value):
    if not cherrypy.serving.response.body:
        return format_json(
            {
                '_error': value
            }, minimal=not eva.core.development).encode('utf-8')


def error_page_400(*args, **kwargs):
    return jsonify_error(kwargs.get('message', 'Invalid function params'))


def error_page_403(*args, **kwargs):
    if 'k' in cherrypy.serving.request.params:
        return jsonify_error('API key has no access to this resource')
    else:
        return jsonify_error('No API key provided')


def error_page_405(*args, **kwargs):
    return jsonify_error(kwargs.get('message', 'Method not allowed'))


def error_page_404(*args, **kwargs):
    msg = kwargs.get('message')
    if not msg or msg == 'Nothing matches the given URI':
        msg = 'Resource or function not found'
    return jsonify_error(msg)


def error_page_500(*args, **kwargs):
    return jsonify_error(kwargs.get('message', 'API function error'))


api_cp_config = {
    'tools.json_out.on': True,
    'tools.sessions.on': False,
    'tools.nocache.on': True,
    'tools.trailing_slash.on': False,
    'error_page.400': error_page_400,
    'error_page.403': error_page_403,
    'error_page.404': error_page_404,
    'error_page.405': error_page_405,
    'error_page.500': error_page_500
}
