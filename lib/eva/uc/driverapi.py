__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"
__api__ = 10

import logging
import rapidjson
import re
import glob
import os
import threading
import importlib

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
from eva.exceptions import MethodNotImplemented

from functools import wraps
from eva.tools import SimpleNamespace

phis = {}
drivers = {}
items_by_phi = {}

shared_namespaces = {}

with_drivers_lock = eva.core.RLocker('uc/driverapi')
with_shared_namespaces_lock = eva.core.RLocker('uc/driverapi/shared_namespaces')

_d = SimpleNamespace(phi_modified=set(), driver_modified=set())

# public API functions, may be imported into PHI and LPI


def get_version():
    """
    Get DriverAPI version
    """
    return __api__


def get_polldelay():
    """
    Get UC poll delay
    """
    return eva.core.config.polldelay


def get_system_name():
    """
    Get EVA ICS node name
    """
    return eva.core.config.system_name


def get_sleep_step():
    """
    Get the default sleep step
    """
    return eva.core.sleep_step


def get_timeout():
    """
    Get the default core timeout
    """
    return eva.core.config.timeout


def transform_value(value, multiply=None, divide=None, round_to=None):
    """
    Generic value transformer

    Args:
        multiply: multiply the value on
        divide: divide the value on
        round_to: round the value to X digits after comma
    """
    if multiply is not None:
        value = value * multiply
    if divide is not None:
        value = value / divide
    if round_to is not None:
        value = round(value, round_to)
    return value


def critical():
    """
    Ask the core to raise critical exception
    """
    return eva.core.critical(from_driver=True)


def log_traceback():
    """
    Ask the core to log traceback of the latest error
    """
    return eva.core.log_traceback()


def lock(l, timeout=None, expires=None):
    """
    Acquire a core lock

    Args:
        l: lock ID/name
        timeout: timeout to acquire the lock
        expires: lock auto-expiration time
    """
    import eva.apikey
    import eva.sysapi
    if expires is None:
        e = eva.core.config.timeout
    else:
        e = expires
        if e > eva.core.config.timeout:
            e = eva.core.config.timeout
    if timeout is None:
        t = eva.core.config.timeout
    else:
        t = timeout
        if t > eva.core.config.timeout:
            t = eva.core.config.timeout
    return eva.sysapi.api.lock(eva.apikey.get_masterkey(),
                               l='eva:phi:' + l,
                               t=t,
                               e=e)


def unlock(l):
    """
    Release a core lock

    Args:
        l: lock ID/name
    """
    import eva.apikey
    import eva.sysapi
    return eva.sysapi.api.unlock(eva.apikey.get_masterkey(), l='eva:phi:' + l)


@with_drivers_lock
def get_phi_items(phi_id):
    return items_by_phi.get(phi_id)


def handle_phi_event(phi, port=None, data=None):
    """
    Ask the core to handle PHI event

    Args:
        phi: PHI module the event is from (usually =self)
        port: the port, where the event is happened
        data: { port: value } dict with the maximum of state ports available
              which may be changed because of the event
    """
    if not data:
        return
    iph = get_phi_items(phi.phi_id)
    if iph:
        for i in iph:
            if i.updates_allowed() and not i.is_destroyed():
                logging.debug('event on PHI %s, port %s, updating item %s' %
                              (phi.phi_id, port, i.full_id))
                i.update(driver_state_in=data)


@with_drivers_lock
def get_phi(phi_id):
    """
    Get PHI module by id
    """
    return phis.get(phi_id)


@with_drivers_lock
def get_driver(driver_id):
    """
    Get driver module by id
    """
    driver = drivers.get(driver_id)
    if driver:
        driver.phi = get_phi(driver.phi_id)
    return driver


def phi_constructor(f):
    """
    PHI constructor decorator

    Automatically calls parent construction, handles "info_only" module loads
    """
    from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI

    @wraps(f)
    def do(self, *args, **kwargs):
        GenericPHI.__init__(self, **kwargs)
        if kwargs.get('info_only'):
            return
        f(self, *args, **kwargs)

    return do


