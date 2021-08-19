__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.1"

import importlib
import jinja2
import threading
import cherrypy

import eva.core
from eva import apikey

from eva.api import cp_client_key
from eva.api import api_result_accepted
from eva.api import http_real_ip
from eva.api import get_aci
from eva.api import cp_api_404

_exposed_sfatpl_lock = threading.RLock()
_exposed_sfatpl = {}


def expose_sfatpl_object(n, o):
    with _exposed_sfatpl_lock:
        _exposed_sfatpl[n] = o


def _get_api():
    import eva.sfa.sfapi
    return eva.sfa.sfapi.api


# j2 template engine functions


def j2_state(i=None, g=None, p=None, k=None):
    if k:
        _k = apikey.key_by_id(k)
    else:
        _k = cp_client_key(from_cookie=True, _aci=True)
    try:
        return _get_api().state(k=_k, i=i, g=g, p=p)
    except:
        eva.core.log_traceback()
        return None


def j2_groups(g=None, p=None, k=None):
    if k:
        _k = apikey.key_by_id(k)
    else:
        _k = cp_client_key(from_cookie=True, _aci=True)
    try:
        return _get_api().groups(k=_k, g=g, p=p)
    except:
        eva.core.log_traceback()
        return None


def j2_api_call(method, params={}, k=None):
    if k:
        _k = apikey.key_by_id(k)
    else:
        _k = cp_client_key(from_cookie=True, _aci=True)
    f = getattr(_get_api(), method)
    try:
        result = f(k=_k, **params)
        if isinstance(result, tuple):
            result, data = result
        else:
            data = None
        if result is True:
            if data == api_result_accepted:
                return None
            else:
                return data
        else:
            return result
    except:
        eva.core.log_traceback()
        return None


def serve_j2(tpl_file, tpl_dir=eva.core.dir_ui):
    j2_loader = jinja2.FileSystemLoader(searchpath=tpl_dir)
    j2 = jinja2.Environment(loader=j2_loader)
    try:
        template = j2.get_template(tpl_file)
    except:
        raise cp_api_404()
    env = {}
    env['request'] = cherrypy.serving.request
    try:
        env['evaHI'] = 'evaHI ' in cherrypy.serving.request.headers.get(
            'User-Agent', '')
    except:
        env['evaHI'] = False
    try:
        k = cp_client_key(from_cookie=True, _aci=True)
    except:
        k = None
    if k:
        server_info = _get_api().test(k=k)[1]
    else:
        server_info = {}
    server_info['remote_ip'] = http_real_ip()
    env['server'] = server_info
    env.update(eva.core.cvars)
    template.globals['state'] = j2_state
    template.globals['groups'] = j2_groups
    template.globals['api_call'] = j2_api_call
    template.globals['get_aci'] = get_aci
    template.globals['import_module'] = importlib.import_module
    with _exposed_sfatpl_lock:
        for n, v in _exposed_sfatpl.items():
            template.globals[n] = v
    try:
        cherrypy.serving.response.headers[
            'Content-Type'] = 'text/html;charset=utf-8'
        return template.render(env).encode()
    except:
        eva.core.log_traceback()
        return 'Server error'


def j2_handler(*args, **kwargs):
    try:
        del cherrypy.serving.response.headers['Content-Length']
    except:
        pass
    return serve_j2(cherrypy.serving.request.path_info.replace('..', ''))
