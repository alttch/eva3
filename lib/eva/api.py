__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "3.1.1"

import cherrypy
import eva.core
import logging
import threading
import time
import math
import jsonpickle
from datetime import datetime
import dateutil
import pytz
import pandas as pd

from eva import apikey
from eva.tools import format_json
from eva.tools import parse_host_port

import eva.users
import eva.notify

host = None
ssl_host = None

port = None
ssl_port = None

# ssl_module = None
ssl_cert = None
ssl_key = None
ssl_chain = None

ei_enabled = True

default_port = 80
default_ssl_port = 443

thread_pool = 15

session_timeout = 3600


def http_api_result(result, env):
    result = {'result': result}
    if env:
        result.update(env)
    return result


def http_api_result_ok(env=None):
    return http_api_result('OK', env)


def http_api_result_error(env=None):
    return http_api_result('ERROR', env)


def update_config(cfg):
    global host, port, ssl_host, ssl_port
    global ssl_module, ssl_cert, ssl_key, ssl_chain
    global session_timeout, thread_pool, ei_enabled
    try:
        host, port = parse_host_port(cfg.get('webapi', 'listen'), default_port)
        logging.debug('webapi.listen = %s:%u' % (host, port))
    except:
        eva.core.log_traceback()
        return False
    try:
        ssl_host, ssl_port = parse_host_port(
            cfg.get('webapi', 'ssl_listen'), default_ssl_port)
        try:
            ssl_module = cfg.get('webapi', 'ssl_module')
        except:
            ssl_module = 'builtin'
        ssl_cert = cfg.get('webapi', 'ssl_cert')
        if ssl_cert[0] != '/': ssl_cert = eva.core.dir_etc + '/' + ssl_cert
        ssl_key = cfg.get('webapi', 'ssl_key')
        if ssl_key[0] != '/': ssl_key = eva.core.dir_etc + '/' + ssl_key
        logging.debug('webapi.ssl_listen = %s:%u' % (ssl_host, ssl_port))
        ssl_chain = cfg.get('webapi', 'ssl_chain')
        if ssl_chain[0] != '/': ssl_chain = eva.core.dir_etc + '/' + ssl_chain
    except:
        pass
    try:
        session_timeout = int(cfg.get('webapi', 'session_timeout'))
    except:
        pass
    logging.debug('webapi.session_timeout = %u' % session_timeout)
    try:
        thread_pool = int(cfg.get('webapi', 'thread_pool'))
    except:
        pass
    logging.debug('webapi.thread_pool = %u' % thread_pool)
    try:
        ei_enabled = (cfg.get('webapi', 'ei_enabled') == 'yes')
    except:
        pass
    logging.debug('webapi.ei_enabled = %s' % ('yes' \
                                if ei_enabled else 'no'))
    return True


def log_api_request(func, auth=None, info=None, dev=False, debug=False):
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
        if not dev:
            if func == 'test': logging.debug(msg)
            else: logging.info(msg)
        else:
            logging.warning(msg)


def http_real_ip():
    if 'X-Real-IP' in cherrypy.request.headers and \
            cherrypy.request.headers['X-Real-IP']!='':
        ip = cherrypy.request.headers['X-Real-IP']
    else:
        ip = cherrypy.request.remote.ip
    return ip


def http_remote_info(k=None):
    return '%s@%s' % (apikey.key_id(k), http_real_ip())


def cp_json_pre():
    ct = cherrypy.request.headers.get('Content-Type')
    if ct == 'application/json':
        try:
            cl = int(cherrypy.request.headers.get('Content-Length'))
            rawbody = cherrypy.request.body.read(cl)
            cherrypy.serving.request.params.update(
                jsonpickle.decode(rawbody.decode()))
        except:
            raise cp_api_error('invalid JSON data')
    return