def lpi_constructor(f):
    """
    LPI constructor decorator

    Automatically calls parent construction, handles "info_only" module loads
    """
    from eva.uc.drivers.lpi.generic_lpi import LPI as GenericLPI

    @wraps(f)
    def do(self, *args, **kwargs):
        GenericLPI.__init__(self, **kwargs)
        if kwargs.get('info_only'):
            return
        f(self, *args, **kwargs)

    return do


# private API functions, not recommended to use


def _gen_phi_map(phi_id, pmap, action_map=False):
    g = {}
    if action_map:
        prop = 'action'
    else:
        prop = 'update'
    for i in pmap:
        if hasattr(i, prop + '_exec') and \
            hasattr(i, prop + '_driver_config') and \
            getattr(i, prop + '_exec').startswith('|'):
            try:
                driver_id = getattr(i, prop + '_exec')[1:]
                cfg = getattr(i, prop + '_driver_config')
                info = {
                    'oid': i.oid,
                    'driver': driver_id,
                    'info': get_driver(driver_id).serialize(full=False),
                    'cmap': get_driver(driver_id).get_item_cmap(cfg),
                    'cfg': getattr(i, prop + '_driver_config')
                }
            except:
                raise
            g.setdefault('items', []).append(info)
            g.setdefault('lpi', {}).setdefault(
                getattr(i, prop + '_exec')[1:].split('.')[1], []).append(info)
            g['info'] = get_phi(phi_id).serialize(full=False)
    result = {phi_id: g}
    return result


@with_drivers_lock
def get_map(phi_id=None, action_map=False):
    try:
        result = {}
        ibp = items_by_phi.copy()
        if phi_id:
            if not phi_id in ibp:
                return None
            return _gen_phi_map(phi_id, ibp[phi_id], action_map)
        for k, v in ibp.items():
            result.update(_gen_phi_map(k, v, action_map))
        return result
    except:
        eva.core.log_traceback()
        return None


def _get_phi_module_fname(mod):
    return f'{eva.core.dir_xc}/drivers/phi/{mod}.py'


def _get_lpi_module_fname(mod):
    return f'{eva.core.dir_xc}/drivers/lpi/{mod}.py'


@with_drivers_lock
def unlink_phi_mod(mod):
    if mod.find('/') != -1 or mod == 'generic_phi':
        return False
    for k, p in phis.copy().items():
        if p.phi_mod_id == mod:
            raise ResourceBusy('PHI module %s is in use, unable to unlink' %
                               mod)
    fname = _get_phi_module_fname(mod)
    try:
        eva.core.prepare_save()
        try:
            os.unlink(fname)
            return True
        finally:
            eva.core.finish_save()
    except FileNotFoundError:
        raise ResourceNotFound(f'PHI module file {fname}')
    except Exception as e:
        raise FunctionFailed('Unable to unlink PHI module {}: {}'.format(
            fname, e))


def put_phi_mod(mod, content, force=False):
    if mod.find('/') != -1:
        raise InvalidParameter('Invalid module file name')
    if mod == 'generic_phi':
        raise ResourceAlreadyExists('generic PHI can not be overriden')
    fname = _get_phi_module_fname(mod)
    if os.path.isfile(fname) and not force:
        raise ResourceAlreadyExists('PHI module {}'.format(fname))
    valid = False
    try:
        # verify code compilation
        compile(content, fname, 'exec')
        # save module code
        try:
            eva.core.prepare_save()
            with open(fname, 'w') as fd:
                fd.write(content)
            eva.core.finish_save()
        except Exception as e:
            raise FunctionFailed('Unable to put PHI module {}: {}'.format(
                fname, e))
        # verify saved module
        if 'mod' not in serialize_x(fname, 'PHI', full=True):
            raise FunctionFailed('Unable to verify module')
        valid = True
        return True
    except FunctionFailed:
        raise
    except:
        raise FunctionFailed(
            'Unable to check PHI module {}, invalid module code'.format(mod))
    finally:
        if not valid:
            try:
                eva.core.prepare_save()
                os.unlink(fname)
                eva.core.finish_save()
            except:
                logging.warning(
                    'Unable to delete invalid module {}'.format(fname))
                eva.core.log_traceback()


