__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "3.1.0"
__api__ = 1

import importlib
import logging
import jsonpickle

import eva.core
from eva.tools import format_json

phis = {}
drivers = {}

items_by_phi = {}


def get_version():
    return __api__


def get_polldelay():
    return eva.core.polldelay


def get_timeout():
    return eva.core.timeout


def critical():
    return eva.core.critical()


def get_phi(phi_id):
    return phis.get(phi_id)


def handle_phi_event(phi_id, port, data):
    #TODO - rewrite
    iph = items.by_phi.get(phi_id)
    if iph:
        ibp = iph.get(str(port))
        if ibp:
            for ie in ibp:
                if not isinstance(ie.update_exec, dict):
                    continue
                driver = drivers.get(ie.updat_exec.get('driver'))
                if driver is None:
                    continue
                if ie.item_type == 'mu':
                    multi = True
                else:
                    multi = False
                state = driver.state(cfg=ie.update_exec, multi=multi)
                if item.updates_allowed():
                    item.update_after_run(state)


def load_phi(phi_id, phi_mod_id, cfg=None, start=True):
    try:
        phi_mod = importlib.import_module('eva.uc.drivers.phi.' + phi_mod_id)
        importlib.reload(phi_mod)
        _api = phi_mod.__api__
        _author = phi_mod.__author__
        _version = phi_mod.__version__
        _description = phi_mod.__description__
        _license = phi_mod.__license__
        logging.info('PHI loaded %s v%s, author: %s, license: %s' %
                     (phi_mod_id, _version, _author, _license))
        logging.debug('%s: %s' % (phi_mod_id, _description))
        if _api > __api__:
            logging.error(
                'Unable to activate PHI %s: ' % phi_mod_id + \
                'controller driver API version is %s, ' % __api__ + \
                'PHI driver API version is %s' % _api)
            return False
    except:
        logging.error('unable to load phi mod %s' % phi_mod_id)
        eva.core.log_traceback()
        return False
    phi = phi_mod.PHI(cfg)
    phi.phi_id = phi_id
    if phi_id in phis:
        phis[phi_id].stop()
    phis[phi_id] = phi
    if start: phi.start()
    return phi


def unload_phi(phi_id):
    phi = get_phi(phi_id)
    if phi is None: return False
    phi.stop()
    del phis[phi_id]
    return True


def serialize(full=False, config=False):
    return {'phi': serialize_phi(full=full, config=config), 'drivers': []}


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


def dump():
    return serialize(full=True, config=True)


def load():
    try:
        data = jsonpickle.decode(
            open(eva.core.dir_runtime + '/uc_drivers.json').read())
        _phi = data.get('phi')
        if _phi:
            for p in _phi:
                load_phi(p['id'], p['mod'], cfg=p['cfg'], start=False)
    except:
        logging.error('unaboe to load uc_drivers.json')
        eva.core.log_traceback()
        return False
    return True


def save():
    try:
        open(eva.core.dir_runtime + '/uc_drivers.json', 'w').write(
            format_json(serialize(config=True), minimal=False))
    except:
        logging.error('unable to save driver state')
        eva.core.log_traceback()
        return False
    return True


def start():
    eva.core.append_stop_func(stop)
    eva.core.append_dump_func('uc.driverapi', dump)
    eva.core.append_save_func(save)
    for k, p in phis.items():
        p.start()


def stop():
    for p in phis:
        p.stop()
