__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2020 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.3.0"
__api__ = 6

import importlib
import logging
import rapidjson
import re
import glob
import os

import eva.core
from eva.tools import format_json

from functools import wraps

from eva.exceptions import InvalidParameter
from eva.exceptions import ResourceNotFound
from eva.exceptions import FunctionFailed
from eva.exceptions import ResourceBusy
from eva.exceptions import ResourceAlreadyExists

exts = {}
env = {}

iec_functions = {}

with_exts_lock = eva.core.RLocker('lm/extapi')

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
    from eva.lm.generic.generic_ext import LMExt as GenericExt

    @wraps(f)
    def do(self, *args, **kwargs):
        GenericExt.__init__(self, **kwargs)
        if kwargs.get('info_only'):
            return
        f(self, *args, **kwargs)

    return do


def load_data(ext):
    datapath = f'{eva.core.dir_runtime}/lm_ext_data.d/{ext.ext_id}.json'
    with open(datapath) as fh:
        ext.data = rapidjson.loads(fh.read())


def save_data(ext):
    datapath = f'{eva.core.dir_runtime}/lm_ext_data.d/{ext.ext_id}.json'
    with open(datapath, 'w') as fh:
        fh.write(rapidjson.dumps(ext.data))


# internal functions


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


def modinfo(mod):
    code = 'from eva.lm.extensions.%s import LMExt;' % mod + \
            ' s=LMExt(info_only=True).serialize(full=True)'
    try:
        d = {}
        exec(code, d)
        result = d.get('s')
        if result:
            try:
                del result['id']
            except:
                pass
        return result
    except Exception as e:
        raise FunctionFailed(e)


def modhelp(mod, context):
    code = 'from eva.lm.extensions.%s import LMExt;' % mod + \
            ' s=LMExt(info_only=True).serialize(helpinfo=\'%s\')' % context
    try:
        d = {}
        exec(code, d)
        result = d.get('s')
    except Exception as e:
        raise FunctionFailed(e)
    if result is None:
        raise ResourceNotFound('Help context not found')
    return result


def list_mods():
    result = []
    mods = glob.glob(eva.core.dir_lib + '/eva/lm/extensions/*.py')
    for p in mods:
        f = os.path.basename(p)[:-3]
        if f != '__init__':
            code = 'from eva.lm.extensions.%s import LMExt;' % f + \
                    ' s=LMExt(info_only=True).serialize(full=True);' + \
                    'f=LMExt(info_only=True).get_functions()'
            try:
                d = {}
                exec(code, d)
                result.append(d['s'])
            except:
                eva.core.log_traceback()
                pass
    return sorted(result, key=lambda k: k['mod'])


@with_exts_lock
def load_ext(ext_id, ext_mod_id, cfg=None, start=True, rebuild=True):
    if not ext_id: raise InvalidParameter('ext id not specified')
    if not re.match("^[A-Za-z0-9_-]*$", ext_id):
        raise InvalidParameter('ext %s id contains forbidden symbols' % ext_id)
    try:
        ext_mod = importlib.import_module('eva.lm.extensions.' + ext_mod_id)
        importlib.reload(ext_mod)
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
    ext = ext_mod.LMExt(cfg=cfg)
    if not ext.ready:
        raise FunctionFailed('unable to init ext mod %s' % ext_mod_id)
    ext.ext_id = ext_id
    if ext_id in exts:
        exts[ext_id].stop()
    exts[ext_id] = ext
    ext.load()
    if start: ext.start()
    if rebuild: rebuild_env()
    return ext


@with_exts_lock
def unload_ext(ext_id, remove_data=False):
    ext = get_ext(ext_id)
    if ext is None: raise ResourceNotFound
    try:
        ext.stop()
        del exts[ext_id]
        rebuild_env()
        if remove_data:
            datapath = f'{eva.core.dir_runtime}/lm_ext_data.d/{ext_id}.json'
            if os.path.isfile(datapath):
                os.unlink(datapath)
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
    if not ext: raise ResourceNotFound
    cfg = ext.cfg
    mod_id = ext.mod_id
    if p and not isinstance(v, dict):
        cfg[p] = v
    else:
        cfg.update(v)
    if v is None: del cfg[p]
    ext = load_ext(ext_id, mod_id, cfg)
    if ext:
        exts[ext_id] = ext
        return True


@eva.core.dump
def dump():
    return serialize(full=True, config=True)


def load():
    try:
        with open(eva.core.dir_runtime + '/lm_extensions.json') as fd:
            data = rapidjson.loads(fd.read())
        for p in data:
            try:
                load_ext(p['id'],
                         p['mod'],
                         cfg=p['cfg'],
                         start=False,
                         rebuild=False)
            except Exception as e:
                logging.error(e)
                eva.core.log_traceback()
        rebuild_env()
        return True
    except Exception as e:
        logging.error('unable to load uc_drivers.json: {}'.format(e))
        eva.core.log_traceback()
        return False


@eva.core.save
@with_exts_lock
def save():
    try:
        with open(eva.core.dir_runtime + '/lm_extensions.json', 'w') as fd:
            fd.write(format_json(serialize(config=True), minimal=False))
        for k, p in exts.items():
            try:
                p.save()
            except:
                logging.error(f'unable to save ext data for {p.ext_id}')
                log_traceback()
        return True
    except Exception as e:
        logging.error('unable to save ext config: {}'.format(e))
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
