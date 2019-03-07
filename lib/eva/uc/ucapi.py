__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.1.2"

import cherrypy
import os
import glob
import eva.core
from eva.api import GenericHTTP_API
from eva.api import JSON_RPC_API
from eva.api import GenericAPI
from eva.api import cp_json_handler
from eva.api import cp_forbidden_key
from eva.api import http_api_result_ok
from eva.api import http_api_result_error
from eva.api import cp_api_error
from eva.api import cp_api_404
from eva.api import cp_need_master
from eva.api import http_real_ip
from eva.tools import dict_from_str
from eva.tools import oid_to_id
from eva.tools import parse_oid
from eva.tools import is_oid
from eva.tools import val_to_boolean
from eva import apikey
import eva.sysapi
import eva.uc.controller
import eva.uc.driverapi
import eva.uc.modbus
import eva.uc.owfs
import eva.ei
import jinja2
import jsonpickle
import logging

api = None


class UC_API(GenericAPI):

    def dev_uc_a(self, k=None):
        return eva.uc.controller.Q.actions_by_item_full_id

    def dev_uc_i(self, k=None, i=None):
        return eva.uc.controller.dump(i)

    def dev_uc_u(self, k=None, i=None):
        if i:
            return eva.uc.controller.get_unit(i)
        else:
            return eva.uc.controller.units_by_full_id

    def dev_uc_mu(self, k=None, i=None):
        if i:
            return eva.uc.controller.get_mu(i)
        else:
            return eva.uc.controller.mu_by_full_id

    def groups(self, k=None, tp=None):
        if apikey.check(k, master=True):
            if tp == 'U' or tp == 'unit':
                return sorted(eva.uc.controller.units_by_group.keys())
            elif tp == 'S' or tp == 'sensor':
                return sorted(eva.uc.controller.sensors_by_group.keys())
            elif tp == 'MU':
                return sorted(eva.uc.controller.mu_by_group.keys())
            else:
                return []
        else:
            groups = []
            m = None
            if tp == 'U' or tp == 'unit':
                m = eva.uc.controller.units_by_full_id
            elif tp == 'S' or tp == 'sensor':
                m = eva.uc.controller.sensors_by_full_id
            if m:
                for i, v in m.copy().items():
                    if apikey.check(k, v) and not v.group in groups:
                        groups.append(v.group)
                return sorted(groups)
            else:
                return []

    def state(self, k=None, i=None, full=False, group=None, tp=None):
        if i:
            item = eva.uc.controller.get_item(i)
            if not item or not apikey.check(k, item): return None
            if is_oid(i):
                t, iid = parse_oid(i)
                if not item or item.item_type != t: return None
            return item.serialize(full=full)
        elif tp or is_oid(group):
            if not tp:
                _tp, grp = parse_oid(group)
            else:
                _tp = tp
                grp = group
            if tp == 'U' or _tp == 'unit':
                gi = eva.uc.controller.units_by_full_id
            elif tp == 'S' or _tp == 'sensor':
                gi = eva.uc.controller.sensors_by_full_id
            else:
                return None
            result = []
            for i, v in gi.copy().items():
                if apikey.check(k, v) and \
                        (not group or \
                            eva.item.item_match(v, [], [grp])):
                    r = v.serialize(full=full)
                    result.append(r)
            return sorted(result, key=lambda k: k['oid'])

    def state_history(self,
                      k=None,
                      a=None,
                      i=None,
                      s=None,
                      e=None,
                      l=None,
                      x=None,
                      t=None,
                      w=None,
                      g=None):
        item = eva.uc.controller.get_item(i)
        if not item or not apikey.check(k, item): return False
        if is_oid(i):
            _t, iid = parse_oid(i)
            if not item or item.item_type != _t: return False
        return self.get_state_history(
            k=k,
            a=a,
            oid=item.oid,
            t_start=s,
            t_end=e,
            limit=l,
            prop=x,
            time_format=t,
            fill=w,
            fmt=g)

    def update(self, k=None, i=None, status=None, value=None, force_virtual=0):
        item = eva.uc.controller.get_item(i)
        if not item or not apikey.check(k, item): return False
        if status or value:
            return item.update_set_state(
                status=status, value=value, force_virtual=force_virtual)
        else:
            item.need_update.set()
            return True

    def action(self,
               k=None,
               i=None,
               action_uuid=None,
               nstatus=None,
               nvalue='',
               priority=None,
               q_timeout=None,
               wait=0):
        item = eva.uc.controller.get_unit(i)
        if not item or not apikey.check(k, item): return None
        return eva.uc.controller.exec_unit_action(
            unit=item,
            nstatus=nstatus,
            nvalue=nvalue,
            priority=priority,
            q_timeout=q_timeout,
            wait=wait,
            action_uuid=action_uuid)

    def action_toggle(self,
                      k=None,
                      i=None,
                      action_uuid=None,
                      priority=None,
                      q_timeout=None,
                      wait=0):
        item = eva.uc.controller.get_unit(i)
        if not item or not apikey.check(k, item): return None
        nstatus = 0 if item.status else 1
        return eva.uc.controller.exec_unit_action(
            unit=item,
            nstatus=nstatus,
            priority=priority,
            q_timeout=q_timeout,
            wait=wait,
            action_uuid=action_uuid)

    def disable_actions(self, k=None, i=None):
        item = eva.uc.controller.get_unit(i)
        if not item or not apikey.check(k, item): return None
        return item.disable_actions()

    def enable_actions(self, k=None, i=None):
        item = eva.uc.controller.get_unit(i)
        if not item or not apikey.check(k, item): return None
        return item.enable_actions()

    def result(self, k=None, uuid=None, item_id=None, group=None, state=None):
        if uuid:
            a = eva.uc.controller.Q.history_get(uuid)
            if not a or not apikey.check(k, a.item): return None
            return a
        else:
            result = []
            if item_id:
                _item_id = oid_to_id(item_id, 'unit')
                if _item_id is None: return None
                ar = None
                item = eva.uc.controller.get_unit(_item_id)
                if not apikey.check(k, item): return None
                if _item_id.find('/') > -1:
                    if _item_id in eva.uc.controller.Q.actions_by_item_full_id:
                        ar = eva.uc.controller.Q.actions_by_item_full_id[
                            _item_id]
                else:
                    if _item_id in eva.uc.controller.Q.actions_by_item_id:
                        ar = eva.uc.controller.Q.actions_by_item_id[_item_id]
                if ar is None: return []
            else:
                ar = eva.uc.controller.Q.actions
            for a in ar:
                if not apikey.check(k, a.item): continue
                if group and \
                        not eva.item.item_match(a.item, [], [ group ]):
                    continue
                if (state == 'Q' or state =='queued') and \
                        not a.is_status_queued():
                    continue
                elif (state == 'R' or state == 'running') and \
                        not a.is_status_running():
                    continue
                elif (state == 'F' or state == 'finished') and \
                        not a.is_finished():
                    continue
                result.append(a)
            return result

    def terminate(self, k=None, uuid=None, i=None):
        if uuid:
            a = eva.uc.controller.Q.history_get(uuid)
            if not a or not apikey.check(k, a.item): return None
            return a.kill()
        elif i:
            item = eva.uc.controller.get_unit(i)
            if not item or not apikey.check(k, item): return None
            return item.terminate()

    def kill(self, k=None, i=None):
        item = eva.uc.controller.get_unit(i)
        if not item or not apikey.check(k, item): return None
        result = item.kill()
        if not result: return 0
        if not item.action_allow_termination: return 2
        return 1

    def q_clean(self, k=None, i=None):
        item = eva.uc.controller.get_unit(i)
        if not item or not apikey.check(k, item): return None
        return item.q_clean()