def modhelp_phi(mod, context):
    try:
        result = serialize_x(_get_phi_module_fname(mod),
                             'PHI',
                             helpinfo=context)
    except Exception as e:
        raise FunctionFailed(e)
    if result is None:
        raise ResourceNotFound('Help context')
    return result


def modinfo_phi(mod):
    try:
        result = serialize_x(_get_phi_module_fname(mod), 'PHI', full=True)
        if result:
            try:
                del result['id']
            except:
                pass
        return result
    except Exception as e:
        raise FunctionFailed(e)


def phi_discover(mod, interface, wait):
    try:
        return get_x_iobj(_get_phi_module_fname(mod),
                          'PHI').discover(interface, wait)
    except AttributeError:
        raise MethodNotImplemented
    except Exception as e:
        raise FunctionFailed(e)


def modhelp_lpi(mod, context):
    try:
        result = serialize_x(_get_lpi_module_fname(mod),
                             'LPI',
                             helpinfo=context)
    except Exception as e:
        raise FunctionFailed(e)
    if result is None:
        raise ResourceNotFound('Help context')
    return result


def modinfo_lpi(mod):
    try:
        result = serialize_x(_get_lpi_module_fname(mod), 'LPI', full=True)
        if result:
            try:
                del result['id']
                del result['lpi_id']
                del result['phi_id']
            except:
                pass
        return result
    except Exception as e:
        raise FunctionFailed(e)


def list_phi_mods():
    result = []
    phi_mods = glob.glob(_get_phi_module_fname('*'))
    for p in phi_mods:
        f = os.path.basename(p)[:-3]
        if f != '__init__':
            try:
                d = serialize_x(p, 'PHI', full=True)
                if d['equipment'][0] != 'abstract':
                    result.append(d)
            except:
                eva.core.log_traceback()
                pass
    return sorted(result, key=lambda k: k['mod'])


def list_lpi_mods():
    result = []
    lpi_mods = glob.glob(_get_lpi_module_fname('*'))
    for p in lpi_mods:
        f = os.path.basename(p)[:-3]
        if f != '__init__':
            try:
                d = serialize_x(p, 'LPI', full=True)
                if d['logic'] != 'abstract':
                    result.append(d)
            except:
                eva.core.log_traceback()
                pass
    return sorted(result, key=lambda k: k['mod'])


@with_drivers_lock
def register_item_update(i):
    u = i.update_exec
    if not u or u[0] != '|' or u.find('.') == -1:
        logging.error(
            'unable to register item ' + \
                    '%s for the driver events, invalid driver str: %s'
            % (i.oid, i.update_exec))
        return False
    phi_id = u[1:].split('.')[0]
    if not phi_id in phis:
        logging.error(
            'unable to register item %s for the driver events, no such PHI: %s'
            % (i.oid, phi_id))
        return False
    items_by_phi[phi_id].add(i)
    logging.debug('item %s registered for driver updates, PHI: %s' %
                  (i.full_id, phi_id))
    return True


@with_drivers_lock
def unregister_item_update(i):
    u = i.update_exec
    if not u or u[0] != '|' or u.find('.') == -1:
        logging.error(
            'unable to unregister item ' + \
                    '%s from the driver events, invalid driver str: %s'
            % (i.oid, i.update_exec))
        return False
    phi_id = u[1:].split('.')[0]
    if not phi_id in phis:
        logging.error(
            'unable to unregister item ' + \
                    '%s from the driver events, no such PHI: %s'
            % (i.oid, phi_id))
        return False
    try:
        items_by_phi[phi_id].remove(i)
        logging.debug('item %s unregistered from driver updates, PHI: %s' %
                      (i.full_id, phi_id))
        return True
    except:
        eva.core.log_traceback()
        return False


