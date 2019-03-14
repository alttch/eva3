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

from eva.tools import is_oid
from eva.tools import parse_oid
from eva.tools import oid_to_id
from eva.tools import dict_from_str

import eva.core
import eva.notify
import eva.api

from eva.api import GenericHTTP_API
from eva.api import GenericAPI
from eva.api import cp_forbidden_key
from eva.api import http_api_result_ok
from eva.api import http_api_result_error
from eva.api import cp_api_error
from eva.api import cp_bad_request
from eva.api import cp_api_404
from eva.api import api_need_master as cp_need_master
from eva.api import restful_api_method
from eva.api import http_real_ip
from eva.api import cp_client_key
from eva.api import set_response_location
from eva.api import generic_web_api_method
from eva.api import MethodNotFound

from eva import apikey

import eva.sfa.controller
import eva.sfa.cloudmanager
import eva.sysapi

from PIL import Image

api = None


def cp_need_dm_rules_list(k):
    if not apikey.check(k, allow=['dm_rules_list']):
        raise cp_forbidden_key()


def cp_need_dm_rule_props(k):
    if not apikey.check(k, allow=['dm_rule_props']):
        raise cp_forbidden_key()


class SFA_API(GenericAPI):

    def management_api_call(self, k=None, i=None, f=None, p=None):
        if not eva.sfa.controller.cloud_manager or \
                not apikey.check(k, master=True):
            return None, None
        controller = eva.sfa.controller.get_controller(i)
        if not controller: return None, -1
        if isinstance(p, dict):
            params = p
        elif isinstance(p, str):
            params = dict_from_str(p)
        else:
            params = None
        return controller.management_api_call(f, params)

    def state(self, k=None, i=None, group=None, tp=None, full=None):
        if is_oid(i):
            _tp, _i = parse_oid(i)
        else:
            _tp = tp
            _i = i
        if not _tp: return None
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
                return None
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

    def state_history(self,
                      k=None,
                      tp=None,
                      a=None,
                      i=None,
                      s=None,
                      e=None,
                      l=None,
                      x=None,
                      t=None,
                      w=None,
                      g=None):
        if is_oid(i):
            _tp, _i = parse_oid(i)
        else:
            _tp = tp
            _i = i
        if not _tp: return False
        if _tp == 'U' or _tp == 'unit':
            gi = eva.sfa.controller.uc_pool.units
        elif _tp == 'S' or _tp == 'sensor':
            gi = eva.sfa.controller.uc_pool.sensors
        elif _tp == 'LV' or _tp == 'lvar':
            gi = eva.sfa.controller.lm_pool.lvars
        else:
            return False
        if not _i in gi: return False
        if not apikey.check(k, gi[_i]):
            return False
        return self.get_state_history(
            k=k,
            a=a,
            oid=gi[_i].oid,
            t_start=s,
            t_end=e,
            limit=l,
            prop=x,
            time_format=t,
            fill=w,
            fmt=g)

    def groups(self, k=None, tp=None, group=None):
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

    def action(self,
               k=None,
               i=None,
               action_uuid=None,
               nstatus=None,
               nvalue='',
               priority=None,
               q=None,
               wait=0):
        unit = eva.sfa.controller.uc_pool.get_unit(oid_to_id(i, 'unit'))
        if not unit or not apikey.check(k, unit): return None
        return eva.sfa.controller.uc_pool.action(
            unit_id=oid_to_id(i, 'unit'),
            status=nstatus,
            value=nvalue,
            wait=wait,
            uuid=action_uuid,
            priority=priority,
            q=q)

    def action_toggle(self,
                      k=None,
                      i=None,
                      action_uuid=None,
                      priority=None,
                      q=None,
                      wait=0):
        unit = eva.sfa.controller.uc_pool.get_unit(oid_to_id(i, 'unit'))
        if not unit or not apikey.check(k, unit): return None
        return eva.sfa.controller.uc_pool.action_toggle(
            unit_id=oid_to_id(i, 'unit'),
            wait=wait,
            uuid=action_uuid,
            priority=priority,
            q=q)

    def result(self, k=None, i=None, u=None, g=None, s=None):
        item = None
        if u:
            a = eva.sfa.controller.uc_pool.action_history_get(u)
            if a:
                item = eva.sfa.controller.uc_pool.get_unit(a['i'])
            else:
                a = eva.sfa.controller.lm_pool.action_history_get(u)
                if not a: return None
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
        if not item or not apikey.check(k, item): return None
        if item.item_type == 'unit':
            return eva.sfa.controller.uc_pool.result(
                unit_id=oid_to_id(i, 'unit'), uuid=u, group=g, status=s)
        elif item.item_type == 'lmacro':
            return eva.sfa.controller.lm_pool.result(
                macro_id=oid_to_id(i, 'lmacro'), uuid=u, group=g, status=s)
        else:
            return None

    def disable_actions(self, k=None, i=None):
        unit = eva.sfa.controller.uc_pool.get_unit(oid_to_id(i, 'unit'))
        if not unit or not apikey.check(k, unit): return None
        return eva.sfa.controller.uc_pool.disable_actions(
            unit_id=oid_to_id(i, 'unit'))

    def enable_actions(self, k=None, i=None):
        unit = eva.sfa.controller.uc_pool.get_unit(oid_to_id(i, 'unit'))
        if not unit or not apikey.check(k, unit): return None
        return eva.sfa.controller.uc_pool.enable_actions(
            unit_id=oid_to_id(i, 'unit'))

    def terminate(self, k=None, i=None, u=None):
        if i:
            unit = eva.sfa.controller.uc_pool.get_unit(oid_to_id(i, 'unit'))
        elif u:
            a = eva.sfa.controller.uc_pool.action_history_get(u)
            unit = eva.sfa.controller.uc_pool.get_unit(a['i'])
        else:
            return None
        if not unit or not apikey.check(k, unit): return None
        return eva.sfa.controller.uc_pool.terminate(
            unit_id=oid_to_id(i, 'unit'), uuid=u)

    def kill(self, k=None, i=None):
        unit = eva.sfa.controller.uc_pool.get_unit(oid_to_id(i, 'unit'))
        if not unit or not apikey.check(k, unit): return None
        return eva.sfa.controller.uc_pool.kill(unit_id=oid_to_id(i, 'unit'))

    def q_clean(self, k=None, i=None):
        unit = eva.sfa.controller.uc_pool.get_unit(oid_to_id(i, 'unit'))
        if not unit or not apikey.check(k, unit): return None
        return eva.sfa.controller.uc_pool.q_clean(unit_id=oid_to_id(i, 'unit'))

    def set(self, k=None, i=None, status=None, value=None):
        lvar = eva.sfa.controller.lm_pool.get_lvar(oid_to_id(i, 'lvar'))
        if not lvar or not apikey.check(k, lvar): return None
        return eva.sfa.controller.lm_pool.set(
            lvar_id=oid_to_id(i, 'lvar'), status=status, value=value)

    def reset(self, k=None, i=None):
        lvar = eva.sfa.controller.lm_pool.get_lvar(oid_to_id(i, 'lvar'))
        if not lvar or not apikey.check(k, lvar): return None
        return eva.sfa.controller.lm_pool.reset(lvar_id=oid_to_id(i, 'lvar'))

    def toggle(self, k=None, i=None):
        lvar = eva.sfa.controller.lm_pool.get_lvar(oid_to_id(i, 'lvar'))
        if not lvar or not apikey.check(k, lvar): return None
        return eva.sfa.controller.lm_pool.toggle(lvar_id=oid_to_id(i, 'lvar'))

    def clear(self, k=None, i=None):
        lvar = eva.sfa.controller.lm_pool.get_lvar(oid_to_id(i, 'lvar'))
        if not lvar or not apikey.check(k, lvar): return None
        return eva.sfa.controller.lm_pool.clear(lvar_id=oid_to_id(i, 'lvar'))

    def list_macros(self, k=None, controller_id=None, group=None):
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
                if len(c) > 2 or c[0] != 'lm': return None
                c_id = c[1]
            else:
                c_id = controller_id
            if c_id not in eva.sfa.controller.lm_pool.macros_by_controller:
                return None
            for a, v in \
                eva.sfa.controller.lm_pool.macros_by_controller[\
                                                        c_id].copy().items():
                if apikey.check(k, v) and (not group or \
                        eva.item.item_match(v, [], [ group ])):
                    result.append(v.serialize(info=True))
        return sorted(result, key=lambda k: k['id'])

    def groups_macro(self, k=None):
        result = []
        for a, v in eva.sfa.controller.lm_pool.macros.copy().items():
            if apikey.check(k, v) and not v.group in result:
                result.append(v.group)
        return sorted(result)

    def run(self,
            k=None,
            i=None,
            args=None,
            kwargs=None,
            priority=None,
            wait=0,
            uuid=None):
        macro = eva.sfa.controller.lm_pool.get_macro(oid_to_id(i, 'lmacro'))
        if not macro or not apikey.check(k, macro): return None
        return eva.sfa.controller.lm_pool.run(
            macro=oid_to_id(i, 'lmacro'),
            args=args,
            kwargs=kwargs,
            priority=priority,
            wait=wait,
            uuid=uuid)

    def list_cycles(self, k=None, controller_id=None, group=None):
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

    def groups_cycle(self, k=None):
        result = []
        for a, v in eva.sfa.controller.lm_pool.cycles.copy().items():
            if apikey.check(k, v) and not v.group in result:
                result.append(v.group)
        return sorted(result)

    def list_controllers(self, k=None, g=None):
        if not apikey.check(k, master = True) or \
                (g is not None and \
                    g not in [ 'uc', 'lm' ]):
            return None
        result = []
        if g is None or g == 'uc':
            for i, v in eva.sfa.controller.remote_ucs.copy().items():
                result.append(v.serialize(info=True))
        if g is None or g == 'lm':
            for i, v in eva.sfa.controller.remote_lms.copy().items():
                result.append(v.serialize(info=True))
        return sorted(result, key=lambda k: k['full_id'])

    def append_controller(self,
                          k=None,
                          uri=None,
                          key=None,
                          makey=None,
                          group=None,
                          mqtt_update=None,
                          ssl_verify=True,
                          timeout=None,
                          save=False):
        if not apikey.check(k, master=True) or not uri: return None
        if group == 'uc' or group is None:
            result = eva.sfa.controller.append_uc(
                uri=uri,
                key=key,
                makey=makey,
                mqtt_update=mqtt_update,
                ssl_verify=ssl_verify,
                timeout=timeout,
                save=save)
            if group is not None and not result:
                return result
            elif result:
                return result.serialize()
        if group == 'lm' or group is None:
            result = eva.sfa.controller.append_lm(
                uri=uri,
                key=key,
                makey=makey,
                mqtt_update=mqtt_update,
                ssl_verify=ssl_verify,
                timeout=timeout,
                save=save)
            if group is not None and not result:
                return result
            elif result:
                return result.serialize()
        return False

    def remove_controller(self, k=None, controller_id=None):
        if not apikey.check(k, master=True) or not controller_id:
            return None
        if not controller_id or controller_id.find('/') == -1: return None
        return eva.sfa.controller.remove_controller(controller_id)

    def list_controller_props(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        item = eva.sfa.controller.get_controller(i)
        return item.serialize(props=True) if item else None

    def get_controller(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        item = eva.sfa.controller.get_controller(i)
        if item is None: return None
        return item.serialize(info=True)

    def test_controller(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        item = eva.sfa.controller.get_controller(i)
        if item is None: return None
        return True if item.test() else False

    def matest_controller(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        item = eva.sfa.controller.get_controller(i)
        if item is None: return None
        return True if item.matest() else False

    def set_controller_prop(self, k=None, i=None, p=None, v=None, save=False):
        if not apikey.check(k, master=True): return None
        controller = eva.sfa.controller.get_controller(i)
        if not controller: return None
        result = controller.set_prop(p, v, save)
        if result and controller.config_changed and save:
            controller.save()
        return result

    def enable_controller(self, k=None, i=None, save=False):
        if not apikey.check(k, master=True): return None
        controller = eva.sfa.controller.get_controller(i)
        if not controller: return None
        result = controller.set_prop('enabled', 1, save)
        if result and controller.config_changed and save:
            controller.save()
        return result

    def disable_controller(self, k=None, i=None, save=False):
        if not apikey.check(k, master=True): return None
        controller = eva.sfa.controller.get_controller(i)
        if not controller: return None
        result = controller.set_prop('enabled', 0, save)
        if result and controller.config_changed and save:
            controller.save()
        return result

    def reload_controller(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        if i != 'ALL':
            if not i or i.find('/') == -1: return None
            try:
                ct, ci = i.split('/')
            except:
                return False
            if ct == 'uc':
                return eva.sfa.controller.uc_pool.reload_controller(ci)
            if ct == 'lm':
                return eva.sfa.controller.lm_pool.reload_controller(ci)
            return False
        else:
            success = True
            if not eva.sfa.controller.uc_pool.reload_controller('ALL'):
                success = False
            if not eva.sfa.controller.lm_pool.reload_controller('ALL'):
                success = False
            return success

    def list_remote(self, k=None, i=None, group=None, tp=None):
        if not apikey.check(k, master=True): return None
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

    def list_rule_props(self, k=None, i=None):
        rule = eva.sfa.controller.lm_pool.get_dm_rule(i)
        if not rule: return None
        if not apikey.check(k, allow = [ 'dm_rule_props' ]) and \
                not apikey.check(k, rule):
            return None
        result = eva.sfa.controller.lm_pool.list_rule_props(i)
        if not result: return None
        if not apikey.check(k, master=True):
            for i in result.copy():
                if i[:9] != 'in_range_' and \
                        i not in [ 'enabled', 'chillout_time', 'condition' ]:
                    del result[i]
        return result

    def set_rule_prop(self, k=None, i=None, p=None, v=None, save=False):
        rule = eva.sfa.controller.lm_pool.get_dm_rule(i)
        if not rule or not p: return None
        if p[:9] == 'in_range_' or p in ['enabled', 'chillout_time']:
            if not apikey.check(k, allow = [ 'dm_rule_props' ]) and \
                    not apikey.check(k, rule):
                return None
        else:
            if not apikey.check(k, master=True): return None
        return eva.sfa.controller.lm_pool.set_rule_prop(i, p, v, save)

    def reload_clients(self, k=None):
        if not apikey.check(k, master=True): return None
        eva.notify.reload_clients()
        return True

    def notify_restart(self, k=None):
        if not apikey.check(k, master=True): return None
        eva.notify.notify_restart()
        return True


class SFA_HTTP_API_abstract(SFA_API):

    @cp_need_master
    def management_api_call(self, k=None, i=None, f=None, p=None):
        code, data = super().management_api_call(k, i=i, f=f, p=p)
        if code is None:
            if data is None:
                raise cp_forbidden_key()
            elif data == -1:
                raise cp_api_404()
        result = {'code': code, 'data': data}
        return result

    def test(self, k=None, icvars=None):
        result = super().test(k=k)
        result['cloud_manager'] = eva.sfa.controller.cloud_manager
        if (icvars):
            cvars = eva.sysapi.api.get_cvar(k=k)
            if cvars is False:
                raise cp_forbidden_key()
            if not cvars:
                cvars = []
            result['cvars'] = cvars
        return result

    def state_all(self, k=None, p=None, g=None):
        result = []
        if p is None: _p = ['U', 'S', 'LV']
        else:
            _p = p
            if not _p: return []
        for tp in _p:
            try:
                result += self.state(k, p=tp, g=g, full=True)
            except:
                pass
        if p is None or 'lcycle' in _p:
            try:
                result += self.list_cycles(k, g=g)
            except:
                pass
        return sorted(
            sorted(result, key=lambda k: k['oid']), key=lambda k: k['type'])

    def state(self, k=None, i=None, g=None, p=None, full=None):
        result = super().state(k, i, g, p, full)
        if not result:
            raise cp_api_404()
        return result

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
        if i and isinstance(i, list) or i.find(',') != -1:
            if not w:
                raise cp_bad_request(
                    '"w" param required to process multiple items')
            if isinstance(i, list):
                items = i
            else:
                items = i.split(',')
            if not g or g == 'list':
                result = {}
            else:
                raise cp_bad_request(
                    'format should be list only to process multiple items')
            for i in items:
                r = super().state_history(
                    k=k, tp=p, a=a, i=i, s=s, e=e, l=l, x=x, t=t, w=w, g=g)
                if r is False: raise cp_api_error('internal error')
                if r is None: raise cp_api_404()
                result['t'] = r['t']
                if 'status' in r:
                    result[i + '/status'] = r['status']
                if 'value' in r:
                    result[i + '/value'] = r['value']
            return result
        else:
            result = super().state_history(
                k=k, tp=p, a=a, i=i, s=s, e=e, l=l, x=x, t=t, w=w, g=g)
            if result is False: raise cp_api_error('internal error')
            if result is None: raise cp_api_404()
            return result

    def groups(self, k=None, p=None, g=None):
        return super().groups(k, p, g)

    @cp_need_master
    def list_controllers(self, k=None, g=None):
        result = super().list_controllers(k, g)
        if result is None: raise cp_api_404()
        return result

    def action(self, k=None, i=None, u=None, s=None, v='', p=None, q=None, w=0):
        if w:
            try:
                _w = float(w)
            except:
                raise cp_bad_request('w is not a number')
        else:
            _w = None
        if p:
            try:
                _p = int(p)
            except:
                raise cp_bad_request('p is not an integer')
        else:
            _p = None
        if q:
            try:
                _q = float(q)
            except:
                raise cp_bad_request('q is not a number')
        else:
            _q = None
        a = super().action(
            k=k,
            i=i,
            action_uuid=u,
            nstatus=s,
            nvalue=v,
            priority=p,
            q=q,
            wait=_w)
        if not a:
            raise cp_api_404()
        return a

    def action_toggle(self, k=None, i=None, u=None, p=None, q=None, w=0):
        if w:
            try:
                _w = float(w)
            except:
                raise cp_bad_request('w is not a number')
        else:
            _w = None
        if p:
            try:
                _p = int(p)
            except:
                raise cp_bad_request('p is not an integer')
        else:
            _p = None
        if q:
            try:
                _q = float(q)
            except:
                raise cp_bad_request('q is not a number')
        else:
            _q = None
        a = super().action_toggle(
            k=k, i=i, action_uuid=u, priority=p, q=q, wait=_w)
        if not a:
            raise cp_api_404()
        return a

    def result(self, k=None, i=None, u=None, g=None, s=None):
        result = super().result(k, i, u, g, s)
        if result is None: raise cp_api_404()
        return result if result is not None else http_api_result_error()

    def terminate(self, k=None, i=None, u=None):
        result = super().terminate(k, i, u)
        if result is None: raise cp_api_404()
        return result if result else http_api_result_error()

    def kill(self, k=None, i=None):
        result = super().kill(k, i)
        if result is None: raise cp_api_404()
        return result if result else \
                http_api_result_error()

    def q_clean(self, k=None, i=None):
        result = super().q_clean(k, i)
        if result is None: raise cp_api_404()
        return result if result else http_api_result_error()

    def disable_actions(self, k=None, i=None):
        result = super().disable_actions(k, i)
        if result is None: raise cp_api_404()
        return result if result else http_api_result_error()

    def enable_actions(self, k=None, i=None):
        result = super().enable_actions(k, i)
        if result is None: raise cp_api_404()
        return result if result else http_api_result_error()

    def set(self, k=None, i=None, s=None, v=None):
        if s is None:
            _s = None
        else:
            try:
                _s = int(s)
            except:
                raise cp_bad_request('s is not an integer')
        result = super().set(k, i, _s, v)
        if result is None:
            raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    def reset(self, k=None, i=None):
        if super().reset(k, i):
            return http_api_result_ok()
        else:
            raise cp_api_404()

    def toggle(self, k=None, i=None):
        if super().toggle(k, i):
            return http_api_result_ok()
        else:
            raise cp_api_404()

    def clear(self, k=None, i=None):
        if super().clear(k, i):
            return http_api_result_ok()
        else:
            raise cp_api_404()

    def list_macros(self, k=None, i=None, g=None):
        result = super().list_macros(k, i, g)
        if result is None: raise cp_api_404()
        return result

    def groups_macro(self, k=None):
        return super().groups_macro(k)

    def list_cycles(self, k=None, i=None, g=None):
        result = super().list_cycles(k, i, g)
        if result is None: raise cp_api_404()
        return result

    def groups_cycle(self, k=None):
        return super().groups_cycle(k)

    def run(self, k=None, i=None, u=None, a=None, kw=None, p=None, w=0):
        if w:
            try:
                _w = float(w)
            except:
                raise cp_bad_request('w is not a number')
        else:
            _w = None
        if p:
            try:
                _p = int(p)
            except:
                raise cp_bad_request('p is not an integer')
        else:
            _p = None
        a = super().run(
            k=k, i=i, args=a, kwargs=kw, priority=_p, wait=_w, uuid=u)
        if not a:
            raise cp_api_404()
        return a

    @cp_need_master
    def append_controller(self,
                          k=None,
                          u=None,
                          a=None,
                          x=None,
                          g=None,
                          m=None,
                          s=None,
                          t=None,
                          save=None):
        sv = eva.tools.val_to_boolean(s)
        result = super().append_controller(k, u, a, x, g, m, sv, t, save)
        return result if result else http_api_result_error()

    @cp_need_master
    def enable_controller(self, k=None, i=None):
        result = super().enable_controller(k, i)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @cp_need_master
    def disable_controller(self, k=None, i=None):
        result = super().disable_controller(k, i)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @cp_need_master
    def remove_controller(self, k=None, i=None):
        result = super().remove_controller(k, i)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @cp_need_master
    def list_controller_props(self, k=None, i=None):
        result = super().list_controller_props(k, i)
        if result is None: raise cp_api_404()
        return result

    @cp_need_master
    def get_controller(self, k=None, i=None):
        result = super().get_controller(k, i)
        if result is None:
            raise cp_api_404()
        return result

    @cp_need_master
    def test_controller(self, k=None, i=None):
        result = super().test_controller(k, i)
        if result is None:
            raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @cp_need_master
    def matest_controller(self, k=None, i=None):
        result = super().matest_controller(k, i)
        if result is None:
            raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @cp_need_master
    def set_controller_prop(self, k=None, i=None, p=None, v=None, save=None):
        if save:
            _save = True
        else:
            _save = False
        result = super().set_controller_prop(k, i, p, v, _save)
        if result is None:
            raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @cp_need_master
    def reload_controller(self, k=None, i=None):
        result = super().reload_controller(k, i)
        if result is None:
            raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @cp_need_master
    def reload_clients(self, k=None):
        return http_api_result_ok() if super().reload_clients(k) \
                else http_api_result_error()

    @cp_need_master
    def notify_restart(self, k=None):
        return http_api_result_ok() if super().notify_restart(k) \
                else http_api_result_error()

    @cp_need_master
    def list_remote(self, k=None, i=None, g=None, p=None):
        result = super().list_remote(k, i, g, p)
        if result is None: raise cp_api_404()
        return result

    def list_rule_props(self, k=None, i=None):
        result = super().list_rule_props(k, i)
        if not result: raise cp_api_404()
        return result

    def set_rule_prop(self, k=None, i=None, p=None, v=None, save=None):
        if save:
            _save = True
        else:
            _save = False
        result = super().set_rule_prop(k, i, p, v, _save)
        if result:
            return result
        else:
            return http_api_result_error()


class SFA_HTTP_API(SFA_HTTP_API_abstract, GenericHTTP_API):

    def __init__(self):
        super().__init__()
        self.expose_api_methods('sfapi')
        if eva.sfa.controller.cloud_manager:
            self._expose(self.management_api_call)


class SFA_JSONRPC_API(eva.sysapi.SysHTTP_API_abstract,
                      eva.sysapi.SysHTTP_API_REST_abstract,
                      eva.api.JSON_RPC_API_abstract, SFA_HTTP_API):

    def __init__(self):
        super().__init__()
        self.expose_api_methods('sfapi', set_api_uri=False)
        if eva.sfa.controller.cloud_manager:
            self._expose(self.management_api_call)


class SFA_REST_API(eva.sysapi.SysHTTP_API_abstract,
                   eva.sysapi.SysHTTP_API_REST_abstract,
                   eva.api.GenericHTTP_API_REST_abstract, SFA_HTTP_API_abstract,
                   GenericHTTP_API):

    @generic_web_api_method
    @restful_api_method
    def GET(self, rtp, k, ii, full, kind, save, for_dir, props):
        try:
            return super().GET(rtp, k, ii, full, save, kind, for_dir, props)
        except MethodNotFound:
            pass
        if rtp == 'action':
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
                    return self.list_controllers(k=k, g=ii)
        elif rtp == 'dmatrix_rule':
            if kind == 'props':
                return self.list_rule_props(k=k, i=ii)
        elif rtp == 'lcycle':
            if kind == 'groups':
                return self.groups_cycle(k=k)
            else:
                return self.list_cycles(k=k, g=ii, i=props.get('controller_id'))
        elif rtp == 'lmacro':
            if kind == 'groups':
                return self.groups_macro(k=k)
            else:
                return self.list_macros(k=k, g=ii, i=props.get('controller_id'))
        elif rtp in ['unit', 'sensor', 'lvar']:
            if kind == 'groups':
                return self.groups(k=k, p=rtp, g=ii)
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
            elif for_dir:
                return self.state(k=k, g=ii, p=rtp, full=full)
            else:
                return self.state(k=k, i=ii, p=rtp, full=full)
        raise MethodNotFound

    @generic_web_api_method
    @restful_api_method
    def POST(self, rtp, k, ii, full, kind, save, for_dir, props):
        try:
            return super().POST(rtp, k, ii, full, save, kind, for_dir, props)
        except MethodNotFound:
            pass
        if rtp == 'action':
            result = None
            if 'm' in props:
                result = self.run(
                    k=k,
                    i=props['m'],
                    a=props.get('a'),
                    kw=props.get('kw'),
                    p=props.get('p'),
                    w=props.get('w', 0))
            else:
                s = props.get('s')
                if s == 'toggle':
                    result = self.action_toggle(
                        k=k,
                        i=props.get('i'),
                        p=props.get('p'),
                        q=props.get('q'),
                        w=props.get('w', 0))
                else:
                    result = self.action(
                        k=k,
                        i=props.get('i'),
                        s=props.get('s'),
                        v=props.get('v'),
                        p=props.get('p'),
                        q=props.get('q'),
                        w=props.get('w', 0))
            if result and 'uuid' in result:
                set_response_location('{}/{}/{}'.format(self.api_uri, rtp,
                                                        result['uuid']))
                return result
        elif rtp == 'controller':
            if (not ii or for_dir or ii.find('/') == -1) and 'cmd' not in props:
                result = self.append_controller(
                    k=k,
                    u=props.get('u'),
                    a=props.get('a'),
                    x=props.get('x'),
                    g=props.get('g', ii),
                    m=props.get('m'),
                    s=props.get('s'),
                    t=props.get('t'),
                    save=save)
                if 'full_id' in result:
                    set_response_location('{}/{}/{}'.format(
                        self.api_uri, rtp, result['full_id']))
                return result
            elif ii and 'cmd' not in props and 'f' in props:
                return self.management_api_call(
                    k=k, i=ii, f=props['f'], p=props.get('p'))
            cmd = props.get('cmd')
            if cmd == 'test':
                return self.test_controller(k=k, i=ii)
            elif cmd == 'matest':
                return self.matest_controller(k=k, i=ii)
            elif cmd == 'reload':
                return self.reload_controller(k=k, i=ii if ii else 'ALL')
        elif rtp == 'core':
            cmd = props.get('cmd')
            if cmd == 'notify_restart':
                return self.notify_restart(k=k)
            elif cmd == 'reload_clients':
                return self.reload_clients(k=k)
        raise MethodNotFound

    @generic_web_api_method
    @restful_api_method
    def PUT(self, rtp, k, ii, full, kind, save, for_dir, props):
        try:
            return super().PUT(rtp, k, ii, full, save, kind, for_dir, props)
        except MethodNotFound:
            pass
        if rtp == 'action':
            if 'm' in props:
                return self.run(
                    k=k,
                    i=props['m'],
                    u=ii,
                    a=props.get('a'),
                    kw=props.get('kw'),
                    p=props.get('p'),
                    w=props.get('w', 0))
            s = props.get('s')
            if s == 'toggle':
                return self.action_toggle(
                    k=k,
                    i=props.get('i'),
                    u=ii,
                    p=props.get('p'),
                    q=props.get('q'),
                    w=props.get('w', 0))
            else:
                return self.action(
                    k=k,
                    i=props.get('i'),
                    u=ii,
                    s=props.get('s'),
                    v=props.get('v'),
                    p=props.get('p'),
                    q=props.get('q'),
                    w=props.get('w', 0))
        raise MethodNotFound

    @generic_web_api_method
    @restful_api_method
    def PATCH(self, rtp, k, ii, full, kind, save, for_dir, props):
        try:
            return super().PATCH(rtp, k, ii, full, save, kind, for_dir, props)
        except MethodNotFound:
            pass
        if rtp == 'action':
            s = props.get('s')
            if 'i' in props:
                if s == 'kill':
                    return self.kill(k=k, i=props.get('i'))
                elif s == 'q_clean':
                    return self.q_clean(k=k, i=props.get('i'))
            elif s == 'term':
                return self.terminate(k=k, i=props.get('i'), u=ii)
        elif rtp == 'controller':
            if not ii: raise cp_api_404()
            for p, v in props.items():
                if self.set_controller_prop(
                        k=k, i=ii, p=p, v=v, save=save).get('result') != 'OK':
                    return http_api_result_error()
            return http_api_result_ok()
        elif rtp == 'dmatrix_rule':
            if not ii: raise cp_api_404()
            for p, v in props.items():
                if self.set_rule_prop(
                        k=k, i=ii, p=p, v=v, save=save).get('result') != 'OK':
                    return http_api_result_error()
            return http_api_result_ok()
        elif rtp == 'lvar':
            s = props.get('s')
            if s == 'clear':
                return self.clear(k=k, i=ii)
            elif s == 'reset':
                return self.reset(k=k, i=ii)
            elif s == 'toggle':
                return self.toggle(k=k, i=ii)
            else:
                return self.set(k=k, i=ii, s=s, v=props.get('v'))
        elif rtp == 'unit':
            if 'action_enabled' in props:
                v = eva.tools.val_to_boolean(props['action_enabled'])
                if v:
                    return self.enable_actions(k=k, i=ii)
                else:
                    return self.disable_actions(k=k, i=ii)
        raise MethodNotFound

    @generic_web_api_method
    @restful_api_method
    def DELETE(self, rtp, k, ii, full, kind, save, for_dir, props):
        try:
            return super().DELETE(rtp, k, ii, full, save, kind, for_dir, props)
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
        _k = cp_client_key()
    result = api.state(k=_k, i=i, group=g, tp=p)
    return result


def j2_groups(g=None, p=None, k=None):
    if k:
        _k = apikey.key_by_id(k)
    else:
        _k = cp_client_key()
    result = api.groups(k=_k, group=g, tp=p)
    return result


def serve_j2(tpl_file, tpl_dir=eva.core.dir_ui):
    j2_loader = jinja2.FileSystemLoader(searchpath=tpl_dir)
    j2 = jinja2.Environment(loader=j2_loader)
    try:
        template = j2.get_template(tpl_file)
    except:
        raise cp_api_404()
    env = {}
    env['request'] = cherrypy.serving.request.params
    k = cp_client_key()
    server_info = api.test(k)
    server_info['remote_ip'] = http_real_ip()
    env['server'] = server_info
    env.update(eva.core.cvars)
    template.globals['state'] = j2_state
    template.globals['groups'] = j2_groups
    return template.render(env).encode()


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
        _k = cp_client_key(k)
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
        _k = cp_client_key(k)
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
    cherrypy.tree.mount(
        http_api,
        http_api.api_uri)
    cherrypy.tree.mount(SFA_JSONRPC_API(), SFA_JSONRPC_API.api_uri)
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
            '/': {
                'tools.sessions.on': True,
                'tools.sessions.timeout': eva.api.config.session_timeout
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
            '/': {
                'tools.sessions.on': True,
                'tools.sessions.timeout': eva.api.config.session_timeout,
                'tools.staticdir.dir': eva.core.dir_eva + '/ui',
                'tools.staticdir.on': True
            }
        })
    eva.sfa.cloudmanager.start()


api = SFA_API()
