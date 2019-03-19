__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.0"

import cherrypy
import jsonpickle
import shlex
import eva.core

import eva.api
import eva.sysapi

from eva.api import GenericHTTP_API
from eva.api import JSON_RPC_API_abstract
from eva.api import GenericAPI

from eva.api import parse_api_params
from eva.api import format_resource_id

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

from eva import apikey

from functools import wraps

import eva.lm.controller
import eva.lm.extapi
import eva.ei
import jinja2
import jsonpickle
import logging


class LM_API(GenericAPI):

    def __init__(self):
        self.controller = eva.lm.controller
        super().__init__()

    @log_d
    def groups(self, **kwargs):
        """
        get item group list

        Get the list of item groups. Useful e.g. for custom interfaces.

        Args:
            k:
            .p: item type (must be set to lvar [LV])
        """
        k, tp = parse_function_params(
            kwargs, 'kp', '.S', defaults={'p': 'lvar'})
        if apikey.check_master(k):
            if tp == 'LV' or tp == 'lvar':
                return sorted(eva.lm.controller.lvars_by_group.keys())
            else:
                return []
        else:
            groups = []
            m = None
            if tp == 'LV' or tp == 'lvar':
                m = eva.lm.controller.lvars_by_full_id
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
        get item state

        State of the item or all items of the specified type can be obtained
        using state command.

        Args:
            k:

        Optional:
            .p: item type (none or lvar [LV])
            .i: item id
            .g: item group
            .full: return full state
        """
        k, i, group, tp, full = parse_function_params(
            kwargs, 'kigpY', '.sssb', defaults={'p': 'lvar'})
        if tp not in ['LV', 'lvar']: return None
        if i:
            item = eva.lm.controller.get_lvar(i)
            if not item or not apikey.check(k, item): raise ResourceNotFound
            if is_oid(i):
                t, iid = parse_oid(i)
                if not item or item.item_type != t: raise ResourceNotFound
            return item.serialize(full=full)
        else:
            gi = eva.lm.controller.lvars_by_full_id
            result = []
            for i, v in gi.copy().items():
                if apikey.check(k, v) and \
                        (not group or \
                            eva.item.item_match(v, [], [group])):
                    r = v.serialize(full=full)
                    result.append(r)
            return sorted(result, key=lambda k: k['oid'])

    @log_i
    def set(self, **kwargs):
        """
        set lvar state

        Set status and value of a :ref:`logic variable<lvar>`.

        Args:
            k:
            .i: lvar id
        
        Optional:
            s: lvar status
            v: lvar value
        """
        k, i, s, v, = parse_function_params(kwargs, 'kisv', '.si.')
        item = eva.lm.controller.get_lvar(i)
        if not item or not apikey.check(k, item): raise ResourceNotFound
        if status and not -1 <= status <= 1:
            raise InvalidParameter('status should be -1, 0 or 1')
        if value is None: v = 'null'
        else: v = value
        return item.update_set_state(status=status, value=v)

    @log_i
    def reset(self, **kwargs):
        """
        reset lvar state

        Set status and value of a :ref:`logic variable<lvar>` to *1*. Useful
        when lvar is being used as a timer to reset it, or as a flag to set it
        *True*.

        Args:
            k:
            .i: lvar id
        """
        k, i = parse_function_params(kwargs, 'ki', '.s')
        return self.set(k=k, i=i, s=1, v='1')

    @log_i
    def clear(self, **kwargs):
        """
        clear lvar state

        set status (if **expires** lvar param > 0) or value (if **expires**
        isn't set) of a :ref:`logic variable<lvar>` to *0*. Useful when lvar is
        used as a timer to stop it, or as a flag to set it *False*.

        Args:
            k:
            .i: lvar id
        """
        k, i = parse_function_params(kwargs, 'ki', '.s')
        item = eva.lm.controller.get_lvar(i)
        if not item or not apikey.check(k, item): raise ResourceNotFound
        return self.set(k=k, i=i, s=0 if item.expires > 0 else 1, v='0')

    @log_i
    def toggle(self, **kwargs):
        """
        toggle lvar state

        switch value of a :ref:`logic variable<lvar>` between *0* and *1*.
        Useful when lvar is being used as a flag to switch it between
        *True*/*False*.

        Args:
            k:
            .i: lvar id
        """
        item = eva.lm.controller.get_lvar(i)
        if not item or not apikey.check(k, item): raise ResourceNotFound
        v = item.value
        if v != '0':
            return self.clear(k=k, i=i)
        else:
            return self.reset(k=k, i=i)

    @log_i
    def run(self, **kwargs):
        """
        execute macro

        Execute a :doc:`macro<macros>` with the specified arguments.

        Args:
            k:
            .i: macro id

        Optional:
        a: macro arguments, array or space separated
        kw: macro keyword arguments, name=value, comma separated or dict
        w: wait for the completion for the specified number of seconds
        .u: action UUID (will be auto generated if none specified)
        p: queue priority (default is 100, lower is better)
        q: global queue timeout, if expires, action is marked as "dead"
        """
        k, i, a, kw, w, u, p, q = parse_function_params(kwargs, 'kiaKwupq',
                                                        '.s..nsin')
        macro = eva.lm.controller.get_macro(i)
        if not macro or not eva.apikey.check(k, macro): raise ResourceNotFound
        if a is None:
            a = []
        else:
            if isinstance(a, list):
                pass
            elif isinstance(a, str):
                try:
                    a = shlex.split(a)
                except:
                    a = a.split(' ')
            else:
                a = [a]
        if isinstance(kw, str):
            try:
                kw = dict_from_str(kw)
            except:
                raise InvalidParameter('Unable to parse kw args')
        elif isinstance(kwargs, dict):
            pass
        else:
            kw = {}
        return self._process_action_result(
            eva.lm.controller.exec_macro(
                macro=macro,
                argv=a,
                kwargs=kw,
                priority=p,
                q_timeout=q,
                wait=w,
                action_uuid=u))

    @log_i
    def result(self, **kwargs):
        """
        macro execution result

        Get :doc:`macro<macros>` execution results either by action uuid or by
        macro id.

        Args:
            k:

        Optional:
            .u: action uuid or
            .i: macro id
            g: filter by unit group
            s: filter by action status: Q for queued, R for running, F for
               finished

        Return:
            list or single serialized action object
        """
        k, u, i, g, s = parse_function_params(kwargs, 'kuigs', '.ssss')
        return self._result(k, u, i, g, s, rtp='lmacro')

# dm rules functions

    @log_d
    def list_rule_props(self, **kwargs):
        """
        list rule properties

        Get all editable parameters of the :doc:`decision
        rule</lm/decision_matrix>`.

        Args:
            k:
            .i: rule id
        """
        k, i = parse_function_params(kwargs, 'ki', '.s')
        if is_oid(i):
            t, i = parse_oid(i)
        item = eva.lm.controller.get_dm_rule(i)
        if not item or (is_oid(i) and item and item.item_type != t):
            raise ResourceNotFound
        if not apikey.check(k, item): raise ResourceNotFound
        result = item.serialize(props=True)
        if not apikey.check_master(k):
            for i in result:
                if i[:9] != 'in_range_' and \
                        i not in [ 'enabled', 'chillout_time', 'condition' ]:
                    del result[i]
        return result

    @log_w
    def set_rule_prop(self, **kwargs):
        """
        set rule parameters

        Set configuration parameters of the :doc:`decision
        rule</lm/decision_matrix>`.

        Args:
        
            k:
            .i: rule id
            .p: property name (or empty for batch set)
        
        Optional:
            .v: propery value (or dict for batch set)
            save: save configuration after successful call
        """
        k, i, p, v, save = parse_api_params(kwargs, 'kipvS', '.s..b')
        item = eva.lm.controller.get_dm_rule(i)
        if not item or not p or not isinstance(p, str): raise ResourceNotFound
        if p[:9] == 'in_range_' or p in ['enabled', 'chillout_time']:
            if not apikey.check(k, allow = [ 'dm_rule_props' ]) and \
                    not apikey.check(k, item):
                        raise ResourceNotFound
        else:
            if not apikey.check_master(k): raise ResourceNotFound
        if not self._set_prop(item, p, v, save):
            raise FunctionFailed
        if (p and p in ['priority', 'description']) or \
                (isinstance(v, dict) and \
                    ('property' in v or 'description' in v)):
            eva.lm.controller.DM.sort()
        return True

    @log_d
    def list_rules(self, **kwargs):
        """
        get rules list

        Get the list of all available :doc:`decision rules<decision_matrix>`.

        Args:
            k:
        """
        k = parse_function_params(kwargs, 'k', '.')
        rmas = apikey.check(k, allow=['dm_rules_list'])
        result = []
        for i in eva.lm.controller.DM.rules.copy():
            if rmas or apikey.check(k, i):
                d = i.serialize(info=True)
                if not apikey.check_master(k):
                    for x in d.copy():
                        if x[:9] != 'in_range_' and \
                                x not in [
                                        'id',
                                        'condition',
                                        'description',
                                        'chillout_ends_in',
                                        'enabled',
                                        'chillout_time'
                                        ]:
                            del d[x]
                result.append(d)
        return result

    def get_rule(self, **kwargs):
        """
        get rule information

        Args:
            k:
            .i: rule id
        """
        k, i = parse_function_params(kwargs, 'ki', '.s')
        item = eva.lm.controller.get_dm_rule(i)
        if not item or not apikey.check(k, item): raise ResourceNotFound
        d = item.serialize(info=True)
        if not apikey.check_master(k):
            for x in d.copy():
                if x[:9] != 'in_range_' and x not in [
                        'id', 'condition', 'description', 'chillout_ends_in',
                        'enabled', 'chillout_time'
                ]:
                    del d[x]
        return d


# master functions for item configuration

    @api_need_master
    def create_rule(self, **kwargs):
        """
        create new rule

        Creates new :doc:`decision rule<decision_matrix>`. Rule id (UUID) is
        generated automatically unless specified.

        Args:
            k: .master

        Optional:
            .u: rule UUID to set
            .v: rule properties (dict)
            save: save unit configuration immediately
        """
        u, v, save = parse_api_params(kwargs, 'uvS', 's.b')
        rule = eva.lm.controller.create_dm_rule(save=save, rule_uuid=u)
        if v and isinstance(v, dict):
            self._set_prop(rule, v=v, save=save)
        return rule.serialize(info=True)


    @api_need_master
    def destroy_rule(self, k=None, i=None):
        """
        delete rule

        Deletes :doc:`decision rule<decision_matrix>`.

        Args:
            k: .master
            .i: rule id
        """
        return eva.lm.controller.destroy_dm_rule(i)

    # TODO
    def groups_macro(self, k=None):
        result = []
        for i, v in eva.lm.controller.macros_by_id.copy().items():
            if apikey.check(k, v) and \
                    v.group not in result:
                result.append(v.group)
        return sorted(result)

    def groups_cycle(self, k=None):
        result = []
        for i, v in eva.lm.controller.cycles_by_id.copy().items():
            if apikey.check(k, v) and \
                    v.group not in result:
                result.append(v.group)
        return sorted(result)

    def get_config(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        item = eva.lm.controller.get_item(i)
        return item.serialize(config=True) if item else None

    def save_config(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        item = eva.lm.controller.get_item(i)
        return item.save() if item else None

    def list(self, k=None, group=None, tp=None):
        if not apikey.check(k, master=True): return None
        result = []
        if tp == 'LV' or tp == 'lvar':
            items = eva.lm.controller.lvars_by_full_id
        else:
            items = eva.lm.controller.items_by_full_id
        for i, v in items.copy().items():
            if not group or eva.item.item_match(v, [], [group]):
                result.append(v.serialize(info=True))
        return sorted(result, key=lambda k: k['oid'])

    def list_remote(self, k=None, i=None, group=None, tp=None):
        if not apikey.check(k, master=True): return None
        result = []
        items = []
        if i:
            controller = eva.lm.controller.get_controller(i)
            if not controller: return None
            c_id = controller.item_id
        if tp is None or tp in ['U', 'unit', '#']:
            if i:
                if not c_id in eva.lm.controller.uc_pool.units_by_controller:
                    return None
                items.append(
                    eva.lm.controller.uc_pool.units_by_controller[c_id])
            else:
                items.append(eva.lm.controller.uc_pool.units_by_controller)
        if tp is None or tp in ['S', 'sensor', '#']:
            if i:
                if not c_id in eva.lm.controller.uc_pool.sensors_by_controller:
                    return None
                items.append(
                    eva.lm.controller.uc_pool.sensors_by_controller[c_id])
            else:
                items.append(eva.lm.controller.uc_pool.sensors_by_controller)
        if not items:
            return None
        if i:
            for x in items:
                for a, v in x.copy().items():
                    if not group or eva.item.item_match(v, [], [group]):
                        result.append(v.serialize(full=True))
        else:
            for x in items:
                for c, d in x.copy().items():
                    for a, v in d.copy().items():
                        if not group or eva.item.item_match(v, [], [group]):
                            result.append(v.serialize(full=True))
        return sorted(
            sorted(result, key=lambda k: k['oid']),
            key=lambda k: ['controller_id'])

    def list_controllers(self, k=None):
        if not apikey.check(k, master=True): return None
        result = []
        for i, v in eva.lm.controller.remote_ucs.copy().items():
            result.append(v.serialize(info=True))
        return sorted(result, key=lambda k: k['full_id'])

    def list_macros(self, k=None, group=None):
        result = []
        for i, v in eva.lm.controller.macros_by_id.copy().items():
            if apikey.check(k, v) and \
                    (not group or eva.item.item_match(v, [], [ group ])):
                result.append(v.serialize(info=True))
        return sorted(result, key=lambda k: k['full_id'])

    def create_macro(self, k=None, i=None, g=None, save=False):
        if not apikey.check(k, master=True): return None
        return eva.lm.controller.create_macro(i, g, save)

    def destroy_macro(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        return eva.lm.controller.destroy_macro(i)

    def list_cycles(self, k=None, group=None):
        result = []
        for i, v in eva.lm.controller.cycles_by_id.copy().items():
            if apikey.check(k, v) and \
                    (not group or eva.item.item_match(v, [], [ group ])):
                result.append(v.serialize(full=True))
        return sorted(result, key=lambda k: k['full_id'])

    def get_cycle(self, k=None, i=None):
        if not apikey.check(k, i): return None
        item = eva.lm.controller.get_cycle(i)
        if not item: return None
        result = item.serialize(full=True)
        if not apikey.check(k, master=True):
            try:
                del result['macro']
                del result['on_error']
            except:
                eva.core.log_traceback()
        return result

    def create_cycle(self, k=None, i=None, g=None, save=False):
        if not apikey.check(k, master=True): return None
        return eva.lm.controller.create_cycle(i, g, save)

    def destroy_cycle(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        return eva.lm.controller.destroy_cycle(i)

    def append_controller(self,
                          k=None,
                          uri=None,
                          key=None,
                          mqtt_update=None,
                          ssl_verify=True,
                          timeout=None,
                          save=False):
        if not apikey.check(k, master=True) or not uri: return None
        return eva.lm.controller.append_controller(
            uri=uri,
            key=key,
            mqtt_update=mqtt_update,
            ssl_verify=ssl_verify,
            timeout=timeout,
            save=save)

    def remove_controller(self, k=None, controller_id=None):
        if not apikey.check(k, master=True) or not controller_id:
            return False
        return eva.lm.controller.remove_controller(controller_id)

    def list_props(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        item = eva.lm.controller.get_item(i)
        return item.serialize(props=True) if item else None

    def list_macro_props(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        item = eva.lm.controller.get_macro(i)
        return item.serialize(props=True) if item else None

    def list_cycle_props(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        item = eva.lm.controller.get_cycle(i)
        return item.serialize(props=True) if item else None

    def list_controller_props(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        item = eva.lm.controller.get_controller(i)
        return item.serialize(props=True) if item else None

    def get_controller(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        item = eva.lm.controller.get_controller(i)
        if item is None: return None
        return item.serialize(info=True)

    def test_controller(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        item = eva.lm.controller.get_controller(i)
        if item is None: return None
        return True if item.test() else False

    def set_prop(self, k=None, i=None, p=None, v=None, save=False):
        if not apikey.check(k, master=True): return None
        item = eva.lm.controller.get_item(i)
        if item:
            result = item.set_prop(p, v, save)
            if result and item.config_changed and save:
                item.save()
            return result
        else:
            return None

    def set_controller_prop(self, k=None, i=None, p=None, v=None, save=False):
        if not apikey.check(k, master=True): return None
        controller = eva.lm.controller.get_controller(i)
        if controller:
            result = controller.set_prop(p, v, save)
            if result and controller.config_changed and save:
                controller.save()
            return result
        else:
            return None

    def enable_controller(self, k=None, i=None, save=False):
        if not apikey.check(k, master=True): return None
        controller = eva.lm.controller.get_controller(i)
        if controller:
            result = controller.set_prop('enabled', 1, save)
            if result and controller.config_changed and save:
                controller.save()
            return result
        else:
            return None

    def disable_controller(self, k=None, i=None, save=False):
        if not apikey.check(k, master=True): return None
        controller = eva.lm.controller.get_controller(i)
        if controller:
            result = controller.set_prop('enabled', 0, save)
            if result and controller.config_changed and save:
                controller.save()
            return result
        else:
            return None

    def set_macro_prop(self, k=None, i=None, p=None, v=None, save=False):
        if not apikey.check(k, master=True): return None
        macro = eva.lm.controller.get_macro(i)
        if macro:
            result = macro.set_prop(p, v, save)
            if result and macro.config_changed and save:
                macro.save()
            return result
        else:
            return None

    def set_cycle_prop(self, k=None, i=None, p=None, v=None, save=False):
        if not apikey.check(k, master=True): return None
        cycle = eva.lm.controller.get_cycle(i)
        if cycle:
            result = cycle.set_prop(p, v, save)
            if result and cycle.config_changed and save:
                cycle.save()
            return result
        else:
            return None

    def start_cycle(self, k=None, i=None):
        if not apikey.check(k, i): return None
        cycle = eva.lm.controller.get_cycle(i)
        if cycle:
            return cycle.start()
        else:
            return None

    def stop_cycle(self, k=None, i=None, wait=False):
        if not apikey.check(k, i): return None
        cycle = eva.lm.controller.get_cycle(i)
        if cycle:
            cycle.stop(wait=wait)
            return True
        else:
            return None

    def reset_cycle_stats(self, k=None, i=None):
        if not apikey.check(k, i): return None
        cycle = eva.lm.controller.get_cycle(i)
        if cycle:
            cycle.reset_stats()
            return True
        else:
            return None

    def reload_controller(self, k=None, i=None):
        if not apikey.check(k, master=True): return False
        if not i: return False
        if i.find('/') > -1:
            c = i.split('/')
            if len(c) > 2 or c[0] != 'uc': return None
            _i = c[1]
        else:
            _i = i
        return eva.lm.controller.uc_pool.reload_controller(_i)


    def create_lvar(self, k = None, lvar_id = None, \
            group = None, save = False):
        if not apikey.check(k, master=True): return None
        if is_oid(lvar_id):
            tp, i = parse_oid(lvar_id)
            if tp != 'lvar': return False
        else:
            i = lvar_id
        return eva.lm.controller.create_lvar(lvar_id=i, group=group, save=save)

    def destroy_lvar(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        return eva.lm.controller.destroy_item(i)

    # master functions for lmacro extension management

    def load_ext(self, k=None, i=None, m=None, cfg=None, save=False):
        if not apikey.check(k, master=True): return None
        if not i or not m: return None
        try:
            _cfg = dict_from_str(cfg)
        except:
            eva.core.log_traceback()
            return None
        if eva.lm.extapi.load_ext(i, m, _cfg):
            if save: eva.lm.extapi.save()
            return eva.lm.extapi.get_ext(i).serialize(full=True, config=True)

    def unload_ext(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        if not i: return None
        result = eva.lm.extapi.unload_ext(i)
        if result and eva.core.db_update == 1: eva.lm.extapi.save()
        return result

    def list_ext(self, k=None, full=False):
        if not apikey.check(k, master=True): return None
        return eva.lm.extapi.serialize(full=full, config=full)

    def get_ext(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        if not i: return None
        ext = eva.lm.extapi.get_ext(i)
        if ext:
            return ext.serialize(full=True, config=True)
        else:
            return None

    def list_ext_mods(self, k=None):
        if not apikey.check(k, master=True): return None
        return eva.lm.extapi.list_mods()

    def modinfo_ext(self, k=None, m=None):
        if not apikey.check(k, master=True): return None
        return eva.lm.extapi.modinfo(m)

    def modhelp_ext(self, k=None, m=None, c=None):
        if not apikey.check(k, master=True): return None
        return eva.lm.extapi.modhelp(m, c)

    def set_ext_prop(self, k=None, i=None, p=None, v=None, save=False):
        if not apikey.check(k, master=True): return None
        ext = eva.lm.extapi.get_ext(i)
        if not ext: return None
        if eva.lm.extapi.set_ext_prop(i, p, v):
            if save: eva.lm.extapi.save()
            return True
        return False


class LM_HTTP_API_abstract(LM_API, GenericHTTP_API):

    def __init__(self):
        super().__init__()


    def groups_macro(self, k=None):
        return super().groups_macro(k)

    def groups_cycle(self, k=None):
        return super().groups_cycle(k)

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

    def list_remote(self, k=None, i=None, g=None, p=None):
        result = super().list_remote(k, i, g, p)
        if result is None: raise cp_api_404()
        return result

    @api_need_master
    def list_controllers(self, k=None):
        result = super().list_controllers(k)
        if result is None: raise cp_api_error()
        return result

    def list_macros(self, k=None, g=None):
        result = super().list_macros(k, g)
        if result is None: raise cp_api_404()
        return result

    @api_need_master
    def create_macro(self, k=None, i=None, g=None, save=None):
        return http_api_result_ok() if super().create_macro(k, i, g, save) \
                else http_api_result_error()

    @api_need_master
    def destroy_macro(self, k=None, i=None):
        result = super().destroy_macro(k, i)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    def list_cycles(self, k=None, g=None):
        result = super().list_cycles(k, g)
        if result is None: raise cp_api_404()
        return result

    @api_need_master
    def create_cycle(self, k=None, i=None, g=None, save=None):
        return http_api_result_ok() if super().create_cycle(k, i, g, save) \
                else http_api_result_error()

    @api_need_master
    def destroy_cycle(self, k=None, i=None):
        result = super().destroy_cycle(k, i)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @api_need_master
    def append_controller(self,
                          k=None,
                          u=None,
                          a=None,
                          m=None,
                          s=None,
                          t=None,
                          save=None):
        sv = eva.tools.val_to_boolean(s)
        return http_api_result_ok() if super().append_controller(
            k, u, a, m, sv, t, save) else http_api_result_error()

    @api_need_master
    def enable_controller(self, k=None, i=None):
        return http_api_result_ok() if super().enable_controller(k, i) \
                else http_api_result_error()

    @api_need_master
    def disable_controller(self, k=None, i=None):
        return http_api_result_ok() if super().disable_controller(k, i) \
                else http_api_result_error()

    @api_need_master
    def remove_controller(self, k=None, i=None):
        result = super().remove_controller(k, i)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @api_need_master
    def list_props(self, k=None, i=None):
        result = super().list_props(k, i)
        if not result: raise cp_api_404()
        return result

    @api_need_master
    def list_macro_props(self, k=None, i=None):
        result = super().list_macro_props(k, i)
        if not result: raise cp_api_404()
        return result

    @api_need_master
    def list_cycle_props(self, k=None, i=None):
        result = super().list_cycle_props(k, i)
        if not result: raise cp_api_404()
        return result

    @api_need_master
    def get_cycle(self, k=None, i=None):
        result = super().get_cycle(k, i)
        if not result: raise cp_api_404()
        return result

    @api_need_master
    def list_controller_props(self, k=None, i=None):
        result = super().list_controller_props(k, i)
        if not result: raise cp_api_404()
        return result

    @api_need_master
    def get_controller(self, k=None, i=None):
        result = super().get_controller(k, i)
        if result is None:
            raise cp_api_404()
        return result

    @api_need_master
    def test_controller(self, k=None, i=None):
        result = super().test_controller(k, i)
        if result is None:
            raise cp_api_404()
        return http_api_result_ok() if \
                result else http_api_result_error()

    @api_need_master
    def set_prop(self, k=None, i=None, p=None, v=None, save=None):
        if save:
            _save = True
        else:
            _save = False
        return http_api_result_ok() if super().set_prop(k, i, p, v, _save) \
                else http_api_result_error()

    @api_need_master
    def set_macro_prop(self, k=None, i=None, p=None, v=None, save=None):
        if save:
            _save = True
        else:
            _save = False
        return http_api_result_ok() if super().set_macro_prop(
            k, i, p, v, _save) else http_api_result_error()

    @api_need_master
    def set_cycle_prop(self, k=None, i=None, p=None, v=None, save=None):
        if save:
            _save = True
        else:
            _save = False
        return http_api_result_ok() if super().set_cycle_prop(
            k, i, p, v, _save) else http_api_result_error()

    def start_cycle(self, k=None, i=None):
        return http_api_result_ok() if super().start_cycle(
            k, i) else http_api_result_error()

    def stop_cycle(self, k=None, i=None, wait=None):
        return http_api_result_ok() if super().stop_cycle(
            k, i, wait) else http_api_result_error()

    def reset_cycle_stats(self, k=None, i=None):
        return http_api_result_ok() if super().reset_cycle_stats(
            k,
            i,
        ) else http_api_result_error()

    @api_need_master
    def set_controller_prop(self, k=None, i=None, p=None, v=None, save=None):
        if save:
            _save = True
        else:
            _save = False
        return http_api_result_ok() if \
                super().set_controller_prop(k, i, p, v, _save) \
                else http_api_result_error()

    @api_need_master
    def reload_controller(self, k=None, i=None):
        return http_api_result_ok() if super().reload_controller(k, i) \
                else http_api_result_error()

    @api_need_master
    def create_lvar(self, k=None, i=None, g=None, save=None):
        return http_api_result_ok() if super().create_lvar(
            k, i, g, save) else http_api_result_error()

    @api_need_master
    def destroy_lvar(self, k=None, i=None):
        result = super().destroy_lvar(k, i)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @api_need_master
    def load_ext(self, k=None, i=None, m=None, c=None, save=False):
        result = super().load_ext(k, i, m, c, save)
        return result if result else http_api_result_error()

    @api_need_master
    def unload_ext(self, k=None, i=None):
        result = super().unload_ext(k, i)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @api_need_master
    def list_ext(self, k=None, full=None):
        result = super().list_ext(k, full)
        if result is None: raise cp_api_error()
        return result

    @api_need_master
    def list_ext_mods(self, k=None):
        return super().list_ext_mods(k)

    @api_need_master
    def get_ext(self, k=None, i=None):
        result = super().get_ext(k, i)
        if result is False: raise cp_api_error()
        if result is None: raise cp_api_404()
        return result

    @api_need_master
    def modinfo_ext(self, k=None, m=None):
        result = super().modinfo_ext(k, m)
        if not result:
            raise cp_api_error()
        else:
            return result

    @api_need_master
    def modhelp_ext(self, k=None, m=None, c=None):
        result = super().modhelp_ext(k, m, c)
        if result is None:
            raise cp_api_error()
        else:
            return result

    @api_need_master
    def set_ext_prop(self, k=None, i=None, p=None, v=None, save=None):
        result = super().set_ext_prop(k, i, p, v, save)
        if result is False: raise cp_api_error()
        if result is None: raise cp_api_404()
        return http_api_result_ok()


class LM_HTTP_API(LM_HTTP_API_abstract, GenericHTTP_API):

    def __init__(self):
        super().__init__()
        self.expose_api_methods('lmapi')
        self.wrap_exposed()


class LM_JSONRPC_API(eva.sysapi.SysHTTP_API_abstract,
                     eva.sysapi.SysHTTP_API_REST_abstract,
                     eva.api.JSON_RPC_API_abstract, LM_HTTP_API_abstract):

    def __init__(self):
        super().__init__()
        self.expose_api_methods('lmapi', set_api_uri=False)
        self.expose_api_methods('sysapi', set_api_uri=False)


class LM_REST_API(eva.sysapi.SysHTTP_API_abstract,
                  eva.sysapi.SysHTTP_API_REST_abstract,
                  eva.api.GenericHTTP_API_REST_abstract, LM_HTTP_API_abstract,
                  GenericHTTP_API):

    @generic_web_api_method
    @restful_api_method
    def GET(self, r, rtp, *args, **kwargs):
        k, ii, full, save, kind, for_dir, props = restful_params(
            *args, **kwargs)
        if rtp == 'core':
            return self.test(k=k)
        elif rtp == 'lvar':
            if not ii and kind == 'groups':
                return self.groups(k=k, p=rtp)
            else:
                if kind == 'props':
                    return self.list_props(k=k, i=ii)
                elif kind == 'history':
                    return self.state_history(
                        k=k,
                        a=props.get('a'),
                        i=ii,
                        p=rtp,
                        s=props.get('s'),
                        e=props.get('e'),
                        l=props.get('l'),
                        x=props.get('x'),
                        t=props.get('t'),
                        w=props.get('w'),
                        g=props.get('g'))
                else:
                    if for_dir:
                        return self.state(k=k, full=full, g=ii, p=rtp)
                    else:
                        return self.state(k=k, full=full, i=ii, p=rtp)
        elif rtp == 'action':
            return self.result(
                k=k, i=props.get('i'), u=ii, g=props.get('g'), s=props.get('s'))
        elif rtp == 'controller':
            if kind == 'items':
                return self.list_remote(
                    k=k, i=ii, g=props.get('g'), p=props.get('p'))
            elif kind == 'props' and ii and ii.find('/') != -1:
                return self.list_controller_props(k=k, i=ii)
            else:
                if ii and ii.find('/') != -1:
                    return self.get_controller(k=k, i=ii)
                else:
                    return self.list_controllers(k=k)
        elif rtp == 'dmatrix_rule':
            if ii:
                if kind == 'props':
                    return self.list_rule_props(k=k, i=ii)
                else:
                    return self.get_rule(k=k, i=ii)
            else:
                return self.list_rules(k=k)
        elif rtp == 'lcycle':
            if not ii and kind == 'groups':
                return self.groups_cycle(k=k)
            elif ii:
                if kind == 'props':
                    return self.list_cycle_props(k=k, i=ii)
                else:
                    return self.get_cycle(k=k, i=ii)
            else:
                return self.list_cycles(k=k)
        elif rtp == 'lmacro':
            if not ii and kind == 'groups':
                return self.groups_macro(k=k)
            if ii:
                return self.list_macro_props(k=k, i=ii)
            else:
                return self.list_macros(k=k)
        elif rtp == 'ext':
            if ii:
                return self.get_ext(k=k, i=ii)
            else:
                return self.list_ext(k=k)
        elif rtp == 'ext-module':
            if ii:
                if 'help' in props:
                    return self.modhelp_ext(k=k, m=ii, c=props['help'])
                else:
                    return self.modinfo_ext(k=k, m=ii)
            else:
                return self.list_ext_mods(k=k)
        raise cp_api_404()


def start():
    http_api = LM_HTTP_API()
    cherrypy.tree.mount(http_api, http_api.api_uri)
    cherrypy.tree.mount(jrpc, jrpc.api_uri)
    cherrypy.tree.mount(
        LM_REST_API(),
        LM_REST_API.api_uri,
        config={
            '/': {
                'request.dispatch': cherrypy.dispatch.MethodDispatcher()
            }
        })
    eva.api.jrpc = jrpc
    eva.ei.start()


api = LM_API()
jrpc = LM_JSONRPC_API()
