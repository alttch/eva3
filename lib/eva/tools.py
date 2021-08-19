__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.1"

import rapidjson
import jsonpickle
import time
import socket
import struct
import threading
import logging
import uuid
import string
import random
import os

from collections import OrderedDict

from functools import wraps

from pyaltt2.locker import Locker
from pyaltt2.converters import safe_int, val_to_boolean
from pyaltt2.crypto import gen_random_str
from pyaltt2.lp import parse_func_str
from pyaltt2.network import parse_host_port, netacl_match

from pathlib import Path

dir_etc = os.path.realpath(
    os.path.abspath(os.path.dirname(__file__)) + '/../../etc')

schema_lock = threading.RLock()

SCHEMAS = {}


def read_uri(fname,
             dirname=None,
             file_read_mode='r',
             b64=False,
             check_only=False):

    def _encode(content):
        if b64:
            import base64
            content = base64.b64encode(content).decode()
        return content

    if dirname and (
            dirname.startswith('http://') or dirname.startswith('https://')
    ) and not (fname.startswith('http://') or fname.startswith('https://')):
        fname = dirname + '/' + fname

    if fname.startswith('http://') or fname.startswith('https://'):
        import requests
        result = requests.head(fname) if check_only else requests.get(fname)
        if not result.ok:
            raise Exception('http code {}'.format(result.status_code))
        return result.text if file_read_mode == 'r' else _encode(result.content)
    else:
        if not fname.startswith('/') and not fname.startswith('./') and dirname:
            fname = dirname + '/' + fname
        if check_only:
            return os.path.exists(fname)
        else:
            with open(fname, file_read_mode) as fd:
                return _encode(fd.read())


def kb_uri(article_id):
    return f'https://kb.eva-ics.com/articles/{article_id}.html'


def validate_schema(data, schema_id):
    import jsonschema
    import importlib
    with schema_lock:
        if schema_id in SCHEMAS:
            schema = SCHEMAS[schema_id]
        else:
            mod = importlib.import_module(f'eva.schemas.{schema_id}')
            schema = getattr(mod, f'SCHEMA_{schema_id.upper()}')
            SCHEMAS[schema_id] = schema
    jsonschema.validate(data, schema=schema)


def generate_template(tplc):
    import jinja2
    import importlib
    if not isinstance(tplc, str):
        tplc = tplc.read()
    tpl = jinja2.Template(tplc)
    tpl.globals['import_module'] = importlib.import_module
    tpl.globals['time_ns'] = int(time.time() * 1000000000)
    return tpl


def render_template(tplc, cfg=None, raw=False):
    import yaml
    if cfg is None:
        cfg = {}
    elif isinstance(cfg, str):
        cfg = dict_from_str(cfg)
    data = generate_template(tplc).render(cfg)
    return data if raw else yaml.load(data)


class ConfigFile():
    """
    A helper to manage .ini files

    Example:

        with ConfigFile('file.ini') as cf:
            cf.set('section', 'field1', 'value1')
    """

    def __init__(self, fname, init_if_missing=False, backup=True):
        self.fname = fname if '/' in fname else f'{dir_etc}/{fname}'
        self.init_if_missing = init_if_missing
        self._changed = False
        self.backup = backup

    def is_changed(self):
        """
        Returns True, if configuration file was changed and will be saved after
        the statement exit
        """
        return self._changed

    def __enter__(self):
        self.open()
        return self

    def open(self):
        from configparser import ConfigParser
        self.cp = ConfigParser(inline_comment_prefixes=';')
        if not os.path.exists(self.fname):
            if self.init_if_missing:
                import shutil
                shutil.copy(f'{self.fname}-dist', self.fname)
            else:
                raise FileNotFoundError(f'File not found: {self.fname}')
        self.cp.read(self.fname)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        if self._changed:
            import shutil
            from datetime import datetime
            if self.backup:
                shutil.move(
                    self.fname,
                    f'{self.fname}-{datetime.now().strftime("%Y%m%d%H%M%S")}')
            with open(self.fname, 'w') as fh:
                self.cp.write(fh)

    def add_section(self, section, values):
        """
        Add section with dict of values
        """
        self.cp[section] = values
        self._changed = True

    def get_section(self, section):
        """
        Get dict of section values
        """
        from configparser import NoOptionError, NoSectionError
        try:
            return self.cp[section]
        except (NoOptionError, NoSectionError) as e:
            raise KeyError(str(e))

    def set(self, section, name, value):
        """
        Set section field value
        """
        try:
            if self.get(section, name) == str(value):
                return
        except:
            pass
        try:
            self.cp[section][name] = str(value)
        except:
            self.cp.add_section(section)
            self.cp[section][name] = str(value)
        self._changed = True

    def get(self, section, name):
        from configparser import NoOptionError, NoSectionError
        try:
            return self.cp.get(section, name)
        except (NoOptionError, NoSectionError) as e:
            raise KeyError(str(e))

    def delete(self, section, name):
        """
        Delete field from section
        """
        try:
            self.cp.remove_option(section, name)
            self._changed = True
        except:
            pass

    def remove_section(self, section):
        """
        Remove section
        """
        try:
            self.cp.remove_section(section)
        except:
            pass

    def replace_section(self, section, values):
        """
        Replace section with dict of values
        """
        self.remove_section(section)
        return self.add_section(section, values)

    def append(self, section, name, value):
        """
        Append value to array field (in .ini configs, arrays are string fields
        with values, separated with commas)
        """
        try:
            current = [x.strip() for x in self.get(section, name).split(',')]
            if value not in current:
                current.append(value)
                self.set(section, name, ', '.join(current))
        except:
            self.set(section, name, value)
            return

    def remove(self, section, name, value):
        """
        Remove value from array field
        """
        try:
            current = [x.strip() for x in self.get(section, name).split(',')]
            if value in current:
                current.remove(value)
                self.set(section, name, ', '.join(current))
        except:
            return


