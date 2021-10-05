__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.2"

import cherrypy
import os
import glob
import logging
import threading
import importlib
import requests
import yaml
import base64
import eva.lang

try:
    yaml.warnings({'YAMLLoadWarning': False})
except:
    pass

from io import BytesIO
from functools import wraps

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
from eva.api import cp_bad_request
from eva.api import cp_api_404

from eva.api import api_need_master
from eva.api import restful_api_method
from eva.api import http_real_ip
from eva.api import cp_client_key
from eva.api import set_restful_response_location
from eva.api import generic_web_api_method
from eva.api import MethodNotFound

from eva.api import HTTP_API_Logger

from eva.api import log_d
from eva.api import log_i
from eva.api import log_w
from eva.api import notify_plugins

from eva.api import key_check
from eva.api import key_check_master

from eva.api import cp_nocache

from eva.api import get_aci

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

import eva.registry

from eva.sfa.sfatpl import j2_handler, serve_j2

api = None
"""
supervisor lock

can be either None (not locked) or dict with fields

o=dict(u, utp, key) # lock owner
l=<None|'u'|'k'>
c=<None|'u'|'k'>
"""
supervisor_lock = {}

with_supervisor_lock = eva.core.RLocker('sfa/sfapi')


def api_need_supervisor(f):

    @wraps(f)
    def do(*args, **kwargs):
        if not key_check(kwargs.get('k'), allow=['supervisor']):
            raise AccessDenied
        return f(*args, **kwargs)

    return do


def api_need_supervisor_pass(f):

    @wraps(f)
    def do(*args, **kwargs):
        if not can_pass_supervisor_lock(kwargs.get('k')):
            raise AccessDenied('server is locked by supervisor')
        return f(*args, **kwargs)

    return do


@with_supervisor_lock
def can_pass_supervisor_lock(k, op='l'):
    if not supervisor_lock or key_check_master(k, ro_op=True):
        return True
    else:
        ltp = supervisor_lock[op]
        if ltp is None and key_check(k, allow=['supervisor'], ro_op=True):
            return True
        elif ltp == 'k' and apikey.key_id(k) == supervisor_lock['o']['key_id']:
            return True
        elif ltp == 'u' and get_aci('u') == \
                supervisor_lock['o'].get('u') and \
                get_aci('utp') == supervisor_lock['o'].get('utp'):
            return True
    return False


