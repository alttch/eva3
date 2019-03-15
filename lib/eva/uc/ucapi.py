__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.0"

import cherrypy
import os
import glob
import eva.core

from eva.api import GenericHTTP_API
from eva.api import JSON_RPC_API_abstract
from eva.api import GenericAPI
from eva.api import parse_api_params
from eva.api import http_real_ip
from eva.api import api_need_master

from eva.api import api_result_accepted

from eva.api import generic_web_api_method
from eva.api import restful_api_method

from eva.api import MethodNotFound

from eva.api import log_d
from eva.api import log_i
from eva.api import log_w

from eva.tools import dict_from_str
from eva.tools import oid_to_id
from eva.tools import parse_oid
from eva.tools import is_oid
from eva.tools import val_to_boolean

from eva.exceptions import FunctionFailed
from eva.exceptions import ResourceNotFound
from eva.exceptions import AccessDenied

from eva.tools import InvalidParameter
from eva.tools import parse_function_params

from eva.item import get_state_history

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

    @log_d
    def groups(self, **kwargs):
        """
        get item group list

        Get the list of item groups. Useful e.g. for custom interfaces.

        Args:
            k:
            p: item type (unit [U] or sensor [S])
        """
        k, tp = parse_function_params(kwargs, 'kp', '.S')
        if apikey.check_master(k):
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

    @log_d
    def state(self, **kwargs):
        """
        get item group list

        Get the list of item groups. Useful e.g. for custom interfaces.

        Args:
            k:
            p: item type (unit [U] or sensor [S])
        """
        k, i, group, tp, full = parse_api_params(kwargs, 'kiYgp', '.sssb')
        if i:
            item = eva.uc.controller.get_item(i)
            if not item or not apikey.check(k, item): raise ResourceNotFound
            if is_oid(i):
                t, iid = parse_oid(i)
                if not item or item.item_type != t: raise ResourceNotFound
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
                raise ResourceNotFound
            result = []
            for i, v in gi.copy().items():
                if apikey.check(k, v) and \
                        (not group or \
                            eva.item.item_match(v, [], [grp])):
                    r = v.serialize(full=full)
                    result.append(r)
            return sorted(result, key=lambda k: k['oid'])

    @staticmethod
    def _get_state_history(k=None,
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
        if not item or not apikey.check(k, item): raise ResourceNotFound
        if is_oid(i):
            _t, iid = parse_oid(i)
            if not item or item.item_type != _t: raise ResourceNotFound
        return get_state_history(
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

    @log_d
    def state_history(self, **kwargs):
        """
        get item state history

        State history of one :doc:`item</items>` or several items of the
        specified type can be obtained using **state_history** command.

        Args:
            k:
            a: history notifier id (default: db_1)
            i: item oids or full ids, list or comma separated

        Optional:
            s: start time (timestamp or ISO)
            e: end time (timestamp or ISO)
            l: records limit (doesn't work with "w")
            x: prop ("status" or "value", default: "value")
            t: time format("iso" or "raw" for unix timestamp, default is "raw")
            w: fill frame with the interval (e.g. "1T" - 1 min, "2H" - 2 hours
                etc.)
            g: output format ("list" or "dict", default is "list")
        """
        k, a, i, s, e, l, x, t, w, g = parse_function_params(
            kwargs, 'kaiselxtwg', '.sr..issss')
        if (isinstance(i, str) and i and i.find(',') != -1) or \
                isinstance(i, list):
            if not w:
                raise InvalidParameter(
                    '"w" is required to process multiple items')
            if isinstance(i, str):
                items = i.split(',')
            else:
                items = i
            if not g or g == 'list':
                result = {}
            else:
                raise InvalidParameter(
                    'format should be list only to process multiple items')
            for i in items:
                r = self._get_state_history.state_history(
                    k=k, a=a, i=i, s=s, e=e, l=l, x=x, t=t, w=w, g=g)
                result['t'] = r['t']
                if 'status' in r:
                    result[i + '/status'] = r['status']
                if 'value' in r:
                    result[i + '/value'] = r['value']
            return result
        else:
            result = self._get_state_history(
                k=k, a=a, i=i, s=s, e=e, l=l, x=x, t=t, w=w, g=g)
            return result

    @log_i
    def update(self, **kwargs):
        """
        update the status and value of the item

        Updates the status and value of the :doc:`item</items>`. This is one of the
        ways of passive state update, for example with the use of an external
        controller. Calling without **s** and **v** params will force item to
        perform passive update requesting its status from update script
        or driver.

        Args:
            k:
            .i: item id
        
        Optional:

            s: item status
            v: item value
        """
        k, i, s, v, force_virtual = parse_function_params(
            kwargs, 'kisvV', '.si.b')
        item = eva.uc.controller.get_item(i)
        if not item or not apikey.check(k, item): raise ResourceNotFound
        if s or v:
            return item.update_set_state(
                status=s, value=v, force_virtual=force_virtual)
        else:
            item.need_update.set()
            return True, api_result_accepted

    @staticmethod
    def _process_action_result(a):
        if not a: raise ResourceNotFound('unit found, but something not')
        if a.is_status_dead():
            raise FunctionFailed('{} is dead '.format(a.uiid))
        return a.serialize()

    @log_i
    def action(self,
               k=None,
               i=None,
               action_uuid=None,
               nstatus=None,
               nvalue='',
               priority=None,
               q_timeout=None,
               wait=0):
        """
        create unit control action
        
        The call is considered successful when action is put into the action
        queue of selected unit.

        Args:
            k:
            i: unit id
            s: desired unit status

        Optional:
            v: desired unit value
            w: wait for the completion for the specified number of seconds
            .u: action UUID (will be auto generated if none specified)
            p: queue priority (default is 100, lower is better)
            q: global queue timeout, if expires, action is marked as "dead"

        Returns:
            Serialized action object. If action is marked as dead, an error is
            returned (exception raised)
        """
        k, i, s, v, w, u, p, q = parse_function_params(kwargs, 'kisvwupq',
                                                       '.sR.nsin')
        item = eva.uc.controller.get_unit(i)
        if not item or not apikey.check(k, item): raise ResourceNotFound
        return self._process_action_result(
            eva.uc.controller.exec_unit_action(
                unit=item,
                nstatus=s,
                nvalue=v,
                priority=p,
                q_timeout=q,
                wait=w,
                action_uuid=u))

    @log_i
    def action_toggle(self, **kwargs):
        """
        create unit control action
        
        The call is considered successful when action is put into the action
        queue of selected unit.

        Args:
            k:
            i: unit id

        Optional:
            w: wait for the completion for the specified number of seconds
            .u: action UUID (will be auto generated if none specified)
            p: queue priority (default is 100, lower is better)
            q: global queue timeout, if expires, action is marked as "dead"

        Returns:
            Serialized action object. If action is marked as dead, an error is
            returned (exception raised)
        """
        k, i, w, u, p, q = parse_function_params(kwargs, 'kiwupq', '.snsin')
        item = eva.uc.controller.get_unit(i)
        if not item or not apikey.check(k, item): raise ResourceNotFound
        s = 0 if item.status else 1
        return self._process_action_result(
            eva.uc.controller.exec_unit_action(
                unit=item,
                nstatus=s,
                priority=p,
                q_timeout=q,
                wait=w,
                action_uuid=u))

    @log_i
    def disable_actions(self, **kwargs):
        """
        disable unit actions

        Disables unit to run and queue new actions.

        Args:
            k:
            i: unit id
        """
        k, i = parse_function_params(kwargs, 'ki', '.s')
        item = eva.uc.controller.get_unit(i)
        if not item or not apikey.check(k, item): raise ResourceNotFound
        return item.disable_actions()

    @log_i
    def enable_actions(self, **kwargs):
        """
        enable unit actions

        Enables unit to run and queue new actions.

        Args:
            k:
            i: unit id
        """
        k, i = parse_function_params(kwargs, 'ki', '.s')
        item = eva.uc.controller.get_unit(i)
        if not item or not apikey.check(k, item): return ResourceNotFound
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
        if not apikey.check_master(k): return None
        item = eva.uc.controller.get_item(i)
        if is_oid(i):
            t, iid = parse_oid(i)
            if not item or item.item_type != t: return None
        return item.serialize(config=True) if item else None

    def save_config(self, k=None, i=None):
        if not apikey.check_master(k): return None
        item = eva.uc.controller.get_item(i)
        if is_oid(i):
            t, iid = parse_oid(i)
            if not item or item.item_type != t: return None
        return item.save() if item else None

    def list(self, k=None, group=None, tp=None):
        if not apikey.check_master(k): return None
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
        if not apikey.check_master(k): return None
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
        if not apikey.check_master(k): return None
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
        if not apikey.check_master(k): return None
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
        if not apikey.check_master(k): return None
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
        if not apikey.check_master(k): return None
        return eva.uc.controller.create_mu(
            mu_id=oid_to_id(mu_id, 'mu'),
            group=group,
            virtual=virtual,
            save=save)

    def create(self, k=None, oid=None, virtual=False, save=False):
        if not apikey.check_master(k):
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
        if not apikey.check_master(k): return None
        return eva.uc.controller.clone_item(
            item_id=i, new_item_id=n, group=g, save=save)

    def clone_group(self, k=None, g=None, n=None, p=None, r=None, save=False):
        if not apikey.check_master(k): return None
        return eva.uc.controller.clone_group(
            group=g, new_group=n, prefix=p, new_prefix=r, save=save)

    def destroy(self, k=None, i=None, g=None):
        if not apikey.check_master(k): return None
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
        if not apikey.check_master(k): return None
        if not i or not params: return False
        result = eva.uc.modbus.create_modbus_port(
            i, params, lock=lock, timeout=timeout, delay=delay, retries=retries)
        if result and save: eva.uc.modbus.save()
        return result

    def destroy_modbus_port(self, k=None, i=None):
        if not apikey.check_master(k): return None
        result = eva.uc.modbus.destroy_modbus_port(i)
        if result and eva.core.db_update == 1: eva.uc.modbus.save()
        return result

    def list_modbus_ports(self, k=None):
        if not apikey.check_master(k): return None
        return sorted(eva.uc.modbus.serialize(), key=lambda k: k['id'])

    def test_modbus_port(self, k=None, i=None):
        if not apikey.check_master(k): return None
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
        if not apikey.check_master(k): return None
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
        if not apikey.check_master(k): return None
        result = eva.uc.owfs.destroy_owfs_bus(i)
        if result and eva.core.db_update == 1: eva.uc.owfs.save()
        return result

    def list_owfs_buses(self, k=None):
        if not apikey.check_master(k): return None
        return sorted(eva.uc.owfs.serialize(), key=lambda k: k['id'])

    def test_owfs_bus(self, k=None, i=None):
        if not apikey.check_master(k): return None
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
        if not apikey.check_master(k): return None
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
        if not apikey.check_master(k): return None
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
        if not apikey.check_master(k): return None
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
        if not apikey.check_master(k): return None
        if not i: return None
        result = eva.uc.driverapi.unload_phi(i)
        if result and eva.core.db_update == 1: eva.uc.driverapi.save()
        return result

    def unlink_phi_mod(self, k=None, m=None):
        if not apikey.check_master(k): return None
        if not m: return None
        result = eva.uc.driverapi.unlink_phi_mod(m)
        return result

    def put_phi_mod(self, k=None, m=None, c=None, force=None):
        if not apikey.check_master(k): return None
        if not m: return None
        result = eva.uc.driverapi.put_phi_mod(m, c, force)
        return result if not result else api.modinfo_phi(k, m)

    def unload_driver(self, k=None, i=None):
        if not apikey.check_master(k): return None
        if not i: return None
        result = eva.uc.driverapi.unload_driver(i)
        if result and eva.core.db_update == 1: eva.uc.driverapi.save()
        return result

    def get_phi_map(self, k=None, phi_id=None, action_map=None):
        if not apikey.check_master(k): return None
        return eva.uc.driverapi.get_map(phi_id, action_map)

    def list_phi(self, k=None, full=False):
        if not apikey.check_master(k): return None
        return sorted(
            eva.uc.driverapi.serialize_phi(full=full, config=full),
            key=lambda k: k['id'])

    def list_drivers(self, k=None, full=False):
        if not apikey.check_master(k): return None
        return sorted(
            eva.uc.driverapi.serialize_lpi(full=full, config=full),
            key=lambda k: k['id'])

    def get_phi(self, k=None, i=None):
        if not apikey.check_master(k): return None
        if not i: return None
        phi = eva.uc.driverapi.get_phi(i)
        if phi:
            return phi.serialize(full=True, config=True)
        else:
            return None

    def set_phi_prop(self, k=None, i=None, p=None, v=None, save=False):
        if not apikey.check_master(k): return None
        if not i: return None
        phi = eva.uc.driverapi.get_phi(i)
        if not phi: return None
        if eva.uc.driverapi.set_phi_prop(i, p, v):
            if save: eva.uc.driverapi.save()
            return True
        return False

    def get_driver(self, k=None, i=None):
        if not apikey.check_master(k): return None
        if not i: return None
        lpi = eva.uc.driverapi.get_driver(i)
        if lpi:
            return lpi.serialize(full=True, config=True)
        else:
            return None

    def set_driver_prop(self, k=None, i=None, p=None, v=None, save=False):
        if not apikey.check_master(k): return None
        if not i or i.split('.')[-1] == 'default': return None
        lpi = eva.uc.driverapi.get_driver(i)
        if not lp: return None
        if eva.uc.driverapi.set_driver_prop(i, p, v):
            if save: eva.uc.driverapi.save()
            return True
        return False

    def test_phi(self, k=None, i=None, c=None):
        if not apikey.check_master(k): return None
        if not i: return None
        phi = eva.uc.driverapi.get_phi(i)
        if not phi: return None
        return phi.test(c)

    def exec_phi(self, k=None, i=None, c=None, a=None):
        if not apikey.check_master(k): return None
        if not i: return None
        phi = eva.uc.driverapi.get_phi(i)
        if not phi: return None
        return phi.exec(c, a)

    def list_phi_mods(self, k=None):
        if not apikey.check_master(k): return None
        return eva.uc.driverapi.list_phi_mods()

    def list_lpi_mods(self, k=None):
        if not apikey.check_master(k): return None
        return eva.uc.driverapi.list_lpi_mods()

    def modinfo_phi(self, k=None, m=None):
        if not apikey.check_master(k): return None
        return eva.uc.driverapi.modinfo_phi(m)

    def modinfo_lpi(self, k=None, m=None):
        if not apikey.check_master(k): return None
        return eva.uc.driverapi.modinfo_lpi(m)

    def modhelp_phi(self, k=None, m=None, c=None):
        if not apikey.check_master(k) or not c: return None
        return eva.uc.driverapi.modhelp_phi(m, c)

    def modhelp_lpi(self, k=None, m=None, c=None):
        if not apikey.check_master(k) or not c: return None
        return eva.uc.driverapi.modhelp_lpi(m, c)

    def assign_driver(self, k=None, i=None, d=None, c=None, save=False):
        if not apikey.check_master(k): return None
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


class UC_HTTP_API_abstract(UC_API, GenericHTTP_API):

    def __init__(self):
        super().__init__()
        self._nofp_log('put_phi', 'c')

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

    @api_need_master
    def get_config(self, k=None, i=None):
        result = super().get_config(k, i)
        if not result: raise cp_api_404()
        return result

    @api_need_master
    def save_config(self, k=None, i=None):
        return http_api_result_ok() if super().save_config(k, i) \
                else http_api_result_error()

    @api_need_master
    def list(self, k=None, g=None, p=None):
        result = super().list(k, g, p)
        if result is None: raise cp_api_404()
        return result

    @api_need_master
    def list_props(self, k=None, i=None):
        result = super().list_props(k, i)
        if not result: raise cp_api_404()
        return result

    @api_need_master
    def set_prop(self, k=None, i=None, p=None, v=None, save=None):
        if save:
            _save = True
        else:
            _save = False
        return http_api_result_ok() if super().set_prop(k, i, p, v, _save) \
                else http_api_result_error()

    @api_need_master
    def create(self, k=None, i=None, virtual=None, save=None):
        return http_api_result_ok() if super().create(
            k, i, val_to_boolean(virtual), save) else http_api_result_error()

    @api_need_master
    def create_unit(self, k=None, i=None, g=None, virtual=None, save=None):
        return http_api_result_ok() if super().create_unit(
            k, i, g, val_to_boolean(virtual),
            save) else http_api_result_error()

    @api_need_master
    def create_sensor(self, k=None, i=None, g=None, virtual=None, save=None):
        return http_api_result_ok() if super().create_sensor(
            k, i, g, val_to_boolean(virtual),
            save) else http_api_result_error()

    @api_need_master
    def create_mu(self, k=None, i=None, g=None, virtual=None, save=None):
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

    @api_need_master
    def clone(self, k=None, i=None, n=None, g=None, save=None):
        return http_api_result_ok() if super().clone(
            k, i, n, g, save) else http_api_result_error()

    @api_need_master
    def clone_group(self, k = None, g = None, n = None,\
            p = None, r = None, save = None):
        return http_api_result_ok() if super().clone_group(
            k, g, n, p, r, save) else http_api_result_error()

    @api_need_master
    def destroy(self, k=None, i=None, g=None):
        result = super().destroy(k, i, g)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @api_need_master
    def create_modbus_port(self,
                           k=None,
                           i=None,
                           p=None,
                           l=None,
                           t=None,
                           d=None,
                           r=None,
                           save=False):
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

    @api_need_master
    def destroy_modbus_port(self, k=None, i=None):
        return http_api_result_ok() if super().destroy_modbus_port(
            k, i) else http_api_result_error()

    @api_need_master
    def list_modbus_ports(self, k=None):
        return super().list_modbus_ports(k)

    @api_need_master
    def test_modbus_port(self, k=None, i=None):
        return http_api_result_ok() if super().test_modbus_port(
            k, i) else http_api_result_error()

    @api_need_master
    def create_owfs_bus(self,
                        k=None,
                        i=None,
                        n=None,
                        l=None,
                        t=None,
                        d=None,
                        r=None,
                        save=False):
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

    @api_need_master
    def destroy_owfs_bus(self, k=None, i=None):
        return http_api_result_ok() if super().destroy_owfs_bus(
            k, i) else http_api_result_error()

    @api_need_master
    def list_owfs_buses(self, k=None):
        return super().list_owfs_buses(k)

    @api_need_master
    def test_owfs_bus(self, k=None, i=None):
        return http_api_result_ok() if super().test_owfs_bus(
            k, i) else http_api_result_error()

    @api_need_master
    def scan_owfs_bus(self,
                      k=None,
                      i=None,
                      p=None,
                      a=None,
                      n=None,
                      has_all=None,
                      full=None):
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

    @api_need_master
    def load_phi(self, k=None, i=None, m=None, c=None, save=False):
        result = super().load_phi(k, i, m, c, save)
        return result if result else http_api_result_error()

    @api_need_master
    def unload_phi(self, k=None, i=None):
        result = super().unload_phi(k, i)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @api_need_master
    def unlink_phi_mod(self, k=None, m=None):
        return http_api_result_ok() if super().unlink_phi_mod(k, m) \
                else http_api_result_error()

    @api_need_master
    def put_phi_mod(self, k=None, m=None, c=None, force=None):
        result = super().put_phi_mod(k, m, c, force)
        if not result: raise cp_api_error()
        return result

    @api_need_master
    def list_phi(self, k=None, full=None):
        result = super().list_phi(k, full)
        if result is None: raise cp_api_error()
        return result

    @api_need_master
    def get_phi_map(self, k=None, i=None, a=None):
        result = super().get_phi_map(k, i, a)
        if result is None: raise cp_api_error()
        return result

    @api_need_master
    def get_phi(self, k=None, i=None):
        result = super().get_phi(k, i)
        if result is False: raise cp_api_error()
        if result is None: raise cp_api_404()
        return result

    @api_need_master
    def set_phi_prop(self, k=None, i=None, p=None, v=None, save=None):
        result = super().set_phi_prop(k, i, p, v, save)
        if result is False: raise cp_api_error()
        if result is None: raise cp_api_404()
        return http_api_result_ok()

    @api_need_master
    def load_driver(self, k=None, i=None, m=None, p=None, c=None, save=False):
        result = super().load_driver(k, i, m, p, c, save)
        return result if result else http_api_result_error()

    @api_need_master
    def list_drivers(self, k=None, full=None):
        result = super().list_drivers(k, full)
        if result is None: raise cp_api_error()
        return result

    @api_need_master
    def unload_driver(self, k=None, i=None):
        result = super().unload_driver(k, i)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @api_need_master
    def get_driver(self, k=None, i=None):
        result = super().get_driver(k, i)
        if result is False: raise cp_api_error()
        if result is None: raise cp_api_404()
        return result

    @api_need_master
    def set_driver_prop(self, k=None, i=None, p=None, v=None, save=None):
        result = super().set_driver_prop(k, i, p, v, save)
        if result is False: raise cp_api_error()
        if result is None: raise cp_api_404()
        return http_api_result_ok()

    @api_need_master
    def test_phi(self, k=None, i=None, c=None):
        result = super().test_phi(k, i, c)
        if result is None: raise cp_api_404()
        if result is False: raise cp_api_error()
        return result

    @api_need_master
    def exec_phi(self, k=None, i=None, c=None, a=None):
        result = super().exec_phi(k, i, c, a)
        if result is None: raise cp_api_404()
        if result is False: raise cp_api_error()
        return result

    @api_need_master
    def list_phi_mods(self, k=None):
        return super().list_phi_mods(k)

    @api_need_master
    def list_lpi_mods(self, k=None):
        return super().list_lpi_mods(k)

    @api_need_master
    def modinfo_phi(self, k=None, m=None):
        result = super().modinfo_phi(k, m)
        if not result:
            raise cp_api_error()
        else:
            return result

    @api_need_master
    def modhelp_phi(self, k=None, m=None, c=None):
        result = super().modhelp_phi(k, m, c)
        if result is None:
            raise cp_api_error()
        else:
            return result

    @api_need_master
    def modinfo_lpi(self, k=None, m=None):
        result = super().modinfo_lpi(k, m)
        if not result:
            raise cp_api_error()
        else:
            return result

    @api_need_master
    def modhelp_lpi(self, k=None, m=None, c=None):
        result = super().modhelp_lpi(k, m, c)
        if result is None:
            raise cp_api_error()
        else:
            return result

    @api_need_master
    def assign_driver(self, k=None, i=None, d=None, c=None, save=False):
        result = super().assign_driver(k, i, d, c, save)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    def info(self):
        result = super().info()
        result['udp_api_port'] = eva.udpapi.port if \
                eva.udpapi.check_access(http_real_ip()) else None
        return result


class UC_HTTP_API(UC_HTTP_API_abstract, GenericHTTP_API):

    def __init__(self):
        super().__init__()
        self.expose_api_methods('ucapi')
        self.wrap_exposed()


class UC_JSONRPC_API(eva.sysapi.SysHTTP_API_abstract,
                     eva.sysapi.SysHTTP_API_REST_abstract,
                     eva.api.JSON_RPC_API_abstract, UC_HTTP_API_abstract):

    def __init__(self):
        super().__init__()
        self.expose_api_methods('ucapi', set_api_uri=False)
        self.expose_api_methods('sysapi', set_api_uri=False)


class UC_REST_API(eva.sysapi.SysHTTP_API_abstract,
                  eva.sysapi.SysHTTP_API_REST_abstract,
                  eva.api.GenericHTTP_API_REST_abstract, UC_HTTP_API_abstract,
                  GenericHTTP_API):

    @generic_web_api_method
    @restful_api_method
    def GET(self, rtp, k, ii, full, save, kind, for_dir, props):
        try:
            return super().GET(rtp, k, ii, full, save, kind, for_dir, props)
        except MethodNotFound:
            pass
        raise MethodNotFound

    @generic_web_api_method
    @restful_api_method
    def POST(self, rtp, k, ii, full, save, kind, for_dir, props):
        try:
            return super().POST(rtp, k, ii, full, save, kind, for_dir, props)
        except MethodNotFound:
            pass
        raise MethodNotFound

    @generic_web_api_method
    @restful_api_method
    def PUT(self, rtp, k, ii, full, save, kind, for_dir, props):
        try:
            return super().PUT(rtp, k, ii, full, save, kind, for_dir, props)
        except MethodNotFound:
            pass
        raise MethodNotFound

    @generic_web_api_method
    @restful_api_method
    def PATCH(self, rtp, k, ii, full, save, kind, for_dir, props):
        try:
            return super().PATCH(rtp, k, ii, full, save, kind, for_dir, props)
        except MethodNotFound:
            pass
        raise MethodNotFound

    @generic_web_api_method
    @restful_api_method
    def DELETE(self, rtp, k, ii, full, save, kind, for_dir, props):
        try:
            return super().DELETE(rtp, k, ii, full, save, kind, for_dir, props)
        except MethodNotFound:
            pass
        raise MethodNotFound


def start():
    http_api = UC_HTTP_API()
    cherrypy.tree.mount(http_api, http_api.api_uri)
    cherrypy.tree.mount(UC_JSONRPC_API(), UC_JSONRPC_API.api_uri)
    cherrypy.tree.mount(
        UC_REST_API(),
        UC_REST_API.api_uri,
        config={
            '/': {
                'request.dispatch': cherrypy.dispatch.MethodDispatcher()
            }
        })
    eva.ei.start()


api = UC_API()
