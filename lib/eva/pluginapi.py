__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2020 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.3.1"
__api__ = 1

import eva.core
from eva.apikey import check as key_check
from eva.apikey import key_id as key_id
from eva.apikey import check_master as key_check_master
from eva.apikey import get_masterkey

from eva.api import parse_api_params
from eva.api import get_aci
from eva.api import set_aci
from eva.tools import parse_function_params

from eva.api import log_d as api_log_d
from eva.api import log_i as api_log_i
from eva.api import log_w as api_log_w

import eva.api

from eva.api import MethodNotFound
from eva.exceptions import FunctionFailed
from eva.exceptions import ResourceNotFound

from eva.api import APIX

from eva.api import api_need_master
from eva.sysapi import api_need_file_management
from eva.sysapi import api_need_rpvt
from eva.sysapi import api_need_cmd
from eva.sysapi import api_need_sysfunc
from eva.sysapi import api_need_lock

import logging

from eva.core import db as get_db
from eva.core import userdb as get_userdb


# general functions
def api_call(method, key_id=None, **kwargs):
    """
    Call controller API method

    Args:
        key_id: API key ID. If key_id is None, masterkey is used
        other: passed to API method as-is
    Returns:
        API function result
    Raises:
        eva.exceptions.*
    """
    if not eva.api.jrpc:
        raise FunctionFailed('API not initialized')
    f = eva.api.jrpc._get_api_function(method)
    if not f:
        raise MethodNotFound
    result = f(
        k=apikey.key_by_id(key_id) if key_id is not None else get_masterkey(),
        **kwargs)
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
    Get plugin API version
    """
    return __api__


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


# register methods and functions


def register_lmacro_object(n, o):
    """
    Register custom object for LM PLC macros

    Args:
        n: object name
        o: object itself
    """
    if get_product().code != 'lm':
        raise RuntimeError(
            'Can not register lmacro object, wrong controller type')
    import eva.lm.macro_api
    eva.lm.macro_api.expose_object(n, o)
    logging.debug(f'lmacro object registered: {n} -> {o}')


def register_sfatpl_object(n, o):
    """
    Register custom object for SFA Templates

    Args:
        n: object name
        o: object itself
    """
    if get_product().code != 'sfa':
        raise RuntimeError(
            'Can not register SFA Templates object, wrong controller type')
    import eva.sfa.sfapi
    eva.sfa.sfapi.expose_sfatpl_object(n, o)
    logging.debug(f'SFA Templates object registered: {n} -> {o}')


def register_apix(o, sys_api=False):
    """
    Register API extension (APIX) object
    """
    for m in dir(o):
        if not m.startswith('_'):
            f = getattr(o, m)
            if f.__class__.__name__ == 'method':
                eva.api.expose_api_method(f.__name__, f, sys_api=sys_api)
                logging.debug(f'API method registered: {f.__name__} -> {f}' +
                              (' (SYS API)' if sys_api else ''))
