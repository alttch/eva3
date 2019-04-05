__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.1"

import cherrypy
import logging
import threading
import time
import math
import jsonpickle
import eva.tokens as tokens

import eva.core
from eva import apikey

from eva.tools import format_json
from eva.tools import parse_host_port
from eva.tools import parse_function_params
from eva.tools import val_to_boolean
from eva.tools import is_oid
from eva.tools import oid_to_id
from eva.tools import parse_oid

from eva.client import apiclient

from eva.exceptions import FunctionFailed
from eva.exceptions import ResourceNotFound
from eva.exceptions import AccessDenied
from eva.exceptions import ResourceAlreadyExists
from eva.exceptions import ResourceBusy
from eva.exceptions import InvalidParameter

import eva.users
import eva.notify
import eva.benchmark

from pyaltt import g

from functools import wraps

from types import SimpleNamespace

from base64 import b64decode

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
    session_no_prolong=False,
    thread_pool=15,
    ei_enabled=True,
    use_x_real_ip=False)

api_result_accepted = 2


class MethodNotFound(Exception):

    def __str__(self):
        msg = super().__str__()
        return msg if msg else 'API method not found'


def api_need_master(f):

    @wraps(f)
    def do(*args, **kwargs):
        if not eva.apikey.check_master(kwargs.get('k')):
            raise AccessDenied
        return f(*args, **kwargs)

    return do


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
        if ii: ii += '/'
        ii += l
    else:
        ii = None
    save = val_to_boolean(kwargs.get('save'))
    kind = kwargs.get('kind', kind)
    method = kwargs.get('method')
    for_dir = cherrypy.request.path_info.endswith('/')
    if 'k' in kwargs: del kwargs['k']
    if 'save' in kwargs: del kwargs['save']
    if 'kind' in kwargs: del kwargs['kind']
    if 'method' in kwargs: del kwargs['method']
    return k, ii, save, kind, method, for_dir, kwargs


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
            raise cp_bad_request(e)
        except TypeError as e:
            eva.core.log_traceback()
            raise cp_bad_request()
        except ResourceNotFound as e:
            eva.core.log_traceback()
            raise cp_api_404(e)
        except MethodNotFound as e:
            eva.core.log_traceback()
            raise cp_api_405(e)
        except (ResourceAlreadyExists, ResourceBusy) as e:
            eva.core.log_traceback()
            raise cp_api_409(e)
        except AccessDenied as e:
            eva.core.log_traceback()
            raise cp_forbidden_key(e)
        except FunctionFailed as e:
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
        else:
            data = None
        if result is False:
            raise FunctionFailed
        if result is None:
            raise ResourceNotFound
        if (f.__name__ == 'POST' and
                'Location' in cherrypy.serving.response.headers
           ) or f.__name__ == 'PUT':
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
        tokens.expire = config.session_timeout
    except:
        pass
    logging.debug('webapi.session_timeout = %u' % config.session_timeout)
    try:
        config.session_timeout = int(cfg.get('webapi', 'session_timeout'))
        tokens.expire = config.session_timeout
    except:
        pass
    try:
        config.session_no_prolong = (cfg.get('webapi',
                                             'session_no_prolong') == 'yes')
        tokens.prolong_disabled = config.session_no_prolong
    except:
        pass
    logging.debug('webapi.session_no_prolong = %s' % ('yes' \
                                if config.session_no_prolong else 'no'))
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

    def log_api_request(self, func, params, logger, fp_hide):
        msg = 'API request '
        auth = self.get_auth(func, params)
        info = self.prepare_info(func, params, fp_hide)
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

    def __call__(self, func, params, logger, fp_hide):
        self.log_api_request(func.__name__, params.copy(), logger, fp_hide)

    def prepare_info(self, func, p, fp_hide):
        # if not eva.core.config.development:
        if 'k' in p: del p['k']
        if func.startswith('set_') or func.endswith('_set'):
            fp = p.get('p')
            if fp in ['key', 'masterkey', 'password']: p[fp] = '<hidden>'
        fplist = fp_hide.get(func)
        if fplist:
            for fp in fplist:
                if callable(fp):
                    fp(func, p)
                elif fp in p:
                    p[fp] = '<hidden>'
        return p

    def get_auth(self, func, params):
        return apikey.key_id(params.get('k'))


class HTTP_API_Logger(API_Logger):

    def get_auth(self, func, params):
        return http_remote_info(params.get('k'))


def cp_check_perm(api_key=None, path_info=None):
    k = api_key if api_key else cp_client_key()
    path = path_info if path_info is not None else \
            cherrypy.serving.request.path_info
    if k is not None: cherrypy.serving.request.params['k'] = k
    # pass login and info
    if path in ['/login', '/info', '/token']: return
    if apikey.check(k, ip=http_real_ip()): return
    raise cp_forbidden_key()


