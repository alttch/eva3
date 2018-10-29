__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "3.1.2"
__api__ = 2

import importlib
import logging
import jsonpickle
import re
import glob
import os
import threading

import eva.core
import eva.sysapi
import eva.apikey
from eva.tools import format_json

phis = {}
drivers = {}
items_by_phi = {}

# public API functions, may be imported into PHI and LPI


def get_version():
    return __api__


def get_polldelay():
    return eva.core.polldelay


def get_sleep_step():
    return eva.core.sleep_step


def get_timeout():
    return eva.core.timeout


def critical():
    return eva.core.critical(from_driver=True)


def log_traceback():
    return eva.core.log_traceback()


def lock(l, timeout=None, expires=None):
    if expires is None:
        e = eva.core.timeout
    else:
        e = expires
        if e > eva.core.timeout: e = eva.core.timeout
    if timeout is None:
        t = eva.core.timeout
    else:
        t = timeout
        if t > eva.core.timeout: t = eva.core.timeout
    return eva.sysapi.api.lock(
        eva.apikey.masterkey, l='eva:phi:' + l, timeout=t, expires=e)


def unlock(l):
    return eva.sysapi.api.unlock(eva.apikey.masterkey, l='eva:phi:' + l)


def handle_phi_event(phi, port, data):
    if not data: return
    iph = items_by_phi.get(phi.phi_id)
    if iph:
        for i in iph:
            if i.updates_allowed() and not i.is_destroyed():
                logging.debug('event on PHI %s, port %s, updating item %s' %
                              (phi.phi_id, port, i.full_id))
                t = threading.Thread(target=update_item, args=(i, data))
                t.start()


def get_phi(phi_id):
    return phis.get(phi_id)


def get_driver(driver_id):
    driver = drivers.get(driver_id)
    if driver:
        driver.phi = get_phi(driver.phi_id)
    return driver


# private API functions, not recommended to use


def unlink_phi_mod(mod):
    if mod.find('/') != -1 or mod == 'generic_phi': return False
    for k, p in phis.copy().items():
        if p.phi_mod_id == mod:
            logging.error('PHI module %s is in use, unable to unlink' % mod)
            return False
    fname = '{}/drivers/phi/{}.py'.format(eva.core.dir_xc, mod)
    try:
        if not eva.core.prepare_save(): return False
        os.unlink(fname)
        if not eva.core.finish_save(): return False
    except:
        logging.error('Unable to unlink PHI module %s' % fname)
        eva.core.log_traceback()
        return False
    return True


def put_phi_mod(mod, content, force=False):
    if mod.find('/') != -1 or mod == 'generic_phi': return False
    fname = '{}/drivers/phi/{}.py'.format(eva.core.dir_xc, mod)
    code = '{}\n\ns=PHI(info_only=True).serialize(full=True)'.format(content)
    try:
        d = {}
        exec(code, d)
        if 's' not in d or 'mod' not in d['s']:
            raise Exception('Invalid module code')
    except:
        logging.error(
            'Unable to check PHI module %s, invalid module code' % mod)
        eva.core.log_traceback()
        return False
    if os.path.isfile(fname) and not force:
        logging.error('Unable to overwrite PHI module %s' % fname)
        return False
    try:
        if not eva.core.prepare_save(): return False
        open(fname, 'w').write(content)
        if not eva.core.finish_save(): return False
    except:
        logging.error('Unable to put PHI module %s' % fname)
        eva.core.log_traceback()
        return False
    return True


def modhelp_phi(mod, context):
    code = 'from eva.uc.drivers.phi.%s import PHI;' % mod + \
            ' s=PHI(info_only=True).serialize(helpinfo=\'%s\')' % context
    try:
        d = {}
        exec(code, d)
        result = d.get('s')
        return result
    except:
        eva.core.log_traceback()
        return None


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
    except:
        eva.core.log_traceback()
        return None


def modhelp_lpi(mod, context):
    code = 'from eva.uc.drivers.lpi.%s import LPI;' % mod + \
            ' s=LPI(info_only=True).serialize(helpinfo=\'%s\')' % context
    try:
        d = {}
        exec(code, d)
        result = d.get('s')
        return result
    except:
        return None


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
    except:
        return None


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
                pass
    return sorted(result, key=lambda k: k['mod'])


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
    logging.debug(
        'item %s registered for driver updates, PHI: %s' % (i.full_id, phi_id))
    return True


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


