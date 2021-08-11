__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"
__api__ = 7

import logging
import rapidjson
import re
import glob
import os

import eva.core
import eva.registry

from eva.tools import format_json

from eva.x import import_x
from eva.x import serialize_x
from eva.x import get_x_iobj

from eva.exceptions import InvalidParameter
from eva.exceptions import ResourceNotFound
from eva.exceptions import FunctionFailed
from eva.exceptions import ResourceBusy
from eva.exceptions import ResourceAlreadyExists

from functools import wraps
from eva.tools import SimpleNamespace

exts = {}
env = {}

iec_functions = {}

with_exts_lock = eva.core.RLocker('lm/extapi')

_d = SimpleNamespace(modified=set())

# extension functions


def get_version():
    return __api__


def get_polldelay():
    return eva.core.config.polldelay


def get_timeout():
    return eva.core.config.timeout


def critical():
    return eva.core.critical(from_driver=True)


def log_traceback():
    return eva.core.log_traceback()


def ext_constructor(f):
    from eva.lm.extensions.generic import LMExt as GenericExt

    @wraps(f)
    def do(self, *args, **kwargs):
        GenericExt.__init__(self, **kwargs)
        if kwargs.get('info_only'):
            return
        f(self, *args, **kwargs)

    return do


def load_data(ext):
    datapath = f'data/lm/extension_data/{ext.ext_id}'
    ext.data = eva.registry.key_get(datapath, default={})


def save_data(ext):
    datapath = f'data/lm/extension_data/{ext.ext_id}'
    eva.registry.key_set(datapath, ext.data)


# internal functions


def _get_ext_module_fname(mod, get_system=True):
    p = f'{eva.core.dir_lib}/eva/lm/extensions/{mod}.py'
    if get_system and os.path.exists(p):
        return p
    else:
        return f'{eva.core.dir_runtime}/lm-extensions/{mod}.py'


@with_exts_lock
def get_ext(ext_id):
    return exts.get(ext_id)


@with_exts_lock
def rebuild_env():
    global env, iec_functions
    _env = {}
    _iec_functions = {}
    for i, e in exts.copy().items():
        for f in e.get_functions():
            try:
                _env['{}_{}'.format(e.ext_id, f)] = getattr(e, f)
                logging.info('New macro function loaded: %s_%s' % (i, f))
            except:
                logging.error('Unable to add function %s extension %s' % (i, f))
                eva.core.log_traceback()
        for f, v in e.get_iec_functions().items():
            if '{}_{}'.format(e.ext_id, f) in _env:
                _iec_functions['{}_{}'.format(e.ext_id, f)] = {
                    'name': '{}_{}'.format(e.ext_id, f),
                    'description': v.get('description', ''),
                    'editable': False,
                    'src': None,
                    'type': 'extension',
                    'group': 'extensions/{}'.format(e.ext_id),
                    'var_in': v.get('var_in', []),
                    'var_out': v.get('var_out', []),
                }
    env = _env
    iec_functions = _iec_functions


def modhelp(mod, context):
    try:
        result = serialize_x(_get_ext_module_fname(mod),
                             'LMExt',
                             helpinfo=context)
    except Exception as e:
        raise FunctionFailed(e)
    if result is None:
        raise ResourceNotFound('Help context')
    return result


def modinfo(mod):
    try:
        result = serialize_x(_get_ext_module_fname(mod), 'LMExt', full=True)
        if result:
            try:
                del result['id']
            except:
                pass
        return result
    except Exception as e:
        raise FunctionFailed(e)


def list_mods():
    result = []
    mods = glob.glob(_get_ext_module_fname('*', get_system=False))
    for p in mods:
        f = os.path.basename(p)[:-3]
        if f not in ('__init__', 'generic'):
            try:
                d = serialize_x(p, 'LMExt', full=True)
                result.append(d)
            except:
                eva.core.log_traceback()
    for p in glob.glob(f'{eva.core.dir_lib}/eva/lm/extensions/*.py'):
        f = os.path.basename(p)[:-3]
        if f not in ('__init__', 'generic'):
            try:
                d = serialize_x(p, 'LMExt', full=True)
                result.append(d)
            except:
                eva.core.log_traceback()
    return sorted(result, key=lambda k: k['mod'])


