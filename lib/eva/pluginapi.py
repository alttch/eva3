__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"
__api__ = 2

import threading

import eva.core
from eva.apikey import key_id as key_id
from eva.apikey import key_by_id
from eva.apikey import get_masterkey

from eva.api import parse_api_params
from eva.api import get_aci
from eva.api import set_aci
from eva.tools import parse_function_params

from eva.api import log_d as api_log_d
from eva.api import log_i as api_log_i
from eva.api import log_w as api_log_w

from eva.api import key_check
from eva.api import key_check_master

import eva.api

from eva.api import MethodNotFound
from eva.exceptions import FunctionFailed
from eva.exceptions import ResourceNotFound
from eva.exceptions import ResourceBusy
from eva.exceptions import ResourceAlreadyExists
from eva.exceptions import AccessDenied
from eva.exceptions import MethodNotImplemented
from eva.exceptions import TimeoutException
from eva.tools import InvalidParameter

from eva.api import APIX

from eva.api import api_need_master
from eva.sysapi import api_need_file_management
from eva.sysapi import api_need_rpvt
from eva.sysapi import api_need_cmd
from eva.sysapi import api_need_sysfunc
from eva.sysapi import api_need_lock

from eva.upnp import discover as upnp_discover
from eva.uc.drivers.tools.mqtt import MQTT
from eva.uc.drivers.tools.snmp import get as snmp_get
from eva.uc.drivers.tools.snmp import set as snmp_set

from eva.mailer import send as sendmail

import logging

from eva.core import db as get_db
from eva.core import userdb as get_userdb
from eva.core import format_db_uri
from eva.core import create_db_engine
from eva.core import dir_eva, dir_runtime, dir_ui, dir_pvt, dir_xc
from eva.tools import get_caller_module

from functools import partial

from neotasker import g

get_cmod = partial(get_caller_module, sdir='plugins')

g_lock = threading.RLock()

# general functions


def get_directory(tp):
    """
    Get path to EVA ICS directory

    Args:
        tp: directory type: eva, runtime, ui, pvt or xc
    Raises:
        LookupError: if directory type is invalid
    """
    if tp not in ['eva', 'runtime', 'ui', 'pvt', 'xc']:
        raise LookupError
    else:
        return getattr(eva.core, f'dir_{tp}')


def api_call(method, key_id=None, **kwargs):
    """
    Call controller API method

    Args:
        key_id: API key ID. If key_id is None, masterkey is used
        other: passed to API method as-is
    Returns:
        API function result
    Raises:
        eva.exceptions
    """
    if not eva.api.jrpc:
        raise FunctionFailed('API not initialized')
    f = eva.api.jrpc._get_api_function(method)
    if not f:
        raise MethodNotFound
    auth_bak = get_aci('auth')
    set_aci('auth', 'key')
    result = f(k=key_by_id(key_id) if key_id is not None else get_masterkey(),
               **kwargs)
    set_aci('auth', auth_bak)
    if isinstance(result, tuple):
        res, data = result
        if res is True:
            return data
        elif res is False:
            raise FunctionFailed
        elif res is None:
            raise ResourceNotFound
    else:
        return result


def get_version():
    """
    Get Plugin API version
    """
    return __api__


def check_version(min_version):
    """
    Check plugin API version

    Args:
        min_version: min Plugin API version required
    Raises:
        RuntimeError: if Plugin API version is too old
    """
    if __api__ < min_version:
        raise RuntimeError('Plugin API version '
                           f'({__api__}) is too old, required: {min_version}')


def get_logger(mod=None):
    """
    Get plugin logger

    Args:
        mod: self module name (optional)
    Returns:
        logger object
    """
    return logging.getLogger(f'eva.plugins.{mod if mod else get_cmod()}')


def get_polldelay():
    """
    Get core poll delay
    """
    return eva.core.config.polldelay


def get_system_name():
    """
    Get system name (host name)
    """
    return eva.core.config.system_name


def get_product():
    """
    Get product object
    
    Returns:
        namespace(name, code, build)
    """
    return eva.core.product


def get_item(i):
    """
    Get controller item

    Args:
        i: item oid
    Returns:
        None if item is not found
    """
    return eva.core.controllers[0].get_item(i)


def check_product(code):
    """
    Check controller type

    Args:
        code: required controller type (uc, lm or sfa)
    Raises:
        RuntimeError: if current controller type is wrong
    """
    if eva.core.product.code != code:
        raise RuntimeError(f'This plugin can be run only inside {code.upper()}')