class ShellConfigFile():
    """
    A helper to manage shell scripts configuration files

    Example:

        with ShellConfigFile('eva_config') as cf:
            cf.set('KEYNAME', 0)
    """

    def __init__(self, fname, init_if_missing=False, backup=True):
        self.fname = fname if '/' in fname else f'{dir_etc}/{fname}'
        self.init_if_missing = init_if_missing
        self._changed = False
        self.backup = backup
        self._data = {}

    def is_changed(self):
        """
        Returns True, if configuration file was changed and will be saved after
        the statement exit
        """
        return self._changed

    def __enter__(self):
        self.open()
        return self

    def open(self):
        if not os.path.exists(self.fname):
            if self.init_if_missing:
                import shutil
                shutil.copy(f'{self.fname}-dist', self.fname)
            else:
                raise FileNotFoundError
        with open(self.fname) as fh:
            for line in fh.readlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    try:
                        name, value = line.split('=', 1)
                        if (value.startswith('"') and value.endswith('"')) or \
                            (value.startswith('\'') and value.endswith('\'')):
                            value = value[1:-1]
                        self._data[name] = value.strip()
                    except:
                        raise ValueError(
                            f'Invalid config file: {self.fname} ({line})')

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        if self._changed:
            import shutil
            from datetime import datetime
            if self.backup:
                shutil.move(
                    self.fname,
                    f'{self.fname}-{datetime.now().strftime("%Y%m%d%H%M%S")}')
            with open(self.fname, 'w') as fh:
                for k, v in self._data.items():
                    try:
                        float(v)
                        fh.write(f'{k}={v}\n')
                    except:
                        fh.write(f'{k}="{v}"\n')

    def set(self, name, value):
        """
        Set field to value
        """
        if self._data.get(name) != value:
            self._data[name] = value
            self._changed = True

    def get(self, name, default=KeyError):
        """
        Get field value
        """
        try:
            return self._data[name]
        except KeyError:
            if default is KeyError:
                raise
            else:
                return default

    def delete(self, name):
        """
        Delete field
        """
        try:
            del self._data[name]
            self._changed = True
        except:
            pass

    def append(self, name, value):
        """
        Append value to array field (in shell configs, arrays are string fields
        with values, separated with spaces)
        """
        current = [x.strip() for x in self._data.get(name, '').split()]
        if value not in current:
            current.append(value)
            self.set(name, ' '.join(current))

    def remove(self, name, value):
        """
        Remove value from array field
        """
        current = [x.strip() for x in self._data.get(name, '').split()]
        if value in current:
            current.remove(value)
            self.set(name, ' '.join(current))


class SimpleNamespace():

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def compare(a, b):
    return (a > b) - (a < b)


def prepare_safe_serialize(v, maxlen=100):
    if isinstance(v, dict):
        result = {}
        for i, z in v.items():
            result[i] = prepare_safe_serialize(z)
        return result
    elif isinstance(v, list) or isinstance(v, tuple):
        result = []
        for z in v:
            result.append(prepare_safe_serialize(z))
        return result
    elif isinstance(v, str):
        if len(v) > maxlen:
            return v[:maxlen] + '...'
    elif isinstance(v, bytes):
        return '<binary>'
    elif isinstance(v, float) or isinstance(v, int) or isinstance(v, bool):
        return v
    return str(v)


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
    if not ignore_extra:
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


def get_caller(stack_len=0):
    import inspect
    return inspect.getouterframes(inspect.currentframe(), 2)[stack_len + 2]


def get_caller_module(stack_len=0, sdir=None):
    fname = get_caller(stack_len + 1).filename
    p = Path(fname)
    parent = p.absolute().parent.name
    if parent == sdir:
        return p.stem
    else:
        return parent