@with_drivers_lock
def load_phi(phi_id,
             phi_mod_id,
             phi_cfg=None,
             start=True,
             config_validated=False,
             _o=None,
             set_modified=True):
    if not phi_id:
        raise InvalidParameter('PHI id not specified')
    if not re.match("^[A-Za-z0-9_-]*$", phi_id):
        raise InvalidParameter('PHI %s id contains forbidden symbols' % phi_id)
    if _o is None:
        # import module
        try:
            phi_mod = import_x(_get_phi_module_fname(phi_mod_id))
            _api = phi_mod.__api__
            _author = phi_mod.__author__
            _version = phi_mod.__version__
            _description = phi_mod.__description__
            _license = phi_mod.__license__
            _equipment = phi_mod.__equipment__
            logging.info('PHI loaded %s v%s, author: %s, license: %s' %
                         (phi_mod_id, _version, _author, _license))
            logging.debug('%s: %s' % (phi_mod_id, _description))
            if _equipment == 'abstract':
                logging.error(
                    'Unable to activate PHI %s: ' % phi_mod_id + \
                    'abstract module'
                    )
                raise FunctionFailed('PHI module is abstract')
            if _api > __api__:
                logging.error(
                    'Unable to activate PHI %s: ' % phi_mod_id + \
                    'controller driver API version is %s, ' % __api__ + \
                    'PHI driver API version is %s' % _api)
                raise FunctionFailed('unsupported driver API version')
        except Exception as e:
            raise FunctionFailed('unable to load PHI mod {}: {}'.format(
                phi_mod_id, e))
    else:
        phi_mod = _o.__xmod__
    phi = phi_mod.PHI(phi_cfg=phi_cfg,
                      config_validated=config_validated,
                      _xmod=phi_mod)
    if not phi.ready:
        raise FunctionFailed('unable to init PHI mod %s' % phi_mod_id)
    phi.phi_id = phi_id
    phi.oid = 'phi:uc/%s/%s' % (eva.core.config.system_name, phi_id)
    if phi_id in phis:
        try:
            phis[phi_id]._stop_processors()
            phis[phi_id]._stop()
        except:
            eva.core.log_traceback()
    phis[phi_id] = phi
    if set_modified:
        _d.phi_modified.add(phi_id)
    if not phi_id in items_by_phi:
        items_by_phi[phi_id] = set()
    if start:
        try:
            phi._start()
            phi._start_processors()
        except:
            eva.core.log_traceback()
    ld = phi.get_default_lpi()
    if ld:
        load_driver('default', ld, phi_id, start=True)
    return phi


@with_drivers_lock
def load_driver(lpi_id,
                lpi_mod_id,
                phi_id,
                lpi_cfg=None,
                start=True,
                config_validated=False,
                _o=None,
                set_modified=True):
    if get_phi(phi_id) is None:
        raise ResourceNotFound(
            'Unable to load LPI, unknown PHI: {}'.format(phi_id))
    if not lpi_id:
        raise InvalidParameter('LPI id not specified')
    if not re.match("^[A-Za-z0-9_-]*$", lpi_id):
        raise InvalidParameter(
            'LPI {} id contains forbidden symbols'.format(lpi_id))
    if _o is None:
        # import module
        try:
            lpi_mod = import_x(_get_lpi_module_fname(lpi_mod_id))
            _api = lpi_mod.__api__
            _author = lpi_mod.__author__
            _version = lpi_mod.__version__
            _description = lpi_mod.__description__
            _license = lpi_mod.__license__
            _logic = lpi_mod.__logic__
            logging.info('LPI loaded %s v%s, author: %s, license: %s' %
                         (lpi_mod_id, _version, _author, _license))
            logging.debug('%s: %s' % (lpi_mod_id, _description))
            if _logic == 'abstract':
                logging.error(
                    'Unable to activate LPI %s: ' % lpi_mod_id + \
                    'abstract module'
                    )
                return False
            if _api > __api__:
                logging.error(
                    'Unable to activate LPI %s: ' % lpi_mod_id + \
                    'controller driver API version is %s, ' % __api__ + \
                    'LPI driver API version is %s' % _api)
                return False
        except Exception as e:
            raise FunctionFailed('unable to load LPI mod {}: {}'.format(
                lpi_mod_id, e))
    else:
        lpi_mod = _o.__xmod__
    lpi = lpi_mod.LPI(lpi_cfg=lpi_cfg,
                      phi_id=phi_id,
                      config_validated=config_validated,
                      _xmod=lpi_mod)
    if not lpi.ready:
        raise FunctionFailed('unable to init LPI mod %s' % lpi_mod_id)
    lpi.lpi_id = lpi_id
    lpi.driver_id = phi_id + '.' + lpi_id
    lpi.oid = 'driver:uc/%s/%s' % (eva.core.config.system_name, lpi.driver_id)
    if lpi.driver_id in drivers:
        try:
            drivers[lpi.driver_id]._stop()
        except:
            eva.core.log_traceback()
    drivers[lpi.driver_id] = lpi
    if set_modified:
        _d.driver_modified.add(lpi.driver_id)
    if start:
        try:
            lpi._start()
        except:
            eva.core.log_traceback()
    return lpi