def get_sleep_step():
    """
    Get core sleep step
    """
    return eva.core.sleep_step


def get_timeout():
    """
    Get default timeout
    """
    return eva.core.config.timeout


def critical():
    """
    Send critical event
    """
    return eva.core.critical(from_driver=True)


def log_traceback():
    """
    Log traceback
    """
    return eva.core.log_traceback()


def spawn(f, *args, **kwargs):
    """
    Run function as a thread in EVA ICS thread pool

    Args:
        f: callable
        args/kwargs: passed to function as-is
    Returns:
        concurrent.futures Future object
    """
    return eva.core.spawn(f, *args, **kwargs)


def get_thread_local(var, default=None, mod=None):
    """
    Get thread-local variable

    Args:
        var: variable name
        default: default, if doesn't exists
        mod: self module name (optional)
    Returns:
        variable value or None if variable isn't set
    """
    return g.get(f'x_{mod if mod else get_cmod()}_{var}', default)


def set_thread_local(var, value=None, mod=None):
    """
    Set thread-local variable

    Args:
        var: variable name
        value: value to set
        mod: self module name (optional)
    """
    return g.set(f'x_{mod if mod else get_cmod()}_{var}', value)


def has_thread_local(var, mod=None):
    """
    Check if thread-local variable exists

    Args:
        var: variable name
        mod: self module name (optional)
    Returns:
        True if exists
    """
    return g.has(f'x_{mod if mod else get_cmod()}_{var}')


def clear_thread_local(var, mod=None):
    """
    Check if thread-local variable exists

    Args:
        var: variable name
        mod: self module name (optional)
    Returns:
        True if exists
    """
    return g.clear(f'x_{mod if mod else get_cmod()}_{var}')


def get_plugin_db(db, mod=None):
    """
    Get plugin custom database SQLAlchemy connection

    The connection object is stored as thread-local and re-used if possible

    Args:
        db: SQLAlchemy DB engine
    """
    n = (f'x_{mod if mod else get_cmod()}___dbconn')
    with g_lock:
        if not g.has(n):
            g.set(n, db.connect())
        else:
            try:
                dbconn = g.get(n)
                dbconn.execute('select 1')
            except:
                try:
                    dbconn.close()
                except:
                    pass
                g.set(n, db.connect())
        return g.get(n)


# register methods and functions


def register_lmacro_object(n, o, mod=None):
    """
    Register custom object for LM PLC macros

    Object is registered as x_{plugin}_{n}

    Args:
        n: object name
        o: object itself
        mod: self module name (optional)
    """
    if get_product().code != 'lm':
        raise RuntimeError(
            'Can not register lmacro object, wrong controller type')
    import eva.lm.macro_api
    n = f'x_{mod if mod else get_cmod()}_{n}'
    eva.lm.macro_api.expose_object(n, o)
    logging.debug(f'lmacro object registered: {n} -> {o}')


def register_sfatpl_object(n, o, mod=None):
    """
    Register custom object for SFA Templates

    Object is registered as x_{plugin}_{n}

    Args:
        n: object name
        o: object itself
        mod: self module name (optional)
    """
    if get_product().code != 'sfa':
        raise RuntimeError(
            'Can not register SFA Templates object, wrong controller type')
    import eva.sfa.sfatpl
    n = f'x_{mod if mod else get_cmod()}_{n}'
    eva.sfa.sfatpl.expose_sfatpl_object(n, o)
    logging.debug(f'SFA Templates object registered: {n} -> {o}')


def register_apix(o, sys_api=False, mod=None):
    """
    Register API extension (APIX) object

    All object methods (except internal and private) are automatically exposed
    as API functions

    Functions are registered as x_{plugin}_{fn}

    Args:
        o: APIX object
        sys_api: if True, object functions are registered as SYS API
        mod: self module name (optional)
    """
    caller = mod if mod else get_cmod()
    for m in dir(o):
        if not m.startswith('_'):
            f = getattr(o, m)
            if f.__class__.__name__ == 'method':
                n = f'x_{caller}_{f.__name__}'
                eva.api.expose_api_method(n, f, sys_api=sys_api)
                logging.debug(f'API method registered: {n} -> {f}' +
                              (' (SYS API)' if sys_api else ''))