def http_real_ip(get_gw=False):
    if get_gw and g.has('eva_ics_gw'):
        return 'gateway/' + g.get('eva_ics_gw')
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
            cherrypy.serving.request.params.update(jsonpickle.decode(raw))
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
    except:
        raise cp_bad_request('invalid JSON data')
    if not data:
        raise cp_bad_request('no JSON data provided')
    cherrypy.serving.request.params['p'] = data


def cp_nocache():
    headers = cherrypy.serving.response.headers
    headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    headers['Pragma'] = 'no-cache'
    headers['Expires'] = '0'


def log_d(f):

    @wraps(f)
    def do(self, *args, **kwargs):
        self.log_api_call(f, kwargs, logging.debug, self._fp_hide_in_log)
        return f(self, *args, **kwargs)

    return do


def log_i(f):

    @wraps(f)
    def do(self, *args, **kwargs):
        self.log_api_call(f, kwargs, logging.info, self._fp_hide_in_log)
        return f(self, *args, **kwargs)

    return do


def log_w(f):

    @wraps(f)
    def do(self, *args, **kwargs):
        self.log_api_call(f, kwargs, logging.warning, self._fp_hide_in_log)
        return f(self, *args, **kwargs)

    return do


class GenericAPI(object):

    @staticmethod
    def _process_action_result(a):
        if not a: raise ResourceNotFound('item found, but something not')
        if a.is_status_dead():
            raise FunctionFailed('{} is dead'.format(a.uiid))
        return a.serialize()

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
                           g=None):
        import eva.item
        item = self.controller.get_item(i)
        if not item or not apikey.check(k, item): raise ResourceNotFound(i)
        if is_oid(i):
            _t, iid = parse_oid(i)
            if not item or item.item_type != _t: raise ResourceNotFound(i)
        return eva.item.get_state_history(
            a=a,
            oid=item.oid,
            t_start=s,
            t_end=e,
            limit=l,
            prop=x,
            time_format=t,
            fill=w,
            fmt=g)

    def _result(self, k, u, i, g, s, rtp):
        import eva.item
        if u:
            a = self.controller.Q.history_get(u)
            if not a or not apikey.check(k, a.item): raise ResourceNotFound
            return a.serialize()
        else:
            result = []
            if i:
                item_id = oid_to_id(i, rtp)
                if item_id is None: raise ResourceNotFound
                ar = None
                item = self.controller.get_item(rtp + ':' + item_id)
                if not apikey.check(k, item): raise ResourceNotFound
                if item_id.find('/') > -1:
                    if item_id in self.controller.Q.actions_by_item_full_id:
                        ar = self.controller.Q.actions_by_item_full_id[item_id]
                else:
                    if item_id in self.controller.Q.actions_by_item_id:
                        ar = self.controller.Q.actions_by_item_id[item_id]
                if ar is None: return []
            else:
                ar = self.controller.Q.actions
            for a in ar:
                if not apikey.check(k, a.item): continue
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
        for prop, value in v.items() if isinstance(v, dict) else {p: v}.items():
            if not item.set_prop(prop, value, False):
                raise FunctionFailed('{}.{} = {} unable to set'.format(
                    item.oid, prop, value))
        if save: item.save()
        return True

    def __init__(self):
        self._fp_hide_in_log = {}
        self.log_api_call = API_Logger()

    def _nofp_log(self, func, params):
        fp = self._fp_hide_in_log.setdefault(func, [])
        fp += params if isinstance(params, list) else [params]

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
        result = {
            'acl': apikey.serialized_acl(k),
            'system': eva.core.config.system_name,
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
        if apikey.check_master(k):
            result['file_management'] = \
                    eva.sysapi.config.api_file_management_allowed
        if apikey.check(k, sysfunc=True):
            result['debug'] = eva.core.config.debug
            result['setup_mode'] = eva.core.config.setup_mode
            result['db_update'] = eva.core.config.db_update
            result['polldelay'] = eva.core.config.polldelay
            if eva.core.config.development:
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
                except Exception as e:
                    logging.error('Unable to calculate CRT: {}'.format(e))
                    eva.core.log_traceback()
                    result['benchmark_crt'] = -1
        return True, result

    @log_d
    def state_history(self, **kwargs):
        """
        get item state history

        State history of one :doc:`item</items>` or several items of the
        specified type can be obtained using **state_history** command.

        Args:
            k:
            a: history notifier id (default: db_1)
            .i: item oids or full ids, list or comma separated

        Optional:
            s: start time (timestamp or ISO)
            e: end time (timestamp or ISO)
            l: records limit (doesn't work with "w")
            x: state prop ("status" or "value")
            t: time format("iso" or "raw" for unix timestamp, default is "raw")
            w: fill frame with the interval (e.g. "1T" - 1 min, "2H" - 2 hours
                etc.), start time is required
            g: output format ("list" or "dict", default is "list")
        """
        k, a, i, s, e, l, x, t, w, g = parse_function_params(
            kwargs, 'kaiselxtwg', '.sr..issss')
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
            for i in items:
                r = self._get_state_history(
                    k=k, a=a, i=i, s=s, e=e, l=l, x=x, t=t, w=w, g=g)
                result['t'] = r['t']
                if 'status' in r:
                    result[i + '/status'] = r['status']
                if 'value' in r:
                    result[i + '/value'] = r['value']
            return result
        else:
            result = self._get_state_history(
                k=k, a=a, i=i, s=s, e=e, l=l, x=x, t=t, w=w, g=g)
            return result

    # return version for embedded hardware
    @log_d
    def info(self, **kwargs):
        return {
            'platfrom': 'eva',
            'product': eva.core.product.code,
            'version': eva.core.version,
            'system': eva.core.config.system_name,
        }

    @log_i
    def login(self, **kwargs):
        """
        log in and get authentication token

        Obtains authentication :doc:`token</api_tokens>` which can be used in
        API calls instead of API key.

        If both **k** and **u** args are absent, but API method is called with
        HTTP request, which contain HTTP header for basic authorization, the
        function will try to parse it and log in user with credentials
        provided.

        Args:
            k: valid API key or
            u: user login
            p: user password

        Returns:
            A dict, containing API key ID and authentication token
        """
        if not tokens.is_enabled():
            raise FunctionFailed('Session tokens are disabled')
        k, u, p = parse_function_params(kwargs, 'kup', '.ss')
        if not u and not k and hasattr(cherrypy, 'serving') and hasattr(
                cherrypy.serving, 'request'):
            auth_header = cherrypy.serving.request.headers.get('authorization')
            if auth_header:
                try:
                    scheme, params = auth_header.split(' ', 1)
                    if scheme.lower() == 'basic':
                        u, p = b64decode(params).decode().split(':', 1)
                except Exception as e:
                    eva.core.log_traceback()
                    raise FunctionFailed(e)
        if not u and k:
            if k in apikey.keys:
                ki = apikey.key_id(k)
                token = tokens.append_token(ki)
                if not token:
                    raise FunctionFailed('token generation error')
                return {'key': apikey.key_id(k), 'token': token}
            raise AccessDenied
        key = eva.users.authenticate(u, p)
        if key in apikey.keys_by_id:
            token = tokens.append_token(key, u)
            if not token:
                raise FunctionFailed('token generation error')
            return {'key': key, 'token': token}
        raise AccessDenied('Assigned API key is invalid')

    @log_d
    def logout(self, **kwargs):
        """
        log out and purge authentication token

        Purges authentication :doc:`token</api_tokens>`

        If API key is used as parameter value, the function purges all tokens
        assigned to it.

        Args:
            k: valid API key or token
        """
        if not tokens.is_enabled():
            raise FunctionFailed('Session tokens are disabled')
        k = parse_function_params(kwargs, 'k', '.')
        if k.startswith('token:'):
            tokens.remove_token(k)
        else:
            tokens.remove_token(key_id=apikey.key_id(k))
        return True


class GenericCloudAPI(object):

    @log_w
    @api_need_master
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
        if result: return True
        else: raise FunctionFailed('{}: test failed'.format(c.full_id))

    @log_i
    @api_need_master
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


def cp_json_handler(*args, **kwargs):
    value = cherrypy.serving.request._json_inner_handler(*args, **kwargs)
    response = cherrypy.serving.response
    if value or value == 0 or isinstance(value, list):
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
    value = cherrypy.serving.request._json_inner_handler(*args, **kwargs)
    if value is None:
        cherrypy.serving.response.status = 202
        return
    else:
        return format_json(
            value, minimal=not eva.core.config.development).encode('utf-8')


def _http_client_key(_k=None, from_cookie=False):
    if _k: return _k
    k = cherrypy.request.headers.get('X-Auth-Key')
    if k: return k
    if 'k' in cherrypy.serving.request.params:
        k = cherrypy.serving.request.params['k']
    if k: return k
    if from_cookie:
        k = cherrypy.serving.request.cookie.get('auth')
        if k: k = k.value
        if k and not k.startswith('token:'):
            k = None
    if k: return k
    k = eva.apikey.key_by_ip_address(http_real_ip())
    return k


def key_token_parse(k):
    token = tokens.get_token(k)
    if not token:
        raise AccessDenied('Invalid token')
    return apikey.key_by_id(token['ki'])


def cp_client_key(k=None, from_cookie=False):
    k = _http_client_key(k, from_cookie=from_cookie)
    if k and k.startswith('token:'):
        try:
            return key_token_parse(k)
        except AccessDenied as e:
            raise cp_forbidden_key(e)
    else:
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
            data = jsonpickle.decode(
                open('{}/eva/apidata/{}_data.json'.format(
                    eva.core.dir_lib, api_id)).read())
            self._expose(data['functions'])
            for f, a in data['aliases'].items():
                self._expose(f, a)
            if set_api_uri:
                self.api_uri = data['uri']
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

        payload = kwargs.get('p')
        result = []
        for pp in payload if isinstance(payload, list) else [payload]:
            if not isinstance(pp, dict) or not pp:
                raise cp_bad_request('Invalid JSON RPC payload')
            if pp.get('jsonrpc') != '2.0':
                raise cp_api_error('Unsupported RPC protocol')
            req_id = pp.get('id')
            try:
                p = pp.get('params', {})
                method = pp.get('method')
                if not method: raise FunctionFailed('API method not defined')
                f = self._get_api_function(method)
                if not f:
                    raise MethodNotFound
                k = p.get('k')
                if method != 'login':
                    if not k:
                        raise AccessDenied
                    if k.startswith('token:'):
                        k = key_token_parse(k)
                        p['k'] = k
                    if not apikey.check(k=k):
                        raise AccessDenied
                result = f(**p)
                if isinstance(result, tuple):
                    result, data = result
                else:
                    data = None
                if result is True:
                    result = {'ok': True}
                    if isinstance(data, dict):
                        result.update(data)
                elif result is False:
                    raise FunctionFailed
                elif result is None:
                    raise ResourceNotFound
                r = {'jsonrpc': '2.0', 'result': result, 'id': req_id}
            except ResourceNotFound as e:
                eva.core.log_traceback()
                r = format_error(apiclient.result_not_found, e)
            except AccessDenied as e:
                eva.core.log_traceback()
                r = format_error(apiclient.result_forbidden, e)
            except MethodNotFound as e:
                eva.core.log_traceback()
                r = format_error(apiclient.result_func_unknown, e)
            except InvalidParameter as e:
                eva.core.log_traceback()
                r = format_error(apiclient.result_invalid_params, e)
            except ResourceAlreadyExists as e:
                eva.core.log_traceback()
                r = format_error(apiclient.result_already_exists, e)
            except ResourceBusy as e:
                eva.core.log_traceback()
                r = format_error(apiclient.result_busy, e)
            except Exception as e:
                eva.core.log_traceback()
                r = format_error(apiclient.result_func_failed, e)
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
        GenericAPI.__init__(self)
        GenericHTTP_API_abstract.__init__(self)
        self._cp_config = api_cp_config.copy()
        self._cp_config['tools.auth.on'] = True
        self._cp_config['tools.json_pre.on'] = True
        self._cp_config['tools.json_out.handler'] = cp_json_handler

    def wrap_exposed(self):
        super().wrap_exposed(cp_api_function)


def mqtt_discovery_handler(notifier_id, d):
    logging.info(
        'MQTT discovery handler got info from %s' % notifier_id + \
        ' about %s, but no real handler registered' % d
    )


def mqtt_api_handler(notifier_id, data, callback):
    try:
        if not data or data[0] != '|':
            raise FunctionFailed('invalid packet data')
        pfx, api_key_id, d = data.split('|', 2)
        try:
            ce = apikey.key_ce(api_key_id)
            if ce is None:
                raise FunctionFailed('invalid key')
            d = ce.decrypt(d.encode()).decode()
            call_id, payload = d.split('|', 1)
        except:
            logging.warning(
                'MQTT API: invalid api key in encrypted packet from ' +
                notifier_id)
            raise
        try:
            payload = jsonpickle.decode(payload)
        except:
            eva.core.log_traceback()
            raise FunctionFailed('Invalid JSON data')
        g.set('eva_ics_gw', 'mqtt:' + notifier_id)
        try:
            response = jrpc(p=payload)
        except:
            eva.core.log_traceback()
            callback(call_id, '500|')
            raise FunctionFailed('API error')
        response = ce.encrypt(jsonpickle.encode(response).encode())
        callback(call_id, '200|' + response.decode())
    except Exception as e:
        logging.warning('MQTT API: API call failed from {}: {}'.format(
            notifier_id, e))
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
    if not eva.core.config.development:
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
    'tools.json_out.on': True,
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
