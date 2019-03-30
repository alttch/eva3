__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.0"

import cherrypy
import os
import glob
import logging
import jinja2
import requests

from io import BytesIO

from cherrypy.lib.static import serve_file
from eva.tools import format_json
from eva.tools import dict_merge

from eva.tools import is_oid
from eva.tools import parse_oid
from eva.tools import oid_to_id
from eva.tools import dict_from_str
from eva.tools import tiny_httpe

import eva.core
import eva.notify
import eva.api

from eva.api import GenericHTTP_API
from eva.api import JSON_RPC_API_abstract
from eva.api import GenericAPI
from eva.api import GenericCloudAPI
from eva.api import parse_api_params
from eva.api import api_need_master

from eva.api import api_result_accepted

from eva.api import cp_forbidden_key
from eva.api import cp_api_error
from eva.api import cp_api_404

from eva.api import api_need_master
from eva.api import restful_api_method
from eva.api import http_real_ip
from eva.api import cp_client_key
from eva.api import set_restful_response_location
from eva.api import generic_web_api_method
from eva.api import MethodNotFound

from eva.api import log_d
from eva.api import log_i
from eva.api import log_w

from eva.exceptions import FunctionFailed
from eva.exceptions import ResourceNotFound
from eva.exceptions import ResourceBusy
from eva.exceptions import AccessDenied
from eva.exceptions import InvalidParameter

from eva.exceptions import ecall

from eva.tools import parse_function_params
from eva.tools import val_to_boolean

from eva import apikey

import eva.sfa.controller
import eva.sfa.cloudmanager
import eva.sysapi

from PIL import Image

api = None