class SFA_API(GenericAPI, GenericCloudAPI):

    def __init__(self):
        self.controller = eva.sfa.controller
        super().__init__()

    @log_i
    @api_need_supervisor
    @notify_plugins
    def supervisor_message(self, **kwargs):
        """
        send broadcast message

        Args:
            k: .allow=supervisor
            m: message text
            .u: message sender user (requires master key)
            .a: message sender API key (requires master key)

        Restful:
            If master key is used, sender can be overriden with "sender"
            argument, which should be a dictionary and contain:

            * u = message sender user

            * key_id = message sender API key ID
        """
        k, m, u, a = parse_function_params(kwargs, 'kmua', '.S..')
        if (u or a) and not key_check_master(k):
            raise AccessDenied(
                'master key required to override user or API key sender info')
        if not u:
            u = get_aci('u')
        if not a:
            a = get_aci('key_id')
        eva.notify.supervisor_event(subject='message',
                                    data={
                                        'sender': {
                                            'key_id': a,
                                            'u': u
                                        },
                                        'text': m
                                    })
        return True

    @log_w
    @api_need_supervisor
    @with_supervisor_lock
    @notify_plugins
    def supervisor_lock(self, **kwargs):
        """
        set supervisor API lock

        When supervisor lock is set, SFA API functions become read-only for all
        users, except users in the lock scope.

        Args:
            k: .allow=supervisor
            .l: lock scope (null = any supervisor can pass, u = only owner can
                pass, k = all users with owner's API key can pass)
            .c: unlock/override scope (same as lock type)
            .u: lock user (requires master key)
            .p: user type (null for local, "msad" for Active Directory etc.)
            .a: lock API key ID (requires master key)

        Restful:
            supervisor_lock should be a dictionary. If the dictionary is empty,
            default lock is set.

            * attribute "l" = "<k|u>" sets lock scope (key / user)

            * attribute "c" = "<k|u>" set unlock/override scope

            attribute "o" overrides lock owner (master key is required) with
                sub-attributes:

                * "u" = user

                * "utp" = user type (null for local, "msad" for Active
                    Directory etc.)

                * "key_id" = API key ID


        """
        k, l, c, u, p, a = parse_function_params(kwargs, 'klcupa', '......')
        if not can_pass_supervisor_lock(k, op='c'):
            raise AccessDenied(
                'supervisor lock is already set, unable to override')
        if (u or a or p) and not key_check_master(k):
            raise AccessDenied(
                'master key required to set user or API key lock')
        if l not in [None, 'k', 'u']:
            raise InvalidParameter('l = <null|k|u>')
        if c not in [None, 'k', 'u']:
            raise InvalidParameter('c = <null|k|u>')
        if not u:
            u = get_aci('u')
        if not p:
            p = get_aci('utp')
        if not a:
            a = get_aci('key_id')
        if p and not u:
            raise InvalidParameter('user type is specified but no user login')
        if (l == 'u' or c == 'u') and not u:
            raise FunctionFailed(
                'lock type "user" is requested but user is not set')
        supervisor_lock.clear()
        supervisor_lock.update({
            'o': {
                'u': u,
                'utp': p,
                'key_id': a
            },
            'l': l,
            'c': c
        })
        eva.notify.supervisor_event(subject='lock', data=supervisor_lock)
        return True

    @log_w
    @api_need_supervisor
    @with_supervisor_lock
    @notify_plugins
    def supervisor_unlock(self, **kwargs):
        """
        clear supervisor API lock

        API key should have permission to clear existing supervisor lock

        Args:
            k: .allow=supervisor
        Returns:
            Successful result is returned if lock is either cleared or not set
        """
        k = parse_function_params(kwargs, 'k', '.')
        if not can_pass_supervisor_lock(k, op='c'):
            raise AccessDenied
        supervisor_lock.clear()
        eva.notify.supervisor_event(subject='unlock')
        return True

    @log_i
    @api_need_master
    @notify_plugins
    def management_api_call(self, **kwargs):
        if not eva.sfa.controller.config.cloud_manager:
            raise MethodNotFound
        i, f, p, t = parse_api_params(kwargs, 'ifpt', 'SS.n')
        controller = eva.sfa.controller.get_controller(i)
        if not controller:
            raise ResourceNotFound('controller')
        if isinstance(p, dict):
            params = p
        elif isinstance(p, str):
            params = dict_from_str(p)
        else:
            params = None
        return controller.management_api_call(f, params, timeout=t)

    @log_d
    @notify_plugins
    def test(self, **kwargs):
        """
        test API/key and get system info

        Test can be executed with any valid API key of the controller the
        function is called to.

        The result section "controllers" contains connection status of remote
        controllers. The API key must have an access either to "uc" and "lm"
        groups ("remote_uc:uc" and "remote_lm:lm") or to particular controller
        oids.

        Args:
            k: any valid API key

        Returns:
            JSON dict with system info and current API key permissions (for
            masterkey only { "master": true } is returned)
        """
        k, icvars = parse_function_params(kwargs, ['k', 'icvars'], '.b')
        result = super().test(k=k)[1]
        result['cloud_manager'] = eva.sfa.controller.config.cloud_manager
        # not need to lock object as only pointer is required
        result['supervisor_lock'] = supervisor_lock
        if not result['supervisor_lock']:
            result['supervisor_lock'] = None
        if (icvars):
            result['cvars'] = eva.core.get_cvar()
        controllers = {}
        for cc in [
                eva.sfa.controller.remote_ucs, eva.sfa.controller.remote_lms
        ]:
            for i, v in cc.copy().items():
                if key_check(k, oid=v.oid, ro_op=True):
                    controllers[v.full_id] = v.connected
        if controllers:
            result['connected'] = controllers
        return True, result

    @log_d
    @notify_plugins
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
        k, i, group, tp, full = parse_function_params(kwargs, 'kigpY', '.s.sb')
        if is_oid(i):
            _tp, _i = parse_oid(i)
        else:
            _tp = tp
            _i = i
        if not _tp:
            raise ResourceNotFound
        if _tp == 'U' or _tp == 'unit':
            gi = eva.sfa.controller.uc_pool.units
        elif _tp == 'S' or _tp == 'sensor':
            gi = eva.sfa.controller.uc_pool.sensors
        elif _tp == 'LV' or _tp == 'lvar':
            gi = eva.sfa.controller.lm_pool.lvars
        else:
            return []
        if _i:
            if _i in gi and key_check(k, gi[_i], ro_op=True):
                return gi[_i].serialize(full=full)
            else:
                raise ResourceNotFound
        result = []
        if isinstance(group, list):
            _group = group
        elif isinstance(group, str):
            _group = str(group).split(',')
        else:
            _group = None
        for i, v in gi.copy().items():
            if key_check(k, v, ro_op=True) and \
                    (not group or \
                        eva.item.item_match(v, [], _group)):
                r = v.serialize(full=full)
                result.append(r)
        return sorted(result, key=lambda k: k['oid'])

    @log_d
    @notify_plugins
    def groups(self, **kwargs):
        """
        get item group list

        Get the list of item groups. Useful e.g. for custom interfaces.

        Args:
            k:
            .p: item type (unit [U], sensor [S] or lvar [LV])
        """
        k, tp, group = parse_api_params(kwargs, 'kpg', '.Ss')
        if not tp:
            return []
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
            if key_check(k, v, ro_op=True) and (not group or \
                        eva.item.item_match(v, [], [group])) and \
                        v.group not in result:
                result.append(v.group)
        return sorted(result)

    @log_i
    @api_need_supervisor_pass
    @notify_plugins
    def action(self, **kwargs):
        """
        create unit control action
        
        The call is considered successful when action is put into the action
        queue of selected unit.

        Args:
            k:
            .i: unit id

        Optional:
            s: desired unit status
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
        if v is not None:
            v = str(v)
        unit = eva.sfa.controller.uc_pool.get_unit(oid_to_id(i, 'unit'))
        if not unit:
            raise ResourceNotFound
        elif not key_check(k, unit):
            raise AccessDenied
        return ecall(
            eva.sfa.controller.uc_pool.action(unit_id=oid_to_id(i, 'unit'),
                                              status=s,
                                              value=v,
                                              wait=w,
                                              uuid=u,
                                              priority=p,
                                              q=q))

    @log_i
    @api_need_supervisor_pass
    @notify_plugins
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
        if not unit:
            raise ResourceNotFound
        elif not key_check(k, unit):
            raise AccessDenied
        return ecall(
            eva.sfa.controller.uc_pool.action_toggle(unit_id=oid_to_id(
                i, 'unit'),
                                                     wait=w,
                                                     uuid=u,
                                                     priority=p,
                                                     q=q))

    @log_i
    @notify_plugins
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
               finished, D for dead

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
                if not a:
                    raise ResourceNotFound
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
        if not item or not key_check(k, item, ro_op=True):
            raise ResourceNotFound
        if item.item_type == 'unit':
            return ecall(
                eva.sfa.controller.uc_pool.result(unit_id=oid_to_id(i, 'unit'),
                                                  uuid=u,
                                                  group=g,
                                                  status=s))
        elif item.item_type == 'lmacro':
            return ecall(
                eva.sfa.controller.lm_pool.result(macro_id=oid_to_id(
                    i, 'lmacro'),
                                                  uuid=u,
                                                  group=g,
                                                  status=s))
        else:
            raise ResourceNotFound

    @log_i
    @api_need_supervisor_pass
    @notify_plugins
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
        if not unit:
            raise ResourceNotFound
        elif not key_check(k, unit):
            raise AccessDenied
        return ecall(
            eva.sfa.controller.uc_pool.disable_actions(
                unit_id=oid_to_id(i, 'unit')))

    @log_i
    @api_need_supervisor_pass
    @notify_plugins
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
        if not unit:
            raise ResourceNotFound
        elif not key_check(k, unit):
            raise AccessDenied
        return ecall(
            eva.sfa.controller.uc_pool.enable_actions(
                unit_id=oid_to_id(i, 'unit')))

    @log_w
    @api_need_supervisor_pass
    @notify_plugins
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
        if not unit:
            raise ResourceNotFound
        elif not key_check(k, unit):
            raise AccessDenied
        result = ecall(
            eva.sfa.controller.uc_pool.terminate(unit_id=oid_to_id(i, 'unit'),
                                                 uuid=u))
        if result is True and i:
            return True, api_result_accepted
        else:
            return result

    @log_w
    @api_need_supervisor_pass
    @notify_plugins
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
        if not unit:
            raise ResourceNotFound
        elif not key_check(k, unit):
            raise AccessDenied
        result = ecall(
            eva.sfa.controller.uc_pool.kill(unit_id=oid_to_id(i, 'unit')))
        if result is True:
            return result, api_result_accepted
        if 'ok' in result:
            del result['ok']
        return True, result

    @log_w
    @api_need_supervisor_pass
    @notify_plugins
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
        if not unit:
            raise ResourceNotFound
        elif not key_check(k, unit):
            raise AccessDenied
        return ecall(
            eva.sfa.controller.uc_pool.q_clean(unit_id=oid_to_id(i, 'unit')))

    @log_i
    @api_need_supervisor_pass
    @notify_plugins
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
        if v is not None:
            v = str(v)
        lvar = eva.sfa.controller.lm_pool.get_lvar(oid_to_id(i, 'lvar'))
        if not lvar:
            raise ResourceNotFound
        elif not key_check(k, lvar):
            raise AccessDenied
        return ecall(
            eva.sfa.controller.lm_pool.set(lvar_id=oid_to_id(i, 'lvar'),
                                           status=s,
                                           value=v))

    @log_i
    @api_need_supervisor_pass
    @notify_plugins
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
        if not lvar:
            raise ResourceNotFound
        elif not key_check(k, lvar):
            raise AccessDenied
        return ecall(
            eva.sfa.controller.lm_pool.reset(lvar_id=oid_to_id(i, 'lvar')))

    @log_i
    @api_need_supervisor_pass
    @notify_plugins
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
        if not lvar:
            raise ResourceNotFound
        elif not key_check(k, lvar):
            raise AccessDenied
        return ecall(
            eva.sfa.controller.lm_pool.clear(lvar_id=oid_to_id(i, 'lvar')))

    @log_i
    @api_need_supervisor_pass
    @notify_plugins
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
        if not lvar:
            raise ResourceNotFound
        elif not key_check(k, lvar):
            raise AccessDenied
        return ecall(
            eva.sfa.controller.lm_pool.toggle(lvar_id=oid_to_id(i, 'lvar')))

    @log_i
    @api_need_supervisor_pass
    @notify_plugins
    def increment(self, **kwargs):
        """
        increment lvar value

        Increment value of a :ref:`logic variable<lvar>`. Initial value should
        be number

        Args:
            k:
            .i: lvar id
        """
        k, i = parse_function_params(kwargs, 'ki', '.s')
        lvar = eva.sfa.controller.lm_pool.get_lvar(oid_to_id(i, 'lvar'))
        if not lvar:
            raise ResourceNotFound
        elif not key_check(k, lvar):
            raise AccessDenied
        return ecall(
            eva.sfa.controller.lm_pool.increment(lvar_id=oid_to_id(i, 'lvar')))

    @log_i
    @api_need_supervisor_pass
    @notify_plugins
    def decrement(self, **kwargs):
        """
        decrement lvar value

        Decrement value of a :ref:`logic variable<lvar>`. Initial value should
        be number

        Args:
            k:
            .i: lvar id
        """
        k, i = parse_function_params(kwargs, 'ki', '.s')
        lvar = eva.sfa.controller.lm_pool.get_lvar(oid_to_id(i, 'lvar'))
        if not lvar:
            raise ResourceNotFound
        elif not key_check(k, lvar):
            raise AccessDenied
        return ecall(
            eva.sfa.controller.lm_pool.decrement(lvar_id=oid_to_id(i, 'lvar')))

    @log_d
    @notify_plugins
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
                    if key_check(k, v, ro_op=True) and \
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
                if key_check(k, v, ro_op=True) and (not group or \
                        eva.item.item_match(v, [], [ group ])):
                    result.append(v.serialize(info=True))
        return sorted(result, key=lambda k: k['id'])

    @log_d
    @notify_plugins
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
            if key_check(k, v, ro_op=True) and not v.group in result:
                result.append(v.group)
        return sorted(result)

    @log_i
    @api_need_supervisor_pass
    @notify_plugins
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
        if not macro:
            raise ResourceNotFound
        elif not key_check(k, macro):
            raise AccessDenied
        return ecall(
            eva.sfa.controller.lm_pool.run(macro=oid_to_id(i, 'lmacro'),
                                           args=a,
                                           kwargs=kw,
                                           priority=p,
                                           q_timeout=q,
                                           wait=w,
                                           uuid=u))

    @log_d
    @notify_plugins
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
        if isinstance(group, list):
            _group = group
        else:
            _group = str(group).split(',')
        if not controller_id:
            for c, d in \
                eva.sfa.controller.lm_pool.cycles_by_controller.copy().items():
                for a, v in d.copy().items():
                    if key_check(k, v, ro_op=True) and \
                        (not group or \
                            eva.item.item_match(v, [], _group)):
                        result.append(v.serialize(full=True))
        else:
            if controller_id.find('/') != -1:
                c = controller_id.split('/')
                if len(c) > 2 or c[0] != 'lm':
                    return None
                c_id = c[1]
            else:
                c_id = controller_id
            if c_id not in eva.sfa.controller.lm_pool.cycles_by_controller:
                return None
            for a, v in \
                eva.sfa.controller.lm_pool.cycles_by_controller[\
                                                        c_id].copy().items():
                if key_check(k, v, ro_op=True) and (not group or \
                        eva.item.item_match(v, [], _group)):
                    result.append(v.serialize(info=True))
        return sorted(result, key=lambda k: k['id'])

    @log_d
    @notify_plugins
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
        if not item or not key_check(k, item, ro_op=True):
            raise ResourceNotFound
        return item.serialize(full=True)

    @log_d
    @notify_plugins
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
            if key_check(k, v, ro_op=True) and not v.group in result:
                result.append(v.group)
        return sorted(result)

    @log_i
    @api_need_master
    @notify_plugins
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
    @notify_plugins
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
        save = save or eva.core.config.auto_save
        if group == 'uc' or group is None:
            c = eva.sfa.controller.append_uc(uri=uri,
                                             key=key,
                                             makey=makey,
                                             mqtt_update=mqtt_update,
                                             ssl_verify=ssl_verify,
                                             timeout=timeout,
                                             save=save)
            if c:
                return c.serialize(info=True)
        if group == 'lm' or group is None:
            c = eva.sfa.controller.append_lm(uri=uri,
                                             key=key,
                                             makey=makey,
                                             mqtt_update=mqtt_update,
                                             ssl_verify=ssl_verify,
                                             timeout=timeout,
                                             save=save)
            if c:
                return c.serialize(info=True)
        raise FunctionFailed

    @log_i
    @api_need_master
    @notify_plugins
    def matest_controller(self, **kwargs):
        """
        test management API connection to remote controller

        Args:
            k: .master
            .i: controller id
        """
        i = parse_api_params(kwargs, 'i', 'S')
        item = eva.sfa.controller.get_controller(i)
        return True if item.matest() else False

    @log_i
    @api_need_master
    @notify_plugins
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
                return eva.sfa.controller.uc_pool.manually_reload_controller(ci)
            elif ct == 'lm':
                return eva.sfa.controller.lm_pool.manually_reload_controller(ci)
            raise InvalidParameter('controller type unknown')
        else:
            success = True
            if not eva.sfa.controller.uc_pool.manually_reload_controller('ALL'):
                success = False
            if not eva.sfa.controller.lm_pool.manually_reload_controller('ALL'):
                success = False
            if not success:
                raise FunctionFailed
            return True

    @log_i
    @api_need_master
    @notify_plugins
    def upnp_rescan_controllers(self, **kwargs):
        """
        rescan controllers via UPnP

        Args:
            k: .master
        """
        parse_api_params(kwargs, '', '')
        import eva.upnp
        if eva.upnp.discovery_worker.is_active():
            eva.upnp.discovery_worker.trigger_threadsafe()
            return True
        else:
            return False

    @log_i
    @api_need_master
    @notify_plugins
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
            if not controller:
                return None
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
        return sorted(sorted(result, key=lambda k: k['oid']),
                      key=lambda k: ['controller_id'])

    @api_need_master
    def reload_clients(self, **kwargs):
        """
        ask connected clients to reload

        Sends **reload** event to all connected clients asking them to reload
        the interface.

        All the connected clients receive the event with *subject="reload"* and
        *data="asap"*. If the clients use :ref:`js_framework`, they can catch
        *server.reload* event.

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
        *data="restart"*. If the clients use :ref:`js_framework`, they can
        catch *server.restart* event.

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
        if p is None:
            _p = ['U', 'S', 'LV']
        else:
            _p = p
            if not _p:
                return []
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
        return sorted(sorted(result, key=lambda k: k['oid']),
                      key=lambda k: k['type'])


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
                return self.state_history(k=k,
                                          i='{}:{}'.format(rtp, ii),
                                          **props)
            elif kind == 'log':
                return self.state_log(k=k, i='{}:{}'.format(rtp, ii), **props)
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
        if rtp == 'core':
            if method == 'supervisor_message':
                if 'sender' in props:
                    sender = props['sender']
                    if 'u' in sender:
                        props['u'] = sender['u']
                    if 'key_id' in sender:
                        props['a'] = sender['key_id']
                    del props['sender']
                return self.supervisor_message(k=k, **props)
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
                if not a:
                    raise FunctionFailed
                set_restful_response_location(a['uuid'], 'action')
                return a
        elif rtp == 'lvar':
            if ii:
                v = props.get('v')
                if v == '!increment':
                    return self.increment(k=k, i=ii)
                if v == '!decrement':
                    return self.decrement(k=k, i=ii)
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
            elif method == 'upnp-rescan':
                return self.upnp_rescan_controllers(k=k)
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
        if rtp == 'core':
            if 'supervisor_lock' in props:
                kw = props['supervisor_lock']
                if kw is None:
                    self.supervisor_unlock(k=k)
                else:
                    if 'o' in kw:
                        kw['u'] = kw['o'].get('u')
                        kw['a'] = kw['o'].get('key_id')
                        kw['p'] = kw['o'].get('utp')
                        del kw['o']
                    if not self.supervisor_lock(k=k, **kw):
                        raise FunctionFailed
                del props['supervisor_lock']
                if not props:
                    return True
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
                    return super().set_controller_prop(k=k,
                                                       i=ii,
                                                       save=save,
                                                       v=props)
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