@with_drivers_lock
def set_phi_prop(phi_id, p, v):
    if not p and not isinstance(v, dict):
        raise InvalidParameter('property not specified')
    phi = get_phi(phi_id)
    if not phi:
        raise ResourceNotFound
    cfg = phi.phi_cfg.copy()
    phi_mod_id = phi.phi_mod_id
    if p and not isinstance(v, dict):
        cfg[p] = v
    else:
        for prop, value in v.items():
            if value is not None and value != '':
                cfg[prop] = value
            else:
                try:
                    del cfg[prop]
                except:
                    pass
    if v is None:
        del cfg[p]
    phi.validate_config(cfg, config_type='config')
    phi = load_phi(phi_id,
                   phi_mod_id,
                   cfg,
                   start=True,
                   config_validated=True,
                   _o=phi)
    if phi:
        return True


@with_drivers_lock
def unload_phi(phi_id):
    phi = get_phi(phi_id)
    if phi is None:
        raise ResourceNotFound
    for k, l in drivers.copy().items():
        if l.phi_id == phi_id:
            if l.lpi_id == 'default':
                unload_driver(l.driver_id)
    if items_by_phi[phi_id]:
        raise ResourceBusy('Unable to unload PHI %s, it is in use' % (phi_id))
    try:
        phi._stop_processors()
        phi._stop()
    except:
        eva.core.log_traceback()
    try:
        phi.unload()
    except:
        eva.core.log_traceback()
    del phis[phi_id]
    _d.phi_modified.add(phi_id)
    return True


@with_drivers_lock
def set_driver_prop(driver_id, p, v):
    if not p and not isinstance(v, dict):
        raise InvalidParameter('property not specified')
    lpi = get_driver(driver_id)
    if not lpi:
        raise ResourceNotFound
    cfg = lpi.lpi_cfg.copy()
    if p and not isinstance(v, dict):
        cfg[p] = v
    else:
        for prop, value in v.items():
            if value is not None and value != '':
                cfg[prop] = value
            else:
                try:
                    del cfg[prop]
                except:
                    pass
    if v is None:
        del cfg[p]
    lpi.validate_config(cfg, config_type='config')
    lpi = load_driver(lpi.lpi_id,
                      lpi.lpi_mod_id,
                      lpi.phi_id,
                      cfg,
                      start=True,
                      config_validated=True,
                      _o=lpi)
    if lpi:
        return True


@with_drivers_lock
def unload_driver(driver_id):
    lpi = get_driver(driver_id)
    if lpi is None:
        raise ResourceNotFound
    err = None
    for i in items_by_phi[lpi.phi_id]:
        if i.update_exec and i.update_exec[1:] == driver_id:
            logging.error('Unable to unload driver %s, it is in use by %s' %
                          (driver_id, i.oid))
            err = i.oid
    if err:
        raise ResourceBusy(
            'Unable to unload driver, it is in use by {}'.format(err))
    try:
        lpi._stop()
    except:
        eva.core.log_traceback()
    del drivers[lpi.driver_id]
    _d.driver_modified.add(lpi.driver_id)
    return True


@with_drivers_lock
def serialize(full=False, config=False):
    return {
        'phi': serialize_phi(full=full, config=config),
        'lpi': serialize_lpi(full=full, config=config)
    }


@with_drivers_lock
def serialize_phi(full=False, config=False):
    result = []
    for k, p in phis.copy().items():
        try:
            r = p.serialize(full=full, config=config)
            result.append(r)
        except:
            logging.error('phi %s serialize error' % k)
            eva.core.log_traceback()
    return result


@with_drivers_lock
def serialize_lpi(full=False, config=False):
    result = []
    for k in drivers.copy().keys():
        try:
            p = get_driver(k)
            r = p.serialize(full=full, config=config)
            result.append(r)
        except:
            logging.error('driver %s serialize error' % k)
            eva.core.log_traceback()
    return result