class SFA_API(GenericAPI, GenericCloudAPI):

    def __init__(self):
        self.controller = eva.sfa.controller
        super().__init__()

    @log_i
    @api_need_master
    def management_api_call(self, **kwargs):
        if not eva.sfa.controller.cloud_manager:
            raise MethodNotFound
        i, f, p = parse_api_params(kwargs, 'ifp', 'SS.')
        if not eva.sfa.controller.cloud_manager:
            raise AccessDenied
        controller = eva.sfa.controller.get_controller(i)
        if not controller: raise ResourceNotFound('controller')
        if isinstance(p, dict):
            params = p
        elif isinstance(p, str):
            params = dict_from_str(p)
        else:
            params = None
        return controller.management_api_call(f, params)

    @log_d
    def test(self, **kwargs):
        """
        test API/key and get system info

        Test can be executed with any valid API key of the controller the
        function is called to.

        Args:
            k: any valid API key

        Returns:
            JSON dict with system info and current API key permissions (for
            masterkey only { "master": true } is returned)
        """
        k, icvars = parse_function_params(kwargs, ['k', 'icvars'], '.b')
        result = super().test(k=k)[1]
        result['cloud_manager'] = eva.sfa.controller.cloud_manager
        if (icvars):
            result['cvars'] = eva.core.get_cvar()
        return True, result

    @log_d
    def state(self, **kwargs):
        """
        get item state

        State of the item or all items of the specified type can be obtained
        using state command.

        Args:
            k:
            .p: item type (unit [U], sensor [S] or lvar [LV])

        Optional:
            .i: item id
            .g: item group
            .full: return full state
        """
        k, i, group, tp, full = parse_function_params(kwargs, 'kigpY', '.sssb')
        if is_oid(i):
            _tp, _i = parse_oid(i)
        else:
            _tp = tp
            _i = i
        if not _tp: raise ResourceNotFound
        if _tp == 'U' or _tp == 'unit':
            gi = eva.sfa.controller.uc_pool.units
        elif _tp == 'S' or _tp == 'sensor':
            gi = eva.sfa.controller.uc_pool.sensors
        elif _tp == 'LV' or _tp == 'lvar':
            gi = eva.sfa.controller.lm_pool.lvars
        else:
            return []
        if _i:
            if _i in gi and apikey.check(k, gi[_i]):
                return gi[_i].serialize(full=full)
            else:
                raise ResourceNotFound
        result = []
        if isinstance(group, list): _group = group
        else: _group = str(group).split(',')
        for i, v in gi.copy().items():
            if apikey.check(k, v) and \
                    (not group or \
                        eva.item.item_match(v, [], _group)):
                r = v.serialize(full=full)
                result.append(r)
        return sorted(result, key=lambda k: k['oid'])

    @log_d
    def groups(self, **kwargs):
        """
        get item group list

        Get the list of item groups. Useful e.g. for custom interfaces.

        Args:
            k:
            .p: item type (unit [U], sensor [S] or lvar [LV])
        """
        k, tp, group = parse_api_params(kwargs, 'kpg', '.Ss')
        if not tp: return []
        if tp == 'U' or tp == 'unit':
            gi = eva.sfa.controller.uc_pool.units
        elif tp == 'S' or tp == 'sensor':
            gi = eva.sfa.controller.uc_pool.sensors
        elif tp == 'LV' or tp == 'lvar':
            gi = eva.sfa.controller.lm_pool.lvars
        else:
            return None
        result = []
        for i, v in gi.copy().items():
            if apikey.check(k, v) and (not group or \
                        eva.item.item_match(v, [], [group])) and \
                        v.group not in result:
                result.append(v.group)
        return sorted(result)

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
        unit = eva.sfa.controller.uc_pool.get_unit(oid_to_id(i, 'unit'))
        if not unit or not apikey.check(k, unit): raise ResourceNotFound
        return ecall(
            eva.sfa.controller.uc_pool.action(
                unit_id=oid_to_id(i, 'unit'),
                status=s,
                value=v,
                wait=w,
                uuid=u,
                priority=p,
                q=q))

    @log_i
    def action_toggle(self, **kwargs):
        """
        toggle unit status

        Create unit control action to toggle its status (1->0, 0->1)

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
        unit = eva.sfa.controller.uc_pool.get_unit(oid_to_id(i, 'unit'))
        if not unit or not apikey.check(k, unit): raise ResourceNotFound
        return ecall(
            eva.sfa.controller.uc_pool.action_toggle(
                unit_id=oid_to_id(i, 'unit'), wait=w, uuid=u, priority=p, q=q))

    @log_i
    def result(self, **kwargs):
        """
        get action status or macro run result

        Checks the result of the action by its UUID or returns the actions for
        the specified unit or execution result of the specified macro.

        Args:
            k:

        Optional:
            .u: action uuid or
            .i: unit/macro oid (either uuid or oid must be specified)
            g: filter by unit group
            s: filter by action status: Q for queued, R for running, F for
               finished

        Returns:
            list or single serialized action object
        """
        k, u, i, g, s = parse_function_params(kwargs, 'kuigs', '.ssss')
        item = None
        if u:
            a = eva.sfa.controller.uc_pool.action_history_get(u)
            if a:
                item = eva.sfa.controller.uc_pool.get_unit(a['i'])
            else:
                a = eva.sfa.controller.lm_pool.action_history_get(u)
                if not a: raise ResourceNotFound
                item = eva.sfa.controller.lm_pool.get_macro(a['i'])
        elif i:
            if is_oid(i):
                t, _i = parse_oid(i)
                if t == 'unit':
                    item = eva.sfa.controller.uc_pool.get_unit(_i)
                elif t == 'lmacro':
                    item = eva.sfa.controller.lm_pool.get_macro(_i)
            else:
                item = eva.sfa.controller.uc_pool.get_unit(i)
        if not item or not apikey.check(k, item): raise ResourceNotFound
        if item.item_type == 'unit':
            return ecall(
                eva.sfa.controller.uc_pool.result(
                    unit_id=oid_to_id(i, 'unit'), uuid=u, group=g, status=s))
        elif item.item_type == 'lmacro':
            return ecall(
                eva.sfa.controller.lm_pool.result(
                    macro_id=oid_to_id(i, 'lmacro'), uuid=u, group=g, status=s))
        else:
            raise ResourceNotFound

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
        unit = eva.sfa.controller.uc_pool.get_unit(oid_to_id(i, 'unit'))
        if not unit or not apikey.check(k, unit): raise ResourceNotFound
        return ecall(
            eva.sfa.controller.uc_pool.disable_actions(
                unit_id=oid_to_id(i, 'unit')))

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
        unit = eva.sfa.controller.uc_pool.get_unit(oid_to_id(i, 'unit'))
        if not unit or not apikey.check(k, unit): raise ResourceNotFound
        return ecall(
            eva.sfa.controller.uc_pool.enable_actions(
                unit_id=oid_to_id(i, 'unit')))

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
        if i:
            unit = eva.sfa.controller.uc_pool.get_unit(oid_to_id(i, 'unit'))
        elif u:
            a = eva.sfa.controller.uc_pool.action_history_get(u)
            if not a:
                raise ResourceNotFound
            unit = eva.sfa.controller.uc_pool.get_unit(a['i'])
        else:
            raise ResourceNotFound
        if not unit or not apikey.check(k, unit): raise ResourceNotFound
        result = ecall(
            eva.sfa.controller.uc_pool.terminate(
                unit_id=oid_to_id(i, 'unit'), uuid=u))
        if result is True and i:
            return True, api_result_accepted
        else:
            return result

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
        unit = eva.sfa.controller.uc_pool.get_unit(oid_to_id(i, 'unit'))
        if not unit or not apikey.check(k, unit): raise ResourceNotFound
        result = ecall(
            eva.sfa.controller.uc_pool.kill(unit_id=oid_to_id(i, 'unit')))
        if result is True:
            return result, api_result_accepted
        if 'ok' in result:
            del result['ok']
        return True, result

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
        unit = eva.sfa.controller.uc_pool.get_unit(oid_to_id(i, 'unit'))
        if not unit or not apikey.check(k, unit): raise ResourceNotFound
        return ecall(
            eva.sfa.controller.uc_pool.q_clean(unit_id=oid_to_id(i, 'unit')))

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
        lvar = eva.sfa.controller.lm_pool.get_lvar(oid_to_id(i, 'lvar'))
        if not lvar or not apikey.check(k, lvar): raise ResourceNotFound
        return ecall(
            eva.sfa.controller.lm_pool.set(
                lvar_id=oid_to_id(i, 'lvar'), status=s, value=v))

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
        lvar = eva.sfa.controller.lm_pool.get_lvar(oid_to_id(i, 'lvar'))
        if not lvar or not apikey.check(k, lvar): raise ResourceNotFound
        return ecall(
            eva.sfa.controller.lm_pool.reset(lvar_id=oid_to_id(i, 'lvar')))

    @log_i
    def toggle(self, **kwargs):
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
        lvar = eva.sfa.controller.lm_pool.get_lvar(oid_to_id(i, 'lvar'))
        if not lvar or not apikey.check(k, lvar): raise ResourceNotFound
        return ecall(
            eva.sfa.controller.lm_pool.toggle(lvar_id=oid_to_id(i, 'lvar')))

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
        lvar = eva.sfa.controller.lm_pool.get_lvar(oid_to_id(i, 'lvar'))
        if not lvar or not apikey.check(k, lvar): raise ResourceNotFound
        return ecall(
            eva.sfa.controller.lm_pool.clear(lvar_id=oid_to_id(i, 'lvar')))

    @log_d
    def list_macros(self, **kwargs):
        """
        get macro list

        Get the list of all available :doc:`macros</lm/macros>`.

        Args:
            k:

        Optional:
            .g: filter by group
            i: filter by controller
        """
        k, controller_id, group = parse_function_params(kwargs, 'kig', '.ss')
        result = []
        if not controller_id:
            for c, d in \
                eva.sfa.controller.lm_pool.macros_by_controller.copy().items():
                for a, v in d.copy().items():
                    if apikey.check(k, v) and \
                        (not group or \
                            eva.item.item_match(v, [], [ group ])):
                        result.append(v.serialize(info=True))
        else:
            if controller_id.find('/') != -1:
                c = controller_id.split('/')
                if len(c) > 2 or c[0] != 'lm':
                    raise InvalidParameter('controller must be LM PLC')
                c_id = c[1]
            else:
                c_id = controller_id
            if c_id not in eva.sfa.controller.lm_pool.macros_by_controller:
                raise ResourceNotFound('controller not found')
            for a, v in \
                eva.sfa.controller.lm_pool.macros_by_controller[\
                                                        c_id].copy().items():
                if apikey.check(k, v) and (not group or \
                        eva.item.item_match(v, [], [ group ])):
                    result.append(v.serialize(info=True))
        return sorted(result, key=lambda k: k['id'])

    @log_d
    def groups_macro(self, **kwargs):
        """
        get macro groups list


        Get the list of macros. Useful e.g. for custom interfaces.

        Args:
            k:
        """
        k = parse_function_params(kwargs, 'k', '.')
        result = []
        for a, v in eva.sfa.controller.lm_pool.macros.copy().items():
            if apikey.check(k, v) and not v.group in result:
                result.append(v.group)
        return sorted(result)

    @log_i
    def run(self, **kwargs):
        """
        execute macro

        Execute a :doc:`macro</lm/macros>` with the specified arguments.

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
        macro = eva.sfa.controller.lm_pool.get_macro(oid_to_id(i, 'lmacro'))
        if not macro or not apikey.check(k, macro): raise ResourceNotFound
        return ecall(
            eva.sfa.controller.lm_pool.run(
                macro=oid_to_id(i, 'lmacro'),
                args=a,
                kwargs=kw,
                priority=p,
                q_timeout=q,
                wait=w,
                uuid=u))

    @log_d
    def list_cycles(self, **kwargs):
        """
        get cycle list

        Get the list of all available :doc:`cycles</lm/cycles>`.

        Args:
            k:

        Optional:
            .g: filter by group
            i: filter by controller
        """
        k, controller_id, group = parse_function_params(kwargs, 'kig', '.ss')
        result = []
        if isinstance(group, list): _group = group
        else: _group = str(group).split(',')
        if not controller_id:
            for c, d in \
                eva.sfa.controller.lm_pool.cycles_by_controller.copy().items():
                for a, v in d.copy().items():
                    if apikey.check(k, v) and \
                        (not group or \
                            eva.item.item_match(v, [], _group)):
                        result.append(v.serialize(full=True))
        else:
            if controller_id.find('/') != -1:
                c = controller_id.split('/')
                if len(c) > 2 or c[0] != 'lm': return None
                c_id = c[1]
            else:
                c_id = controller_id
            if c_id not in eva.sfa.controller.lm_pool.cycles_by_controller:
                return None
            for a, v in \
                eva.sfa.controller.lm_pool.cycles_by_controller[\
                                                        c_id].copy().items():
                if apikey.check(k, v) and (not group or \
                        eva.item.item_match(v, [], _group)):
                    result.append(v.serialize(info=True))
        return sorted(result, key=lambda k: k['id'])

    @log_d
    def get_cycle(self, **kwargs):
        """
        get cycle information

        Args:
            k:
            .i: cycle id

        Returns:
            field "value" contains real average cycle interval
        """
        k, i = parse_function_params(kwargs, 'ki', '.S')
        item = eva.sfa.controller.lm_pool.cycles.get(
            oid_to_id(i, required='lcycle'))
        if not item or not apikey.check(k, item): raise ResourceNotFound
        return item.serialize(full=True)

    @log_d
    def groups_cycle(self, **kwargs):
        """
        get cycle groups list


        Get the list of cycles. Useful e.g. for custom interfaces.

        Args:
            k:
        """
        k = parse_function_params(kwargs, 'k', '.')
        result = []
        for a, v in eva.sfa.controller.lm_pool.cycles.copy().items():
            if apikey.check(k, v) and not v.group in result:
                result.append(v.group)
        return sorted(result)

    @log_i
    @api_need_master
    def list_controllers(self, **kwargs):
        """
        get controllers list

        Get the list of all connected :ref:`controllers<sfa_remote_c>`.

        Args:
            k: .master
            .g: filter by group ("uc" or "lm")
        """
        g = parse_api_params(kwargs, 'g', 's')
        if g is not None and g not in ['uc', 'lm']:
            raise InvalidParameter('group should be "uc" or "lm"')
        result = []
        if g is None or g == 'uc':
            for i, v in eva.sfa.controller.remote_ucs.copy().items():
                result.append(v.serialize(info=True))
        if g is None or g == 'lm':
            for i, v in eva.sfa.controller.remote_lms.copy().items():
                result.append(v.serialize(info=True))
        return sorted(result, key=lambda k: k['full_id'])

    @log_i
    @api_need_master
    def append_controller(self, **kwargs):
        """
        connect remote controller via HTTP

        Connects remote :ref:`controller<sfa_remote_c>` to the local.

        Args:
            k: .master
            u: Controller API uri (*proto://host:port*, port not required
                if default)
            a: remote controller API key (\$key to use local key)

        Optional:
            m: ref:`MQTT notifier<mqtt_>` to exchange item states in real time
                (default: *eva_1*)
            s: verify remote SSL certificate or pass invalid
            t: timeout (seconds) for the remote controller API calls
            g: controller type ("uc" or "lm"), autodetected if none
            save: save connected controller configuration on the disk
                immediately after creation
        """
        uri, group, key, makey, mqtt_update, ssl_verify, timeout, \
                save = parse_api_params(kwargs, 'ugaxmstS', 'Sssssbnb')
        if group == 'uc' or group is None:
            c = eva.sfa.controller.append_uc(
                uri=uri,
                key=key,
                makey=makey,
                mqtt_update=mqtt_update,
                ssl_verify=ssl_verify,
                timeout=timeout,
                save=save)
            if c: return c.serialize(info=True)
        if group == 'lm' or group is None:
            c = eva.sfa.controller.append_lm(
                uri=uri,
                key=key,
                makey=makey,
                mqtt_update=mqtt_update,
                ssl_verify=ssl_verify,
                timeout=timeout,
                save=save)
            if c: return c.serialize(info=True)
        raise FunctionFailed

    @log_i
    @api_need_master
    def matest_controller(self, **kwargs):
        """
        test management API connection to remote controller

        Args:
            k: .master
            .i: controller id
        """
        i = parse_api_params(kwargs, 'i', 'S')
        item = eva.sfa.controller.get_controller(i)
        if item is None: return None
        return True if item.matest() else False

    @log_i
    @api_need_master
    def reload_controller(self, **kwargs):
        """
        reload controller

        Reloads items from connected controller. If controller ID "ALL" is
        specified, all connected controllers are reloaded.

        Args:
            k: .master
            .i: controller id
        """
        i = parse_api_params(kwargs, 'i', 'S')
        if i != 'ALL':
            if not i or i.find('/') == -1:
                raise InvalidParameter('controller type not specified')
            try:
                ct, ci = i.split('/')
            except:
                raise InvalidParameter('controller type not specified')
            if ct == 'uc':
                return eva.sfa.controller.uc_pool.reload_controller(ci)
            elif ct == 'lm':
                return eva.sfa.controller.lm_pool.reload_controller(ci)
            raise InvalidParameter('controller type unknown')
        else:
            success = True
            if not eva.sfa.controller.uc_pool.reload_controller('ALL'):
                success = False
            if not eva.sfa.controller.lm_pool.reload_controller('ALL'):
                success = False
            if not success:
                raise FunctionFailed
            return True

    @log_i
    @api_need_master
    def list_remote(self, **kwargs):
        """
        get a list of items from connected controllers

        Get a list of the items loaded from the connected controllers. Useful
        to debug the controller connections.

        Args:
            k: .master

        Optional:
            .i: controller id
            g: filter by item group
            p: filter by item type
        """
        i, group, tp = parse_api_params(kwargs, 'igp', 'sss')
        result = []
        items_uc = []
        items_lm = []
        if i:
            controller = eva.sfa.controller.get_controller(i)
            if not controller: return None
            c_id = controller.item_id
            c_fid = controller.full_id
            c_t = controller.group
        if tp is None or tp in ['U', 'unit', '#']:
            if i:
                if c_t == 'uc':
                    if not c_id in \
                            eva.sfa.controller.uc_pool.units_by_controller:
                        return None
                    items_uc.append(
                        eva.sfa.controller.uc_pool.units_by_controller[c_id])
            else:
                items_uc.append(eva.sfa.controller.uc_pool.units_by_controller)
        if tp is None or tp in ['S', 'sensor', '#']:
            if i:
                if c_t == 'uc':
                    if not c_id in \
                            eva.sfa.controller.uc_pool.sensors_by_controller:
                        return None
                    items_uc.append(
                        eva.sfa.controller.uc_pool.sensors_by_controller[c_id])
            else:
                items_uc.append(
                    eva.sfa.controller.uc_pool.sensors_by_controller)
        if tp is None or tp in ['LV', 'lvar', '#']:
            if i:
                if c_t == 'lm':
                    if not c_id in \
                        eva.sfa.controller.lm_pool.lvars_by_controller:
                        return None
                    items_lm.append(
                        eva.sfa.controller.lm_pool.lvars_by_controller[c_id])
            else:
                items_lm.append(eva.sfa.controller.lm_pool.lvars_by_controller)
        if not items_uc and not items_lm:
            return None
        if i:
            if items_uc:
                for x in items_uc:
                    for a, v in x.copy().items():
                        if not group or eva.item.item_match(v, [], [group]):
                            result.append(v.serialize(full=True))
            if items_lm:
                for x in items_lm:
                    for a, v in x.copy().items():
                        if not group or eva.item.item_match(v, [], [group]):
                            result.append(v.serialize(full=True))
        else:
            for x in items_uc:
                for c, d in x.copy().items():
                    for a, v in d.copy().items():
                        if not group or eva.item.item_match(v, [], [group]):
                            result.append(v.serialize(full=True))
            for x in items_lm:
                for c, d in x.copy().items():
                    for a, v in d.copy().items():
                        if not group or eva.item.item_match(v, [], [group]):
                            result.append(v.serialize(full=True))
        return sorted(
            sorted(result, key=lambda k: k['oid']),
            key=lambda k: ['controller_id'])

    @api_need_master
    def reload_clients(self, **kwargs):
        """
        ask connected clients to reload

        Sends **reload** event to all connected clients asking them to reload
        the interface.

        All the connected clients receive the event with *subject="reload"* and
        *data="asap"*. If the clients use :doc:`sfa_framework`, they can
        define :ref:`eva_sfa_reload_handler<sfw_reload>` function.

        Args:
            k: .master
        """
        eva.notify.reload_clients()
        return True

    @api_need_master
    def notify_restart(self, **kwargs):
        """
        notify connected clients about server restart

        Sends a **server restart** event to all connected clients asking them
        to prepare for server restart.

        All the connected clients receive the event with *subject="server"* and
        *data="restart"*. If the clients use :doc:`sfa_framework`, they can
        define :ref:`eva_sfa_server_restart_handler<sfw_server_restart>`
        function.

        Server restart notification is sent automatically to all connected
        clients when the server is restarting. This API function allows to send
        server restart notification without actual server restart, which may be
        useful e.g. for testing, handling frontend restart etc.

        Args:
            k: .master
        """
        eva.notify.notify_restart()
        return True