def _tool_error_response(e, code=500):
    cherrypy.serving.response.headers['Content-Type'] = 'text/plain'
    cherrypy.serving.response.status = code
    return str(e).encode()


def serve_pvt(*args,
              k=None,
              f=None,
              c=None,
              ic=None,
              nocache=None,
              regdata=False,
              **kwargs):
    if f is None:
        f = '/'.join(args)
    _k = cp_client_key(k, from_cookie=True, _aci=True)
    _r = '%s@%s' % (apikey.key_id(_k), http_real_ip())
    if f is None or f == '' or f.find('..') != -1 or f[0] == '/':
        raise cp_api_404()
    if not key_check(
            _k, pvt_file='%/' + f if regdata else f, ip=http_real_ip(),
            ro_op=True):
        logging.warning('pvt %s file %s access forbidden' % (_r, f))
        raise cp_forbidden_key()
    if regdata:
        return serve_json_yml(f, dts='%pvt')
    elif f.endswith('.j2'):
        return serve_j2('/' + f, tpl_dir=eva.core.dir_pvt)
    elif f.endswith('.json') or f.endswith('.yml') or f.endswith('.yaml'):
        return serve_json_yml(f, dts='pvt')
    _f = eva.core.dir_pvt + '/' + f
    _f_alt = None
    if c:
        fls = [x for x in glob.glob(_f) if os.path.isfile(x)]
        if not fls:
            raise cp_api_404()
        if c == 'newest':
            _f = max(fls, key=os.path.getmtime)
            fls.remove(_f)
            if fls:
                _f_alt = max(fls, key=os.path.getmtime)
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
            if nocache:
                cp_nocache()
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
                if os.path.getsize(_f) > 10000000:
                    raise
                from PIL import Image
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
                if nocache:
                    cp_nocache()
                logging.info('pvt %s file access %s' % (_r, f))
                return result
            else:
                raise cp_bad_request()
        except cherrypy.HTTPError:
            raise
        except:
            eva.core.log_traceback()
            raise cp_api_error()
    if nocache:
        cp_nocache()
    logging.info('pvt %s file access %s' % (_r, f))
    return serve_file(_f)


