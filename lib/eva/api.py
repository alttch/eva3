__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"

import cherrypy
import logging
import threading
import time
import math
import importlib
import rapidjson
import msgpack
import eva.tokens as tokens
import uuid

import eva.core
import eva.crypto
from eva import apikey

from eva.core import plugins_event_apicall

from eva.tools import format_json
from eva.tools import parse_host_port
from eva.tools import parse_function_params
from eva.tools import val_to_boolean
from eva.tools import is_oid
from eva.tools import oid_to_id
from eva.tools import parse_oid
from eva.tools import dict_from_str
from eva.tools import prepare_safe_serialize

from eva.client import apiclient
from functools import partial

from eva.exceptions import FunctionFailed
from eva.exceptions import ResourceNotFound
from eva.exceptions import AccessDenied
from eva.exceptions import ResourceAlreadyExists
from eva.exceptions import ResourceBusy
from eva.exceptions import InvalidParameter
from eva.exceptions import MethodNotImplemented

import eva.users
import eva.notify
import eva.benchmark

from neotasker import g

from functools import wraps

from eva.tools import SimpleNamespace

from eva.types import CT_JSON, CT_MSGPACK

import base64

default_port = 80
default_ssl_port = 443

config = SimpleNamespace(host='127.0.0.1',
                         port=default_port,
                         ssl_host=None,
                         ssl_port=default_ssl_port,
                         ssl_module=None,
                         ssl_cert=None,
                         ssl_key=None,
                         ssl_chain=None,
                         ssl_force_redirect=False,
                         session_timeout=0,
                         session_no_prolong=False,
                         thread_pool=15,
                         ei_enabled=True,
                         use_x_real_ip=False)

api_result_accepted = 2

msgpack_loads = partial(msgpack.loads, raw=False)

_exposed_lock = threading.RLock()
_exposed = {}


def key_check_master(*args, ro_op=False, **kwargs):
    """
    check master API key access

    Args:
        k: API key, required
        ro_op: is item operation read-only
    """
    result = apikey.check_master(*args, **kwargs)
    if result is True and not ro_op:
        if get_aci('auth') == 'token' and tokens.get_token_mode(
                get_aci('token')) != tokens.TOKEN_MODE_NORMAL:
            raise TokenRestricted
    return result


def key_check(*args, ro_op=False, **kwargs):
    """
    check API key access

    Arguments are ACL which can be combined

    Args:
        k: API key, required
        items: item objects
        oid: OID (mqtt-style masks allowed)
        allow: check allows
        pvt_file: access to pvt resource
        pvt_file: access to rpvt resource
        ip: caller IP
        master: is master access required
        sysfunc: is sysfunc required
        ro_op: is item operation read-only
    """
    result = apikey.check(*args, ro_op=ro_op, **kwargs)
    if result is True and not ro_op:
        if get_aci('auth') == 'token' and tokens.get_token_mode(
                get_aci('token')) != tokens.TOKEN_MODE_NORMAL:
            raise TokenRestricted
    return result


def expose_api_method(fn, f, sys_api=False):
    if f.__class__.__name__ != 'method':
        raise ValueError('only class methods can be exposed')
    else:
        with _exposed_lock:
            _exposed[fn] = (f, sys_api)


class MethodNotFound(Exception):
    """
    raised when requested method is not found
    """

    def __str__(self):
        msg = super().__str__()
        return msg if msg else 'API method not found'


class EvaHIAuthenticationRequired(Exception):
    pass


class TokenRestricted(Exception):
    pass


def api_need_master(f):
    """
    API method decorator to pass if API key is masterkey
    """

    @wraps(f)
    def do(*args, **kwargs):
        if not key_check_master(kwargs.get('k')):
            raise AccessDenied
        return f(*args, **kwargs)

    return do


def init_api_call(http_call=True, **kwargs):
    if config.ssl_force_redirect:
        req = cherrypy.serving.request
        if req.scheme == 'http' and req.method == 'GET':
            host = req.headers.get('Host')
            if host:
                host = host.rsplit(':', 1)[0]
            else:
                host = config.ssl_host
            try:
                path = req.request_line.split(maxsplit=2)[1]
            except:
                path = ''
            url = f'https://{host}:{config.ssl_port}{path}'
            raise cherrypy.HTTPRedirect(url, 301)
    aci = kwargs.copy() if kwargs else {}
    if http_call:
        aci['id'] = str(cherrypy.serving.request.unique_id)
    elif eva.core.config.keep_api_log:
        aci['id'] = str(uuid.uuid4())
    g.set('aci', aci)


def clear_api_call():
    g.clear('aci')


def log_api_call_result(status):
    if eva.core.config.keep_api_log:
        i = get_aci('id')
        if i:
            eva.users.api_log_set_status(i, status)


def get_aci(field, default=None):
    """
    get API call info field

    Args:
        field: ACI field
        default: default value if ACI field isn't set

    Returns:
        None if ACI field isn't set
    """
    aci = g.get('aci')
    if aci is None:
        return default
    else:
        return aci.get(field, default)


def set_aci(field, value):
    """
    set API call info field

    Args:
        field: ACI field
        value: field value

    Returns:
        True if value is set, False for error (e.g. ACI isn't initialized)
    """
    try:
        g.get('aci')[field] = value
        return True
    except TypeError:
        return False


def http_api_result(result, env):
    result = {'result': result}
    if env:
        result.update(env)
    return result


def http_api_result_ok(env=None):
    return http_api_result('OK', env)


def http_api_result_error(env=None):
    cherrypy.serving.response.status = 500
    return http_api_result('ERROR', env)


def cp_forbidden_key(message=None):
    if message:
        msg = str(message)
    else:
        if 'k' in cherrypy.serving.request.params:
            msg = 'API key has no access to selected resource or function'
        else:
            msg = 'No API key provided'
    return cherrypy.HTTPError(403, msg if msg else None)


def cp_api_error(message=None):
    msg = str(message) if message else ''
    return cherrypy.HTTPError(500, msg if msg else None)


def cp_api_404(message=None):
    msg = str(message) if message else 'Resource or function not found'
    return cherrypy.HTTPError(404, msg if msg else None)


def cp_api_405(message=None):
    msg = str(message) if message else ''
    return cherrypy.HTTPError(405, msg if msg else None)


def cp_api_409(message=None):
    msg = str(message) if message else ''
    return cherrypy.HTTPError(409, msg if msg else None)


def cp_bad_request(message=None):
    msg = str(message) if message else ''
    return cherrypy.HTTPError(400, msg if msg else None)


def parse_api_params(params, names='', types='', defaults=None):
    """
    calls parse_function_params but omits API key
    """
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


def format_resource_id(rtp, i):
    return {'type': rtp, 'id': i}


def restful_parse_params(*args, **kwargs):
    k = kwargs.get('k')
    kind = None
    if args:
        ii = '/'.join(args[:-1])
        l = args[-1]
        if l.find('@') != -1:
            l, kind = l.split('@', 1)
        if ii:
            ii += '/'
        ii += l
    else:
        ii = None
    save = val_to_boolean(kwargs.get('save'))
    kind = kwargs.get('kind', kind)
    method = kwargs.get('method')
    for_dir = cherrypy.request.path_info.endswith('/')
    if 'k' in kwargs:
        del kwargs['k']
    if 'save' in kwargs:
        del kwargs['save']
    if 'kind' in kwargs:
        del kwargs['kind']
    if 'method' in kwargs:
        del kwargs['method']
    return k, ii, save, kind, method, for_dir, kwargs


