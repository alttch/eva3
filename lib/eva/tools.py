__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2020 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.3.1"

import rapidjson
import jsonpickle
import time
import socket
import struct
import threading
import logging
import hashlib
import uuid
import string
import random

from collections import OrderedDict

from functools import wraps

from pyaltt2.locker import Locker
from pyaltt2.converters import safe_int, val_to_boolean
from pyaltt2.crypto import gen_random_str
from pyaltt2.lp import parse_func_str
from pyaltt2.network import parse_host_port, netacl_match


class MultiOrderedDict(OrderedDict):

    def __setitem__(self, key, value):
        if isinstance(value, list) and key in self:
            self[key].extend(value)
        else:
            super().__setitem__(key, value)


class InvalidParameter(Exception):

    def __str__(self):
        msg = super().__str__()
        return 'Invalid parameter' + (': {}'.format(msg) if msg else '')


def config_error(fname, section, key, value):
    logging.error('%s error, unknown value %s = "%s" in section %s' % \
            (fname, key, value, section))


def format_json(obj, minimal=False, unpicklable=False):
    if unpicklable:
        return rapidjson.dumps(rapidjson.loads(jsonpickle.encode(obj,
                unpicklable = unpicklable)), indent=4, sort_keys=True) \
                    if not minimal else \
                    jsonpickle.encode(obj, unpicklable = unpicklable)
    else:
        return rapidjson.dumps(obj, indent=4, sort_keys=True) \
            if not minimal else rapidjson.dumps(obj)


def fname_remove_unsafe(fname):
    return fname.replace('/', '').replace('..', '')


# throws exception
def dict_from_str(s):
    if not isinstance(s, str):
        return s
    result = {}
    if not s:
        return result
    vals = s.split(',')
    for v in vals:
        name, value = v.split('=')
        if value.find('||') != -1:
            _value = value.split('||')
            value = []
            for _v in _value:
                if _v.find('|') != -1:
                    value.append(arr_from_str(_v))
                else:
                    value.append([_v])
        else:
            value = arr_from_str(value)
        if isinstance(value, str):
            try:
                value = float(value)
                if value == int(value):
                    value = int(value)
            except:
                pass
        result[name] = value
    return result


def arr_from_str(s):
    if not isinstance(s, str) or s.find('|') == -1:
        return s
    result = []
    vals = s.split('|')
    for v in vals:
        try:
            _v = float(v)
            if _v == int(_v):
                _v = int(_v)
        except:
            _v = v
        result.append(_v)
    return result


def print_json(obj):
    print(format_json(obj))


def wait_for(func, wait_timeout, delay, wait_for_false=False, abort_func=None):
    a = 0
    if wait_for_false:
        while func() and a < wait_timeout / delay:
            if abort_func and abort_func():
                break
            a += 1
            time.sleep(delay)
    else:
        while not func() and a < (wait_timeout() if callable(wait_timeout) else
                                  wait_timeout) / delay:
            if abort_func and abort_func():
                break
            a += 1
            time.sleep(delay)
    return func()


__special_param_names = {
    'S': 'save',
    'K': 'kw',
    'Y': 'full',
    'J': '_j',
    'F': 'force',
    'H': 'has_all',
    'W': 'wait',
    'U': 'uri'
}

__special_param_codes = {
    'save': 'S',
    'kw': 'K',
    'full': 'Y',
    '_j': 'J',
    'force': 'F',
    'has_all': 'H',
    'wait': 'W',
    'uri': 'U'
}


def __get_special_param_name(p):
    return __special_param_names.get(p, p)


def __get_special_param_code(p):
    return __special_param_codes.get(p, p)