class SFA_HTTP_API_abstract(SFA_API, GenericHTTP_API):

    def management_api_call(self, **kwargs):
        code, data = super().management_api_call(**kwargs)
        return {'code': code, 'data': data}

    def state_all(self, **kwargs):
        k, p, g = parse_function_params(kwargs, 'kpg', '...')
        result = []
        if p is None: _p = ['U', 'S', 'LV']
        else:
            _p = p
            if not _p: return []
        for tp in _p:
            try:
                result += self.state(k=k, p=tp, g=g, full=True)
            except:
                pass
        if p is None or 'lcycle' in _p:
            try:
                result += self.list_cycles(k=k, g=g)
            except:
                pass
        return sorted(
            sorted(result, key=lambda k: k['oid']), key=lambda k: k['type'])


class SFA_HTTP_API(SFA_HTTP_API_abstract, GenericHTTP_API):

    def __init__(self):
        super().__init__()
        self.expose_api_methods('sfapi')
        self.wrap_exposed()


class SFA_JSONRPC_API(eva.sysapi.SysHTTP_API_abstract,
                      eva.api.JSON_RPC_API_abstract, SFA_HTTP_API_abstract):

    def __init__(self):
        super().__init__()
        self.expose_api_methods('sfapi', set_api_uri=False)
        self.expose_api_methods('sysapi', set_api_uri=False)