def serve_json_yml(fname, dts='ui'):
    if fname.startswith('/pvt/'):
        kw = cherrypy.serving.request.params
        kw['f'] = fname[5:]
        return serve_pvt(**kw)
    elif fname.startswith('/%pvt/'):
        kw = cherrypy.serving.request.params
        kw['f'] = fname[6:]
        kw['regdata'] = True
        return serve_pvt(**kw)
    elif fname.startswith('/%pub/'):
        try:
            data = eva.registry.key_get('userdata/pub/{}'.format(
                fname[6:].replace('..', '')))
        except KeyError:
            raise cp_api_404()
    elif dts == '%pvt':
        try:
            data = eva.registry.key_get('userdata/pvt/{}'.format(
                fname.replace('..', '')))
        except KeyError:
            raise cp_api_404()
    else:
        infile = '{}/{}/{}'.format(eva.core.dir_eva, dts,
                                   fname).replace('..', '')
        if not os.path.isfile(infile):
            raise cp_api_404()
        with open(infile) as fd:
            data = fd.read()
    cas = cherrypy.serving.request.params.get('as')
    lang = cherrypy.serving.request.params.get('lang')
    if not isinstance(data, str) and not cas:
        cas = 'json'
    if cas or lang:
        try:
            if isinstance(data, str):
                data = yaml.load(data)
            if lang:
                document_name = fname.rsplit('.')[0]
                if document_name.startswith('/'):
                    document_name = document_name[1:]
                data = eva.lang.convert(data,
                                        lang,
                                        document_name=document_name,
                                        localedir=[
                                            eva.core.dir_pvt + '/locales',
                                            eva.core.dir_ui + '/locales'
                                        ])
        except Exception as e:
            eva.core.log_traceback()
            return _tool_error_response(e)
        if not cas:
            cas = fname.rsplit('.', 1)[-1]
        if cas == 'json':
            try:
                data = format_json(data,
                                   minimal=not eva.core.config.development)
            except Exception as e:
                return _tool_error_response(e)
            cherrypy.serving.response.headers[
                'Content-Type'] = 'application/json'
        elif cas in ['yml', 'yaml']:
            data = yaml.dump(data, default_flow_style=False)
            cherrypy.serving.response.headers[
                'Content-Type'] = 'application/x-yaml'
        elif cas == 'js':
            var = cherrypy.serving.request.params.get('var')
            func = cherrypy.serving.request.params.get('func')
            if var:
                if eva.core.config.development:
                    data = 'var {} = {};'.format(
                        var, format_json(data, minimal=False))
                else:
                    data = 'var {}={};'.format(var,
                                               format_json(data, minimal=True))
            elif func:
                if eva.core.config.development:
                    data = 'function {}() {{\n  return {};\n}}'.format(
                        func, format_json(data, minimal=False))
                else:
                    data = 'function {}(){{return {};}}'.format(
                        func, format_json(data, minimal=True))
            else:
                return _tool_error_response('var/func not specified', 400)
            cherrypy.serving.response.headers[
                'Content-Type'] = 'application/javascript'
        else:
            return _tool_error_response('Invalid "as" format', 400)
    return data.encode('utf-8')