class GenericAPI(object):

    def test(self, k=None):
        """
        API test, key test and info request, k = any valid key
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
        if apikey.check(k, sysfunc=True):
            result['debug'] = eva.core.debug
            result['setup_mode'] = eva.core.setup_mode
            result['db_update'] = eva.core.db_update
            result['polldelay'] = eva.core.polldelay
            if eva.core.development:
                result['development'] = True
        return result

    # return version for embedded hardware
    def info(self):
        return {
            'platfrom':
            'eva',
            'product':
            eva.core.product_code,
            'version':
            eva.core.version,
            'system':
            eva.core.system_name,
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
        if oid is None: return False
        n = eva.notify.get_db_notifier(a)
        if t_start and fill: tf = 'iso'
        else: tf = time_format
        if not n: return False
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
            return None
        if t_start and fill and result:
            tz = pytz.timezone(time.tzname[0])
            try:
                t_s = float(t_start)
            except:
                try:
                    t_s = dateutil.parser.parse(t_start).timestamp()
                except:
                    return None
            if t_end:
                try:
                    t_e = float(t_end)
                except:
                    try:
                        t_e = dateutil.parser.parse(t_end).timestamp()
                    except:
                        return None
            else:
                t_e = time.time()
            if t_e > time.time(): t_e = time.time()
            try:
                df = pd.DataFrame(result)
                df = df.set_index('t')
                df.index = pd.to_datetime(df.index, utc=True)
                i2 = pd.date_range(
                    start=datetime.fromtimestamp(t_s, tz),
                    end=datetime.fromtimestamp(t_e, tz),
                    freq=fill)
                sp = df.reindex(i2, method='pad').to_dict(orient='split')
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
                return None
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
            return None
        return result

    def dev_cvars(self, k=None):
        """ get only custom vars from ENV
        """
        return eva.core.cvars

    def dev_env(self, k=None):
        """ get ENV (env is used for external scripts)
        """
        return eva.core.env

    def dev_k(self, k=None):
        """ get all API keys
        """
        return apikey.keys

    def dev_n(self, k=None, id=None):
        """ get all notifiers
        """
        return eva.notify.dump(id)

    def dev_t(self, k=None):
        """ get list of all threads
        """
        result = {}
        for t in threading.enumerate().copy():
            if t.name[:10] != 'CP Server ':
                result[t.name] = {}
                result[t.name]['daemon'] = t.daemon
                result[t.name]['alive'] = t.is_alive()
        return result

    def dev_test_critical(self, k=None):
        """ test critical
        """
        eva.core.critical()
        return 'called core critical'


def cp_json_handler(*args, **kwargs):
    value = cherrypy.serving.request._json_inner_handler(*args, **kwargs)
    return format_json(value, minimal=not eva.core.development).encode('utf-8')


def cp_forbidden_key():
    return cherrypy.HTTPError('403 API Forbidden', 'API Key access error')


def cp_api_error(msg=''):
    return cherrypy.HTTPError('500 API Error', msg)


def cp_api_404(msg=''):
    return cherrypy.HTTPError('404 API Object Not Found', msg)


def cp_need_master(k):
    if not eva.apikey.check(k, master=True): raise cp_forbidden_key()


def cp_client_key(_k=None):
    if _k: return _k
    if 'k' in cherrypy.serving.request.params:
        k = cherrypy.serving.request.params['k']
    else:
        try:
            k = cherrypy.session.get('k')
        except:
            k = None
        if k is None: k = eva.apikey.key_by_ip_address(http_real_ip())
    return k


class GenericHTTP_API(GenericAPI):

    _cp_config = {
        'tools.json_pre.on': True,
        'tools.json_out.on': True,
        'tools.json_out.handler': cp_json_handler,
        'tools.auth.on': True,
        'tools.sessions.on': True,
        'tools.sessions.timeout': session_timeout
    }

    def cp_check_perm(self, rlp=None):
        k = cp_client_key()
        if k is not None: cherrypy.serving.request.params['k'] = k
        if cherrypy.serving.request.path_info[:6] == '/login': return
        if cherrypy.serving.request.path_info[:5] == '/info': return
        if cherrypy.serving.request.path_info[:4] == '/dev': dev = True
        else: dev = False
        if dev and not eva.core.development: raise cp_forbidden_key()
        p = cherrypy.serving.request.params.copy()
        if not eva.core.development and 'k' in p: del (p['k'])
        if rlp:
            for rp in rlp:
                try:
                    del p[rp]
                except:
                    pass
        log_api_request(cherrypy.serving.request.path_info[1:],
                        http_remote_info(k), p, dev)
        if apikey.check(k, master=dev, ip=http_real_ip()):
            return
        raise cp_forbidden_key()

    def __init__(self):
        cherrypy.tools.json_pre = cherrypy.Tool(
            'before_handler', cp_json_pre, priority=10)
        cherrypy.tools.auth = cherrypy.Tool(
            'before_handler', self.cp_check_perm, priority=60)
        GenericAPI.test.exposed = True
        GenericHTTP_API.login.exposed = True
        GenericHTTP_API.logout.exposed = True
        if eva.core.development:
            GenericAPI.dev_env.exposed = True
            GenericAPI.dev_cvars.exposed = True
            GenericAPI.dev_k.exposed = True
            GenericAPI.dev_n.exposed = True
            GenericAPI.dev_t.exposed = True

    def login(self, k=None, u=None, p=None):
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

    def logout(self, k=None):
        cherrypy.session['k'] = ''
        return http_api_result_ok()


def start():
    if not host: return False
    cherrypy.server.unsubscribe()
    logging.info('HTTP API listening at at %s:%s' % \
            (host, port))
    server1 = cherrypy._cpserver.Server()
    server1.socket_port = port
    server1._socket_host = host
    server1.thread_pool = thread_pool
    server1.subscribe()
    if ssl_host and ssl_module and ssl_cert and ssl_key:
        logging.info('HTTP API SSL listening at %s:%s' % \
                (ssl_host, ssl_port))
        server_ssl = cherrypy._cpserver.Server()
        server_ssl.socket_port = ssl_port
        server_ssl._socket_host = ssl_host
        server_ssl.thread_pool = thread_pool
        server_ssl.ssl_certificate = ssl_cert
        server_ssl.ssl_private_key = ssl_key
        if ssl_chain:
            server_ssl.ssl_certificate_chain = ssl_chain
        if ssl_module:
            server_ssl.ssl_module = ssl_module
        server_ssl.subscribe()
    if not eva.core.development:
        cherrypy.config.update({'environment': 'production'})
        cherrypy.log.access_log.propagate = False
        cherrypy.log.error_log.propagate = False
    else:
        cherrypy.config.update({'global': {'engine.autoreload.on': False}})
    eva.core.append_stop_func(stop)
    cherrypy.engine.start()


def stop():
    cherrypy.engine.exit()