class SFA_REST_API(eva.sysapi.SysHTTP_API_abstract,
                   eva.sysapi.SysHTTP_API_REST_abstract,
                   eva.api.GenericHTTP_API_REST_abstract, SFA_HTTP_API_abstract,
                   GenericHTTP_API):

    @generic_web_api_method
    @restful_api_method
    def GET(self, rtp, k, ii, save, kind, method, for_dir, props):
        try:
            return super().GET(rtp, k, ii, save, kind, method, for_dir, props)
        except MethodNotFound:
            pass
        if rtp in ['unit', 'sensor', 'lvar']:
            if kind == 'groups':
                return self.groups(k=k, p=rtp)
            elif kind == 'history':
                return self.state_history(
                    k=k, i='{}:{}'.format(rtp, ii), **props)
            elif for_dir:
                return self.state(k=k, p=rtp, g=ii, **props)
            else:
                return self.state(k=k, p=rtp, i=ii, **props)
        elif rtp == 'action':
            return self.result(k=k, u=ii, **props)
        elif rtp == 'lmacro':
            if ii:
                if kind == 'props':
                    return self.list_macro_props(k=k, i=ii)
                else:
                    if for_dir:
                        return self.list_macros(k=k, g=ii)
                    else:
                        return self.get_macro(k=k, i=ii)
            else:
                if kind == 'groups':
                    return self.groups_macro(k=k)
                else:
                    return self.list_macros(k=k)
        elif rtp == 'lcycle':
            if ii:
                if kind == 'props':
                    return self.list_cycle_props(k=k, i=ii)
                else:
                    if for_dir:
                        return self.list_cycles(k=k, g=ii)
                    else:
                        return self.get_cycle(k=k, i=ii)
            else:
                if kind == 'groups':
                    return self.groups_cycle(k=k)
                else:
                    return self.list_cycles(k=k)
        elif rtp == 'controller':
            if kind == 'items':
                return self.list_remote(k=k, i=ii, **props)
            elif kind == 'props' and ii and ii.find('/') != -1:
                return self.list_controller_props(k=k, i=ii)
            else:
                if ii and ii.find('/') != -1:
                    return self.get_controller(k=k, i=ii)
                else:
                    return self.list_controllers(k=k, g=ii)
        raise MethodNotFound

    @generic_web_api_method
    @restful_api_method
    def POST(self, rtp, k, ii, save, kind, method, for_dir, props):
        try:
            return super().POST(rtp, k, ii, save, kind, method, for_dir, props)
        except MethodNotFound:
            pass
        if rtp == 'action':
            if not ii:
                a = self.action(k=k, **props)
                set_restful_response_location(a['uuid'], rtp)
                return a
            else:
                if method == 'terminate':
                    return self.terminate(k=k, u=ii)
        elif rtp == 'unit':
            if ii:
                if method == 'kill':
                    return self.kill(k=k, i=ii)
                elif method == 'q_clean':
                    return self.q_clean(k=k, i=ii)
                elif method == 'terminate':
                    return self.terminate(k=k, i=ii)
        elif rtp == 'lmacro':
            if method == "run":
                a = self.run(k=k, i=ii, **props)
                if not a: raise FunctionFailed
                set_restful_response_location(a['uuid'], 'action')
                return a
        elif rtp == 'lvar':
            if ii:
                s = props.get('s')
                if s == 'reset':
                    return self.reset(k=k, i=ii)
                elif s == 'clear':
                    return self.clear(k=k, i=ii)
                elif s == 'toggle':
                    return self.toggle(k=k, i=ii)
                else:
                    return self.set(k=k, i=ii, **props)
        elif rtp == 'controller':
            if (not ii or for_dir or ii.find('/') == -1) and not method:
                result = self.append_controller(k=k, save=save, g=ii, **props)
                if 'full_id' in result:
                    set_restful_response_location(result['full_id'], rtp)
                return result
            elif method == 'test':
                return self.test_controller(k=k, i=ii)
            elif method == 'matest':
                return self.matest_controller(k=k, i=ii)
            elif method == 'reload':
                return self.reload_controller(k=k, i=ii)
        elif rtp == 'core':
            if method == 'reload_clients':
                return self.reload_clients(k=k)
            elif method == 'notify_restart':
                return self.notify_restart(k=k)
        raise MethodNotFound

    @generic_web_api_method
    @restful_api_method
    def PUT(self, rtp, k, ii, save, kind, method, for_dir, props):
        try:
            return super().PUT(rtp, k, ii, save, kind, method, for_dir, props)
        except MethodNotFound:
            pass
        if rtp == 'action':
            if ii:
                return self.action(k=k, u=ii, **props)
        raise MethodNotFound

    @generic_web_api_method
    @restful_api_method
    def PATCH(self, rtp, k, ii, save, kind, method, for_dir, props):
        try:
            return super().PATCH(rtp, k, ii, save, kind, method, for_dir, props)
        except MethodNotFound:
            pass
        if rtp == 'unit':
            if ii:
                if 'action_enabled' in props:
                    v = val_to_boolean(props['action_enabled'])
                    if v is True:
                        return self.enable_actions(k=k, i=ii)
                    elif v is False:
                        return self.disable_actions(k=k, i=ii)
                    else:
                        raise InvalidParameter(
                            '"action_enabled" has invalid value')
        elif rtp == 'controller':
            if ii:
                if props:
                    return super().set_controller_prop(
                        k=k, i=ii, save=save, v=props)
                else:
                    return True
        raise MethodNotFound

    @generic_web_api_method
    @restful_api_method
    def DELETE(self, rtp, k, ii, save, kind, method, for_dir, props):
        try:
            return super().DELETE(rtp, k, ii, save, kind, method, for_dir,
                                  props)
        except MethodNotFound:
            pass
        if rtp == 'controller':
            if ii:
                return self.remove_controller(k=k, i=ii)
        raise MethodNotFound