def json_yml_handler(*args, **kwargs):
    try:
        del cherrypy.serving.response.headers['Content-Length']
    except:
        pass
    return serve_json_yml(cherrypy.serving.request.path_info)


def j2_hook(*args, **kwargs):
    if cherrypy.serving.request.path_info[-3:] == '.j2':
        cherrypy.serving.request.handler = eva.sfa.sfatpl.j2_handler


def html_hook(*args, **kwargs):
    if cherrypy.serving.request.path_info[-4:] == '.htm' or \
        cherrypy.serving.request.path_info[-5:] == '.html':
        cherrypy.serving.response.headers[
            'Content-Type'] = 'text/html;charset=utf-8'


def json_yml_hook(*args, **kwargs):
    if cherrypy.serving.request.path_info[-5:] in ['.json', 'yaml'] or \
        cherrypy.serving.request.path_info[-4:] == '.yml' or \
        cherrypy.serving.request.path_info.startswith('/%pub/') or \
        cherrypy.serving.request.path_info.startswith('/%pvt/'):
        cherrypy.serving.request.handler = json_yml_handler


# ui and pvt


class UI_ROOT():

    _cp_config = {
        'tools.init_call.on': True,
        'tools.j2.on': True,
        'tools.html_charset.on': True,
        'tools.jconverter.on': True,
    }

    def __init__(self):
        cherrypy.tools.j2 = cherrypy.Tool('before_handler',
                                          j2_hook,
                                          priority=100)
        cherrypy.tools.html_charset = cherrypy.Tool('before_handler',
                                                    html_hook,
                                                    priority=100)
        cherrypy.tools.jconverter = cherrypy.Tool('before_handler',
                                                  json_yml_hook,
                                                  priority=100)

    @cherrypy.expose
    def index(self, **kwargs):
        if os.path.exists(eva.core.dir_eva + '/ui/index.j2'):
            return serve_j2('/index.j2')
        if os.path.exists(f'{eva.core.dir_ui}/index.html'):
            cherrypy.serving.response.headers[
                'Content-Type'] = 'text/html;charset=utf-8'
            with open(f'{eva.core.dir_ui}/index.html') as fh:
                return fh.read()
        raise cp_api_404()


