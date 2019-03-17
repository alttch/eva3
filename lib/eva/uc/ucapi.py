__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.0"

import cherrypy
import os
import yaml
import glob
import eva.core

import eva.api
import eva.sysapi

from eva.api import GenericHTTP_API
from eva.api import JSON_RPC_API_abstract
from eva.api import GenericAPI
from eva.api import parse_api_params
from eva.api import http_real_ip
from eva.api import api_need_master

from eva.api import api_result_accepted

from eva.api import generic_web_api_method
from eva.api import restful_api_method
from eva.api import set_restful_response_location

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
from eva.exceptions import ResourceBusy
from eva.exceptions import AccessDenied
from eva.exceptions import InvalidParameter

from eva.tools import parse_function_params

from eva.item import get_state_history

from eva import apikey

from functools import wraps

import eva.uc.controller
import eva.uc.driverapi
import eva.uc.modbus
import eva.uc.owfs
import eva.ei
import jinja2
import jsonpickle
import logging

api = None


def api_need_device(f):

    @wraps(f)
    def do(*args, **kwargs):
        if not eva.apikey.check(kwargs.get('k'), allow=['device']):
            raise AccessDenied
        return f(*args, **kwargs)

    return do


class UC_API(GenericAPI):

    @staticmethod
    def _process_action_result(a):
        if not a: raise ResourceNotFound('unit found, but something not')
        if a.is_status_dead():
            raise FunctionFailed('{} is dead'.format(a.uiid))
        return a.serialize()

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
            a=a,
            oid=item.oid,
            t_start=s,
            t_end=e,
            limit=l,
            prop=x,
            time_format=t,
            fill=w,
            fmt=g)

    @staticmethod
    def _load_device_config(tpl_config=None, device_tpl=None):
        tpl_decoder = {
            'json': jsonpickle.decode,
            'yml': yaml.load,
            'yaml': yaml.load
        }
        if tpl_config is None:
            tpl_config = {}
        elif isinstance(tpl_config, dict):
            pass
        elif isinstance(tpl_config, str):
            config = {}
            try:
                for i in tpl_config.split(','):
                    name, value = i.split('=')
                    config[name] = value
            except:
                raise InvalidParameter('invalid configuration specified')
            tpl_config = config
        else:
            raise InvalidParameter
        try:
            for ext in ['yml', 'yaml', 'json']:
                fname = '{}/tpl/{}.{}'.format(eva.core.dir_runtime, device_tpl,
                                              ext)
                if os.path.isfile(fname):
                    break
                fname = None
            if not fname: raise ResourceNotFound
            tpl = jinja2.Template(open(fname).read())
            cfg = tpl_decoder.get(ext)(tpl.render(tpl_config))
            return cfg
        except ResourceNotFound:
            raise
        except:
            raise FunctionFailed('device template parse error')

    def _device_set_props(self,
                          k=None,
                          i=None,
                          props=None,
                          save=None,
                          clean_snmp=False):
        if clean_snmp:
            self.set_prop(k=k, i=i, p='snmp_trap')
        if props:
            self.set_prop(k=k, i=i, v=props, save=False)
        if save:
            self.save_config(k=k, i=i)
        return True

    @log_d
    def groups(self, **kwargs):
        """
        get item group list

        Get the list of item groups. Useful e.g. for custom interfaces.

        Args:
            k:
            .p: item type (unit [U] or sensor [S])
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
            .p: item type (unit [U] or sensor [S])

        Optional:
            .i: item id
            .g: item group
            .full: return full state
        """
        k, i, group, tp, full = parse_function_params(kwargs, 'kigpY', '.sssb')
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

    @log_d
    def state_history(self, **kwargs):
        """
        get item state history

        State history of one :doc:`item</items>` or several items of the
        specified type can be obtained using **state_history** command.

        Args:
            k:
            a: history notifier id (default: db_1)
            .i: item oids or full ids, list or comma separated

        Optional:
            s: start time (timestamp or ISO)
            e: end time (timestamp or ISO)
            l: records limit (doesn't work with "w")
            x: state prop ("status" or "value")
            t: time format("iso" or "raw" for unix timestamp, default is "raw")
            w: fill frame with the interval (e.g. "1T" - 1 min, "2H" - 2 hours
                etc.), start time is required
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
                r = self._get_state_history(
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
    def action(self, **kwargs):
        """
        create unit control action
        
        The call is considered successful when action is put into the action
        queue of selected unit.

        Args:
            k:
            .i: unit id
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
        if s == 'toggle':
            s = 0 if item.status else 1
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
            .i: unit id

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
            .i: unit id
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
            .i: unit id
        """
        k, i = parse_function_params(kwargs, 'ki', '.s')
        item = eva.uc.controller.get_unit(i)
        if not item or not apikey.check(k, item): raise ResourceNotFound
        return item.enable_actions()

    @log_i
    def result(self, **kwargs):
        """
        get action status

        Checks the result of the action by its UUID or returns the actions for
        the specified unit.

        Args:
            k:
            .u: action uuid or
            .i: unit id

        Optional:
            g: filter by unit group
            s: filter by action status: Q for queued, R for running, F for
               finished

        Return:
            list or single serialized action object
        """
        k, u, i, g, s = parse_function_params(kwargs, 'kuigs', '.ssss')
        if u:
            a = eva.uc.controller.Q.history_get(u)
            if not a or not apikey.check(k, a.item): raise ResourceNotFound
            return a.serialize()
        else:
            result = []
            if i:
                item_id = oid_to_id(i, 'unit')
                if item_id is None: raise ResourceNotFound
                ar = None
                item = eva.uc.controller.get_unit(item_id)
                if not apikey.check(k, item): raise ResourceNotFound
                if item_id.find('/') > -1:
                    if item_id in eva.uc.controller.Q.actions_by_item_full_id:
                        ar = eva.uc.controller.Q.actions_by_item_full_id[
                            item_id]
                else:
                    if item_id in eva.uc.controller.Q.actions_byitem_id:
                        ar = eva.uc.controller.Q.actions_byitem_id[item_id]
                if ar is None: return []
            else:
                ar = eva.uc.controller.Q.actions
            for a in ar:
                if not apikey.check(k, a.item): continue
                if g and \
                        not eva.item.item_match(a.item, [], [ g ]):
                    continue
                if (s == 'Q' or s =='queued') and \
                        not a.is_status_queued():
                    continue
                elif (s == 'R' or s == 'running') and \
                        not a.is_status_running():
                    continue
                elif (s == 'F' or s == 'finished') and \
                        not a.is_finished():
                    continue
                result.append(a.serialize())
            return result

    @log_i
    def update(self, **kwargs):
        """
        update the status and value of the item

        Updates the status and value of the :doc:`item</items>`. This is one of
        the ways of passive state update, for example with the use of an
        external controller. Calling without **s** and **v** params will force
        item to perform passive update requesting its status from update script
        or driver.

        Args:
            k:
            .i: item id
        
        Optional:

            s: item status
            v: item value
        """
        k, i, s, v, force_virtual = parse_function_params(
            kwargs, 'kisvO', '.si.b')
        item = eva.uc.controller.get_item(i)
        if not item or not apikey.check(k, item): raise ResourceNotFound
        if s or v:
            return item.update_set_state(
                status=s, value=v, force_virtual=force_virtual)
        else:
            item.need_update.set()
            return True, api_result_accepted

    @log_w
    def kill(self, **kwargs):
        """
        kill unit actions

        Apart from canceling all queued commands, this function also terminates
        the current running action.
        
        Args:
            k:
            .i: unit id
        
        Returns:
            If the current action of the unit cannot be terminated by
            configuration, the notice "pt" = "denied" will be returned
            additionally (even if there's no action running)
        """
        k, i = parse_function_params(kwargs, 'ki', '.s')
        item = eva.uc.controller.get_unit(i)
        if not item or not apikey.check(k, item): raise ResourceNotFound
        result = item.kill()
        if not result: raise FunctionFailed
        return True if item.action_allow_termination else True, {'pt': 'denied'}

    @log_w
    def q_clean(self, **kwargs):
        """
        clean action queue of unit

        Cancels all queued actions, keeps the current action running.

        Args:
            k:
            .i: unit id
        """
        k, i = parse_function_params(kwargs, 'ki', '.s')
        item = eva.uc.controller.get_unit(i)
        if not item or not apikey.check(k, item): raise ResourceNotFound
        return item.q_clean()

    @log_w
    def terminate(self, **kwargs):
        """
        terminate action execution
        
        Terminates or cancel the action if it is still queued
        
        Args:
            k:
            .u: action uuid or
            .i: unit id
            
        Returns:
       
            An error result will be returned eitner if action is terminated
            (Resource not found) or if termination process is failed or denied
            by unit configuration (Function failed)
        """
        k, u, i = parse_function_params(kwargs, 'kui', '.ss')
        if u:
            a = eva.uc.controller.Q.history_get(u)
            if not a or not apikey.check(k, a.item): raise ResourceNotFound
            return a.kill()
        elif i:
            item = eva.uc.controller.get_unit(i)
            if not item or not apikey.check(k, item): raise ResourceNotFound
            return item.terminate()
        raise InvalidParameter('Either "u" or "i" must be specified')

    # master functions for item configuration

    @log_i
    @api_need_master
    def get_config(self, **kwargs):
        """
        get item configuration

        Args:
            k: .master
            .i: item id

        Returns:
            complete :doc:`item</items>` configuration
        """
        i = parse_api_params(kwargs, 'i', 's')
        if is_oid(i):
            t, i = parse_oid(i)
        item = eva.uc.controller.get_item(i)
        if not item or (is_oid(i) and item and item.item_type != t):
            raise ResourceNotFound
        return item.serialize(config=True)

    @log_i
    @api_need_master
    def save_config(self, **kwargs):
        """
        save item configuration

        Saves :doc:`item</items>`. configuration on disk (even if it hasn't
        been changed)

        Args:
            k: .master
            .i: item id
        """
        i = parse_api_params(kwargs, 'i', 's')
        if is_oid(i):
            t, i = parse_oid(i)
        item = eva.uc.controller.get_item(i)
        if not item or (is_oid(i) and item and item.item_type != t):
            raise ResourceNotFound
        item = eva.uc.controller.get_item(i)
        return item.save()

    @log_i
    @api_need_master
    def list(self, **kwargs):
        """
        list items

        Args:
            k: .master

        Optional:
            .p: filter by item type
            .g: filter by item group

        Returns:
            the list of all :doc:`item</items>` available
        """
        tp, group = parse_api_params(kwargs, 'pg', 'ss')
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

    @log_i
    @api_need_master
    def list_props(self, **kwargs):
        """
        list item properties

        Get all editable parameters of the :doc:`item</items>` confiugration.

        Args:
            k: .master
            .i: item id
        """
        i = parse_api_params(kwargs, 'i', 's')
        if is_oid(i):
            t, i = parse_oid(i)
        item = eva.uc.controller.get_item(i)
        if not item or (is_oid(i) and item and item.item_type != t):
            raise ResourceNotFound
        return item.serialize(props=True)

    @log_i
    @api_need_master
    def set_prop(self, **kwargs):
        """
        set item property

        Set configuration parameters of the :doc:`item</items>`.

        Args:
        
            k: .master
            .i: item id
            .p: property name
        
        Optional:
            .v: property value
        """
        i, p, v, save = parse_api_params(kwargs, 'ipvS', 's..b')
        if not p and not isinstance(v, dict):
            raise InvalidParameter('property not specified')
        if is_oid(i):
            t, i = parse_oid(i)
        item = eva.uc.controller.get_item(i)
        if not item or (is_oid(i) and item and item.item_type != t):
            raise ResourceNotFound
        for prop, value in v.items() if isinstance(v, dict) else {p: v}.items():
            if not item.set_prop(prop, value, False):
                raise FunctionFailed('{}.{} = {} unable to set'.format(
                    item.oid, prop, value))
        if save: item.save()
        return True

    @log_i
    @api_need_master
    def create_unit(self, **kwargs):
        """
        create new unit

        Creates new :ref:`unit<unit>`.

        Args:
        
            k: .master
            .i: unit id

        Optional:

            .g: unit group
            .v: virtual unit (deprecated)
            save: save unit configuration immediately
        """
        i, g, v, save = parse_api_params(kwargs, 'igVS', 'Ssbb')
        return eva.uc.controller.create_unit(
            unit_id=oid_to_id(i, 'unit'), group=g, virtual=v,
            save=save).serialize()

    @log_i
    @api_need_master
    def create_sensor(self, **kwargs):
        """
        create new sensor

        Creates new :ref:`sensor<sensor>`.

        Args:
        
            k: .master
            .i: sensor id

        Optional:

            .g: sensor group
            .v: virtual sensor (deprecated)
            save: save sensor configuration immediately
        """
        i, g, v, save = parse_api_params(kwargs, 'igVS', 'Ssbb')
        return eva.uc.controller.create_sensor(
            sensor_id=oid_to_id(i, 'sensor'), group=g, virtual=v,
            save=save).serialize()

    @log_i
    @api_need_master
    def create_mu(self, **kwargs):
        """
        create multi-update

        Creates new :ref:`multi-update<multiupdate>`.

        Args:
            k: .master
            .i: multi-update id

        Optional:
            .g: multi-update group
            .v: virtual multi-update (deprecated)
            save: save multi-update configuration immediately
        """
        i, g, v, save = parse_api_params(kwargs, 'igVS', 'Ssbb')
        return eva.uc.controller.create_mu(
            mu_id=oid_to_id(i, 'mu'), group=g, virtual=v,
            save=save).serialize()

    @log_i
    @api_need_master
    def create(self, **kwargs):
        """
        create new item

        Creates new :doc:`item</items>`.

        Args:
            k: .master
            .i: item oid (**type:group/id**)

        Optional:
            .g: item group
            .v: virtual item (deprecated)
            save: save multi-update configuration immediately
        """
        k, i, g, v, save = parse_function_params(kwargs, 'kigvS', '.Osbb')
        t, i = parse_oid(i)
        if t == 'unit':
            return self.create_unit(k=k, i=i, virtual=v, save=save)
        elif t == 'sensor':
            return self.create_sensor(k=k, i=i, virtual=v, save=save)
        elif t == 'mu':
            return self.create_mu(k=k, i=i, virtual=v, save=save)
        raise InvalidParameter('oid type unknown')

    @log_i
    @api_need_master
    def clone(self, **kwargs):
        """
        clone item

        Creates a copy of the :doc:`item</items>`.

        Args:
            k: .master
            .i: item id
            n: new item id


        Optional:
            .g: multi-update group
            save: save multi-update configuration immediately
        """
        i, n, g, save = parse_api_params(kwargs, 'ingS', 'SSsb')
        return eva.uc.controller.clone_item(
            item_id=i, new_item_id=n, group=g, save=save).serialize()

    @log_i
    @api_need_master
    def clone_group(self, **kwargs):
        """
        clone group

        Creates a copy of all :doc:`items</items>` from the group.

        Args:
            k: .master
            .g: group to clone
            n: new group to clone to

        Optional:
            p: item ID prefix, e.g. device1. for device1.temp1, device1.fan1 
            r: iem ID prefix in the new group, e.g. device2 (both prefixes must
                be specified)
            save: save configuration immediately
        """
        g, n, p, r, save = parse_api_params(kwargs, 'gnprS', 'SSssb')
        if (p and not r) or (r and not p):
            raise InvalidParameter('both prefixes must be specified')
        return eva.uc.controller.clone_group(
            group=g, new_group=n, prefix=p, new_prefix=r, save=save)

    @log_w
    @api_need_master
    def destroy(self, **kwargs):
        """
        delete item or group

        Deletes the :doc:`item</items>` or the group (and all the items in it)
        from the system.

        Args:
            k: .master
            .i: item id
            .g: group (either item or group must be specified)
        """
        i, g = parse_api_params(kwargs, 'ig', 'ss')
        if not i and not g:
            raise InvalidParameter('either item id or group must be specified')
        return eva.uc.controller.destroy_item(i) if i \
                else eva.uc.controller.destroy_group(g)

    # device functions

    @log_d
    @api_need_device
    def list_device_tpl(self, **kwargs):
        """
        list device templates

        List available device templates from runtime/tpl

        Args:
            k: .masterkey
        """
        result = []
        for ext in ['yml', 'yaml', 'json']:
            for i in glob.glob(eva.core.dir_runtime + '/tpl/*.' + ext):
                result.append({
                    'name': os.path.basename(i)[:-1 * len(ext) - 1],
                    'type': 'JSON' if ext == 'json' else 'YAML'
                })
        return sorted(result, key=lambda k: k['name'])

    @log_i
    @api_need_device
    def create_device(self, **kwargs):
        """
        create device items

        Creates the :ref:`device<device>` from the specified template.

        Args:
            k: .allow=device
            c: device config (*var=value*, comma separated or dict)
            t: device template (*runtime/tpl/<TEMPLATE>.yml|yaml|json*, without
                extension)

        Optional:
            save: save items configuration on disk immediately after
                operation
        """
        k, tpl_config, device_tpl, save = parse_function_params(
            kwargs, 'kctS', '..Sb')
        cfg = self._load_device_config(
            tpl_config=tpl_config, device_tpl=device_tpl)
        _k = eva.apikey.masterkey
        if cfg is None: raise ResourceNotFound
        units = cfg.get('units')
        if units:
            for u in units:
                try:
                    i = u['id']
                    g = u.get('group')
                except:
                    raise InvalidParameter('no id field for unit')
                self.create_unit(k=_k, i=i, g=g, save=save)
        sensors = cfg.get('sensors')
        if sensors:
            for u in sensors:
                try:
                    i = u['id']
                    g = u.get('group')
                except:
                    raise InvalidParameter('no id field for sensor')
                self.create_sensor(k=_k, i=i, g=g, save=save)
        mu = cfg.get('mu')
        if mu:
            for u in mu:
                try:
                    i = u['id']
                    g = u.get('group')
                except:
                    raise InvalidParameter('no id field for mu')
                self.create_mu(k=_k, i=i, g=g, save=save)
        return self._do_update_device(cfg=cfg, save=save)

    @log_i
    @api_need_device
    def update_device(self, **kwargs):
        """
        update device items

        Works similarly to :ref:`ucapi_create_device` function but doesn't
        create new items, updating the item configuration of the existing ones.

        Args:
            k: .allow=device
            c: device config (*var=value*, comma separated or dict)
            t: device template (*runtime/tpl/<TEMPLATE>.yml|yaml|json*, without
                extension)

        Optional:
            save: save items configuration on disk immediately after
                operation
        """
        k, tpl_config, device_tpl, save = parse_function_params(
            kwargs, 'kctS', '..Sb')
        cfg = self._load_device_config(
            tpl_config=tpl_config, device_tpl=device_tpl)
        return self._do_update_device(cfg=cfg, save=save)

    def _do_update_device(self,
                          tpl_config={},
                          device_tpl=None,
                          cfg=None,
                          save=False):
        _k = eva.apikey.masterkey
        if cfg is None:
            cfg = self._load_device_config(
                tpl_config=tpl_config, device_tpl=device_tpl)
        cvars = cfg.get('cvars')
        if cvars:
            for i, v in cvars.items():
                if not eva.sysapi.api.set_cvar(k=_k, i=i, v=v):
                    raise FunctionFailed
        units = cfg.get('units')
        if units:
            for u in units:
                try:
                    i = u['id']
                    g = u['group']
                except:
                    raise InvalidParameter('no fields for unit')
                self._device_set_props(_k, 'unit:{}/{}'.format(g, i),
                                       u.get('props'), save, True)
        sensors = cfg.get('sensors')
        if sensors:
            for u in sensors:
                try:
                    i = u['id']
                    g = u['group']
                except:
                    raise InvalidParameter('no fields for sensor')
                self._device_set_props(_k, 'sensor:{}/{}'.format(g, i),
                                       u.get('props'), save, True)
        mu = cfg.get('mu')
        if mu:
            for u in mu:
                try:
                    i = u['id']
                    g = u['group']
                except:
                    raise InvalidParameter('no fields for mu')
                self._device_set_props(_k, 'mu:{}/{}'.format(g, i),
                                       u.get('props'), save)
        return True

    @log_w
    @api_need_device
    def destroy_device(self, **kwargs):
        """
        delete device items

        Works in an opposite way to :ref:`ucapi_create_device` function,
        destroying all items specified in the template.

        Args:
            k: .allow=device
            c: device config (*var=value*, comma separated or dict)
            t: device template (*runtime/tpl/<TEMPLATE>.yml|yaml|json*, without
                extension)

        Returns:
            The function ignores missing items, so no errors are returned
            unless device configuration file is invalid.
        """
        k, tpl_config, device_tpl, save = parse_function_params(
            kwargs, 'kctS', '..Sb')
        cfg = self._load_device_config(
            tpl_config=tpl_config, device_tpl=device_tpl)
        _k = eva.apikey.masterkey
        if cfg is None: raise ResourceNotFound
        mu = cfg.get('mu')
        if mu:
            for m in mu:
                try:
                    i = m['id']
                    g = u['group']
                except:
                    raise InvalidParameter('no id field for unit')
                try:
                    self.destroy(k=_k, i='mu:{}/{}'.format(g, i))
                except:
                    pass
        units = cfg.get('units')
        if units:
            for u in units:
                try:
                    i = u['id']
                    g = u['group']
                except:
                    raise InvalidParameter('no id field for sensor')
                try:
                    self.destroy(k=_k, i='unit:{}/{}'.format(g, i))
                except:
                    pass
        sensors = cfg.get('sensors')
        if sensors:
            for u in sensors:
                try:
                    i = u['id']
                    g = u['group']
                except:
                    raise InvalidParameter('no id field for mu')
                try:
                    self.destroy(k=_k, i='sensor:{}/{}'.format(g, i))
                except:
                    pass
        cvars = cfg.get('cvars')
        if cvars:
            for cvar in cvars.keys():
                try:
                    eva.sysapi.api.set_cvar(k=_k, i=cvar)
                except:
                    pass
        return True

    # master functions for modbus port management

    @log_i
    @api_need_master
    def create_modbus_port(self, **kwargs):
        """
        create virtual ModBus port

        Creates virtual :doc:`ModBus port</modbus>` with the specified
        configuration.

        ModBus params should contain the configuration of hardware ModBus port.
        The following hardware port types are supported:

        * **tcp** , **udp** ModBus protocol implementations for TCP/IP
            networks. The params should be specified as:
            *<protocol>:<host>[:port]*, e.g.  *tcp:192.168.11.11:502*

        * **rtu**, **ascii**, **binary** ModBus protocol implementations for
            the local bus connected with USB or serial port. The params should
            be specified as:
            *<protocol>:<device>:<speed>:<data>:<parity>:<stop>* e.g.
            *rtu:/dev/ttyS0:9600:8:E:1*

        Args:
            k: .master
            .i: virtual port ID which will be used later in
                :doc:`PHI</drivers>` configurations, required
            p: ModBus params, required
            l: lock port on operations, which means to wait while ModBus port
                is used by other controller thread (driver command)
            t: ModBus operations timeout (in seconds, default: default timeout)
            r: retry attempts for each operation (default: no retries)
            d: delay between virtual port operations (default: 20ms)

        Optional:
            save: save ModBus port config after creation

        Returns:
            If port with the selected ID is already created, error is not
            returned and port is recreated.
        """
        i, p, l, t, d, r, save = parse_api_params(kwargs, 'ipltdrS', 'SSbnnib')
        result = eva.uc.modbus.create_modbus_port(
            i, p, lock=l, timeout=t, delay=d, retries=r)
        if result and save: eva.uc.modbus.save()
        return result

    @log_w
    @api_need_master
    def destroy_modbus_port(self, **kwargs):
        """
        delete virtual ModBus port

        Deletes virtual :doc:`ModBus port</modbus>`.

        Args:
            k: .master
            .i: virtual port ID
        """
        i = parse_api_params(kwargs, 'i', 'S')
        result = eva.uc.modbus.destroy_modbus_port(i)
        if result and eva.core.db_update == 1: eva.uc.modbus.save()
        return result

    @log_d
    @api_need_master
    def list_modbus_ports(self, **kwargs):
        """
        list virtual ModBus ports

        Args:
            k: .master
            .i: virtual port ID
        """
        parse_api_params(kwargs)
        return sorted(eva.uc.modbus.serialize(), key=lambda k: k['id'])

    @log_d
    @api_need_master
    def get_modbus_port(self, **kwargs):
        """
        get virtual ModBus port configuration

        Args:
            k: .master
            .i: port ID
        """
        i = parse_api_params(kwargs, 'i', 'S')
        return eva.uc.modbus.serialize(i)

    @log_d
    @api_need_master
    def test_modbus_port(self, **kwargs):
        """
        list virtual ModBus ports

        Verifies virtual :doc:`ModBus port</modbus>` by calling connect()
        ModBus client method.

        .. note::

            As ModBus UDP doesn't require a port to be connected, API call
            always returns success unless the port is locked.

        Args:
            k: .master
            .i: virtual port ID
        """
        i = parse_api_params(kwargs, 'i', 'S')
        port = eva.uc.modbus.get_port(i)
        if port: port.release()
        if port is None: raise ResourceNotFound
        elif port is False: raise FunctionFailed('Test failed')
        elif port == 0: raise ResourceBusy
        return True

    # master functions for owfs bus management

    @log_i
    @api_need_master
    def create_owfs_bus(self, **kwargs):
        """
        create OWFS bus

        Creates (defines) :doc:`OWFS bus</owfs>` with the specified
        configuration.

        Parameter "location" ("n") should contain the connection configuration,
        e.g.  "localhost:4304" for owhttpd or "i2c=/dev/i2c-1:ALL", "/dev/i2c-0
        --w1" for local 1-wire bus via I2C, depending on type.

        Args:
            k: .master
            .i: bus ID which will be used later in
                :doc:`PHI</drivers>` configurations, required
            n: OWFS location
            l: lock port on operations, which means to wait while OWFS bus is
                used by other controller thread (driver command)
            t: OWFS operations timeout (in seconds, default: default timeout)
            r: retry attempts for each operation (default: no retries)
            d: delay between bus operations (default: 50ms)

        Optional:
            save: save OWFS bus config after creation

        Returns:
            If bus with the selected ID is already defined, error is not
            returned and bus is recreated.
        """
        i, n, l, t, d, r, save = parse_api_params(kwargs, 'inltdrS', 'SSbnnib')
        result = eva.uc.owfs.create_owfs_bus(
            i, n, lock=l, timeout=t, delay=d, retries=r)
        if result and save: eva.uc.owfs.save()
        return result

    @log_w
    @api_need_master
    def destroy_owfs_bus(self, **kwargs):
        """
        delete OWFS bus

        Deletes (undefines) :doc:`OWFS bus</owfs>`.

        .. note::

            In some cases deleted OWFS bus located on I2C may lock *libow*
            library calls, which require controller restart until you can use
            (create) the same I2C bus again.

        Args:
            k: .master
            .i: bus ID
        """
        i = parse_api_params(kwargs, 'i', 'S')
        result = eva.uc.owfs.destroy_owfs_bus(i)
        if result and eva.core.db_update == 1: eva.uc.owfs.save()
        return result

    @log_d
    @api_need_master
    def list_owfs_buses(self, **kwargs):
        """
        list OWFS buses

        Args:
            k: .master
        """
        parse_api_params(kwargs)
        return sorted(eva.uc.owfs.serialize(), key=lambda k: k['id'])

    @log_d
    @api_need_master
    def get_owfs_bus(self, **kwargs):
        """
        get OWFS bus configuration

        Args:
            k: .master
            .i: bus ID
        """
        i = parse_api_params(kwargs, 'i', 'S')
        return eva.uc.owfs.serialize(i)

    @log_d
    @api_need_master
    def test_owfs_bus(self, **kwargs):
        """
        test OWFS bus

        Verifies :doc:`OWFS bus</owfs>` checking library initialization status.

        Args:
            k: .master
            .i: bus ID
        """
        i = parse_api_params(kwargs, 'i', 'S')
        bus = eva.uc.owfs.get_bus(i)
        if bus: bus.release()
        if bus is None: raise ResourceNotFound
        elif bus is False: raise FunctionFailed('Test failed')
        elif bus == 0: raise ResourceBusy
        return True

    @log_i
    @api_need_master
    def scan_owfs_bus(self, **kwargs):
        """
        scan OWFS bus

        Scan :doc:`OWFS bus</owfs>` for connected 1-wire devices.

        Args:
            k: .master
            .i: bus ID

        Optional:
            p: specified equipment type (e.g. DS18S20,DS2405), list or comma
                separated
            a: Equipment attributes (e.g. temperature, PIO), list comma
                separated
            n: Equipment path
            has_all: Equipment should have all specified attributes
            full: obtain all attributes plus values
            
        Returns:
            If both "a" and "full" args are specified. the function will
            examine and values of attributes specified in "a" param. (This will
            poll "released" bus, even if locking is set up, so be careful with
            this feature in production environment).
        """
        i, p, a, n, has_all, full = parse_api_params(kwargs, 'ipanHY', 'S..sbb')
        try:
            if p and not isinstance(p, list):
                p = p.split(',')
        except:
            raise InvalidParameter('Unable to parse type')
        try:
            if a and not isinstance(a, list):
                a = a.split(',')
        except:
            raise InvalidParameter('Unable to parse attributes')
        bus = eva.uc.owfs.get_bus(i)
        if bus: bus.release()
        elif bus is None: raise ResourceNotFound
        else: raise FunctionFailed('Unable to acquire bus')
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

    # master functions for PHI configuration

    @log_i
    @api_need_master
    def load_phi(self, **kwargs):
        """
        load PHI module

        Loads :doc:`Physical Interface</drivers>`.

        Args:
            k: .master
            .i: PHI ID
            m: PHI module

        Optional:
            c: PHI configuration
            save: save driver configuration after successful call
        """
        i, m, cfg, save = parse_api_params(kwargs, 'imcS', 'SS.b')
        try:
            _cfg = dict_from_str(cfg)
        except:
            raise InvalidParameter('Unable to parse config')
        if eva.uc.driverapi.load_phi(i, m, _cfg):
            if save: eva.uc.driverapi.save()
            return eva.uc.driverapi.get_phi(i).serialize(full=True, config=True)

    @log_d
    @api_need_master
    def get_phi(self, **kwargs):
        """
        get loaded PHI information

        Args:
            k: .master
            .i: PHI ID
        """
        i = parse_api_params(kwargs, 'i', 'S')
        phi = eva.uc.driverapi.get_phi(i)
        if phi:
            return phi.serialize(full=True, config=True)
        else:
            raise ResourceNotFound

    @log_i
    @api_need_master
    def set_phi_prop(self, **kwargs):
        """
        set PHI configuration property

        appends property to PHI configuration and reloads module

        Args:
            k: .master
            .i: PHI ID
            .p: property name (or empty for batch set)
            .v: propery value (or dict for batch set)

        Optional:
            save: save configuration after successful call
        """
        i, p, v, save = parse_api_params(kwargs, 'ipvS', 'S.Rb')
        eva.uc.driverapi.set_phi_prop(i, p, v)
        if save: eva.uc.driverapi.save()
        return True

    @log_d
    @api_need_master
    def list_phi(self, **kwargs):
        """
        list loaded PHIs

        Args:
            k: .master
            full: get exntended information
        """
        full = parse_api_params(kwargs, 'Y', 'b')
        return sorted(
            eva.uc.driverapi.serialize_phi(full=full, config=full),
            key=lambda k: k['id'])

    @log_i
    @api_need_master
    def test_phi(self, **kwargs):
        """
        test PHI

        Get PHI test result (as-is). All PHIs respond to **self** command,
        **help** command returns all available test commands.

        Args:
            k: .master
            .m: PHI id
            .c: test command
        """
        i, c = parse_api_params(kwargs, 'ic', 'SS')
        phi = eva.uc.driverapi.get_phi(i)
        if not phi: raise ResourceNotFound
        return phi.test(c)

    @log_i
    @api_need_master
    def exec_phi(self, **kwargs):
        """
        execute additional PHI commands

        Execute PHI command and return execution result (as-is). **help**
        command returns all available commands.

        Args:
            k: .master
            .i: PHI id
            .c: command to exec
        """
        i, c = parse_api_params(kwargs, 'ic', 'SS')
        phi = eva.uc.driverapi.get_phi(i)
        if not phi: raise ResourceNotFound
        return phi.exec(c, c)

    @log_w
    @api_need_master
    def unload_phi(self, **kwargs):
        """
        unload PHI

        Unloads PHI. PHI should not be used by any :doc:`driver</drivers>`
        (except *default*, but the driver should not be in use by any
        :doc:`item</items>`).

        If driver <phi_id.default> (which's loaded automatically with PHI) is
        present, it will be unloaded as well.

        Args:
            k: .master
            .i: PHI ID
        """
        i = parse_api_params(kwargs, 'i', 'S')
        eva.uc.driverapi.unload_phi(i)
        if eva.core.db_update == 1: eva.uc.driverapi.save()
        return True

    @log_w
    @api_need_master
    def unlink_phi_mod(self, **kwargs):
        """
        delete PHI module file

        Deletes PHI module file, if the module is loaded, all its instances
        should be unloaded first.

        Args:
            k: .master
            .m: PHI module name (without *.py* extension)
        """
        m = parse_api_params(kwargs, 'm', 'S')
        eva.uc.driverapi.unlink_phi_mod(m)
        return True

    @log_w
    @api_need_master
    def put_phi_mod(self, **kwargs):
        """
        upload PHI module

        Allows to upload new PHI module to *xc/drivers/phi* folder.

        Args:
            k: .master
            .m: PHI module name (without *.py* extension)
            c: module content

        Optional:
            force: overwrite PHI module file if exists
        """
        m, c, force = parse_api_params(kwargs, 'mcF', 'SSb')
        eva.uc.driverapi.put_phi_mod(m, c, force)
        return eva.uc.driverapi.modinfo_phi(m)

    @log_d
    @api_need_master
    def modinfo_phi(self, **kwargs):
        """
        get PHI module info

        Args:
            k: .master
            .m: PHI module name (without *.py* extension)
        """
        m = parse_api_params(kwargs, 'm', 'S')
        return eva.uc.driverapi.modinfo_phi(m)

    @log_d
    @api_need_master
    def modhelp_phi(self, **kwargs):
        """
        get PHI usage help

        Args:
            k: .master
            .m: PHI module name (without *.py* extension)
            .c: help context (*cfg*, *get* or *set*)
        """
        m, c = parse_api_params(kwargs, 'mc', 'SS')
        return eva.uc.driverapi.modhelp_phi(m, c)

    @log_d
    @api_need_master
    def list_phi_mods(self, **kwargs):
        """
        get list of available PHI modules

        Args:
            k: .master
        """
        return eva.uc.driverapi.list_phi_mods()

    @log_d
    @api_need_master
    def get_phi_map(self, **kwargs):
        phi_id, action_map = parse_api_params(kwargs, 'ia', 'S.')
        return eva.uc.driverapi.get_map(phi_id, action_map)

    # master functions for LPI/driver management

    @log_i
    @api_need_master
    def load_driver(self, **kwargs):
        """
        Loads a :doc:`driver</drivers>`, combining previously loaded PHI and
        chosen LPI module.

        Args:
            k: .master
            .i: LPI ID
            m: LPI module
            .p: PHI ID

        Optional:
            c: Driver (LPI) configuration, optional
            save: save configuration after successful call
        """
        i, m, p, c, save = parse_api_params(kwargs, 'impcS', 'SSS.b')
        try:
            _cfg = dict_from_str(cfg)
        except:
            raise InvalidParameter('Unable to parse config')
        if eva.uc.driverapi.load_driver(i, m, p, _cfg):
            if save: eva.uc.driverapi.save()
            return eva.uc.driverapi.get_driver(p + '.' + i).serialize(
                full=True, config=True)

    @log_w
    @api_need_master
    def unload_driver(self, **kwargs):
        """
        unload driver

        Unloads driver. Driver should not be used by any :doc:`item</items>`.

        Args:
            k: .master
            i: driver ID
        """
        i = parse_api_params(kwargs, 'i', 'S')
        eva.uc.driverapi.unload_driver(i)
        if eva.core.db_update == 1: eva.uc.driverapi.save()
        return True

    @log_d
    @api_need_master
    def list_drivers(self, **kwargs):
        """
        list loaded drivers

        Args:
            k: .master
            full: get exntended information
        """
        full = parse_api_params(kwargs, 'Y', 'b')
        return sorted(
            eva.uc.driverapi.serialize_lpi(full=full, config=full),
            key=lambda k: k['id'])

    @log_d
    @api_need_master
    def get_driver(self, **kwargs):
        """
        get loaded PHI information

        Args:
            k: .master
            .i: PHI ID
        """
        i = parse_api_params(kwargs, 'i', 'S')
        if not i: return None
        lpi = eva.uc.driverapi.get_driver(i)
        if lpi:
            return lpi.serialize(full=True, config=True)
        else:
            raise ResourceNotFound

    @log_i
    @api_need_master
    def set_driver_prop(self, **kwargs):
        """
        set driver (LPI) configuration property

        appends property to LPI configuration and reloads module

        Args:
            k: .master
            .i: driver ID
            .p: property name (or empty for batch set)
            .v: propery value (or dict for batch set)

        Optional:
            save: save driver configuration after successful call
        """
        i, p, v, save = parse_api_params(kwargs, 'ipvS', 'S.Rb')
        if i.split('.')[-1] == 'default':
            raise ResourceBusy('Properties for default drivers can not be set')
        eva.uc.driverapi.set_driver_prop(i, p, v)
        if save: eva.uc.driverapi.save()
        return True

    @log_d
    @api_need_master
    def list_lpi_mods(self, **kwargs):
        """
        get list of available LPI modules

        Args:
            k: .master
        """
        return eva.uc.driverapi.list_lpi_mods()

    @log_d
    @api_need_master
    def modinfo_lpi(self, **kwargs):
        """
        get LPI module info

        Args:
            k: .master
            .m: LPI module name (without *.py* extension)
        """
        m = parse_api_params(kwargs, 'm', 'S')
        return eva.uc.driverapi.modinfo_lpi(m)

    @log_d
    @api_need_master
    def modhelp_lpi(self, **kwargs):
        """
        get LPI usage help

        Args:
            k: .master
            .m: LPI module name (without *.py* extension)
            .c: help context (*cfg*, *action* or *update*)
        """
        m, c = parse_api_params(kwargs, 'mc', 'SS')
        return eva.uc.driverapi.modhelp_lpi(m, c)

    @log_i
    @api_need_master
    def assign_driver(self, **kwargs):
        """
        assign driver to item

        Sets the specified driver to :doc:`item</items>`, automatically
        updating item props:

        * **action_driver_config**,**update_driver_config** to the specified
            configuration
        * **action_exec**, **update_exec** to do all operations via driver
            function calls (sets both to *|<driver_id>*)

        To unassign driver, set driver ID to empty/null.

        Args:
            k: masterkey
            i: item ID
            d: driver ID (if none - all above item props are set to *null*)
            c: configuration (e.g. port number)

        Optional:
            save: save item configuration after successful call
        """
        k, i, d, c, save = parse_function_params(kwargs, 'kidcS', '.S..b')
        if is_oid(i):
            t, i = parse_oid(i)
        item = eva.uc.controller.get_item(i)
        if not item or (is_oid(i) and item and item.item_type != t):
            raise ResourceNotFound
        drv_p = '|' + d if d else None
        props = {'update_driver_config': c, 'update_exec': drv_p}
        if item.item_type == 'unit':
            props['action_driver_config'] = c
            props['action_exec'] = drv_p
        self.set_prop(k=k, i=i, v=props)
        return True


class UC_HTTP_API_abstract(UC_API, GenericHTTP_API):

    def __init__(self):
        super().__init__()
        self._nofp_log('put_phi_mod', 'c')

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
    def GET(self, rtp, k, ii, full, save, kind, method, for_dir, props):
        try:
            return super().GET(rtp, k, ii, full, save, kind, method, for_dir,
                               props)
        except MethodNotFound:
            pass
        if rtp in ['unit', 'sensor', 'mu']:
            if kind == 'groups':
                return self.groups(k=k, p=rtp)
            elif kind == 'history':
                return self.state_history(k=k, i=ii, **props)
            elif kind == 'props':
                return self.list_props(k=k, i=ii)
            elif for_dir:
                return self.state(k=k, p=rtp, g=ii, full=full, **props)
            else:
                return self.state(k=k, p=rtp, i=ii, full=full, **props)
        elif rtp == 'action':
            return self.result(
                k=k, i=props.get('i'), u=ii, g=props.get('g'), s=props.get('s'))
        elif rtp == 'driver':
            if ii:
                return self.get_driver(k=k, i=ii)
            else:
                return self.list_drivers(k=k, full=full)
        elif rtp == 'lpi-module':
            if ii:
                if 'help' in props:
                    return self.modhelp_lpi(k=k, m=ii, c=props['help'])
                else:
                    return self.modinfo_lpi(k=k, m=ii)
            else:
                return self.list_lpi_mods(k=k)
        elif rtp == 'phi':
            if ii:
                return self.get_phi(k=k, i=ii)
            else:
                return self.list_phi(k=k, full=full)
        elif rtp == 'phi-module':
            if ii:
                if 'help' in props:
                    return self.modhelp_phi(k=k, m=ii, c=props['help'])
                else:
                    return self.modinfo_phi(k=k, m=ii)
            else:
                return self.list_phi_mods(k=k)
        elif rtp == 'modbus':
            if ii:
                return self.get_modbus_port(k=k, i=ii)
            else:
                return self.list_modbus_ports(k=k)
        elif rtp == 'owfs':
            if ii:
                return self.get_owfs_bus(k=k, i=ii)
            else:
                return self.list_owfs_buses(k=k)
        elif rtp == 'device-tpl':
            if not ii:
                return self.list_device_tpl(k=k)
        raise MethodNotFound

    @generic_web_api_method
    @restful_api_method
    def POST(self, rtp, k, ii, full, save, kind, method, for_dir, props):
        try:
            return super().POST(rtp, k, ii, full, save, kind, method, for_dir,
                                props)
        except MethodNotFound:
            pass
        if rtp == 'action':
            if not ii:
                a = self.action(k=k, **props)
                set_restful_response_location(a['uuid'], 'action')
                return a
        elif rtp == 'phi':
            if ii:
                if method == 'test':
                    return self.test_phi(k=k, i=ii, **props)
                elif method == 'exec':
                    return self.exec_phi(k=k, i=ii, **props)
        elif rtp == 'modbus':
            if ii:
                if method == 'test':
                    return self.test_modbus_port(k=k, i=ii)
        elif rtp == 'owfs':
            if ii:
                if method == 'test':
                    return self.test_owfs_bus(k=k, i=ii)
                elif method == 'scan':
                    return self.scan_owfs_bus(k=k, i=ii, full=full, **props)
        elif rtp == 'device-tpl':
            if ii:
                if method == 'create':
                    return self.create_device(k=k, t=ii, **props)
                elif method == 'update':
                    return self.update_device(k=k, t=ii, **props)
                elif method == 'delete':
                    return self.destroy_device(k=k, t=ii, **props)
        raise MethodNotFound

    @generic_web_api_method
    @restful_api_method
    def PUT(self, rtp, k, ii, full, save, kind, method, for_dir, props):
        try:
            return super().PUT(rtp, k, ii, full, save, kind, method, for_dir,
                               props)
        except MethodNotFound:
            pass
        if rtp == 'action':
            if ii:
                return self.action(k=k, u=ii, **props)
        elif rtp in ['unit', 'sensor', 'mu']:
            self.create(k=k, i=rtp + ':' + ii, save=save)
            self.set_prop(k=k, i=ii, v=props, save=save)
            return self.state(k=k, i=ii, p=rtp, full=True)
        elif rtp == 'driver':
            try:
                phi_id, lpi_id = ii.split('.')
            except:
                raise InvalidParameter('Invalid driver ID')
            return self.load_driver(k=k, i=lpi_id, p=phi_id, save=save**props)
        elif rtp == 'modbus':
            return self.create_modbus_port(k=k, i=ii, save=save, **props)
        elif rtp == 'owfs':
            return self.create_owfs_bus(k=k, i=ii, save=save, **props)
        elif rtp == 'phi':
            return self.load_phi(k=k, i=ii, save=save, **props)
        elif rtp == 'phi-module':
            return self.put_phi_mod(k=k, m=ii, **props)
        raise MethodNotFound

    @generic_web_api_method
    @restful_api_method
    def PATCH(self, rtp, k, ii, full, save, kind, method, for_dir, props):
        try:
            return super().PATCH(rtp, k, ii, full, save, kind, method, for_dir,
                                 props)
        except MethodNotFound:
            pass
        raise MethodNotFound

    @generic_web_api_method
    @restful_api_method
    def DELETE(self, rtp, k, ii, full, save, kind, method, for_dir, props):
        try:
            return super().DELETE(rtp, k, ii, full, save, kind, method, for_dir,
                                  props)
        except MethodNotFound:
            pass
        if rtp == 'driver':
            if ii:
                return self.unload_driver(k=k, i=ii)
        elif rtp == 'phi':
            if ii:
                return self.unload_phi(k=k, i=ii)
        elif rtp == 'phi-module':
            if ii:
                return self.unlink_phi_mod(k=k, m=ii)
        elif rtp == 'modbus':
            if ii:
                return self.destroy_modbus_port(k=k, i=ii)
        elif rtp == 'owfs':
            if ii:
                return self.destroy_owfs_bus(k=k, i=ii)
        elif rtp in ['unit', 'sensor', 'mu']:
            if ii:
                return self.destroy(k=k, i=rtp + ':' + ii)
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