# j2 template engine functions


def j2_state(i=None, g=None, p=None, k=None):
    if k:
        _k = apikey.key_by_id(k)
    else:
        _k = cp_client_key(from_cookie=True)
    try:
        return api.state(k=_k, i=i, g=g, p=p)
    except:
        eva.core.log_traceback()
        return None


def j2_groups(g=None, p=None, k=None):
    if k:
        _k = apikey.key_by_id(k)
    else:
        _k = cp_client_key(from_cookie=True)
    try:
        return api.groups(k=_k, g=g, p=p)
    except:
        eva.core.log_traceback()
        return None


def j2_api_call(method, params={}, k=None):
    if k:
        _k = apikey.key_by_id(k)
    else:
        _k = cp_client_key(from_cookie=True)
    f = getattr(api, method)
    try:
        result = f(k=_k, **params)
        if isinstance(result, tuple):
            result, data = result
        else:
            data = None
        if result is True:
            if data == api_result_accepted:
                return None
            else:
                return data
        else:
            return result
    except:
        eva.core.log_traceback()
        return None


def serve_j2(tpl_file, tpl_dir=eva.core.dir_ui):
    j2_loader = jinja2.FileSystemLoader(searchpath=tpl_dir)
    j2 = jinja2.Environment(loader=j2_loader)
    try:
        template = j2.get_template(tpl_file)
    except:
        raise cp_api_404()
    env = {}
    env['request'] = cherrypy.serving.request
    k = cp_client_key(from_cookie=True)
    if k:
        server_info = api.test(k=k)[1]
    else:
        server_info = {}
    server_info['remote_ip'] = http_real_ip()
    env['server'] = server_info
    env.update(eva.core.cvars)
    template.globals['state'] = j2_state
    template.globals['groups'] = j2_groups
    template.globals['api_call'] = j2_api_call
    try:
        return template.render(env).encode()
    except:
        eva.core.log_traceback()
        return 'Server error'