@with_exts_lock
def load_ext(ext_id,
             ext_mod_id,
             cfg=None,
             start=True,
             rebuild=True,
             config_validated=False,
             _o=None,
             set_modified=True):
    if not ext_id:
        raise InvalidParameter('ext id not specified')
    if not re.match("^[A-Za-z0-9_-]*$", ext_id):
        raise InvalidParameter('ext %s id contains forbidden symbols' % ext_id)
    if _o is None:
        # import module
        try:
            ext_mod = import_x(_get_ext_module_fname(ext_mod_id))
            _api = ext_mod.__api__
            _author = ext_mod.__author__
            _version = ext_mod.__version__
            _description = ext_mod.__description__
            _license = ext_mod.__license__
            _functions = ext_mod.__functions__
            logging.info('Extension loaded %s v%s, author: %s, license: %s' %
                         (ext_mod_id, _version, _author, _license))
            logging.debug('%s: %s' % (ext_mod_id, _description))
            if _api > __api__:
                logging.error(
                    'Unable to activate extension %s: ' % ext_mod_id + \
                    'controller extension API version is %s, ' % __api__ + \
                    'extension API version is %s' % _api)
                raise FunctionFailed('unsupported ext API version')
        except Exception as e:
            raise FunctionFailed('unable to load ext mod {}: {}'.format(
                ext_mod_id, e))
    else:
        ext_mod = _o.__xmod__
    ext = ext_mod.LMExt(cfg=cfg,
                        config_validated=config_validated,
                        _xmod=ext_mod)
    if not ext.ready:
        raise FunctionFailed('unable to init ext mod %s' % ext_mod_id)
    ext.ext_id = ext_id
    if ext_id in exts:
        exts[ext_id].stop()
    exts[ext_id] = ext
    if set_modified:
        _d.modified.add(ext_id)
    ext.load()
    if start:
        ext.start()
    if rebuild:
        rebuild_env()
    return ext


@with_exts_lock
def unload_ext(ext_id, remove_data=False):
    ext = get_ext(ext_id)
    if ext is None:
        raise ResourceNotFound
    try:
        ext.stop()
        del exts[ext_id]
        _d.modified.add(ext_id)
        rebuild_env()
        if remove_data:
            if not eva.core.prepare_save():
                raise RuntimeError('Unable to prepare save')
            datapath = f'data/lm/extension_data/{ext.ext_id}'
            eva.registry.key_delete(datapath)
            if not eva.core.finish_save():
                raise RuntimeError('Unable to finish save')
        return True
    except:
        eva.core.log_traceback()
        return False


@with_exts_lock
def serialize(full=False, config=False):
    result = []
    for k, p in exts.copy().items():
        try:
            r = p.serialize(full=full, config=config)
            result.append(r)
        except:
            logging.error('extension %s serialize error' % k)
            eva.core.log_traceback()
    return result


@with_exts_lock
def set_ext_prop(ext_id, p, v):
    if not p and not isinstance(v, dict):
        raise InvalidParameter('property not specified')
    ext = get_ext(ext_id)
    if not ext:
        raise ResourceNotFound
    cfg = ext.cfg.copy()
    mod_id = ext.mod_id
    if p and not isinstance(v, dict):
        cfg[p] = v
    else:
        cfg.update(v)
    if v is None:
        del cfg[p]
    ext.validate_config(cfg, config_type='config')
    ext = load_ext(ext_id, mod_id, cfg, config_validated=True, _o=ext)
    if ext:
        return True


@eva.core.dump
@eva.core.minidump
def dump():
    return serialize(full=True, config=True)


@with_exts_lock
def load():
    try:
        for i, cfg in eva.registry.key_get_recursive('config/lm/extensions'):
            try:
                if i != cfg['id']:
                    raise ValueError(f'Extension {i} id mismatch')
                load_ext(cfg['id'],
                         cfg['mod'],
                         cfg=cfg['cfg'],
                         start=False,
                         rebuild=False,
                         set_modified=False)
            except Exception as e:
                logging.error(e)
                eva.core.log_traceback()
        _d.modified.clear()
        rebuild_env()
        return True
    except Exception as e:
        logging.error(f'Error loading LM extensions: {e}')
        eva.core.log_traceback()
        return False


@eva.core.save
@with_exts_lock
def save():
    try:
        for i in _d.modified:
            # do not use KeyError, as it may be raised by serialize
            kn = f'config/lm/extensions/{i}'
            if i in exts:
                eva.registry.key_set(kn, exts[i].serialize(config=True))
            else:
                eva.registry.key_delete(kn)
        _d.modified.clear()
        return True
    except Exception as e:
        logging.error(f'Error saving extensions: {e}')
        eva.core.log_traceback()
    return False


@with_exts_lock
def start():
    for k, p in exts.items():
        try:
            p.start()
        except Exception as e:
            logging.error('unable to start {}: {}'.format(k, e))
            eva.core.log_traceback()


@eva.core.stop
@with_exts_lock
def stop():
    for k, p in exts.items():
        try:
            p.stop()
        except Exception as e:
            logging.error('unable to stop {}: {}'.format(k, e))
            eva.core.log_traceback()
    if eva.core.config.db_update != 0:
        save()
