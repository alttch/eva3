__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "3.1.0"
__api__ = 1

import eva.core

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

def parse_driver_str(s):
    if x.find('|') == -1:
        return None
    x = s.split('|')
    driver_id = x[1]
    cfg = None
    if len(x) > 2:
        cfg = '|'.join(x[2:])
    return driver_id, cfg

def handle_phi_event(phi_id, port, data):
    iph = items.by_phi.get(phi_id)
    if iph:
        ibp = iph.get(str(port))
        if ibp:
            for ie in ibp:
                c = parse_driver_str(ie.update_exec)
                if not c: continue
                _driver_id = c[1]
                _cfg = c[2]
                driver = drivers.get(driver_id)
                if driver is None:
                    continue
                if ie.item_type == 'mu':
                    multi = True
                else:
                    multi = False
                state = driver.state(cfg=_cfg, multi = multi)
                if item.updates_allowed():
                    item.update_after_run(state)