# master functions for item configuration

    def get_config(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        item = eva.uc.controller.get_item(i)
        if is_oid(i):
            t, iid = parse_oid(i)
            if not item or item.item_type != t: return None
        return item.serialize(config=True) if item else None

    def save_config(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        item = eva.uc.controller.get_item(i)
        if is_oid(i):
            t, iid = parse_oid(i)
            if not item or item.item_type != t: return None
        return item.save() if item else None

    def list(self, k=None, group=None, tp=None):
        if not apikey.check(k, master=True): return None
        result = []
        if tp == 'U' or tp == 'unit':
            items = eva.uc.controller.units_by_full_id
        elif tp == 'S' or tp == 'sensor':
            items = eva.uc.controller.sensors_by_full_id
        elif tp == 'MU' or tp == 'mu':
            items = eva.uc.controller.mu_by_full_id
        else:
            items = eva.uc.controller.items_by_full_id
        for i, v in items.copy().items():
            if not group or eva.item.item_match(v, [], [group]):
                result.append(v.serialize(info=True))
        return sorted(result, key=lambda k: k['oid'])

    def list_props(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        item = eva.uc.controller.get_item(i)
        return item.serialize(props=True) if item else None

    def _set_props(self,
                   k=None,
                   i=None,
                   props=None,
                   save=None,
                   clean_snmp=False):
        if clean_snmp:
            if not api.set_prop(k, i=i, p='snmp_trap'):
                return False
        if props:
            for p, v in props.items():
                try:
                    if not api.set_prop(k, i=i, p=p, v=v, save=None):
                        return False
                except:
                    eva.core.log_traceback()
                    return False
        if save:
            api.save_config(k, i=i)
        return True

    def set_prop(self, k=None, i=None, p=None, v=None, save=False):
        if not apikey.check(k, master=True): return None
        item = eva.uc.controller.get_item(i)
        if item:
            result = item.set_prop(p, v, save)
            if result and item.config_changed and save:
                item.save()
            return result
        else:
            return None

    def create_unit(self,
                    k=None,
                    unit_id=None,
                    group=None,
                    virtual=False,
                    save=False):
        if not apikey.check(k, master=True): return None
        return eva.uc.controller.create_unit(
            unit_id=oid_to_id(unit_id, 'unit'),
            group=group,
            virtual=virtual,
            save=save)

    def create_sensor(self,
                      k=None,
                      sensor_id=None,
                      group=None,
                      virtual=False,
                      save=False):
        if not apikey.check(k, master=True): return None
        return eva.uc.controller.create_sensor(
            sensor_id=oid_to_id(sensor_id, 'sensor'),
            group=group,
            virtual=virtual,
            save=save)

    def create_mu(self,
                  k=None,
                  mu_id=None,
                  group=None,
                  virtual=False,
                  save=False):
        if not apikey.check(k, master=True): return None
        return eva.uc.controller.create_mu(
            mu_id=oid_to_id(mu_id, 'mu'),
            group=group,
            virtual=virtual,
            save=save)

    def create(self, k=None, oid=None, virtual=False, save=False):
        if not apikey.check(k, master=True):
            return None
        t, i = parse_oid(oid)
        if t is None or i is None: return None
        if t == 'unit':
            return api.create_unit(k, i, virtual=virtual, save=save)
        if t == 'sensor':
            return api.create_sensor(k, i, virtual=virtual, save=save)
        if t == 'mu':
            return api.create_mu(k, i, virtual=virtual, save=save)
        return None

    def load_device_config(self, tpl_config={}, device_tpl=None):
        try:
            tpl = jinja2.Template(
                open(eva.core.dir_runtime + '/tpl/' + device_tpl +
                     '.json').read())
        except:
            logging.error('device template file error: %s' % device_tpl)
            eva.core.log_traceback()
            return None
        try:
            cfg = jsonpickle.decode(tpl.render(tpl_config))
        except:
            logging.error('device template decode error')
            eva.core.log_traceback()
            return None
        return cfg

    def list_device_tpl(self, k=None):
        if not apikey.check(k, allow=['device']): return None
        result = []
        for i in glob.glob(eva.core.dir_runtime + '/tpl/*.json'):
            result.append(os.path.basename(i)[:-5])
        return sorted(result)

    def create_device(self, k=None, tpl_config={}, device_tpl=None, save=False):
        if not apikey.check(k, allow=['device']): return None
        _k = eva.apikey.masterkey
        cfg = self.load_device_config(
            tpl_config=tpl_config, device_tpl=device_tpl)
        if cfg is None: return False
        units = cfg.get('units')
        if units:
            for u in units:
                try:
                    i = u['id']
                    g = u.get('group')
                except:
                    return False
                try:
                    if not api.create_unit(_k, unit_id=i, group=g, save=save):
                        return False
                except:
                    eva.core.log_traceback()
                    return False
        sensors = cfg.get('sensors')
        if sensors:
            for u in sensors:
                try:
                    i = u['id']
                    g = u.get('group')
                except:
                    return False
                try:
                    if not api.create_sensor(
                            _k, sensor_id=i, group=g, save=save):
                        return False
                except:
                    eva.core.log_traceback()
                    return False
        mu = cfg.get('mu')
        if mu:
            for u in mu:
                try:
                    i = u['id']
                    g = u.get('group')
                except:
                    return False
                try:
                    if not api.create_mu(_k, mu_id=i, group=g, save=save):
                        return False
                except:
                    eva.core.log_traceback()
                    return False
        return api.update_device(k, cfg=cfg, save=save)

    def update_device(self,
                      k=None,
                      tpl_config={},
                      device_tpl=None,
                      cfg=None,
                      save=False):
        if not apikey.check(k, allow=['device']): return None
        _k = eva.apikey.masterkey
        if cfg is None:
            cfg = self.load_device_config(
                tpl_config=tpl_config, device_tpl=device_tpl)
        if cfg is None: return False
        cvars = cfg.get('cvars')
        if cvars:
            for i, v in cvars.items():
                try:
                    if not eva.sysapi.api.set_cvar(_k, i, v):
                        return False
                except:
                    eva.core.log_traceback()
                    return False
        units = cfg.get('units')
        if units:
            for u in units:
                try:
                    i = u['id']
                    g = u['group']
                except:
                    return False
                try:
                    if not api._set_props(_k, 'unit:{}/{}'.format(g, i),
                                          u.get('props'), save, True):
                        return False
                except:
                    eva.core.log_traceback()
                    return False
        sensors = cfg.get('sensors')
        if sensors:
            for u in sensors:
                try:
                    i = u['id']
                    g = u['group']
                except:
                    return False
                try:
                    if not api._set_props(_k, 'sensor:{}/{}'.format(g, i),
                                          u.get('props'), save, True):
                        return False
                except:
                    eva.core.log_traceback()
                    return False
        mu = cfg.get('mu')
        if mu:
            for u in mu:
                try:
                    i = u['id']
                    g = u['group']
                except:
                    return False
                try:
                    if not api._set_props(_k, 'mu:{}/{}'.format(g, i),
                                          u.get('props'), save):
                        return False
                except:
                    eva.core.log_traceback()
                    return False
        return True

    def destroy_device(self, k=None, tpl_config={}, device_tpl=None):
        if not apikey.check(k, allow=['device']): return None
        _k = eva.apikey.masterkey
        cfg = self.load_device_config(
            tpl_config=tpl_config, device_tpl=device_tpl)
        if cfg is None: return False
        mu = cfg.get('mu')
        if mu:
            for m in mu:
                try:
                    i = m['id']
                    g = u['group']
                except:
                    return False
                try:
                    api.destroy(_k, 'mu:{}/{}'.format(g, i))
                except:
                    pass
        units = cfg.get('units')
        if units:
            for u in units:
                try:
                    i = u['id']
                    g = u['group']
                except:
                    return False
                try:
                    api.destroy(_k, 'unit:{}/{}'.format(g, i))
                except:
                    pass
        sensors = cfg.get('sensors')
        if sensors:
            for u in sensors:
                try:
                    i = u['id']
                    g = u['group']
                except:
                    return False
                try:
                    api.destroy(_k, 'sensor:{}/{}'.format(g, i))
                except:
                    pass
        cvars = cfg.get('cvars')
        if cvars:
            for cvar in cvars.keys():
                try:
                    eva.sysapi.api.set_cvar(_k, cvar)
                except:
                    pass
        return True

    def clone(self, k=None, i=None, n=None, g=None, save=False):
        if not apikey.check(k, master=True): return None
        return eva.uc.controller.clone_item(
            item_id=i, new_item_id=n, group=g, save=save)

    def clone_group(self, k=None, g=None, n=None, p=None, r=None, save=False):
        if not apikey.check(k, master=True): return None
        return eva.uc.controller.clone_group(
            group=g, new_group=n, prefix=p, new_prefix=r, save=save)

    def destroy(self, k=None, i=None, g=None):
        if not apikey.check(k, master=True): return None
        return eva.uc.controller.destroy_item(i) if i \
                else eva.uc.controller.destroy_group(g)

    # master functions for modbus port management

    def create_modbus_port(self,
                           k=None,
                           i=None,
                           params=None,
                           lock=False,
                           timeout=None,
                           delay=None,
                           retries=None,
                           save=False):
        if not apikey.check(k, master=True): return None
        if not i or not params: return False
        result = eva.uc.modbus.create_modbus_port(
            i, params, lock=lock, timeout=timeout, delay=delay, retries=retries)
        if result and save: eva.uc.modbus.save()
        return result

    def destroy_modbus_port(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        result = eva.uc.modbus.destroy_modbus_port(i)
        if result and eva.core.db_update == 1: eva.uc.modbus.save()
        return result

    def list_modbus_ports(self, k=None):
        if not apikey.check(k, master=True): return None
        return sorted(eva.uc.modbus.serialize(), key=lambda k: k['id'])

    def test_modbus_port(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        port = eva.uc.modbus.get_port(i)
        result = True if port else False
        if result: port.release()
        return result

    # master functions for owfs bus management

    def create_owfs_bus(self,
                        k=None,
                        i=None,
                        location=None,
                        lock=False,
                        timeout=None,
                        delay=None,
                        retries=None,
                        save=False):
        if not apikey.check(k, master=True): return None
        if not i or not location: return False
        result = eva.uc.owfs.create_owfs_bus(
            i,
            location,
            lock=lock,
            timeout=timeout,
            delay=delay,
            retries=retries)
        if result and save: eva.uc.owfs.save()
        return result

    def destroy_owfs_bus(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        result = eva.uc.owfs.destroy_owfs_bus(i)
        if result and eva.core.db_update == 1: eva.uc.owfs.save()
        return result

    def list_owfs_buses(self, k=None):
        if not apikey.check(k, master=True): return None
        return sorted(eva.uc.owfs.serialize(), key=lambda k: k['id'])

    def test_owfs_bus(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        bus = eva.uc.owfs.get_bus(i)
        result = True if bus else False
        if result: bus.release()
        return result

    def scan_owfs_bus(self,
                      k=None,
                      i=None,
                      p=None,
                      a=None,
                      n=None,
                      has_all=None,
                      full=None):
        if not apikey.check(k, master=True): return None
        bus = eva.uc.owfs.get_bus(i)
        if not bus: return None
        bus.release()
        kwargs = {}
        if p: kwargs['sensor_type'] = p
        if a:
            kwargs['has_' + ('all' if has_all else 'one')] = a
        if n:
            eq = [n]
        else:
            eq = [s.path for s in bus._ow.find(**kwargs)]
        result = []
        for r in eq:
            sensor = bus._ow.sensor(r)
            s = {'type': sensor.type, 'path': sensor.path}
            if full:
                s['attrs'] = sensor.attrs
                if a:
                    for attr in (a if isinstance(a, list) else [a]):
                        s[attr] = bus.read(r, attr)
            result.append(s)
        return sorted(
            sorted(result, key=lambda k: k['path']), key=lambda k: k['type'])

    # master functions for driver configuration

    def load_phi(self, k=None, i=None, m=None, cfg=None, save=False):
        if not apikey.check(k, master=True): return None
        if not i or not m: return None
        try:
            _cfg = dict_from_str(cfg)
        except:
            eva.core.log_traceback()
            return None
        if eva.uc.driverapi.load_phi(i, m, _cfg):
            if save: eva.uc.driverapi.save()
            return eva.uc.driverapi.get_phi(i).serialize(full=True, config=True)

    def load_driver(self, k=None, i=None, m=None, p=None, cfg=None, save=False):
        if not apikey.check(k, master=True): return None
        if not i or not m or not p: return None
        try:
            _cfg = dict_from_str(cfg)
        except:
            eva.core.log_traceback()
            return None
        if eva.uc.driverapi.load_driver(i, m, p, _cfg):
            if save: eva.uc.driverapi.save()
            return eva.uc.driverapi.get_driver(p + '.' + i).serialize(
                full=True, config=True)

    def unload_phi(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        if not i: return None
        result = eva.uc.driverapi.unload_phi(i)
        if result and eva.core.db_update == 1: eva.uc.driverapi.save()
        return result

    def unlink_phi_mod(self, k=None, m=None):
        if not apikey.check(k, master=True): return None
        if not m: return None
        result = eva.uc.driverapi.unlink_phi_mod(m)
        return result

    def put_phi_mod(self, k=None, m=None, c=None, force=None):
        if not apikey.check(k, master=True): return None
        if not m: return None
        result = eva.uc.driverapi.put_phi_mod(m, c, force)
        return result if not result else api.modinfo_phi(k, m)

    def unload_driver(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        if not i: return None
        result = eva.uc.driverapi.unload_driver(i)
        if result and eva.core.db_update == 1: eva.uc.driverapi.save()
        return result

    def get_phi_map(self, k=None, phi_id=None, action_map=None):
        if not apikey.check(k, master=True): return None
        return eva.uc.driverapi.get_map(phi_id, action_map)

    def list_phi(self, k=None, full=False):
        if not apikey.check(k, master=True): return None
        return sorted(
            eva.uc.driverapi.serialize_phi(full=full, config=full),
            key=lambda k: k['id'])

    def list_drivers(self, k=None, full=False):
        if not apikey.check(k, master=True): return None
        return sorted(
            eva.uc.driverapi.serialize_lpi(full=full, config=full),
            key=lambda k: k['id'])

    def get_phi(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        if not i: return None
        phi = eva.uc.driverapi.get_phi(i)
        if phi:
            return phi.serialize(full=True, config=True)
        else:
            return False

    def set_phi_prop(self, k=None, i=None, p=None, v=None, save=False):
        if not apikey.check(k, master=True): return None
        if not i: return None
        phi = eva.uc.driverapi.get_phi(i)
        if phi:
            if eva.uc.driverapi.set_phi_prop(i, p, v):
                if save: eva.uc.driverapi.save()
                return True
        return False

    def get_driver(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        if not i: return None
        lpi = eva.uc.driverapi.get_driver(i)
        if lpi:
            return lpi.serialize(full=True, config=True)
        else:
            return False

    def set_driver_prop(self, k=None, i=None, p=None, v=None, save=False):
        if not apikey.check(k, master=True): return None
        if not i or i.split('.')[-1] == 'default': return None
        lpi = eva.uc.driverapi.get_driver(i)
        if lpi:
            if eva.uc.driverapi.set_driver_prop(i, p, v):
                if save: eva.uc.driverapi.save()
                return True
        return False

    def test_phi(self, k=None, i=None, c=None):
        if not apikey.check(k, master=True): return None
        if not i: return False
        phi = eva.uc.driverapi.get_phi(i)
        if phi:
            return phi.test(c)
        else:
            return False

    def exec_phi(self, k=None, i=None, c=None, a=None):
        if not apikey.check(k, master=True): return None
        if not i: return False
        phi = eva.uc.driverapi.get_phi(i)
        if phi:
            return phi.exec(c, a)
        else:
            return False

    def list_phi_mods(self, k=None):
        if not apikey.check(k, master=True): return None
        return eva.uc.driverapi.list_phi_mods()

    def list_lpi_mods(self, k=None):
        if not apikey.check(k, master=True): return None
        return eva.uc.driverapi.list_lpi_mods()

    def modinfo_phi(self, k=None, m=None):
        if not apikey.check(k, master=True): return None
        return eva.uc.driverapi.modinfo_phi(m)

    def modinfo_lpi(self, k=None, m=None):
        if not apikey.check(k, master=True): return None
        return eva.uc.driverapi.modinfo_lpi(m)

    def modhelp_phi(self, k=None, m=None, c=None):
        if not apikey.check(k, master=True) or not c: return None
        return eva.uc.driverapi.modhelp_phi(m, c)

    def modhelp_lpi(self, k=None, m=None, c=None):
        if not apikey.check(k, master=True) or not c: return None
        return eva.uc.driverapi.modhelp_lpi(m, c)

    def assign_driver(self, k=None, i=None, d=None, c=None, save=False):
        if not apikey.check(k, master=True): return None
        item = eva.uc.controller.get_item(i)
        if not item: return None
        if not api.set_prop(k, i, 'update_driver_config', c): return False
        if item.item_type == 'unit' and \
                not api.set_prop(k, i, 'action_driver_config', c):
            return False
        drv_p = '|' + d if d else None
        if not api.set_prop(k, i, 'update_exec', drv_p): return False
        if item.item_type == 'unit' and \
                not api.set_prop(k, i, 'action_exec', drv_p):
            return False
        if save: item.save()
        return True


class UC_HTTP_API(JSON_RPC_API, GenericHTTP_API, UC_API):

    def cp_check_perm(self, api_key=None, k=None, path_info=None):
        if cherrypy.serving.request.path_info[:8] == '/put_phi':
            rlp = ['c']
        else:
            rlp = None
        super().cp_check_perm(api_key=api_key, rlp=rlp, path_info=path_info)

    def __init__(self):
        super().__init__()
        if eva.core.development:
            UC_API.dev_uc_a.exposed = True
            UC_API.dev_uc_i.exposed = True
            UC_API.dev_uc_u.exposed = True
            UC_API.dev_uc_mu.exposed = True
        UC_HTTP_API.index.exposed = True
        UC_HTTP_API.groups.exposed = True
        UC_HTTP_API.state.exposed = True
        UC_HTTP_API.state_history.exposed = True
        UC_HTTP_API.update.exposed = True
        UC_HTTP_API.action.exposed = True
        UC_HTTP_API.action_toggle.exposed = True
        UC_HTTP_API.result.exposed = True
        UC_HTTP_API.terminate.exposed = True
        UC_HTTP_API.kill.exposed = True
        UC_HTTP_API.q_clean.exposed = True
        UC_HTTP_API.disable_actions.exposed = True
        UC_HTTP_API.enable_actions.exposed = True

        UC_HTTP_API.get_config.exposed = True
        UC_HTTP_API.save_config.exposed = True
        UC_HTTP_API.list.exposed = True
        UC_HTTP_API.list_props.exposed = True
        UC_HTTP_API.set_prop.exposed = True

        UC_HTTP_API.create.exposed = True
        UC_HTTP_API.create_unit.exposed = True
        UC_HTTP_API.create_sensor.exposed = True
        UC_HTTP_API.create_mu.exposed = True
        UC_HTTP_API.list_device_tpl.exposed = True
        UC_HTTP_API.create_device.exposed = True
        UC_HTTP_API.update_device.exposed = True

        UC_HTTP_API.clone.exposed = True
        UC_HTTP_API.clone_group.exposed = True

        UC_HTTP_API.destroy.exposed = True
        UC_HTTP_API.destroy_device.exposed = True

        UC_HTTP_API.create_modbus_port.exposed = True
        UC_HTTP_API.destroy_modbus_port.exposed = True
        UC_HTTP_API.list_modbus_ports.exposed = True
        UC_HTTP_API.test_modbus_port.exposed = True

        UC_HTTP_API.create_owfs_bus.exposed = True
        UC_HTTP_API.destroy_owfs_bus.exposed = True
        UC_HTTP_API.list_owfs_buses.exposed = True
        UC_HTTP_API.test_owfs_bus.exposed = True
        UC_HTTP_API.scan_owfs_bus.exposed = True

        UC_HTTP_API.load_phi.exposed = True
        UC_HTTP_API.unload_phi.exposed = True
        UC_HTTP_API.unlink_phi_mod.exposed = True
        UC_HTTP_API.put_phi_mod.exposed = True
        UC_HTTP_API.list_phi.exposed = True
        UC_HTTP_API.get_phi_map.exposed = True
        UC_HTTP_API.get_phi.exposed = True

        UC_HTTP_API.load_driver.exposed = True
        UC_HTTP_API.list_drivers.exposed = True
        UC_HTTP_API.unload_driver.exposed = True
        UC_HTTP_API.get_driver.exposed = True

        UC_HTTP_API.test_phi.exposed = True
        UC_HTTP_API.exec_phi.exposed = True

        UC_HTTP_API.list_phi_mods.exposed = True
        UC_HTTP_API.list_lpi_mods.exposed = True

        UC_HTTP_API.modinfo_phi.exposed = True
        UC_HTTP_API.modinfo_lpi.exposed = True

        UC_HTTP_API.modhelp_phi.exposed = True
        UC_HTTP_API.modhelp_lpi.exposed = True

        UC_HTTP_API.set_phi_prop.exposed = True
        UC_HTTP_API.set_driver_prop.exposed = True
        UC_HTTP_API.assign_driver.exposed = True

        UC_HTTP_API.info.exposed = True

    def state_history(self,
                      k=None,
                      a=None,
                      i=None,
                      p=None,
                      s=None,
                      e=None,
                      l=None,
                      x=None,
                      t=None,
                      w=None,
                      g=None):
        if (isinstance(i, str) and i and i.find(',') != -1) or \
                isinstance(i, list):
            if not w:
                raise cp_api_error(
                    '"w" param required to process multiple items')
            if isinstance(i, str):
                items = i.split(',')
            else:
                items = i
            if not g or g == 'list':
                result = {}
            else:
                raise cp_api_error(
                    'format should be list only to process multiple items')
            for i in items:
                r = super().state_history(
                    k=k, a=a, i=i, s=s, e=e, l=l, x=x, t=t, w=w, g=g)
                if r is None: raise cp_api_error('internal error')
                if r is False: raise cp_api_404()
                result['t'] = r['t']
                if 'status' in r:
                    result[i + '/status'] = r['status']
                if 'value' in r:
                    result[i + '/value'] = r['value']
            return result
        else:
            result = super().state_history(
                k=k, a=a, i=i, s=s, e=e, l=l, x=x, t=t, w=w, g=g)
            if result is None: raise cp_api_error('internal error')
            if result is False: raise cp_api_404()
            return result

    def update(self, k=None, i=None, s=None, v=None, force_virtual=''):
        if force_virtual:
            _fv = True
        else:
            _fv = False
        if s is None:
            _s = None
        else:
            try:
                _s = int(s)
            except:
                raise cp_api_error('status is not an integer')
        if super().update(k, i, _s, v, _fv):
            return http_api_result_ok()
        else:
            raise cp_api_404()

    def action(self, k=None, i=None, u=None, s=None, v='', p=None, q=None, w=0):
        if w:
            try:
                _w = float(w)
            except:
                raise cp_api_error('wait is not a float')
        else:
            _w = None
        if p:
            try:
                _p = int(p)
            except:
                raise cp_api_error('priority is not an integer')
        else:
            _p = None
        if q:
            try:
                _q = float(q)
            except:
                raise cp_api_error('q_timeout is not a float')
        else:
            _q = None
        a = super().action(
            k=k,
            i=i,
            action_uuid=u,
            nstatus=s,
            nvalue=v,
            priority=_p,
            q_timeout=_q,
            wait=_w)
        if not a:
            raise cp_api_404()
        if a.is_status_dead():
            raise cp_api_error('queue error, action is dead')
        return a.serialize()

    def action_toggle(self, k=None, i=None, u=None, p=None, q=None, w=0):
        if w:
            try:
                _w = float(w)
            except:
                raise cp_api_error('wait is not a float')
        else:
            _w = None
        if p:
            try:
                _p = int(p)
            except:
                raise cp_api_error('priority is not an integer')
        else:
            _p = None
        if q:
            try:
                _q = float(q)
            except:
                raise cp_api_error('q_timeout is not a float')
        else:
            _q = None
        a = super().action_toggle(
            k=k, i=i, action_uuid=u, priority=_p, q_timeout=_q, wait=_w)
        if not a:
            raise cp_api_404()
        if a.is_status_dead():
            raise cp_api_error('queue error, action is dead')
        return a.serialize()

    def result(self, k=None, u=None, i=None, g=None, s=None):
        a = super().result(k, u, i, g, s)
        if a is None:
            raise cp_api_404()
        if isinstance(a, list):
            return [x.serialize() for x in a]
        else:
            return a.serialize()

    def terminate(self, k=None, u=None, i=None):
        result = super().terminate(k, u, i)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    def kill(self, k=None, i=None):
        result = super().kill(k, i)
        if result is None: raise cp_api_404()
        remark = {}
        if result == 2: remark['pt'] = 'denied'
        return http_api_result_ok(remark) if result else \
                http_api_result_error()

    def q_clean(self, k=None, i=None):
        result = super().q_clean(k, i)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    def disable_actions(self, k=None, i=None):
        result = super().disable_actions(k, i)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    def enable_actions(self, k=None, i=None):
        result = super().enable_actions(k, i)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    def get_config(self, k=None, i=None):
        cp_need_master(k)
        result = super().get_config(k, i)
        if not result: raise cp_api_404()
        return result

    def save_config(self, k=None, i=None):
        cp_need_master(k)
        return http_api_result_ok() if super().save_config(k, i) \
                else http_api_result_error()

    def list(self, k=None, g=None, p=None):
        cp_need_master(k)
        result = super().list(k, g, p)
        if result is None: raise cp_api_404()
        return result

    def list_props(self, k=None, i=None):
        cp_need_master(k)
        result = super().list_props(k, i)
        if not result: raise cp_api_404()
        return result

    def set_prop(self, k=None, i=None, p=None, v=None, save=None):
        cp_need_master(k)
        if save:
            _save = True
        else:
            _save = False
        return http_api_result_ok() if super().set_prop(k, i, p, v, _save) \
                else http_api_result_error()

    def create(self, k=None, i=None, virtual=None, save=None):
        cp_need_master(k)
        return http_api_result_ok() if super().create(
            k, i, val_to_boolean(virtual), save) else http_api_result_error()

    def create_unit(self, k=None, i=None, g=None, virtual=None, save=None):
        cp_need_master(k)
        return http_api_result_ok() if super().create_unit(
            k, i, g, val_to_boolean(virtual),
            save) else http_api_result_error()

    def create_sensor(self, k=None, i=None, g=None, virtual=None, save=None):
        cp_need_master(k)
        return http_api_result_ok() if super().create_sensor(
            k, i, g, val_to_boolean(virtual),
            save) else http_api_result_error()

    def create_mu(self, k=None, i=None, g=None, virtual=None, save=None):
        cp_need_master(k)
        return http_api_result_ok() if super().create_mu(
            k, i, g, val_to_boolean(virtual),
            save) else http_api_result_error()

    def list_device_tpl(self, k):
        result = super().list_device_tpl(k)
        return result if result is not None else http_api_result_error()

    def create_device(self, k=None, c=None, t=None, save=None):
        config = {}
        if not c:
            return http_api_result_error()
        if isinstance(c, dict):
            config = c
        else:
            try:
                for i in c.split(','):
                    name, value = i.split('=')
                    config[name] = value
            except:
                raise cp_api_error()
        return http_api_result_ok() if super().create_device(
            k=k, tpl_config=config, device_tpl=t,
            save=save) else http_api_result_error()

    def update_device(self, k=None, c=None, t=None, save=None):
        config = {}
        if not c:
            return http_api_result_error()
        if isinstance(c, dict):
            config = c
        else:
            try:
                for i in c.split(','):
                    name, value = i.split('=')
                    config[name] = value
            except:
                raise cp_api_error()
        return http_api_result_ok() if super().update_device(
            k=k, tpl_config=config, device_tpl=t,
            save=save) else http_api_result_error()

    def destroy_device(self, k=None, c=None, t=None):
        config = {}
        if not c:
            return http_api_result_error()
        if isinstance(c, dict):
            config = c
        else:
            try:
                for i in c.split(','):
                    name, value = i.split('=')
                    config[name] = value
            except:
                raise cp_api_error()
        return http_api_result_ok() if super().destroy_device(
            k=k, tpl_config=config, device_tpl=t) else http_api_result_error()

    def clone(self, k=None, i=None, n=None, g=None, save=None):
        cp_need_master(k)
        return http_api_result_ok() if super().clone(
            k, i, n, g, save) else http_api_result_error()

    def clone_group(self, k = None, g = None, n = None,\
            p = None, r = None, save = None):
        cp_need_master(k)
        return http_api_result_ok() if super().clone_group(
            k, g, n, p, r, save) else http_api_result_error()

    def destroy(self, k=None, i=None, g=None):
        cp_need_master(k)
        return http_api_result_ok() if super().destroy(k, i, g) \
                else http_api_result_error()

    def create_modbus_port(self,
                           k=None,
                           i=None,
                           p=None,
                           l=None,
                           t=None,
                           d=None,
                           r=None,
                           save=False):
        cp_need_master(k)
        if t:
            try:
                _t = float(t)
            except:
                raise cp_api_error()
        else:
            _t = None
        if d:
            try:
                _d = float(d)
            except:
                raise cp_api_error()
        else:
            _d = None
        if r:
            try:
                _r = int(r)
            except:
                raise cp_api_error()
        else:
            _r = None
        return http_api_result_ok() if super().create_modbus_port(
            k, i, p, val_to_boolean(l), _t, _d, _r,
            save) else http_api_result_error()

    def destroy_modbus_port(self, k=None, i=None):
        cp_need_master(k)
        return http_api_result_ok() if super().destroy_modbus_port(
            k, i) else http_api_result_error()

    def list_modbus_ports(self, k=None):
        cp_need_master(k)
        return super().list_modbus_ports(k)

    def test_modbus_port(self, k=None, i=None):
        cp_need_master(k)
        return http_api_result_ok() if super().test_modbus_port(
            k, i) else http_api_result_error()

    def create_owfs_bus(self,
                        k=None,
                        i=None,
                        n=None,
                        l=None,
                        t=None,
                        d=None,
                        r=None,
                        save=False):
        cp_need_master(k)
        if t:
            try:
                _t = float(t)
            except:
                raise cp_api_error()
        else:
            _t = None
        if d:
            try:
                _d = float(d)
            except:
                raise cp_api_error()
        else:
            _d = None
        if r:
            try:
                _r = int(r)
            except:
                raise cp_api_error()
        else:
            _r = None
        return http_api_result_ok() if super().create_owfs_bus(
            k, i, n, val_to_boolean(l), _t, _d, _r,
            save) else http_api_result_error()

    def destroy_owfs_bus(self, k=None, i=None):
        cp_need_master(k)
        return http_api_result_ok() if super().destroy_owfs_bus(
            k, i) else http_api_result_error()

    def list_owfs_buses(self, k=None):
        cp_need_master(k)
        return super().list_owfs_buses(k)

    def test_owfs_bus(self, k=None, i=None):
        cp_need_master(k)
        return http_api_result_ok() if super().test_owfs_bus(
            k, i) else http_api_result_error()

    def scan_owfs_bus(self,
                      k=None,
                      i=None,
                      p=None,
                      a=None,
                      n=None,
                      has_all=None,
                      full=None):
        cp_need_master(k)
        if p:
            _p = p if isinstance(p, list) else p.split(',')
        else:
            _p = None
        if a:
            _a = a if isinstance(a, list) else a.split(',')
        else:
            _a = None
        result = super().scan_owfs_bus(k, i, _p, _a, n, has_all, full)
        return result if result is not None else http_api_result_error()

    def load_phi(self, k=None, i=None, m=None, c=None, save=False):
        cp_need_master(k)
        result = super().load_phi(k, i, m, c, save)
        return result if result else http_api_result_error()

    def unload_phi(self, k=None, i=None):
        cp_need_master(k)
        return http_api_result_ok() if super().unload_phi(k, i) \
                else http_api_result_error()

    def unlink_phi_mod(self, k=None, m=None):
        cp_need_master(k)
        return http_api_result_ok() if super().unlink_phi_mod(k, m) \
                else http_api_result_error()

    def put_phi_mod(self, k=None, m=None, c=None, force=None):
        cp_need_master(k)
        result = super().put_phi_mod(k, m, c, force)
        if not result: raise cp_api_error()
        return result

    def list_phi(self, k=None, full=None):
        cp_need_master(k)
        result = super().list_phi(k, full)
        if result is None: raise cp_api_error()
        return result

    def get_phi_map(self, k=None, i=None, a=None):
        cp_need_master(k)
        result = super().get_phi_map(k, i, a)
        if result is None: raise cp_api_error()
        return result

    def get_phi(self, k=None, i=None):
        cp_need_master(k)
        result = super().get_phi(k, i)
        if result is None: raise cp_api_error()
        if result is False: raise cp_api_404()
        return result

    def set_phi_prop(self, k=None, i=None, p=None, v=None, save=None):
        cp_need_master(k)
        result = super().set_phi_prop(k, i, p, v, save)
        if result is None: raise cp_api_error()
        if result is False: raise cp_api_404()
        return http_api_result_ok()

    def load_driver(self, k=None, i=None, m=None, p=None, c=None, save=False):
        cp_need_master(k)
        result = super().load_driver(k, i, m, p, c, save)
        return result if result else http_api_result_error()

    def list_drivers(self, k=None, full=None):
        cp_need_master(k)
        result = super().list_drivers(k, full)
        if result is None: raise cp_api_error()
        return result

    def unload_driver(self, k=None, i=None):
        cp_need_master(k)
        return http_api_result_ok() if super().unload_driver(k, i) \
                else http_api_result_error()

    def get_driver(self, k=None, i=None):
        cp_need_master(k)
        result = super().get_driver(k, i)
        if result is None: raise cp_api_error()
        if result is False: raise cp_api_404()
        return result

    def set_driver_prop(self, k=None, i=None, p=None, v=None, save=None):
        cp_need_master(k)
        result = super().set_driver_prop(k, i, p, v, save)
        if result is None: raise cp_api_error()
        if result is False: raise cp_api_404()
        return http_api_result_ok()

    def test_phi(self, k=None, i=None, c=None):
        cp_need_master(k)
        result = super().test_phi(k, i, c)
        if result is False: raise cp_api_404()
        if result is None: raise cp_api_error()
        return result

    def exec_phi(self, k=None, i=None, c=None, a=None):
        cp_need_master(k)
        result = super().exec_phi(k, i, c, a)
        if result is False: raise cp_api_404()
        if result is None: raise cp_api_error()
        return result

    def list_phi_mods(self, k=None):
        cp_need_master(k)
        return super().list_phi_mods(k)

    def list_lpi_mods(self, k=None):
        cp_need_master(k)
        return super().list_lpi_mods(k)

    def modinfo_phi(self, k=None, m=None):
        cp_need_master(k)
        result = super().modinfo_phi(k, m)
        if not result:
            raise cp_api_error()
        else:
            return result

    def modhelp_phi(self, k=None, m=None, c=None):
        cp_need_master(k)
        result = super().modhelp_phi(k, m, c)
        if result is None:
            raise cp_api_error()
        else:
            return result

    def modinfo_lpi(self, k=None, m=None):
        cp_need_master(k)
        result = super().modinfo_lpi(k, m)
        if not result:
            raise cp_api_error()
        else:
            return result

    def modhelp_lpi(self, k=None, m=None, c=None):
        cp_need_master(k)
        result = super().modhelp_lpi(k, m, c)
        if result is None:
            raise cp_api_error()
        else:
            return result

    def assign_driver(self, k=None, i=None, d=None, c=None, save=False):
        cp_need_master(k)
        result = super().assign_driver(k, i, d, c, save)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    def info(self):
        result = super().info()
        result['udp_api_port'] = eva.udpapi.port if \
                eva.udpapi.check_access(http_real_ip()) else None
        return result


def start():
    global api
    api = UC_API()
    cherrypy.tree.mount(UC_HTTP_API(), '/uc-api')
    eva.ei.start()