def load_phi(phi_id, phi_mod_id, phi_cfg=None, start=True):
    if not phi_id: return False
    if not re.match("^[A-Za-z0-9_-]*$", phi_id):
        logging.debug('PHI %s id contains forbidden symbols' % phi_id)
        return False
    try:
        phi_mod = importlib.import_module('eva.uc.drivers.phi.' + phi_mod_id)
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
            return False
        if _api > __api__:
            logging.error(
                'Unable to activate PHI %s: ' % phi_mod_id + \
                'controller driver API version is %s, ' % __api__ + \
                'PHI driver API version is %s' % _api)
            return False
    except:
        logging.error('unable to load PHI mod %s' % phi_mod_id)
        eva.core.log_traceback()
        return False
    phi = phi_mod.PHI(phi_cfg=phi_cfg)
    if not phi.ready:
        logging.error('unable to init PHI mod %s' % phi_mod_id)
        return False
    phi.phi_id = phi_id
    phi.oid = 'phi:uc/%s/%s' % (eva.core.system_name, phi_id)
    if phi_id in phis:
        try:
            phis[phi_id]._stop()
        except:
            eva.core.log_traceback()
    phis[phi_id] = phi
    if not phi_id in items_by_phi:
        items_by_phi[phi_id] = set()
    if start:
        try:
            phi._start()
        except:
            eva.core.log_traceback()
    ld = phi.get_default_lpi()
    if ld:
        load_driver('default', ld, phi_id, start=True)
    return phi


def load_driver(lpi_id, lpi_mod_id, phi_id, lpi_cfg=None, start=True):
    if get_phi(phi_id) is None:
        logging.error('Unable to load LPI, unknown PHI: %s' % phi_id)
        return False
    if not lpi_id: return False
    if not re.match("^[A-Za-z0-9_-]*$", lpi_id):
        logging.debug('LPI %s id contains forbidden symbols' % lpi_id)
        return False
    try:
        lpi_mod = importlib.import_module('eva.uc.drivers.lpi.' + lpi_mod_id)
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
    except:
        logging.error('unable to load LPI mod %s' % lpi_mod_id)
        eva.core.log_traceback()
        return False
    lpi = lpi_mod.LPI(lpi_cfg=lpi_cfg, phi_id=phi_id)
    if not lpi.ready:
        logging.error('unable to init LPI mod %s' % lpi_mod_id)
        return False
    lpi.lpi_id = lpi_id
    lpi.driver_id = phi_id + '.' + lpi_id
    lpi.oid = 'driver:uc/%s/%s' % (eva.core.system_name, lpi.driver_id)
    if lpi.driver_id in drivers:
        try:
            drivers[lpi.driver_id]._stop()
        except:
            eva.core.log_traceback()
    drivers[lpi.driver_id] = lpi
    if start:
        try:
            lpi._start()
        except:
            eva.core.log_traceback()
    return lpi


def unload_phi(phi_id):
    phi = get_phi(phi_id)
    if phi is None: return False
    err = False
    for k, l in drivers.copy().items():
        if l.phi_id == phi_id:
            if l.lpi_id == 'default':
                ru = unload_driver(l.driver_id)
            else:
                ru = False
            if not ru:
                logging.error(
                    'Unable to unload PHI %s, it is in use by driver %s' %
                    (phi_id, k))
                err = True
    if items_by_phi[phi_id]:
        logging.error('Unable to unload PHI %s, it is in use' % (phi_id))
        err = True
    if err: return False
    try:
        phi._stop()
    except:
        eva.core.log_traceback()
    del phis[phi_id]
    return True


def unload_driver(driver_id):
    lpi = get_driver(driver_id)
    if lpi is None: return False
    err = False
    for i in items_by_phi[lpi.phi_id]:
        if i.update_exec and i.update_exec[1:] == driver_id:
            logging.error('Unable to unload driver %s, it is in use by %s' %
                          (driver_id, i.oid))
            err = True
    if err: return False
    try:
        lpi._stop()
    except:
        eva.core.log_traceback()
    del drivers[lpi.driver_id]
    return True


def serialize(full=False, config=False):
    return {
        'phi': serialize_phi(full=full, config=config),
        'lpi': serialize_lpi(full=full, config=config)
    }


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


def dump():
    return serialize(full=True, config=True)


def load():
    try:
        data = jsonpickle.decode(
            open(eva.core.dir_runtime + '/uc_drivers.json').read())
        _phi = data.get('phi')
        if _phi:
            for p in _phi:
                load_phi(p['id'], p['mod'], phi_cfg=p['cfg'], start=False)
        _lpi = data.get('lpi')
        if _lpi:
            for l in _lpi:
                load_driver(
                    l['lpi_id'],
                    l['mod'],
                    l['phi_id'],
                    lpi_cfg=l['cfg'],
                    start=False)
    except:
        logging.error('unable to load uc_drivers.json')
        eva.core.log_traceback()
        return False
    return True


def save():
    try:
        open(eva.core.dir_runtime + '/uc_drivers.json', 'w').write(
            format_json(serialize(config=True), minimal=False))
    except:
        logging.error('unable to save drivers config')
        eva.core.log_traceback()
        return False
    return True


def start():
    eva.core.append_dump_func('uc.driverapi', dump)
    eva.core.append_save_func(save)
    for k, p in drivers.items():
        try:
            p._start()
        except:
            eva.core.log_traceback()
    for k, p in phis.items():
        try:
            p._start()
        except:
            eva.core.log_traceback()


def stop():
    for k, p in drivers.items():
        try:
            p._stop()
        except:
            eva.core.log_traceback()
    for k, p in phis.items():
        try:
            p._stop()
        except:
            eva.core.log_traceback()
