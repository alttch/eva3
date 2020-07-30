__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2020 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.3.0"
__api__ = 8

import importlib
import logging
import rapidjson
import re
import glob
import os
import threading

import eva.core
from eva.tools import format_json

from eva.exceptions import InvalidParameter
from eva.exceptions import ResourceNotFound
from eva.exceptions import FunctionFailed
from eva.exceptions import ResourceBusy
from eva.exceptions import ResourceAlreadyExists
from eva.exceptions import MethodNotImplemented

from functools import wraps
from types import SimpleNamespace

phis = {}
drivers = {}
items_by_phi = {}

shared_namespaces = {}

with_drivers_lock = eva.core.RLocker('uc/driverapi')
with_shared_namespaces_lock = eva.core.RLocker('uc/driverapi/shared_namespaces')

_d = SimpleNamespace(modified=False)

# public API functions, may be imported into PHI and LPI


def get_version():
    return __api__


def get_polldelay():
    return eva.core.config.polldelay


def get_system_name():
    return eva.core.config.system_name


def get_sleep_step():
    return eva.core.sleep_step


def get_timeout():
    return eva.core.config.timeout


def critical():
    return eva.core.critical(from_driver=True)


def log_traceback():
    return eva.core.log_traceback()


def lock(l, timeout=None, expires=None):
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
    import eva.apikey
    import eva.sysapi
    return eva.sysapi.api.unlock(eva.apikey.get_masterkey(), l='eva:phi:' + l)


@with_drivers_lock
def handle_phi_event(phi, port=None, data=None):
    if not data:
        return
    iph = items_by_phi.get(phi.phi_id)
    if iph:
        for i in iph:
            if i.updates_allowed() and not i.is_destroyed():
                logging.debug('event on PHI %s, port %s, updating item %s' %
                              (phi.phi_id, port, i.full_id))
                eva.core.spawn(update_item, i, data)


@with_drivers_lock
def get_phi(phi_id):
    return phis.get(phi_id)


@with_drivers_lock
def get_driver(driver_id):
    driver = drivers.get(driver_id)
    if driver:
        driver.phi = get_phi(driver.phi_id)
    return driver


def phi_constructor(f):
    from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI

    @wraps(f)
    def do(self, *args, **kwargs):
        GenericPHI.__init__(self, **kwargs)
        if kwargs.get('info_only'):
            return
        f(self, *args, **kwargs)

    return do


def lpi_constructor(f):
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
                continue
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


@with_drivers_lock
def unlink_phi_mod(mod):
    if mod.find('/') != -1 or mod == 'generic_phi':
        return False
    for k, p in phis.copy().items():
        if p.phi_mod_id == mod:
            raise ResourceBusy('PHI module %s is in use, unable to unlink' %
                               mod)
    fname = '{}/drivers/phi/{}.py'.format(eva.core.dir_xc, mod)
    try:
        eva.core.prepare_save()
        os.unlink(fname)
        eva.core.finish_save()
        return True
    except Exception as e:
        raise FunctionFailed('Unable to unlink PHI module {}: {}'.format(
            fname, e))


def put_phi_mod(mod, content, force=False):
    if mod.find('/') != -1:
        raise InvalidParameter('Invalid module file name')
    if mod == 'generic_phi':
        raise ResourceAlreadyExists('generic PHI can not be overriden')
    fname = '{}/drivers/phi/{}.py'.format(eva.core.dir_xc, mod)
    if os.path.isfile(fname) and not force:
        raise ResourceAlreadyExists('PHI module {}'.format(fname))
    valid = False
    try:
        compile(content, fname, 'exec')
        try:
            eva.core.prepare_save()
            with open(fname, 'w') as fd:
                fd.write(content)
            eva.core.finish_save()
        except Exception as e:
            raise FunctionFailed('Unable to put PHI module {}: {}'.format(
                fname, e))
        d = {}
        code = 'from eva.uc.drivers.phi.%s import PHI;' % mod + \
                ' s=PHI(info_only=True).serialize(full=True)'
        exec(code, d)
        if 's' not in d or 'mod' not in d['s']:
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
    code = 'from eva.uc.drivers.phi.%s import PHI;' % mod + \
            ' s=PHI(info_only=True).serialize(helpinfo=\'%s\')' % context
    try:
        d = {}
        exec(code, d)
        result = d.get('s')
    except Exception as e:
        raise FunctionFailed(e)
    if result is None:
        raise ResourceNotFound('Help context not found')
    return result


def modinfo_phi(mod):
    code = 'from eva.uc.drivers.phi.%s import PHI;' % mod + \
            ' s=PHI(info_only=True).serialize(full=True)'
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


def phi_discover(mod, interface, wait):
    code = 'from eva.uc.drivers.phi.{} import PHI;'.format(mod) + \
            ' s=PHI(info_only=True).discover(interface, {})'.format(wait)
    try:
        d = {'interface': interface}
        exec(code, d)
        result = d.get('s')
        return result
    except AttributeError:
        raise MethodNotImplemented
    except Exception as e:
        raise FunctionFailed(e)


