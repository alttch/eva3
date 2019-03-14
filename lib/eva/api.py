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


class NoAPIMethodException(Exception):
    pass


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


def cp_bad_request(msg=None):
    return cherrypy.HTTPError(400, msg if msg else None)


def parse_api_params(params, names='', types='', defaults=None):
    result = parse_function_params(params, 'k' + names, '.' + types,
                                   defaults)[1:]
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


def restful_api_function(f):

    @wraps(f)
    def do(c, rtp, *args, **kwargs):
        k, ii, full, save, kind, for_dir, props = restful_parse_params(
            *args, **kwargs)
        result = f(c, rtp, k, ii, full, kind, save, for_dir, props)
        if isinstance(result, dict):
            if result.get('result', 'OK') == 'OK':
                if 'result' in result: del result['result']
                n = f.__name__
                if n == 'POST':
                    if 'Location' in cherrypy.serving.response.headers:
                        cherrypy.serving.response.status = 201
                    else:
                        if not result:
                            return None
                elif n == 'PUT' or n == 'PATCH' or n == 'DELETE':
                    if not result:
                        return None
            else:
                if 'result' in result: del result['result']
        return result

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


def log_api_request(func, auth=None, info=None, debug=False):
    msg = 'API request '
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
    if debug:
        logging.debug(msg)
    else:
        if not eva.core.development or func == 'test':
            logging.debug(msg)
        else:
            logging.info(msg)


def log_http_api_request(k, func):
    p = prepare_http_request_logging_params(func)
    log_api_request(func=func, auth=http_remote_info(k), info=p, debug=False)


def prepare_http_request_logging_params(func):
    p = cherrypy.serving.request.params.copy()
    if not eva.core.development:
        if 'k' in p: del (p['k'])
        if func.startswith('set_'):
            try:
                if p.get('p') in ['key', 'masterkey']: del p['v']
            except:
                pass
    return p


def cp_check_perm(api_key=None, path_info=None):
    k = api_key if api_key else cp_client_key()
    path = path_info if path_info is not None else \
            cherrypy.serving.request.path_info
    if k is not None: cherrypy.serving.request.params['k'] = k
    # pass login and info
    if path.endswith('/login') or path.endswith('/info'): return
    log_http_api_request(k, path[1:])
    if apikey.check(k, ip=http_real_ip()): return
    raise cp_forbidden_key()


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


def cp_api_pre():
    g.api_call_log = {}


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


class GenericAPI(object):

    def test(self, k):
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
    def info(self):
        parse_api_params(params=kwargs)
        return {
            'platfrom': 'eva',
            'product': eva.core.product_code,
            'version': eva.core.version,
            'system': eva.core.system_name,
        }

    def get_state_history(self,
                          k=None,
                          a=None,
                          oid=None,
                          t_start=None,
                          t_end=None,
                          limit=None,
                          prop=None,
                          time_format=None,
                          fill=None,
                          fmt=None):
        if oid is None: return None
        n = eva.notify.get_db_notifier(a)
        if t_start and fill: tf = 'iso'
        else: tf = time_format
        if not n: return None
        try:
            result = n.get_state(
                oid=oid,
                t_start=t_start,
                t_end=t_end,
                limit=limit,
                prop=prop,
                time_format=tf)
        except:
            logging.warning('state history call failed, arch: %s, oid: %s' %
                            (n.notifier_id, oid))
            eva.core.log_traceback()
            return False
        if t_start and fill and result:
            tz = pytz.timezone(time.tzname[0])
            try:
                t_s = float(t_start)
            except:
                try:
                    t_s = dateutil.parser.parse(t_start).timestamp()
                except:
                    return False
            if t_end:
                try:
                    t_e = float(t_end)
                except:
                    try:
                        t_e = dateutil.parser.parse(t_end).timestamp()
                    except:
                        return False
            else:
                t_e = time.time()
            if t_e > time.time(): t_e = time.time()
            try:
                df = pd.DataFrame(result)
                df = df.set_index('t')
                df.index = pd.to_datetime(df.index, utc=True)
                sp1 = df.resample(fill).mean()
                sp2 = df.resample(fill).pad()
                sp = sp1.fillna(sp2).to_dict(orient='split')
                result = []
                for i in range(0, len(sp['index'])):
                    t = sp['index'][i].timestamp()
                    if time_format == 'iso':
                        t = datetime.fromtimestamp(t, tz).isoformat()
                    r = {'t': t}
                    if 'status' in sp['columns'] and 'value' in sp['columns']:
                        try:
                            r['status'] = int(sp['data'][i][0])
                        except:
                            r['status'] = None
                        r['value'] = sp['data'][i][1]
                    elif 'status' in sp['columns']:
                        try:
                            r['status'] = int(sp['data'][i][0])
                        except:
                            r['status'] = None
                    elif 'value' in sp['columns']:
                        r['value'] = sp['data'][i][0]
                    if 'value' in r and isinstance(
                            r['value'], float) and math.isnan(r['value']):
                        r['value'] = None
                    result.append(r)
            except:
                logging.warning('state history dataframe error')
                eva.core.log_traceback()
                return False
        if not fmt or fmt == 'list':
            res = {'t': []}
            for r in result:
                res['t'].append(r['t'])
                if 'status' in r:
                    if 'status' in res:
                        res['status'].append(r['status'])
                    else:
                        res['status'] = [r['status']]
                if 'value' in r:
                    if 'value' in res:
                        res['value'].append(r['value'])
                    else:
                        res['value'] = [r['value']]
            result = res
        elif fmt == 'dict':
            pass
        else:
            return False
        return result