def j2_handler(*args, **kwargs):
    try:
        del cherrypy.serving.response.headers['Content-Length']
    except:
        pass
    return serve_j2(cherrypy.serving.request.path_info.replace('..', ''))


def j2_hook(*args, **kwargs):
    if cherrypy.serving.request.path_info[-3:] == '.j2':
        cherrypy.serving.request.handler = j2_handler


# ui and pvt


class UI_ROOT():

    _cp_config = {'tools.j2.on': True}

    def __init__(self):
        cherrypy.tools.j2 = cherrypy.Tool(
            'before_handler', j2_hook, priority=100)

    @cherrypy.expose
    def index(self, **kwargs):
        if os.path.isfile(eva.core.dir_eva + '/ui/index.j2'):
            return serve_j2('/index.j2')
        if os.path.isfile(eva.core.dir_eva + '/ui/index.html'):
            return serve_file(eva.core.dir_eva + '/ui/index.html')
        raise cp_api_404()


class SFA_HTTP_Root:

    @cherrypy.expose
    def index(self, **kwargs):
        q = cherrypy.request.query_string
        if q: q = '?' + q
        raise cherrypy.HTTPRedirect('/ui/' + q)

    def _no_cache(self):
        cherrypy.serving.response.headers['Expires'] = \
                'Sun, 19 Nov 1978 05:00:00 GMT'
        cherrypy.serving.response.headers['Cache-Control'] = \
            'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
        cherrypy.serving.response.headers['Pragma'] = 'no-cache'

    @cherrypy.expose
    def rpvt(self, k=None, f=None, nocache=None):
        _k = cp_client_key(k, from_cookie=True)
        _r = '%s@%s' % (apikey.key_id(_k), http_real_ip())
        if f is None: raise cp_bad_request('uri not provided')
        if not apikey.check(_k, rpvt_uri=f, ip=http_real_ip()):
            logging.warning('rpvt %s uri %s access forbidden' % (_r, f))
            raise cp_forbidden_key()
        try:
            if f.find('//') == -1: _f = 'http://' + f
            else: _f = f
            r = requests.get(_f, timeout=eva.core.timeout)
        except:
            raise cp_api_error()
        if r.status_code != 200:
            raise cp_api_error('remote response %s' % r.status_code)
        ctype = r.headers.get('Content-Type')
        if ctype:
            cherrypy.serving.response.headers['Content-Type'] = ctype
        if nocache: self._no_cache()
        return BytesIO(r.content)

    @cherrypy.expose
    def pvt(self, k=None, f=None, c=None, ic=None, nocache=None):
        _k = cp_client_key(k, from_cookie=True)
        _r = '%s@%s' % (apikey.key_id(_k), http_real_ip())
        if f is None or f == '' or f.find('..') != -1 or f[0] == '/':
            raise cp_api_404()
        if not apikey.check(_k, pvt_file=f, ip=http_real_ip()):
            logging.warning('pvt %s file %s access forbidden' % (_r, f))
            raise cp_forbidden_key()
        if f[-3:] == '.j2':
            return serve_j2('/' + f, tpl_dir=eva.core.dir_pvt)
        _f = eva.core.dir_pvt + '/' + f
        _f_alt = None
        if c:
            fls = [x for x in glob.glob(_f) if os.path.isfile(x)]
            if not fls: raise cp_api_404()
            if c == 'newest':
                _f = max(fls, key=os.path.getmtime)
                fls.remove(_f)
                if fls: _f_alt = max(fls, key=os.path.getmtime)
            elif c == 'oldest':
                _f = min(fls, key=os.path.getmtime)
            elif c == 'list':
                l = []
                for x in fls:
                    l.append({
                        'name': os.path.basename(x),
                        'size': os.path.getsize(x),
                        'time': {
                            'c': os.path.getctime(x),
                            'm': os.path.getmtime(x)
                        }
                    })
                cherrypy.response.headers['Content-Type'] = 'application/json'
                if nocache: self._no_cache()
                logging.info('pvt %s file list %s' % (_r, f))
                return format_json(sorted(l, key=lambda k: k['name'])).encode()
            else:
                raise cp_api_error()
        if ic:
            try:
                icmd, args, fmt = ic.split(':')
                if icmd == 'resize':
                    x, y, q = args.split('x')
                    x = int(x)
                    y = int(y)
                    q = int(q)
                    if os.path.getsize(_f) > 10000000: raise
                    try:
                        image = Image.open(_f)
                        image.thumbnail((x, y))
                        result = image.tobytes(fmt, 'RGB', q)
                    except:
                        if not _f_alt or os.path.getsize(_f_alt) > 10000000:
                            raise
                        image = Image.open(_f_alt)
                        image.thumbnail((x, y))
                        result = image.tobytes(fmt, 'RGB', q)
                    cherrypy.response.headers['Content-Type'] = 'image/' + fmt
                    if nocache: self._no_cache()
                    logging.info('pvt %s file access %s' % (_r, f))
                    return result
                else:
                    logging.error('pvt %s file %s resize error' % (_r, f))
                    raise
            except:
                raise cp_api_error()
        if nocache: self._no_cache()
        logging.info('pvt %s file access %s' % (_r, f))
        return serve_file(_f)