def modhelp_lpi(mod, context):
    code = 'from eva.uc.drivers.lpi.%s import LPI;' % mod + \
            ' s=LPI(info_only=True).serialize(helpinfo=\'%s\')' % context
    try:
        d = {}
        exec(code, d)
        result = d.get('s')
    except Exception as e:
        raise FunctionFailed(e)
    if result is None:
        raise ResourceNotFound('Help context not found')
    return result


def modinfo_lpi(mod):
    code = 'from eva.uc.drivers.lpi.%s import LPI;' % mod + \
            ' s=LPI(info_only=True).serialize(full=True)'
    try:
        d = {}
        exec(code, d)
        result = d.get('s')
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
    phi_mods = glob.glob(eva.core.dir_lib + '/eva/uc/drivers/phi/*.py')
    for p in phi_mods:
        f = os.path.basename(p)[:-3]
        if f != '__init__':
            code = 'from eva.uc.drivers.phi.%s import PHI;' % f + \
                    ' s=PHI(info_only=True).serialize(full=True)'
            try:
                d = {}
                exec(code, d)
                if d['s']['equipment'][0] != 'abstract':
                    result.append(d['s'])
            except:
                eva.core.log_traceback()
                pass
    return sorted(result, key=lambda k: k['mod'])


def list_lpi_mods():
    result = []
    lpi_mods = glob.glob(eva.core.dir_lib + '/eva/uc/drivers/lpi/*.py')
    for p in lpi_mods:
        f = os.path.basename(p)[:-3]
        if f != '__init__':
            code = 'from eva.uc.drivers.lpi.%s import LPI;' % f +  \
                    ' s=LPI(info_only=True).serialize(full=True)'
            try:
                d = {}
                exec(code, d)
                if d['s']['logic'] != 'abstract':
                    result.append(d['s'])
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


def update_item(i, data):
    i.update(driver_state_in=data)


@with_drivers_lock
def load_phi(phi_id, phi_mod_id, phi_cfg=None, start=True):
    if not phi_id:
        raise InvalidParameter('PHI id not specified')
    if not re.match("^[A-Za-z0-9_-]*$", phi_id):
        raise InvalidParameter('PHI %s id contains forbidden symbols' % phi_id)
    try:
        phi_mod = importlib.import_module('eva.uc.drivers.phi.' + phi_mod_id)
        # doesn't work but we hope
        importlib.reload(phi_mod)
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
    phi = phi_mod.PHI(phi_cfg=phi_cfg)
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
    set_modified()
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
def load_driver(lpi_id, lpi_mod_id, phi_id, lpi_cfg=None, start=True):
    if get_phi(phi_id) is None:
        raise ResourceNotFound(
            'Unable to load LPI, unknown PHI: {}'.format(phi_id))
    if not lpi_id:
        raise InvalidParameter('LPI id not specified')
    if not re.match("^[A-Za-z0-9_-]*$", lpi_id):
        raise InvalidParameter(
            'LPI {} id contains forbidden symbols'.format(lpi_id))
    try:
        lpi_mod = importlib.import_module('eva.uc.drivers.lpi.' + lpi_mod_id)
        # doesn't work but we hope
        importlib.reload(lpi_mod)
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
    lpi = lpi_mod.LPI(lpi_cfg=lpi_cfg, phi_id=phi_id)
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
    set_modified()
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
    cfg = phi.phi_cfg
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
    phi = load_phi(phi_id, phi_mod_id, cfg, start=True)
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
    set_modified()
    return True


@with_drivers_lock
def set_driver_prop(driver_id, p, v):
    if not p and not isinstance(v, dict):
        raise InvalidParameter('property not specified')
    lpi = get_driver(driver_id)
    if not lpi:
        raise ResourceNotFound
    cfg = lpi.lpi_cfg
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
    lpi = load_driver(lpi.lpi_id, lpi.lpi_mod_id, lpi.phi_id, cfg, start=True)
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
    set_modified()
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


def load():
    try:
        with open(eva.core.dir_runtime + '/uc_drivers.json') as fd:
            data = rapidjson.loads(fd.read())
        _phi = data.get('phi')
        if _phi:
            for p in _phi:
                try:
                    load_phi(p['id'], p['mod'], phi_cfg=p['cfg'], start=False)
                except Exception as e:
                    logging.error(e)
                    eva.core.log_traceback()
        _lpi = data.get('lpi')
        if _lpi:
            for l in _lpi:
                try:
                    load_driver(l['lpi_id'],
                                l['mod'],
                                l['phi_id'],
                                lpi_cfg=l['cfg'],
                                start=False)
                except Exception as e:
                    logging.error(e)
                    eva.core.log_traceback()
        _d.modified = False
        return True
    except Exception as e:
        logging.error('unable to load uc_drivers.json: {}'.format(e))
        eva.core.log_traceback()
        return False


@eva.core.save
def save():
    if _d.modified:
        try:
            with open(eva.core.dir_runtime + '/uc_drivers.json', 'w') as fd:
                fd.write(format_json(serialize(config=True), minimal=False))
            _d.modified = False
            return True
        except Exception as e:
            logging.error('unable to save drivers config: {}'.format(e))
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


def set_modified():
    _d.modified = True