def generic_web_api_method(f):
    """
    convert function exceptions to web exceptions
    """

    @wraps(f)
    def do(*args, **kwargs):
        try:
            result = jsonify(f(*args, **kwargs))
            log_api_call_result('OK')
            return result
        except InvalidParameter as e:
            log_api_call_result('InvalidParameter')
            eva.core.log_traceback()
            raise cp_bad_request(e)
        except MethodNotImplemented as e:
            log_api_call_result('MethodNotImplemented')
            raise cp_bad_request(e)
        except TypeError as e:
            log_api_call_result('TypeError')
            eva.core.log_traceback()
            raise cp_bad_request()
        except ResourceNotFound as e:
            log_api_call_result('ResourceNotFound')
            eva.core.log_traceback()
            raise cp_api_404(e)
        except MethodNotFound as e:
            log_api_call_result('MethodNotFound')
            eva.core.log_traceback()
            raise cp_api_405(e)
        except ResourceAlreadyExists as e:
            log_api_call_result('ResourceAlreadyExists')
            eva.core.log_traceback()
            raise cp_api_409(e)
        except ResourceBusy as e:
            log_api_call_result('ResourceBusy')
            eva.core.log_traceback()
            raise cp_api_409(e)
        except AccessDenied as e:
            log_api_call_result('AccessDenied')
            eva.core.log_traceback()
            raise cp_forbidden_key(e)
        except TokenRestricted as e:
            log_api_call_result('TokenRestricted')
            eva.core.log_traceback()
            raise cp_forbidden_key(e)
        except FunctionFailed as e:
            log_api_call_result('FunctionFailed')
            eva.core.log_traceback()
            raise cp_api_error(e)

    return do


def standard_web_api_method(f):
    """
    Updates Allow and checks for method
    """

    @wraps(f)
    def do(*args, **kwargs):
        allow = ['GET', 'HEAD', 'POST']
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
    def do(_api_class_name, _api_resource_type, *args, **kwargs):
        k, ii, save, kind, method, for_dir, props = restful_parse_params(
            *args, **kwargs)
        result = f(_api_class_name, _api_resource_type, k, ii, save, kind,
                   method, for_dir, props)
        if isinstance(result, tuple):
            result, data = result
            if isinstance(result, bytes):
                cherrypy.serving.response.headers['Content-Type'] = data
                return result
        else:
            data = None
        if result is False:
            raise FunctionFailed
        if result is None:
            raise ResourceNotFound
        if (f.__name__ == 'POST' and 'Location'
                in cherrypy.serving.response.headers) or f.__name__ == 'PUT':
            cherrypy.serving.response.status = 201
        if result is True:
            if data == api_result_accepted:
                cherrypy.serving.response.status = 202
                return None
            else:
                return data
        else:
            return result

    return do