def cp_json_handler(*args, **kwargs):
    value = cherrypy.serving.request._json_inner_handler(*args, **kwargs)
    if isinstance(value,
                  dict) and (not value or
                             ('result' in value and value['result'] != 'OK')):
        warn = ''
        for w in g.api_call_log.get(30, []):
            if warn:
                warn += '\n'
            warn += w
        err = ''
        for e in g.api_call_log.get(40, []):
            if err:
                err += '\n'
            err += e
        crit = ''
        for c in g.api_call_log.get(50, []):
            if crit:
                crit += '\n'
            crit += c
        if warn: value['_warning'] = warn
        if err: value['_error'] = err
        if crit: value['_critical'] = crit
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
            raise AccessDenied()
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


def cp_api_function(f):

    @wraps(f)
    def do(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
            if result is True:
                return http_api_result_ok()
            elif result is False:
                raise FunctionFailed()
            elif result is None:
                raise cp_api_404()
            else:
                if isinstance(result, str) or isinstance(
                        result, dict) or isinstance(result, list):
                    return result
                else:
                    return result.serialize()
        except InvalidParameter as e:
            raise cp_bad_request(str(e))
        except TypeError as e:
            raise cp_bad_request()
        except ResourceNotFound as e:
            raise cp_api_404(str(e))
        except FunctionFailed as e:
            return http_api_result_error()

    return do


class GenericHTTP_API_abstract:

    def __init__(self):
        self.__exposed = {}

    def __call__(self, *args, **kwargs):
        func = self.get_api_function(args)
        if func:
            try:
                return func(**kwargs)
            except TypeError:
                raise cp_bad_request()
        else:
            raise cp_api_404()

    def wrap_exposed(self, decorator):
        for k, v in self.__exposed:
            v = decorator(v)

    def _expose(self, f):
        if callable(f):
            self.__exposed[f.__name__] = f
        elif isinstance(f, str):
            self.__exposed[f] = getattr(self, f)
        elif isinstance(f, list):
            for func in f:
                self._expose(func)

    def get_api_function(self, f):
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

    def index(self, k=None):
        payload = getattr(cherrypy.serving.request, 'json_rpc_payload')
        http_err_codes = {403: 2, 404: 6, 500: 10}
        result = []
        for p in payload if isinstance(payload, list) else [payload]:
            if not isinstance(payload, dict) or not p:
                raise cp_bad_request('Invalid JSON RPC payload')
            if p.get('jsonrpc') != '2.0':
                raise cp_api_error('unsupported RPC protocol')
            req_id = p.get('id')
            try:
                r = {
                    'jsonrpc': '2.0',
                    'result': self._json_rpc(**p),
                    'id': req_id
                }
            except cherrypy.HTTPError as e:
                code = http_err_codes.get(e.code, 4)
                msg = e._message
                if not msg and code == 404: msg = 'API object not found'
                r = {
                    'jsonrpc': '2.0',
                    'error': {
                        'code': code,
                        'message': msg if msg else e.reason
                    }
                }
            except Exception as e:
                err = str(e)
                r = {'jsonrpc': '2.0', 'error': {'code': 10, 'message': err}}
            if req_id:
                r['id'] = req_id
                if isinstance(payload, list):
                    result.append(r)
                else:
                    result = r
        return result if result else None

    def _json_rpc(self, **kwargs):
        try:
            method = kwargs.get('method')
            if not method: raise NoAPIMethodException
            func = self.get_api_function(method)
            if not func:
                raise NoAPIMethodException
        except:
            raise cp_api_404('API method not found')
        params = kwargs.get('params', {})
        if 'k' not in params: params['k'] = kwargs.get('k')
        cp_check_perm(api_key=params['k'], path_info='/' + method)
        return func(**params)


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

    def login(self, k, u=None, p=None):
        if not u and k:
            if k in apikey.keys:
                cherrypy.session['k'] = k
                return http_api_result_ok({'key': apikey.key_id(k)})
            else:
                cherrypy.session['k'] = ''
                raise cp_forbidden_key()
        key = eva.users.authenticate(u, p)
        if eva.apikey.check(apikey.key_by_id(key), ip=http_real_ip()):
            cherrypy.session['k'] = apikey.key_by_id(key)
            return http_api_result_ok({'key': key})
        cherrypy.session['k'] = ''
        raise cp_forbidden_key()

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
    cherrypy.tools.api_pre = cherrypy.Tool(
        'before_handler', cp_api_pre, priority=20)
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


def error_page_404(*args, **kwargs):
    msg = kwargs.get('message')
    if not msg or msg == 'Nothing matches the given URI':
        msg = 'Resource or function not found'
    return jsonify_error(msg)


def error_page_500(*args, **kwargs):
    return jsonify_error(kwargs.get('message', 'API function error'))


api_cp_config = {
    'tools.api_pre.on': True,
    'tools.json_out.on': True,
    'tools.sessions.on': False,
    'tools.nocache.on': True,
    'tools.trailing_slash.on': False,
    'error_page.400': error_page_400,
    'error_page.403': error_page_403,
    'error_page.404': error_page_404,
    'error_page.500': error_page_500
}