def parse_function_params(params,
                          names,
                          types='',
                          defaults=None,
                          e=InvalidParameter,
                          ignore_extra=False):
    """
    Args:
        names: parameter names (list or string if short)
            S: equal to 'save'
            Y: equal to 'full'
            J: equal to '_j'
            F: equal to 'force'
        values: parameter values
            R: required, any not null and non-empty string
            r: required, but empty strings are possible
            s: required, should be string
            S: required, should be non-empty string
            b: boolean (or 0/1 or boolean-like strings)
            B: boolean (or 0/1 or boolean-like strings), required
            i: integer, can be None
            f or n: float(number), can be None
            I: integer, required
            F or N: float(number), required
            D: dict, required
            T: tuple, required
            X: set, required
            L: list, required
            . (dot): optional
            o: oid, can be null
            O: OID required
        params: dict
        defaults: dict (name/value)
        e: exception to raise
    """
    result = ()
    err = 'Invalid parameter value: {} = "{}", {} required'
    if len(params) != len(names) and not ignore_extra:
        for p in params.keys():
            p = __get_special_param_code(p)
            if p not in names:
                raise e('Invalid function parameter: {}'.format(p))
    if not names:
        return result
    for i in range(len(names)):
        n = __get_special_param_name(names[i])
        required = types[i]
        value = params.get(n)
        if value is None and defaults:
            value = defaults.get(n)
        if required == '.':
            result += (value,)
        elif required == 'R':
            if value is None or value == '':
                raise e(err.format(n, value, 'non-empty'))
            result += (value,)
        elif required == 'r':
            if value is None or value == '':
                raise e(err.format(n, value, 'non-null'))
            result += (value,)
        elif required == 'i':
            if value is not None:
                try:
                    result += (int(value),)
                except:
                    raise e(err.format(n, value, 'integer'))
            else:
                result += (None,)
        elif required == 'f' or required == 'n':
            if value is not None:
                try:
                    result += (float(value),)
                except:
                    raise e(err.format(n, value, 'number'))
            else:
                result += (None,)
        elif required == 'I':
            try:
                result += (int(value),)
            except:
                raise e(err.format(n, value, 'integer'))
        elif required == 'F' or required == 'N':
            try:
                result += (float(value),)
            except:
                raise e(err.format(n, value, 'number'))
        elif required == 's':
            if value is not None:
                if not isinstance(value, str):
                    raise e(err.format(n, value, 'string'))
            result += (value,)
        elif required == 'S':
            if not isinstance(value, str) or value == '':
                raise e(err.format(n, value, 'non-empty string'))
            result += (value,)
        elif required == 'b':
            if value is not None:
                val = val_to_boolean(value)
                if val is None:
                    raise e(err.format(n, value, 'boolean'))
                result += (val,)
            else:
                result += (None,)
        elif required == 'B':
            val = val_to_boolean(value)
            if val is None:
                raise e(err.format(n, value, 'boolean'))
            result += (val,)
        elif required == 'D':
            if not isinstance(value, dict):
                raise e(err.format(n, value, 'dict'))
            result += (value,)
        elif required == 'T':
            if not isinstance(value, tuple):
                raise e(err.format(n, value, 'tuple'))
            result += (value,)
        elif required == 'X':
            if not isinstance(value, set):
                raise e(err.format(n, value, 'set'))
            result += (value,)
        elif required == 'L':
            if not isinstance(value, list):
                raise e(err.format(n, value, 'list'))
            result += (value,)
        elif required == 'o':
            if value is not None:
                if not is_oid(value):
                    raise e(err.format(n, value, 'oid'))
            result += (value,)
        elif required == 'O':
            if not is_oid(value):
                raise e(err.format(n, value, 'oid'))
            result += (value,)
        else:
            raise e('Parameter parser internal error')
    return result if len(result) > 1 else result[0]


def is_oid(oid):
    if oid is None or not isinstance(oid, str):
        return False
    return oid.find(':') != -1


def parse_oid(oid):
    if oid is None or not isinstance(oid, str):
        return None, None
    try:
        tp, i = oid.split(':')
    except:
        return None, None
    return tp, i


def oid_type(oid):
    if oid is None or not isinstance(oid, str):
        return None
    tp, i = parse_oid(oid)
    return tp


def oid_to_id(oid, required=None):
    if not is_oid(oid):
        return oid
    tp, i = parse_oid(oid)
    if tp is None or i is None:
        return None
    if required and tp != required:
        return None
    return i


def error_page_400(*args, **kwargs):
    return '400 Bad Request'


def error_page_403(*args, **kwargs):
    return '403 Forbidden'


def error_page_404(*args, **kwargs):
    return '404 Not Found'


def error_page_405(*args, **kwargs):
    return '405 Method Not Allowed'


def error_page_409(*args, **kwargs):
    return '409 Conflict'


def error_page_500(*args, **kwargs):
    return 'Internal Server Error'


tiny_httpe = {
    'error_page.400': error_page_400,
    'error_page.403': error_page_403,
    'error_page.404': error_page_404,
    'error_page.405': error_page_405,
    'error_page.409': error_page_409,
    'error_page.500': error_page_500
}


def dict_merge(*args):
    """
    merge dicts for compat < 3.5
    """
    result = {}
    for a in args:
        result.update(a)
    return result


def format_modbus_value(val):
    try:
        if val[0] not in ['h', 'c']:
            return None, None, None, None
        if val.find('*') != -1:
            addr, multiplier = val[1:].split('*', 1)
            try:
                multiplier = float(multiplier)
            except:
                return None, None, None, None
        elif val.find('/') != -1:
            addr, multiplier = val[1:].split('/', 1)
            try:
                multiplier = float(multiplier)
                multiplier = 1 / multiplier
            except:
                return None, None, None, None
        else:
            addr = val[1:]
            multiplier = 1
        if addr.startswith('S'):
            addr = addr[1:]
            signed = True
        else:
            signed = False
        addr = safe_int(addr)
        if addr > 9999 or addr < 0:
            return None, None, None, None
        return val[0], addr, multiplier, signed
    except:
        return None, None, None, None


_p_periods = {
    'S': 1,
    'T': 60,
    'H': 3600,
    'D': 86400,
    'W': 604800,
}


def fmt_time(t):
    try:
        return time.time() - _p_periods.get(t[-1]) * int(t[:-1])
    except:
        return t


def get_caller(stack_len=2):
    import inspect
    return inspect.getouterframes(inspect.currentframe(), 2)[stack_len]


def get_caller_module(stack_len=2):
    return get_caller(stack_len + 1).filename.rsplit('.', 1)[0].rsplit('/',
                                                                       1)[-1]