def cp_api_function(f):
    """
    wrapper for direct calling API
    """

    @wraps(f)
    def do(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
            if isinstance(result, tuple):
                result, data = result
                if isinstance(result, bytes):
                    cherrypy.serving.response.headers['Content-Type'] = data
                    return result
            else:
                data = None
            if result is True:
                if data == api_result_accepted:
                    return http_api_result_ok()
                else:
                    return http_api_result_ok(data)
            elif result is False:
                raise FunctionFailed
            elif result is None:
                raise ResourceNotFound
            else:
                return result
        except FunctionFailed as e:
            eva.core.log_traceback()
            err = str(e)
            return http_api_result_error({'_error': err} if err else None)

    return do


def set_response_location(location):
    cherrypy.response.headers['Location'] = location


def set_restful_response_location(i, rtp, api_uri='/r'):
    cherrypy.response.headers['Location'] = '{}/{}/{}'.format(api_uri, rtp, i)


def update_config(cfg):
    try:
        config.host, config.port = parse_host_port(cfg.get('webapi/listen'),
                                                   default_port)
        logging.debug('webapi.listen = %s:%u' % (config.host, config.port))
    except:
        eva.core.log_traceback()
        return False
    try:
        config.ssl_host, config.ssl_port = parse_host_port(
            cfg.get('webapi/ssl-listen'), default_ssl_port)
        try:
            config.ssl_module = cfg.get('webapi/ssl-module')
        except LookupError:
            config.ssl_module = 'builtin'
        config.ssl_cert = cfg.get('webapi/ssl-cert')
        if config.ssl_cert[0] != '/':
            config.ssl_cert = eva.core.dir_etc + '/' + config.ssl_cert
        config.ssl_key = cfg.get('webapi/ssl-key')
        if config.ssl_key[0] != '/':
            config.ssl_key = eva.core.dir_etc + '/' + config.ssl_key
        logging.debug('webapi.ssl_listen = %s:%u' %
                      (config.ssl_host, config.ssl_port))
        config.ssl_chain = cfg.get('webapi/ssl-chain')
        if config.ssl_chain[0] != '/':
            config.ssl_chain = eva.core.dir_etc + '/' + config.ssl_chain
        config.ssl_force_redirect = cfg.get('webapi/ssl-force-redirect')
    except:
        pass
    try:
        config.session_timeout = int(cfg.get('webapi/session-timeout'))
        tokens.expire = config.session_timeout
    except:
        pass
    logging.debug(f'webapi.session_timeout = {config.session_timeout}')
    try:
        config.session_no_prolong = cfg.get('webapi/session-no-prolong')
        tokens.prolong_disabled = config.session_no_prolong
    except:
        pass
    logging.debug(f'webapi.session_no_prolong = {config.session_no_prolong}')
    try:
        config.thread_pool = int(cfg.get('webapi/thread-pool'))
    except:
        pass
    logging.debug(f'webapi.thread_pool = {config.thread_pool}')
    eva.core.db_pool_size = config.thread_pool
    config.ei_enabled = cfg.get('webapi/ei-enabled', default=True)
    logging.debug(f'webapi.ei_enabled = {config.ei_enabled}')
    config.use_x_real_ip = cfg.get('webapi/x-real-ip', default=False)
    logging.debug(f'webapi.x_real_ip = {config.use_x_real_ip}')
    return True


class API_Logger(object):

    def log_api_request(self, func, params, logger, fp_hide, debug=False):
        msg = 'API request '
        auth, ki = self.get_auth(func, params)
        info = self.prepare_info(func, params, fp_hide)
        ip = http_real_ip(get_gw=True, ip_only=True)
        if auth:
            msg += (auth if '@' in auth else (auth + f'@{ip}')) + ':'
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
        # extended API call logging
        if not debug and eva.core.config.keep_api_log:
            i = get_aci('id')
            if i:
                gw = get_aci('gw', 'http')
                auth = get_aci('auth', 'key')
                u = get_aci('u')
                utp = get_aci('utp')
                is_logged = get_aci('logged')
                if not is_logged:
                    eva.users.api_log_insert(i, gw, ip, auth, u, utp, ki, func,
                                             info)
                    set_aci('logged', True)

    def __call__(self, func, params, logger, fp_hide, debug=False):
        self.log_api_request(func if isinstance(func, str) else func.__name__,
                             params.copy(), logger, fp_hide, debug)

    def prepare_info(self, func, p, fp_hide):

        # if not eva.core.config.development:
        if 'k' in p:
            del p['k']
        if func.startswith('set_') or func.endswith('_set'):
            fp = p.get('p')
            if fp in ['key', 'masterkey', 'password']:
                p[fp] = '<hidden>'
        elif func == 'login':
            if 'p' in p:
                p['p'] = '<hidden>'
            if 'a' in p:
                p['a'] = '<hidden>'
        fplist = fp_hide.get(func)
        if fplist:
            for fp in fplist:
                if callable(fp):
                    fp(func, p)
                elif fp in p:
                    p[fp] = '<hidden>'
        for i, v in p.items():
            p[i] = prepare_safe_serialize(v)
        return p

    def get_auth(self, func, params):
        ki = apikey.key_id(params.get('k'))
        if ki:
            set_aci('key_id', ki)
        return ki, ki


class HTTP_API_Logger(API_Logger):

    def get_auth(self, func, params):
        ki = apikey.key_id(params.get('k'))
        if ki:
            set_aci('key_id', ki)
        return f'{ki}@{http_real_ip(get_gw=True)}', ki


def cp_check_perm(api_key=None, path_info=None):
    k = api_key if api_key else cp_client_key(_aci=True)
    path = path_info if path_info is not None else \
            cherrypy.serving.request.path_info
    if k is not None:
        cherrypy.serving.request.params['k'] = k
    # pass login and info
    if path in ['/login', '/info', '/token']:
        return
    if key_check(k, ip=http_real_ip(), ro_op=True):
        return
    if api:
        api._log_api_call('', {}, logging.warning, {})
        logging.warning(f'API call {get_aci("id")} access denied')
        log_api_call_result('AccessDenied')
    raise cp_forbidden_key()


def http_real_ip(get_gw=False, ip_only=False):
    if get_gw:
        gw = get_aci('gw')
        if gw:
            return None if ip_only else 'gateway/' + gw
    if config.use_x_real_ip and 'X-Real-IP' in cherrypy.request.headers and \
            cherrypy.request.headers['X-Real-IP']!='':
        ip = cherrypy.request.headers['X-Real-IP']
    else:
        ip = cherrypy.request.remote.ip
    return ip


def cp_json_pre():
    g.set('ct_format', CT_JSON)
    try:
        if cherrypy.request.headers.get('Content-Type') == 'application/json':
            cl = int(cherrypy.request.headers.get('Content-Length'))
            raw = cherrypy.request.body.read(cl).decode()
        elif 'X-JSON' in cherrypy.request.headers:
            raw = cherrypy.request.headers.get('X-JSON')
        else:
            return
        if raw:
            cherrypy.serving.request.params.update(rapidjson.loads(raw))
    except:
        raise cp_bad_request('invalid JSON data')
    return


def get_json_payload(force_json=False):
    ct = cherrypy.request.headers.get('Content-Type')
    if ct == 'application/msgpack' or ct == 'application/x-msgpack':
        g.set('ct_format', CT_MSGPACK)
        cl = int(cherrypy.request.headers.get('Content-Length'))
        raw = cherrypy.request.body.read(cl)
        decoder = msgpack_loads
    elif force_json or ct == 'application/json':
        g.set('ct_format', CT_JSON)
        cl = int(cherrypy.request.headers.get('Content-Length'))
        raw = cherrypy.request.body.read(cl).decode()
        decoder = rapidjson.loads
    elif 'X-JSON' in cherrypy.request.headers:
        g.set('ct_format', CT_JSON)
        raw = cherrypy.request.headers.get('X-JSON')
        decoder = rapidjson.loads
    else:
        return None
    return decoder(raw) if raw else None


def cp_jsonrpc_pre():
    r = cherrypy.serving.request
    if r.method == 'GET':
        try:
            data = {
                'jsonrpc': '2.0',
                'method': r.params.get('m'),
                'params': rapidjson.loads(r.params.get('p'))
            }
            i = r.params.get('i')
            try:
                i = int(i)
            except:
                pass
            if i:
                data['id'] = i
        except:
            eva.core.log_traceback()
            raise cp_bad_request('invalid JSON data')
    elif r.method == 'POST':
        try:
            data = get_json_payload(force_json=True)
        except:
            eva.core.log_traceback()
            raise cp_bad_request('invalid JSON data')
        if not data:
            logging.debug('no JSON data provided')
            raise cp_bad_request('no JSON data provided')
    else:
        raise cp_api_405()
    r.params['p'] = data


def cp_nocache():
    headers = cherrypy.serving.response.headers
    headers['Cache-Control'] = ('no-cache, no-store, must-revalidate, '
                                'post-check=0, pre-check=0')
    headers['Pragma'] = 'no-cache'
    headers['Expires'] = '0'


def log_d(f):
    """
    API method decorator to log API call as DEBUG
    """

    @wraps(f)
    def do(self, *args, **kwargs):
        self._log_api_call(f,
                           kwargs,
                           logging.debug,
                           self._fp_hide_in_log,
                           debug=True)
        return f(self, *args, **kwargs)

    return do


def notify_plugins(f):
    """
    API method decorator to notify plugins about the API call
    """

    @wraps(f)
    def do(self, *args, **kwargs):
        if plugins_event_apicall(f, kwargs) is False:
            return False
        else:
            return f(self, *args, **kwargs)

    return do


def log_i(f):
    """
    API method decorator to log API call as INFO
    """

    @wraps(f)
    def do(self, *args, **kwargs):
        self._log_api_call(f, kwargs, logging.info, self._fp_hide_in_log)
        return f(self, *args, **kwargs)

    return do


def log_w(f):
    """
    API method decorator to log API call as WARNING
    """

    @wraps(f)
    def do(self, *args, **kwargs):
        self._log_api_call(f, kwargs, logging.warning, self._fp_hide_in_log)
        return f(self, *args, **kwargs)

    return do


class API:

    def __init__(self):
        self._fp_hide_in_log = {}
        self._log_api_call = API_Logger()


class APIX(API):
    """
    API blueprint extension class
    """
    pass


class GenericAPI(API):

    @staticmethod
    def _process_action_result(a):
        if not a:
            raise ResourceNotFound('item found, option')
        if a.is_status_dead():
            raise FunctionFailed('{} is dead'.format(a.uuid))
        return a.serialize()

    @staticmethod
    def _get_timezone(z):
        if z:
            import pytz
            try:
                return pytz.timezone(z)
            except:
                raise FunctionFailed(f'Invalid time zone: {z}')
        else:
            return None

    def _get_state_history(self,
                           k=None,
                           a=None,
                           i=None,
                           s=None,
                           e=None,
                           l=None,
                           x=None,
                           t=None,
                           w=None,
                           g=None,
                           o=None,
                           z=None):
        tz = self._get_timezone(z)
        import eva.item
        if not is_oid(i):
            item = self.controller.get_item(i)
            i = item.oid
        if '+' in i or '#' in i:
            raise InvalidParameter('wildcard oids are not supported')
        if not key_check_master(k, ro_op=True) and (not key_check(
                k, oid=i, ro_op=True)):
            raise ResourceNotFound(i)
        return eva.item.get_state_history(a=a,
                                          oid=i,
                                          t_start=s,
                                          t_end=e,
                                          limit=l,
                                          prop=x,
                                          time_format=t,
                                          fill=w,
                                          fmt=g,
                                          xopts=o,
                                          tz=tz)

    def _result(self, k, u, i, g, s, rtp):
        import eva.item
        if u:
            a = self.controller.Q.history_get(u)
            if not a or not key_check(k, a.item, ro_op=True):
                raise ResourceNotFound
            return a.serialize()
        else:
            result = []
            if i:
                item_id = oid_to_id(i, rtp)
                if item_id is None:
                    raise ResourceNotFound
                ar = None
                item = self.controller.get_item(rtp + ':' + item_id)
                if not key_check(k, item, ro_op=True):
                    raise ResourceNotFound
                if item_id.find('/') > -1:
                    if item_id in self.controller.Q.actions_by_item_full_id:
                        ar = self.controller.Q.actions_by_item_full_id[item_id]
                else:
                    if item_id in self.controller.Q.actions_by_item_id:
                        ar = self.controller.Q.actions_by_item_id[item_id]
                if ar is None:
                    return []
            else:
                ar = self.controller.Q.actions
            for a in ar:
                if not key_check(k, a.item, ro_op=True):
                    continue
                if g and \
                        not eva.item.item_match(a.item, [], [ g ]):
                    continue
                if (s == 'Q' or s =='queued') and \
                        not a.is_status_queued():
                    continue
                elif (s == 'R' or s == 'running') and \
                        not a.is_status_running():
                    continue
                elif (s == 'F' or s == 'finished') and \
                        not a.is_finished():
                    continue
                result.append(a.serialize())
            return result

    @staticmethod
    def _set_prop(item, p=None, v=None, save=False):
        for prop, value in v.items() if isinstance(v, dict) and not p else {
                p: v
        }.items():
            if not item.set_prop(prop, value, False):
                raise FunctionFailed('{}.{} = {} unable to set'.format(
                    item.oid, prop, value))
        if save:
            item.save()
        return True

    def _nofp_log(self, func, params):
        fp = self._fp_hide_in_log.setdefault(func, [])
        fp += params if isinstance(params, list) else [params]

    @log_d
    @notify_plugins
    def test(self, **kwargs):
        """
        test API/key and get system info

        Test can be executed with any valid API key of the controller the
        function is called to.

        For SFA, the result section "connected" contains connection status of
        remote controllers. The API key must have an access either to "uc" and
        "lm" groups ("remote_uc:uc" and "remote_lm:lm") or to particular
        controller oids.

        Args:
            k: any valid API key

        Returns:
            JSON dict with system info and current API key permissions (for
            masterkey only { "master": true } is returned)
        """
        k = parse_function_params(kwargs, 'k', 'S')
        aci = g.get('aci').copy()
        for f in ['id', 'token']:
            try:
                del aci[f]
            except KeyError:
                pass
        result = {
            'acl': apikey.serialized_acl(k),
            'aci': aci,
            'system': eva.core.config.system_name,
            'controller': eva.core.config.controller_name,
            'time': time.time(),
            'log_level': eva.core.config.default_log_level_id,
            'version': eva.core.version,
            'product_name': eva.core.product.name,
            'product_code': eva.core.product.code,
            'product_build': eva.core.product.build,
            'uptime': int(time.time() - eva.core.start_time)
        }
        if eva.core.config.enterprise_layout is not None:
            result['layout'] = 'enterprise' if \
                    eva.core.config.enterprise_layout else 'simple'
        try:
            if key_check_master(k):
                result['file_management'] = \
                        eva.sysapi.config.api_file_management_allowed
        except TokenRestricted:
            pass
        try:
            if key_check(k, sysfunc=True):
                result['debug'] = eva.core.config.debug
                result['setup_mode'] = eva.core.is_setup_mode()
                result['db_update'] = eva.core.config.db_update
                result['polldelay'] = eva.core.config.polldelay
                result['threads'] = len(threading.enumerate())
                result['boot_id'] = eva.core._flags.boot_id
                if eva.core.config.development:
                    result['development'] = True
                if eva.benchmark.enabled and eva.benchmark.intervals:
                    intervals = []
                    for k, v in eva.benchmark.intervals.items():
                        s = v.get('s')
                        e = v.get('e')
                        if s is None or e is None:
                            continue
                        intervals.append(e - s)
                    try:
                        result['benchmark_crt'] = sum(intervals) / float(
                            len(intervals))
                    except Exception as e:
                        logging.error('Unable to calculate CRT: {}'.format(e))
                        eva.core.log_traceback()
                        result['benchmark_crt'] = -1
        except TokenRestricted:
            pass
        return True, result

    @log_d
    @notify_plugins
    def state_history(self, **kwargs):
        """
        get item state history

        State history of one :doc:`item</items>` or several items of the
        specified type can be obtained using **state_history** command.

        If master key is used, the method attempts to get stored state for an
        item even if it doesn't present currently in system.

        The method can return state log for disconnected items as well.

        Args:
            k:
            a: history notifier id (default: db_1)
            .i: item oids or full ids, list or comma separated

        Optional:
            s: start time (timestamp or ISO or e.g. 1D for -1 day)
            e: end time (timestamp or ISO or e.g. 1D for -1 day)
            l: records limit (doesn't work with "w")
            x: state prop ("status" or "value")
            t: time format ("iso" or "raw" for unix timestamp, default is "raw")
            z: Time zone (pytz, e.g. UTC or Europe/Prague)
            w: fill frame with the interval (e.g. "1T" - 1 min, "2H" - 2 hours
                etc.), start time is required, set to 1D if not specified
            g: output format ("list", "dict" or "chart", default is "list")
            c: options for chart (dict or comma separated)
            o: extra options for notifier data request

        Returns:
            history data in specified format or chart image.

        For chart, JSON RPC gets reply with "content_type" and "data" fields,
        where content is image content type. If PNG image format is selected,
        data is base64-encoded.

        Options for chart (all are optional):

            * type: chart type (line or bar, default is line)

            * tf: chart time format

            * out: output format (svg, png, default is svg),

            * style: chart style (without "Style" suffix, e.g. Dark)

            * other options:
                http://pygal.org/en/stable/documentation/configuration/chart.html#options
                (use range_min, range_max for range, other are passed as-is)

        If option "w" (fill) is used, number of digits after comma may be
        specified. E.g. 5T:3 will output values with 3 digits after comma.

        Additionally, SI prefix may be specified to convert value to kilos,
        megas etc, e.g. 5T:k:3 - divide value by 1000 and output 3 digits after
        comma. Valid prefixes are: k, M, G, T, P, E, Z, Y.

        If binary prefix is required, it should be followed by "b", e.g.
        5T:Mb:3 - divide value by 2^20 and output 3 digits after comma.
        """
        k, a, i, s, e, l, x, t, w, g, c, o, z = parse_function_params(
            kwargs, 'kaiselxtwgcoz', '.sr..issss...')

        if o:
            if isinstance(o, dict):
                pass
            elif isinstance(o, str):
                o = dict_from_str(o)
            else:
                raise InvalidParameter('o must be dict or str')

        def format_result(result, prop, c=None):
            if c is None:
                return result
            if not prop:
                prop = 'value'
            line = c.get('type', 'line')
            fmt = c.get('out', 'svg')
            chart_t = c.get('tf', '%Y-%m-%d %H:%M')
            range_min = c.get('range_min')
            range_max = c.get('range_max')
            style = c.get('style')
            for x in ['type', 'out', 'tf', 'range_min', 'range_max', 'style']:
                try:
                    del c[x]
                except:
                    pass
            for x in [
                    'explicit_size', 'show_x_labels', 'show_y_labels',
                    'show_minor_x_labels', 'show_minor_y_labels', 'show_legend',
                    'legend_at_bottom', 'include_x_axis', 'inverse_y_axis',
                    'logarithmic', 'print_values', 'dynamic_print_values',
                    'print_zeroes', 'print_labels', 'human_readable', 'stroke',
                    'fill', 'show_only_major_dots', 'show_x_guides',
                    'show_y_guides', 'pretty_print', 'disable_xml_declaration',
                    'no_prefix', 'strict', 'missing_value_fill_truncation'
            ]:
                if x in c:
                    c[x] = val_to_boolean(c[x])
            import pygal
            import datetime
            if line == 'line':
                chartfunc = pygal.Line
            elif line == 'bar':
                chartfunc = pygal.Bar
            else:
                raise InvalidParameter('Chart type should be in: line, bar')
            if style:
                try:
                    pstyles = importlib.import_module('pygal.style')
                    style = getattr(pstyles, '{}Style'.format(style))
                    c['style'] = style
                except:
                    raise ResourceNotFound('chart style: {}'.format(style))
            chart = chartfunc(**c)
            if range_min is not None and range_max is not None:
                chart.range = (range_min, range_max)
            chart.x_labels = map(
                lambda t: datetime.datetime.fromtimestamp(t).strftime(chart_t),
                result['t'])
            if prop != 'multiple':
                chart.add(None, result[prop] if prop else result['value'])
            else:
                del result['t']
                for i, v in result.items():
                    item = self.controller.get_item(i.rsplit('/', 1)[0])
                    chart.add(
                        item.description if item and item.description else i, v)
            result = chart.render()
            if fmt == 'svg':
                return result, 'image/svg+xml'
            elif fmt == 'png':
                import cairosvg
                return cairosvg.svg2png(bytestring=result), 'image/png'
            else:
                raise InvalidParameter(
                    'chart output format must be in: svg, png')

        if g and g not in ['list', 'dict', 'chart']:
            raise InvalidParameter(
                'output format should be in: list, dict or chart')
        if g == 'chart':
            if c:
                try:
                    c = dict_from_str(c)
                    if not isinstance(c, dict):
                        raise Exception
                except:
                    raise InvalidParameter('chart options are invalid')
            else:
                c = {}
            t = None
            g = 'list'
        else:
            c = None
        if (isinstance(i, str) and i and i.find(',') != -1) or \
                isinstance(i, list):
            if not w:
                raise InvalidParameter(
                    '"w" is required to process multiple items')
            if isinstance(i, str):
                items = i.split(',')
            else:
                items = i
            if not g or g == 'list':
                result = {}
            else:
                raise InvalidParameter(
                    'format should be list only to process multiple items')
            result_keys = set()
            for i in items:
                r = self._get_state_history(k=k,
                                            a=a,
                                            i=i,
                                            s=s,
                                            e=e,
                                            l=l,
                                            x=x,
                                            t=t,
                                            w=w,
                                            g=None,
                                            o=o,
                                            z=z)
                process_status = 'status' in r
                process_value = 'value' in r
                for zz, tt in enumerate(r['t']):
                    if tt not in result:
                        result[tt] = {}
                    if process_status:
                        rk = i + '/status'
                        result[tt][rk] = r['status'][zz]
                        result_keys.add(rk)
                    if process_value:
                        rk = i + '/value'
                        result[tt][rk] = r['value'][zz]
                        result_keys.add(rk)
            if not result_keys:
                return {}
            merged_result = {'t': []}
            for tt in sorted(result):
                merged_result['t'].append(tt)
                for rk in result_keys:
                    merged_result.setdefault(rk, []).append(result[tt].get(rk))
            return format_result(merged_result, 'multiple', c)
        else:
            result = self._get_state_history(k=k,
                                             a=a,
                                             i=i,
                                             s=s,
                                             e=e,
                                             l=l,
                                             x=x,
                                             t=t,
                                             w=w,
                                             g=g,
                                             o=o,
                                             z=z)
            return format_result(result, x, c)

    @log_d
    @notify_plugins
    def state_log(self, **kwargs):
        """
        get item state log

        State log of a single :doc:`item</items>` or group of the specified
        type can be obtained using **state_log** command.

        note: only SQL notifiers are supported

        Difference from state_history method:

        * state_log doesn't optimize data to be displayed on charts
        * the data is returned from a database as-is
        * a single item OID or OID mask (e.g. sensor:env/#) can be specified

        note: the method supports MQTT-style masks but only masks with
        wildcard-ending, like "type:group/subgroup/#" are supported.

        The method can return state log for disconnected items as well.

        For wildcard fetching, API key should have an access to the whole
        chosen group.

        note: record limit means the limit for records, fetched from the
        database, but repeating state records are automatically grouped and the
        actual number of returned records can be lower than requested.

        Args:
            k:
            a: history notifier id (default: db_1)
            .i: item oid or oid mask (type:group/subgroup/#)

        Optional:
            s: start time (timestamp or ISO or e.g. 1D for -1 day)
            e: end time (timestamp or ISO or e.g. 1D for -1 day)
            l: records limit (doesn't work with "w")
            t: time format ("iso" or "raw" for unix timestamp, default is "raw")
            z: Time zone (pytz, e.g. UTC or Europe/Prague)
            o: extra options for notifier data request

        Returns:
            state log records (list)
        """
        k, a, i, s, e, l, t, o, z = parse_function_params(
            kwargs, 'kaiseltoz', '.sS..is..')
        if ('+' in (i[:-2] if i.endswith('/+') else i).replace(
                ':+/', '').replace(
                    '/+/', '')) or (i.count('#') > 1 or
                                    ('#' in i and not i.endswith('/#') and
                                     not i.endswith(':#'))):
            raise InvalidParameter(f'i has oid mask "{i}", '
                                   f'which is not supported')
        # as notifier methods can be sql-unsafe - avoid injections
        for _s in ['*', '"', '\'', ' ', ';']:
            if _s in i:
                raise InvalidParameter(f'i contains invalid symbols')
        if o:
            if isinstance(o, dict):
                pass
            elif isinstance(o, str):
                o = dict_from_str(o)
            else:
                raise InvalidParameter('o must be dict or str')
        if not key_check_master(k, ro_op=True) and not key_check(
                k, oid=i, ro_op=True):
            raise ResourceNotFound
        return eva.item.get_state_log(a=a,
                                      oid=i,
                                      t_start=s,
                                      t_end=e,
                                      limit=l,
                                      time_format=t,
                                      xopts=o,
                                      tz=self._get_timezone(z))

    # return version for embedded hardware
    @log_d
    @notify_plugins
    def info(self, **kwargs):
        return {
            'platfrom': 'eva',
            'product': eva.core.product.code,
            'version': eva.core.version,
            'system': eva.core.config.system_name,
        }

    @log_d
    @notify_plugins
    def set_token_readonly(self, **kwargs):
        """
        Set token read-only

        Applies read-only mode for token. In read-only mode, only read-only
        functions work, others return result_token_restricted(15).

        The method works for token-authenticated API calls only.

        To exit read-only mode, user must either re-login or, to keep the
        current token, call "login" API method with both token and user
        credentials.
        """
        if get_aci('auth') != 'token':
            raise FunctionFailed('user is not logged in')
        token_id = get_aci('token')
        t = tokens.get_token(token_id)
        # if apikey.check_master(apikey.key_by_id(t['ki'])):
        # raise MethodNotImplemented('not implemented for master keys')
        if not t:
            raise FunctionFailed
        tokens.set_token_mode(token_id, tokens.TOKEN_MODE_RO)
        return True

    @log_i
    @notify_plugins
    def login(self, **kwargs):
        """
        log in and get authentication token

        Obtains authentication :doc:`token</api_tokens>` which can be used in
        API calls instead of API key.

        If both **k** and **u** args are absent, but API method is called with
        HTTP request, which contain HTTP header for basic authorization, the
        function will try to parse it and log in user with credentials
        provided.

        If authentication token is specified, the function will check it and
        return token information if it is valid.

        If both token and credentials (user or API key) are specified, the
        function will return the token to normal mode.

        Args:
            k: valid API key or
            u: user login
            p: user password
            a: authentication token

        Returns:
            A dict, containing API key ID and authentication token
        """
        if not tokens.is_enabled():
            raise FunctionFailed('Session tokens are disabled')
        k, u, p, a = parse_function_params(kwargs, 'kupa', '.sss')
        if not u and not k and not a and hasattr(
                cherrypy, 'serving') and hasattr(cherrypy.serving, 'request'):
            auth_header = cherrypy.serving.request.headers.get('authorization')
            if auth_header:
                try:
                    scheme, params = auth_header.split(' ', 1)
                    if scheme.lower() == 'basic':
                        u, p = base64.b64decode(params).decode().split(':', 1)
                        u = u.strip()
                except Exception as e:
                    eva.core.log_traceback()
                    raise FunctionFailed(e)
            elif cherrypy.request.headers.get('User-Agent',
                                              '').startswith('evaHI '):
                raise EvaHIAuthenticationRequired
        if a:
            t = tokens.get_token(a)
            if t:
                if k is not None or u is not None:
                    if k is not None:
                        ki = apikey.key_id(k)
                        if ki != t['ki']:
                            raise AccessDenied
                    elif u is not None:
                        ki, _ = eva.users.authenticate(u, p)
                        if ki != t['ki']:
                            raise AccessDenied
                    tokens.set_token_mode(a, tokens.TOKEN_MODE_NORMAL)
                result = {
                    'key': t['ki'],
                    'token': a,
                    'mode': tokens.TOKEN_MODE_NAMES[t['m']]
                }
                if t['u'] is not None:
                    result['user'] = t['u']
                return result
            else:
                if u or k:
                    raise AccessDenied
                # try basic auth or evaHI login
                if hasattr(cherrypy, 'serving') and hasattr(
                        cherrypy.serving, 'request'):
                    auth_header = cherrypy.serving.request.headers.get(
                        'authorization')
                    if auth_header or cherrypy.request.headers.get(
                            'User-Agent', '').startswith('evaHI '):
                        return self.login()
                else:
                    raise AccessDenied('Invalid token')
        if not u and k:
            if not key_check(k, ip=http_real_ip()):
                raise AccessDenied
            ki = apikey.key_id(k)
            token = tokens.append_token(ki)
            if not token:
                raise FunctionFailed('token generation error')
            return {'key': ki, 'token': token}
        key, utp = eva.users.authenticate(u, p)
        if not key_check(apikey.key_by_id(key), ip=http_real_ip()):
            raise AccessDenied
        token = tokens.append_token(key, u, utp)
        if not token:
            raise FunctionFailed('token generation error')
        if eva.core.config.keep_api_log:
            call_id = get_aci('id')
            if call_id:
                eva.users.api_log_update(call_id, ki=key, u=u, utp=utp)
        return {'user': u, 'key': key, 'token': token}

    @log_i
    @notify_plugins
    def logout(self, **kwargs):
        """
        log out and purge authentication token

        Purges authentication :doc:`token</api_tokens>`

        Args:
            k: valid token
        """
        if not tokens.is_enabled():
            raise FunctionFailed('Session tokens are disabled')
        k = get_aci('token')
        if k:
            tokens.remove_token(k)
        return True


class GenericCloudAPI(object):

    @log_w
    @api_need_master
    @notify_plugins
    def remove_controller(self, **kwargs):
        """
        disconnect controller

        Args:
            k: .master
            .i: controller id
        """
        i = parse_api_params(kwargs, 'i', 'S')
        return self.controller.remove_controller(i)

    @log_i
    @api_need_master
    @notify_plugins
    def list_controller_props(self, **kwargs):
        """
        get controller connection parameters

        Args:
            k: .master
            .i: controller id
        """
        i = parse_api_params(kwargs, 'i', 'S')
        return self.controller.get_controller(i).serialize(props=True)

    @log_i
    @api_need_master
    @notify_plugins
    def get_controller(self, **kwargs):
        """
        get connected controller information

        Args:
            k: .master
            .i: controller id
        """
        i = parse_api_params(kwargs, 'i', 'S')
        return self.controller.get_controller(i).serialize(info=True)

    @log_i
    @api_need_master
    @notify_plugins
    def test_controller(self, **kwargs):
        """
        test connection to remote controller

        Args:
            k: .master
            .i: controller id
        """
        i = parse_api_params(kwargs, 'i', 'S')
        c = self.controller.get_controller(i)
        result = c.test()
        if result:
            return True
        else:
            raise FunctionFailed('{}: test failed'.format(c.full_id))

    @log_i
    @api_need_master
    @notify_plugins
    def set_controller_prop(self, **kwargs):
        """
        set controller connection parameters

        Args:
            k: .master
            .i: controller id
            .p: property name (or empty for batch set)
        
        Optional:
            .v: propery value (or dict for batch set)
            save: save configuration after successful call
        """
        i, p, v, save = parse_api_params(kwargs, 'ipvS', 's..b')
        controller = self.controller.get_controller(i)
        if not p and not isinstance(v, dict):
            raise InvalidParameter('property not specified')
        if is_oid(i):
            t, i = parse_oid(i)
        controller = self.controller.get_controller(i)
        if not controller or (is_oid(i) and controller and
                              controller.item_type != t):
            raise ResourceNotFound
        return self._set_prop(controller, p, v, save)

    @log_i
    @api_need_master
    @notify_plugins
    def enable_controller(self, **kwargs):
        """
        enable connected controller

        Args:
            k: .master
            .i: controller id

        Optional:
            save: save configuration after successful call
        """
        i, save = parse_api_params(kwargs, 'iS', 'Sb')
        controller = self.controller.get_controller(i)
        return controller.set_prop('enabled', True, save)

    @log_i
    @api_need_master
    @notify_plugins
    def disable_controller(self, **kwargs):
        """
        disable connected controller

        Args:
            k: .master
            .i: controller id

        Optional:
            save: save configuration after successful call
        """
        i, save = parse_api_params(kwargs, 'iS', 'Sb')
        controller = self.controller.get_controller(i)
        return controller.set_prop('enabled', False, save)


def jsonify(value):
    response = cherrypy.serving.response
    if isinstance(value, bytes):
        return value
    if value or value == 0 or isinstance(value, list):
        fmt = g.get('ct_format')
        if fmt == CT_MSGPACK:
            response.headers['Content-Type'] = 'application/msgpack'
            return apiclient.pack_msgpack(value)
        elif fmt == CT_JSON:
            response.headers['Content-Type'] = 'application/json'
            return format_json(
                value, minimal=not eva.core.config.development).encode('utf-8')
    else:
        try:
            del response.headers['Content-Type']
        except:
            pass
        if not response.status or response.status == 200:
            response.status = 204
        return None


def cp_jsonrpc_handler(*args, **kwargs):
    try:
        response = cherrypy.serving.response
        if response.status == 401:
            return
        value = cherrypy.serving.request._json_inner_handler(*args, **kwargs)
        if value is None:
            cherrypy.serving.response.status = 202
            return
        else:
            fmt = g.get('ct_format')
            if fmt == CT_MSGPACK:
                response.headers['Content-Type'] = 'application/msgpack'
                return apiclient.pack_msgpack(value)
            elif fmt == CT_JSON:
                response.headers['Content-Type'] = 'application/json'
            return format_json(
                value, minimal=not eva.core.config.development).encode('utf-8')
    except:
        eva.core.log_traceback()
        raise


def _http_client_key(_k=None, from_cookie=False):
    if _k:
        return _k
    k = cherrypy.request.headers.get('X-Auth-Key')
    if k:
        return k
    if 'k' in cherrypy.serving.request.params:
        k = cherrypy.serving.request.params['k']
    if k:
        return k
    if from_cookie:
        k = cherrypy.serving.request.cookie.get('auth')
        if k:
            k = k.value
        if k and not k.startswith('token:'):
            k = None
    if k:
        return k
    k = eva.apikey.key_by_ip_address(http_real_ip())
    return k


def key_token_parse(k, _aci=False):
    token = tokens.get_token(k)
    if not token:
        raise AccessDenied('Invalid token')
    if _aci:
        set_aci('auth', 'token')
        set_aci('token', k)
        set_aci('token_mode', tokens.TOKEN_MODE_NAMES[token['m']])
        set_aci('u', token['u'])
        set_aci('utp', token['utp'])
    return apikey.key_by_id(token['ki'])


def cp_client_key(k=None, from_cookie=False, _aci=False):
    k = _http_client_key(k, from_cookie=from_cookie)
    if k and k.startswith('token:'):
        try:
            return key_token_parse(k, _aci=_aci)
        except AccessDenied as e:
            raise cp_forbidden_key(e)
    else:
        return k


class GenericHTTP_API_abstract:

    def __init__(self):
        self.__exposed = {}
        self._log_api_call = HTTP_API_Logger()

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

    def _expose(self, f, alias=None):
        if callable(f):
            self.__exposed[f.__name__ if not alias else alias] = f
        elif isinstance(f, str):
            self.__exposed[f if not alias else alias] = getattr(
                self, f.replace('.', '_'))
        elif isinstance(f, list):
            for func in f:
                self._expose(func)

    def _get_api_function(self, f):
        if isinstance(f, list) or isinstance(f, tuple):
            f = '.'.join(f)
        return self.__exposed.get(f)

    def expose_api_methods(self, api_id, set_api_uri=True):
        try:
            data = rapidjson.loads(
                open('{}/eva/apidata/{}_data.json'.format(
                    eva.core.dir_lib, api_id)).read())
            self._expose(data['functions'])
            for f, a in data['aliases'].items():
                self._expose(f, a)
            if set_api_uri:
                self.api_uri = data['uri']
            with _exposed_lock:
                for fn, x in _exposed.items():
                    f = x[0]
                    s = x[1]
                    if (s and data['uri'] == '/sys-api') or (
                            not s and data['uri'] != '/sys-api'):
                        self._expose(f, fn)
            eva.core.update_corescript_globals(self.__exposed)
        except:
            eva.core.critical()


class JSON_RPC_API_abstract(GenericHTTP_API_abstract):

    api_uri = '/jrpc'

    exposed = True

    def __init__(self, api_uri=None):
        super().__init__()
        self._cp_config = api_cp_config.copy()
        if api_uri:
            self.api_uri = api_uri
        self._cp_config['tools.jsonrpc_pre.on'] = True
        self._cp_config['tools.json_out.on'] = True,
        self._cp_config['tools.json_out.handler'] = cp_jsonrpc_handler

    def __call__(self, **kwargs):

        def format_error(code, msg):
            return {
                'jsonrpc': '2.0',
                'error': {
                    'code': code,
                    'message': str(msg)
                }
            }

        payload = kwargs.get('p', cherrypy.serving.request.params.get('p'))
        result = []
        for pp in payload if isinstance(payload, list) else [payload]:
            if not isinstance(pp, dict) or not pp:
                raise cp_bad_request('Invalid JSON RPC payload')
            if pp.get('jsonrpc') != '2.0':
                raise cp_api_error('Unsupported RPC protocol')
            req_id = pp.get('id')
            method = pp.get('method')
            p = pp.get('params')
            try:
                # fix for some clients
                if isinstance(p, list):
                    p = p[0]
                if p is None:
                    p = {}
                elif not isinstance(p, dict):
                    raise InvalidParameter(
                        f'params - dict expected, {type(p).__name__} found')
                if not method:
                    raise FunctionFailed('API method not defined')
                if method.startswith('cs_'):
                    eva.core.exec_corescripts(event=SimpleNamespace(
                        type=eva.core.CS_EVENT_RPC, topic=method[3:], data=p))
                    res = True
                else:
                    f = self._get_api_function(method)
                    if not f:
                        raise MethodNotFound
                    k = p.get('k')
                    ip = http_real_ip()
                    if method != 'login':
                        if not k:
                            k = eva.apikey.key_by_ip_address(ip)
                            p['k'] = k
                        elif k.startswith('token:'):
                            k = key_token_parse(k, _aci=True)
                            p['k'] = k
                        if not key_check(k=k, ip=ip, ro_op=True):
                            self._log_api_call(f, p, logging.info,
                                               self._fp_hide_in_log)
                            raise AccessDenied
                    res = f(**p)
                if isinstance(res, tuple):
                    res, data = res
                    if isinstance(res, bytes):
                        try:
                            if data != 'image/svg+xml' and not data.startswith(
                                    'text/'):
                                raise Exception
                            res = {
                                'content_type': data,
                                'data': res.decode('utf-8')
                            }
                        except:
                            res = {
                                'content_type':
                                    data,
                                'data':
                                    base64.b64encode(res).decode()
                                    if g.get('ct_format') == CT_JSON else res
                            }
                else:
                    data = None
                if res is True:
                    res = {'ok': True}
                    if isinstance(data, dict):
                        res.update(data)
                elif res is False:
                    raise FunctionFailed
                elif res is None:
                    raise ResourceNotFound
                r = {'jsonrpc': '2.0', 'result': res, 'id': req_id}
                log_api_call_result('OK')
            except ResourceNotFound as e:
                log_api_call_result('ResourceNotFound')
                eva.core.log_traceback()
                r = format_error(apiclient.result_not_found, e)
            except AccessDenied as e:
                log_api_call_result('AccessDenied')
                eva.core.log_traceback()
                r = format_error(apiclient.result_forbidden, e)
            except TokenRestricted as e:
                log_api_call_result('TokenRestricted')
                r = format_error(apiclient.result_token_restricted,
                                 'token restricted')
            except MethodNotFound as e:
                log_api_call_result('MethodNotFound')
                eva.core.log_traceback()
                r = format_error(apiclient.result_func_unknown, e)
            except InvalidParameter as e:
                log_api_call_result('InvalidParameter')
                eva.core.log_traceback()
                r = format_error(apiclient.result_invalid_params, e)
            except MethodNotImplemented as e:
                log_api_call_result('MethodNotImplemented')
                r = format_error(apiclient.result_not_implemented, e)
            except ResourceAlreadyExists as e:
                log_api_call_result('ResourceAlreadyExists')
                eva.core.log_traceback()
                r = format_error(apiclient.result_already_exists, e)
            except ResourceBusy as e:
                log_api_call_result('ResourceBusy')
                eva.core.log_traceback()
                r = format_error(apiclient.result_busy, e)
            except EvaHIAuthenticationRequired:
                cherrypy.serving.response.status = 401
                cherrypy.serving.response.headers[
                    'WWW-Authenticate'] = 'Basic realm="?"'
                return ''
            except Exception as e:
                log_api_call_result('FunctionFailed')
                eva.core.log_traceback()
                r = format_error(apiclient.result_func_failed, e)
            if req_id is not None:
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
        GenericAPI.__init__(self)
        GenericHTTP_API_abstract.__init__(self)
        self._cp_config = api_cp_config.copy()
        self._cp_config['tools.auth.on'] = True
        self._cp_config['tools.json_pre.on'] = True

    def wrap_exposed(self):
        super().wrap_exposed(cp_api_function)


def controller_discovery_handler(notifier_id, controller_id, location,
                                 **kwargs):
    logging.info(
        'MQTT discovery handler got info from %s' % notifier_id + \
        ' about %s, but no real handler registered' % controller_id
    )


def mqtt_api_handler(notifier_id, data, callback):
    try:
        if isinstance(data, str):
            if not data or data[0] != '|':
                raise FunctionFailed('invalid text packet data')
            pfx, api_key_id, d = data.split('|', 2)
            ct = CT_JSON
            ce = apikey.key_ce(api_key_id)
            if ce is None:
                raise FunctionFailed('invalid key')
            try:
                d = ce.decrypt(d.encode()).decode()
            except:
                logging.warning(
                    'MQTT API: invalid API key in encrypted packet from ' +
                    notifier_id)
                raise
            call_id, payload = d.split('|', 1)
            try:
                payload = rapidjson.loads(payload)
            except:
                eva.core.log_traceback()
                raise FunctionFailed('Invalid JSON data')
        else:
            if not data or data[0] != 0:
                raise FunctionFailed('invalid binary packet data')
            pfx, api_key_id, d = data.split(b'\x00', 2)
            api_key_id = api_key_id[1:].decode()
            ct = CT_MSGPACK
            private_key = apikey.key_private512(api_key_id)
            if private_key is None:
                raise FunctionFailed('invalid key')
            d = eva.crypto.decrypt(d, private_key, key_is_hash=True)
            rid = d[:16]
            call_id = rid.hex()
            try:
                payload = msgpack_loads(d[16:])
            except:
                logging.warning('MQTT API: invalid JSON data or API key from ' +
                                notifier_id)
                raise
        init_api_call(gw='mqtt:' + notifier_id, http_call=False)
        try:
            response = jrpc(p=payload)
        except:
            eva.core.log_traceback()
            callback(call_id, '500|')
            raise FunctionFailed('API error')
        if ct == CT_MSGPACK:
            packer = msgpack.Packer(use_bin_type=True)
            response = eva.crypto.encrypt(packer.pack(response),
                                          private_key,
                                          key_is_hash=True)
            callback(call_id, b'\x00\xC8' + response)
        else:
            response = ce.encrypt(rapidjson.dumps(response).encode())
            callback(call_id, '200|' + response.decode())
    except Exception as e:
        logging.warning('MQTT API: API call failed from {}: {}'.format(
            notifier_id, e))
        eva.core.log_traceback()
    finally:
        clear_api_call()


def start():
    if not config.host:
        return False
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
    else:
        config.ssl_force_redirect = False
    if not eva.core.config.development:
        cherrypy.config.update({'environment': 'production'})
        cherrypy.log.access_log.propagate = False
        cherrypy.log.error_log.propagate = False
    else:
        cherrypy.config.update({'global': {'engine.autoreload.on': False}})
    cherrypy.engine.start()


def cp_autojsonrpc():
    r = cherrypy.serving.request
    if r.method == 'POST' and r.path_info == '/' and jrpc is not None:
        init_api_call()
        cp_jsonrpc_pre()
        r._json_inner_handler = jrpc
        r.handler = cp_jsonrpc_handler


@eva.core.stop
def stop():
    cherrypy.engine.exit()


def init():
    cherrypy.tools.init_call = cherrypy.Tool('before_handler',
                                             init_api_call,
                                             priority=5)
    cherrypy.tools.json_pre = cherrypy.Tool('before_handler',
                                            cp_json_pre,
                                            priority=10)
    cherrypy.tools.jsonrpc_pre = cherrypy.Tool('before_handler',
                                               cp_jsonrpc_pre,
                                               priority=10)
    cherrypy.tools.auth = cherrypy.Tool('before_handler',
                                        cp_check_perm,
                                        priority=60)
    cherrypy.tools.nocache = cherrypy.Tool('before_finalize',
                                           cp_nocache,
                                           priority=10)
    cherrypy.tools.autojsonrpc = cherrypy.Tool('before_handler',
                                               cp_autojsonrpc,
                                               priority=10)


def jsonify_error(value):
    if not cherrypy.serving.response.body:
        return format_json(
            {
                '_error': value
            }, minimal=not eva.core.config.development).encode('utf-8')


def error_page_400(*args, **kwargs):
    return jsonify_error(kwargs.get('message', 'Invalid function params'))


def error_page_403(*args, **kwargs):
    return jsonify_error(kwargs.get('message', 'Forbidden'))


def error_page_405(*args, **kwargs):
    return jsonify_error(kwargs.get('message', 'Method not allowed'))


def error_page_404(*args, **kwargs):
    return jsonify_error(kwargs.get('message', 'Not found'))


def error_page_409(*args, **kwargs):
    return jsonify_error(kwargs.get('message', 'Resource conflict'))


def error_page_500(*args, **kwargs):
    return jsonify_error(kwargs.get('message', 'API function error'))


api_cp_config = {
    'tools.init_call.on': True,
    'tools.nocache.on': True,
    'tools.trailing_slash.on': False,
    'error_page.400': error_page_400,
    'error_page.403': error_page_403,
    'error_page.404': error_page_404,
    'error_page.405': error_page_405,
    'error_page.409': error_page_409,
    'error_page.500': error_page_500
}

jrpc = None
api = None