class EVA_Mirror:
    pass


class SFA_HTTP_Root:

    def __init__(self):
        self._fp_hide_in_log = {}
        self._log_api_call = HTTP_API_Logger()

    _cp_config = {
        'tools.init_call.on': True,
        'tools.j2.on': True,
        'tools.jconverter.on': True,
        'tools.autojsonrpc.on': True
    }

    @cherrypy.expose
    def index(self, **kwargs):
        q = cherrypy.request.query_string
        if q:
            q = '?' + q
        raise cherrypy.HTTPRedirect('/ui/' + q)

    @cherrypy.expose
    def favicon_ico(self):
        ico_file = eva.core.dir_ui + '/favicon.ico'
        if not os.path.exists(ico_file):
            ico_file = eva.core.dir_lib + '/eva/i/favicon.ico'
        if not os.path.exists(ico_file):
            raise cp_api_404()
        cherrypy.serving.response.headers['Content-Type'] = 'image/x-icon'
        with open(ico_file, 'rb') as fh:
            return fh.read()

    @cherrypy.expose
    def rpvt(self, k=None, f=None, ic=None, nocache=None):
        _k = cp_client_key(k, from_cookie=True, _aci=True)
        _r = '%s@%s' % (apikey.key_id(_k), http_real_ip())
        if f is None:
            return _tool_error_response('uri not provided', code=400)
        if not key_check(_k, rpvt_uri=f, ip=http_real_ip(), ro_op=True):
            logging.warning('rpvt %s uri %s access forbidden' % (_r, f))
            raise cp_forbidden_key()
        if f[:3] in ['uc/', 'lm/']:
            try:
                controller_id, f = f.split(':', 1)
            except:
                return _tool_error_response('invalid param: {}'.format(f))
            try:
                controller = eva.sfa.controller.get_controller(controller_id)
            except:
                ResourceNotFound
                return _tool_error_response(
                    'Controller not found: {}'.format(controller_id))
            code, result = controller.api_call('rpvt', {
                'f': f,
                'ic': ic,
                'nocache': nocache
            })
            if code:
                return _tool_error_response(
                    'remote controller code {}'.format(code))
            cherrypy.serving.response.headers['Content-Type'] = result[
                'content_type']
            # return base64.b64decode(result['data'])
            return result['data']
        try:
            if f.find('//') == -1:
                _f = 'http://' + f
            else:
                _f = f
            r = requests.get(_f, timeout=eva.core.config.timeout)
        except:
            raise cp_api_error()
        if r.status_code != 200:
            return _tool_error_response('remote response %s' % r.status_code)
        ctype = r.headers.get('Content-Type')
        if ctype:
            cherrypy.serving.response.headers['Content-Type'] = ctype
        if nocache:
            cp_nocache()
        result = r.content
        if ic:
            try:
                icmd, args, fmt = ic.split(':')
                if icmd == 'resize':
                    x, y, q = args.split('x')
                    x = int(x)
                    y = int(y)
                    q = int(q)
                    from PIL import Image
                    image = Image.open(BytesIO(result))
                    image.thumbnail((x, y))
                    result = image.tobytes(fmt, 'RGB', q)
                    cherrypy.response.headers['Content-Type'] = 'image/' + fmt
                else:
                    raise cp_bad_request()
            except cherrypy.HTTPError:
                raise
            except:
                eva.core.log_traceback()
                raise cp_api_error()
        return BytesIO(result)

    @cherrypy.expose
    def pvt(self, *args, **kwargs):
        return serve_pvt(*args, **kwargs)

    @cherrypy.expose
    def upload(self,
               k=None,
               ufile=None,
               process_macro_id=None,
               w=None,
               p=None,
               q=None,
               rdr=None,
               **kwargs):
        params = {
            'k': k,
            'ufile': ufile,
            'process_macro_id': process_macro_id,
            'w': w,
            'p': p,
            'q': q,
            'rdr': rdr
        }
        params.update(kwargs)
        if eva.core.plugins_event_apicall('upload', params) is False:
            raise FunctionFailed
        from neotasker import g
        try:
            if ufile is None:
                raise InvalidParameter('ufile is required')
            if process_macro_id is None:
                raise InvalidParameter('process_macro_id is required')
        except Exception as e:
            logging.error(e)
            eva.core.log_traceback()
            raise cp_bad_request(str(e))
        _k = cp_client_key(k, from_cookie=True, _aci=True)
        try:
            content = ufile.file.read()
        except:
            if rdr:
                raise cherrypy.HTTPRedirect(rdr)
            else:
                cherrypy.response.headers['Content-Type'] = 'application/json'
                return format_json(
                    {
                        'ok': False
                    }, minimal=not eva.core.config.development).encode()
        from hashlib import sha256
        h = sha256()
        h.update(content)
        info = {}
        info['file_name'] = ufile.filename
        info['content_type'] = ufile.content_type.value
        info['system_name'] = f'sfa/{eva.core.config.system_name}'
        info['sha256'] = h.hexdigest()
        info['form'] = kwargs
        self._log_api_call(self.upload, {
            **info,
            **{
                'process_macro_id': process_macro_id,
                'k': _k
            }
        },
                           logging.debug,
                           self._fp_hide_in_log,
                           debug=True)
        try:
            if '/' in ufile.filename:
                raise ValueError('File name contains "/"')
            info['aci'] = g.aci.copy()
            result = api.run(k=_k,
                             i=process_macro_id,
                             w=w,
                             p=p,
                             q=q,
                             kw={
                                 'content': content,
                                 'data': info
                             })
            if eva.core.plugins_event_apicall_result('upload', params,
                                                     result) is False:
                raise FunctionFailed
        except ResourceNotFound as e:
            logging.error(e)
            eva.core.log_traceback()
            raise cp_api_404(f'process macro {process_macro_id} not found')
        except AccessDenied as e:
            logging.error(e)
            eva.core.log_traceback()
            raise cp_forbidden_key('access denied to process macro')
        except Exception as e:
            logging.error(e)
            eva.core.log_traceback()
            raise cp_api_error(str(e))
        if rdr:
            raise cherrypy.HTTPRedirect(rdr)
        else:
            cherrypy.response.headers['Content-Type'] = 'application/json'
            return format_json(
                result, minimal=not eva.core.config.development).encode()


