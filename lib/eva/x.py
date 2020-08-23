import sys
import os
import logging
import threading

from eva.exceptions import InvalidParameter
from types import SimpleNamespace


class GenericX:

    def validate_config(self,
                        config={},
                        config_type='config',
                        ignore_private=False,
                        **kwargs):
        """
        Validates module config

        Does nothing by default. Can e.g. call self.validate_config_whi to
        validate config with module help info, validate config with JSON schema
        or do everything manually

        Note: "driver_assign" always assigns the same parameters for "action"
        and "state" by default. Consider either ignoring config_type='state'
        validation or allow action parameters there.

        Args:
            config: config to validate (may be modified on-the-flow to convert
                variable types for extension config)
            config_type: validation config type ('config', 'state', 'action'
                etc., matches help variable)
            ignore_private: allow any private (starting with "_") parameters as
                they're usually passed as-is to lower level extension (e.g. LPI
                -> PHI)
            kwargs: reserved for the future
        Returns:
            True if config is validated
        Raises:
            eva.exceptions.InvalidParameter: if config contains invalid params
        """
        return True

    def validate_config_whi(self,
                            config={},
                            config_type='config',
                            allow_extra=False,
                            ignore_private=False,
                            xparams=[]):
        """
        Validate config with module help info

        Help info: module help info variable (e.g. __config_help__ for config)

        Args:
            config: config to validate
            config_type: config type (help var to parse, default is 'config')
            allow_extra: allow any extra params in config
            xparams: list of allowed extra params

        Returns:
            True if config is validated. Config dict variables are
            automatically parsed and converted to the required types (except
            extra params if not listed)

        Raises:
            eva.exceptions.InvalidParameter: if configuration is invalid
        """

        def _convert_type(v, type_required):
            if type_required == 'any':
                return v
            from pyaltt2.converters import val_to_boolean
            from pyaltt2.converters import safe_int
            if type_required == 'bool':
                value = val_to_boolean(v)
                if value is None:
                    raise ValueError
                else:
                    return value
            elif type_required == 'str':
                return str(v)
            elif type_required == 'url':
                v = str(v)
                if v.startswith('http://') or v.startswith('https://'):
                    return v
                else:
                    raise ValueError
            elif type_required == 'int':
                return safe_int(v)
            elif type_required == 'uint':
                v = safe_int(v)
                if v < 0:
                    raise ValueError
                else:
                    return v
            elif type_required == 'hex':
                return int(v, 16)
            elif type_required == 'bin':
                return int(v, 2)
            elif type_required == 'float':
                return float(v)
            elif type_required == 'ufloat':
                v = float(v)
                if v < 0:
                    raise ValueError
                else:
                    return v
            elif type_required.startswith('list:'):
                type_required = type_required.split(':', 1)[1]
                for i, val in enumerate(v):
                    v[i] = _convert_type(val, type_required)
                return v
            elif type_required.startswith('enum:'):
                _, type_required, values = type_required.split(':', 2)
                values = [
                    _convert_type(x, type_required) for x in values.split(',')
                ]
                v = _convert_type(v, type_required)
                if v not in values:
                    raise ValueError
                else:
                    return v
            else:
                err = f'Unsupported value type required: "{type_required}"'
                self.log_error(err)
                raise TypeError(err)

        help_array = getattr(self, f'_{config_type}_help').copy()
        help_array += xparams
        help_info = {v['name']: v for v in help_array}
        required_list = [v['name'] for v in help_array if v.get('required')]
        defaults = {
            v['name']: v['default']
            for v in help_array
            if v.get('required') and 'default' in v
        }
        errors = []
        for i in required_list:
            if i not in config:
                if i in defaults:
                    config[i] = defaults[i]
                else:
                    errors.append(f'required param "{i}" is missing')
        for i, v in config.items():
            if i in help_info:
                try:
                    type_required = help_info[i].get('type', 'any')
                    config[i] = _convert_type(v, type_required)
                except:
                    from eva.core import log_traceback
                    log_traceback()
                    errors.append('invalid param '
                                  f'value {i}="{v}" should be {type_required}')
            elif not allow_extra and (ignore_private is True and
                                      not i.startswith('_')):
                errors.append(f'param "{i}" is not allowed')
        if errors:
            raise InvalidParameter(', '.join(errors))
        else:
            return True


_mod_cache_lock = threading.RLock()
_mod_cache = {}


def import_sfm(fname, module_name=None, set_sys_modules=False):
    """
    Import single file as a module

    Args:
        fname: file name to import
    Returns:
        Module globals
    Raises:
        all possible exceptions
    """
    mtime = os.path.getmtime(fname)
    try:
        with _mod_cache_lock:
            cache_entry = _mod_cache[(fname, module_name)]
        if cache_entry['mtime'] < mtime:
            logging.debug(f'{module_name} cache entry for {fname}'
                          f' is obsolete, loading from disk')
        else:
            return cache_entry['mod']
    except KeyError:
        logging.debug(
            f'{module_name} no cache entry for {fname}, loading from disk')
    from importlib.machinery import ModuleSpec
    with open(fname) as fh:
        n = {}
        exec(compile(fh.read(), fname, mode='exec'), n)
        mod = SimpleNamespace(**n)
        if module_name:
            mod.__name__ = module_name
            mod.__spec__ = ModuleSpec(name=module_name,
                                      loader=import_sfm,
                                      origin=fname)
            if set_sys_modules:
                sys.modules[module_name] = mod
        with _mod_cache_lock:
            _mod_cache[(fname, module_name)] = {
                'mtime': os.path.getmtime(fname),
                'mod': mod
            }
        return mod


def import_x(fname):
    return import_sfm(fname,
                      module_name=fname.rsplit('/', 1)[-1].rsplit('.', 1)[0])


def get_x_iobj(fname, xclass):
    mod = import_x(fname)
    return getattr(mod, xclass)(info_only=True, _xmod=mod)


def serialize_x(fname, xclass, **kwargs):
    """
    Serialize GenericX

    Args:
        fname: sfm file
        xclass: extension base class
        kwargs: passed to serialize function
    """
    return get_x_iobj(fname, xclass).serialize(**kwargs)