@eva.core.dump
def dump():
    return serialize(full=True, config=True)


@with_drivers_lock
def load():
    try:
        for i, cfg in eva.registry.key_get_recursive('config/uc/phis'):
            try:
                if i != cfg['id']:
                    raise ValueError(f'PHI {i} id mismatch')
                else:
                    load_phi(i,
                             cfg['mod'],
                             phi_cfg=cfg['cfg'],
                             start=False,
                             set_modified=False)
            except Exception as e:
                logging.error(e)
                eva.core.log_traceback()
        for i, cfg in eva.registry.key_get_recursive('config/uc/drivers'):
            try:
                if i != cfg['id']:
                    raise ValueError(f'driver {i} id mismatch')
                else:
                    load_driver(cfg['lpi_id'],
                                cfg['mod'],
                                cfg['phi_id'],
                                lpi_cfg=cfg['cfg'],
                                start=False,
                                set_modified=False)
            except Exception as e:
                logging.error(e)
                eva.core.log_traceback()
        _d.phi_modified.clear()
        _d.driver_modified.clear()
        return True
    except Exception as e:
        logging.error(f'Error loading drivers: {e}')
        eva.core.log_traceback()
        return False


@eva.core.save
@with_drivers_lock
def save():
    try:
        if not eva.core.prepare_save():
            raise RuntimeError('Unable to prepare save')
        for i in _d.phi_modified:
            # do not use KeyError, as it may be raised by serialize
            kn = f'config/uc/phis/{i}'
            if i in phis:
                eva.registry.key_set(kn, phis[i].serialize(config=True))
            else:
                eva.registry.key_delete(kn)
        for i in _d.driver_modified:
            # do not use KeyError, as it may be raised by serialize
            kn = f'config/uc/drivers/{i}'
            if i in drivers:
                eva.registry.key_set(kn, drivers[i].serialize(config=True))
            else:
                eva.registry.key_delete(kn)
        _d.phi_modified.clear()
        _d.driver_modified.clear()
        if not eva.core.finish_save():
            raise RuntimeError('Unable to finish save')
        return True
    except Exception as e:
        logging.error(f'Error saving drivers: {e}')
        eva.core.log_traceback()
        return False


def start():
    for k, p in drivers.items():
        try:
            p._start()
        except Exception as e:
            logging.error('unable to start {}: {}'.format(k, e))
            eva.core.log_traceback()
    for k, p in phis.items():
        try:
            p._start()
        except Exception as e:
            logging.error('unable to start {}: {}'.format(k, e))
            eva.core.log_traceback()


def start_processors():
    for k, p in phis.items():
        try:
            p._start_processors()
        except Exception as e:
            logging.error('unable to start processors {}: {}'.format(k, e))
            eva.core.log_traceback()


def stop_processors():
    for k, p in phis.items():
        try:
            p._stop_processors()
        except Exception as e:
            logging.error('unable to stop processors {}: {}'.format(k, e))
            eva.core.log_traceback()


@with_drivers_lock
def stop():
    for k, p in drivers.items():
        try:
            p._stop()
        except Exception as e:
            logging.error('unable to stop {}: {}'.format(k, e))
            eva.core.log_traceback()
    for k, p in phis.items():
        try:
            p._stop()
        except Exception as e:
            logging.error('unable to stop {}: {}'.format(k, e))
            eva.core.log_traceback()
    if eva.core.config.db_update != 0:
        save()


class NS:

    def __init__(self):
        self.locker = threading.RLock()

    def has(self, obj_id):
        with self.locker:
            return hasattr(self, obj_id)

    def set(self, obj_id, val):
        with self.locker:
            setattr(self, obj_id, val)

    def get(self, obj_id, default=None):
        with self.locker:
            if not self.has(obj_id):
                if default is None:
                    return None
                else:
                    set(obj_id, default)
            return getattr(self, obj_id)


@with_shared_namespaces_lock
def get_shared_namespace(namespace_id):
    if namespace_id not in shared_namespaces:
        shared_namespaces[namespace_id] = NS()
    return shared_namespaces[namespace_id]