def handle_ui_error(code):
    if os.path.exists(f'{eva.core.dir_ui}/errors/{code}.j2'):
        return serve_j2(f'errors/{code}.j2')
    elif os.path.exists(f'{eva.core.dir_ui}/errors/{code}.html'):
        cherrypy.serving.response.headers[
            'Content-Type'] = 'text/html;charset=utf-8'
        with open(f'{eva.core.dir_ui}/errors/{code}.html') as fh:
            return fh.read()
    else:
        return tiny_httpe[f'error_page.{code}']()


def ui_error_page_400(*args, **kwargs):
    return handle_ui_error('400')


def ui_error_page_403(*args, **kwargs):
    return handle_ui_error('403')


def ui_error_page_404(*args, **kwargs):
    return handle_ui_error('404')


def ui_error_page_405(*args, **kwargs):
    return handle_ui_error('405')


def ui_error_page_409(*args, **kwargs):
    return handle_ui_error('409')


def ui_error_page_500(*args, **kwargs):
    return handle_ui_error('500')


ui_httpe = {
    'error_page.400': ui_error_page_400,
    'error_page.403': ui_error_page_403,
    'error_page.404': ui_error_page_404,
    'error_page.405': ui_error_page_405,
    'error_page.409': ui_error_page_409,
    'error_page.500': ui_error_page_500
}