def start():
    http_api = SFA_HTTP_API()
    cherrypy.tree.mount(http_api, http_api.api_uri)
    cherrypy.tree.mount(jrpc, jrpc.api_uri)
    cherrypy.tree.mount(
        SFA_REST_API(),
        SFA_REST_API.api_uri,
        config={
            '/': {
                'request.dispatch': cherrypy.dispatch.MethodDispatcher()
            }
        })
    cherrypy.tree.mount(
        SFA_HTTP_Root(),
        '/',
        config={
            '/':
            dict_merge({
                'tools.sessions.on': False,
            }, tiny_httpe),
            '/.evahi': {
                'tools.sessions.on': False,
                'tools.staticdir.dir': eva.core.dir_eva + '/ui/.evahi',
                'tools.staticdir.on': True
            },
            '/favicon.ico': {
                'tools.staticfile.on':
                True,
                'tools.staticfile.filename':
                eva.core.dir_eva + '/lib/eva/i/favicon.ico'
            }
        })

    cherrypy.tree.mount(
        UI_ROOT(),
        '/ui',
        config={
            '/':
            dict_merge(
                {
                    'tools.sessions.on': False,
                    'tools.staticdir.dir': eva.core.dir_eva + '/ui',
                    'tools.staticdir.on': True
                }, tiny_httpe)
        })
    eva.sfa.cloudmanager.start()


api = SFA_API()
jrpc = SFA_JSONRPC_API()
