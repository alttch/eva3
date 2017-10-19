__author__ = "Altertech Group, http://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2017 Altertech Group"
__license__ = "See http://www.eva-ics.com/"
__version__ = "3.0.0"

import cherrypy
import eva.core
import logging
import threading
import time

from eva import apikey
from eva.tools import format_json
from eva.tools import parse_host_port

import eva.users


host = None
ssl_host = None

port = None
ssl_port = None

# ssl_module = None
ssl_cert = None
ssl_key = None
ssl_chain = None

default_port = 80
default_ssl_port = 443

thread_pool = 15

session_timeout = 3600

def http_api_result(result, env):
    result = { 'result' : result }
    if env:
        result.update(env)
    return result


def http_api_result_ok(env = None):
    return http_api_result('OK', env)

def http_api_result_error(env = None):
    return http_api_result('ERROR', env)


def update_config(cfg):
    global host, port, ssl_host, ssl_port
    global ssl_module, ssl_cert, ssl_key, ssl_chain
    global session_timeout, thread_pool
    try:
        host, port = parse_host_port(cfg.get('webapi', 'listen'))
        if not port:
            port = default_port
        logging.debug('webapi.listen = %s:%u' % (host, port))
    except:
        eva.core.log_traceback()
        return False
    try:
        ssl_host, ssl_port = parse_host_port(cfg.get('webapi', 'ssl_listen'))
        if not ssl_port:
            ssl_port = default_ssl_port
        try: ssl_module = cfg.get('webapi', 'ssl_module')
        except: ssl_module = 'builtin'
        ssl_cert = cfg.get('webapi', 'ssl_cert')
        if ssl_cert[0] != '/': ssl_cert = eva.core.dir_etc + '/' + ssl_cert
        ssl_key = cfg.get('webapi', 'ssl_key')
        if ssl_key[0] != '/': ssl_key = eva.core.dir_etc + '/' + ssl_key
        logging.debug('webapi.ssl_listen = %s:%u' % (ssl_host, ssl_port))
        ssl_chain = cfg.get('webapi', 'ssl_chain')
        if ssl_chain[0] != '/': ssl_chain = eva.core.dir_etc + '/' + ssl_chain
    except: pass
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
    return True


def log_api_request(func, auth = None, info = None,
        dev = False, debug = False):
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
        else: logging.critical(msg)


def http_real_ip():
    if 'X-Real-IP' in cherrypy.request.headers and \
            cherrypy.request.headers['X-Real-IP']!='':
                ip = cherrypy.request.headers['X-Real-IP']
    else: ip = cherrypy.request.remote.ip
    return ip


def http_remote_info(k = None):
    return '%s@%s' % (apikey.key_id(k), http_real_ip())


class GenericAPI(object):

    def test(self, k = None):
        """
        API test, key test and info request, k = any valid key
        """
        result = http_api_result_ok({
            'acl': apikey.serialized_acl(k),
            'system': eva.core.system_name,
            'time': time.time(),
            'version': eva.core.version,
            'product_name': eva.core.product_name,
            'product_code': eva.core.product_code,
            'product_build': eva.core.product_build
            })
        if apikey.check(k, sysfunc = True):
            result['debug'] = eva.core.debug
            result['db_update'] = eva.core.db_update
            result['polldelay'] = eva.core.polldelay
            if eva.core.development:
                result['development'] = True
        return result


    def dev_cvars(self, k = None) :
        """ get only custom vars from ENV
        """
        return eva.core.cvars


    def dev_env(self, k = None):
        """ get ENV (env is used for external scripts)
        """
        return eva.core.env


    def dev_k(self, k = None):
        """ get all API keys
        """
        return apikey.keys

    
    def dev_n(self, k = None, id = None):
        """ get all notifiers
        """
        return eva.notify.dump(id)


    def dev_t(self, k = None):
        """ get list of all threads
        """
        result = {}
        for t in threading.enumerate().copy():
            if t.name[:10] != 'CP Server ':
                result[t.name] = {}
                result[t.name]['daemon'] = t.daemon
                result[t.name]['alive'] = t.is_alive()
        return result


def cp_json_handler(*args, **kwargs):
    value = cherrypy.serving.request._json_inner_handler(*args, **kwargs)
    return format_json(value,
            minimal = not eva.core.development).encode('utf-8')


def cp_forbidden_key():
    return cherrypy.HTTPError('403 API Forbidden', 'API Key access error')

def cp_api_error(msg = ''):
    return cherrypy.HTTPError('500 API Error', msg)

def cp_api_404(msg = ''):
    return cherrypy.HTTPError('404 API Object Not Found', msg)

def cp_need_master(k):
    if not eva.apikey.check(k, master = True): raise cp_forbidden_key()

class GenericHTTP_API(GenericAPI):

    _cp_config = {
          'tools.json_out.on': True,
          'tools.json_out.handler': cp_json_handler,
          'tools.auth.on': True,
          'tools.sessions.on': True,
          'tools.sessions.timeout': session_timeout
          }


    def cp_check_perm(self):
        if 'k' in cherrypy.serving.request.params:
            k = cherrypy.serving.request.params['k']
        else:
            k = cherrypy.session.get('k')
            if k is None: k = eva.apikey.key_by_ip_address(http_real_ip())
            if k is not None: cherrypy.serving.request.params['k'] = k
        if cherrypy.serving.request.path_info[:6] == '/login': return
        if cherrypy.serving.request.path_info[:4] == '/dev': dev = True
        else: dev = False
        if dev and not eva.core.development: raise cp_forbidden_key()
        p = cherrypy.serving.request.params.copy()
        if not eva.core.development and 'k' in p: del (p['k'])
        log_api_request(cherrypy.serving.request.path_info[1:],
                http_remote_info(k), p, dev)
        if apikey.check(k,
                    master = dev, ip = http_real_ip()): return
        raise cp_forbidden_key()


    def __init__(self):
        cherrypy.tools.auth = cherrypy.Tool('before_handler',
                                self.cp_check_perm, priority=60)
        GenericAPI.test.exposed = True
        GenericHTTP_API.login.exposed = True
        GenericHTTP_API.logout.exposed = True
        if eva.core.development:
            GenericAPI.dev_env.exposed = True
            GenericAPI.dev_cvars.exposed = True
            GenericAPI.dev_k.exposed = True
            GenericAPI.dev_n.exposed = True
            GenericAPI.dev_t.exposed = True


    def login(self, k = None, u = None, p = None):
        if not u and k:
            if k in apikey.keys:
                cherrypy.session['k'] = k
                return http_api_result_ok({ 'key': apikey.key_id(k)})
            else:
                cherrypy.session['k'] = ''
                raise cp_forbidden_key()
        key = eva.users.authenticate(u, p)
        if eva.apikey.check(apikey.key_by_id(key), ip = http_real_ip()):
            cherrypy.session['k'] = apikey.key_by_id(key)
            return http_api_result_ok({ 'key': key})
        cherrypy.session['k'] = ''
        raise cp_forbidden_key()


    def logout(self, k = None):
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
        cherrypy.config.update({ 'global': { 'engine.autoreload.on' : False }})
    eva.core.append_stop_func(stop)
    cherrypy.engine.start()

def stop():
    cherrypy.engine.exit()