def start():
    http_api = SFA_HTTP_API()
    cherrypy.tree.mount(http_api, http_api.api_uri)
    cherrypy.tree.mount(jrpc, jrpc.api_uri)
    cherrypy.tree.mount(SFA_REST_API(),
                        SFA_REST_API.api_uri,
                        config={
                            '/': {
                                'request.dispatch':
                                    cherrypy.dispatch.MethodDispatcher()
                            }
                        })
    cherrypy.tree.mount(
        SFA_HTTP_Root(),
        '/',
        config={
            '/': dict_merge({
                'tools.sessions.on': False,
            }, tiny_httpe),
            '/.evahi': {
                'tools.sessions.on': False,
                'tools.staticdir.dir': eva.core.dir_eva + '/ui/.evahi',
                'tools.staticdir.on': True
            },
        })

    dir_mirror = eva.core.dir_eva + '/mirror'

    if os.path.isdir(dir_mirror):
        cherrypy.tree.mount(
            EVA_Mirror(),
            '/mirror',
            config={
                '/':
                    dict_merge(
                        {
                            'tools.staticdir.on': True,
                            'tools.staticdir.dir': dir_mirror,
                            'tools.staticdir.index': 'index.html'
                        }, tiny_httpe)
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
                    }, ui_httpe)
        })
    eva.api.jrpc = jrpc
    eva.sfa.cloudmanager.start()


api = SFA_API()
eva.api.api = api
jrpc = SFA_JSONRPC_API()
