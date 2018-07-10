__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "3.1.0"

import cherrypy
import jsonpickle
import eva.core
from eva.api import GenericHTTP_API
from eva.api import GenericAPI
from eva.api import cp_json_handler
from eva.api import cp_forbidden_key
from eva.api import http_api_result_ok
from eva.api import http_api_result_error
from eva.api import cp_api_error
from eva.api import cp_api_404
from eva.api import cp_need_master
from eva import apikey
import eva.lm.controller
import eva.lm.extapi
import eva.ei

api = None


def cp_need_dm_rules_list(k):
    if not eva.apikey.check(k, allow=['dm_rules_list']):
        raise cp_forbidden_key()


def cp_need_dm_rule_props(k):
    if not eva.apikey.check(k, allow=['dm_rule_props']):
        raise cp_forbidden_key()


class LM_API(GenericAPI):

    def dev_lm_i(self, k=None, i=None):
        return eva.lm.controller.dump(i)

    def groups(self, k=None, tp=None):
        if apikey.check(k, master=True):
            if tp == 'LV' or tp == 'lvar':
                return sorted(eva.lm.controller.lvars_by_group.keys())
            else:
                return []
        else:
            groups = []
            m = None
            if tp == 'LV' or tp == 'lvar':
                m = eva.lm.controller.lvars_by_id
            if m:
                for i, v in m.copy().items():
                    if apikey.check(k, v) and not v.group in groups:
                        groups.append(v.group)
                return sorted(groups)
            else:
                return []

    def state(self, k=None, i=None, full=False, group=None, tp='LV'):
        if tp not in ['LV', 'lvar']: return None
        if i:
            item = eva.lm.controller.get_lvar(i)
            if not item or not apikey.check(k, item): return None
            return item.serialize(full=full)
        else:
            gi = eva.lm.controller.lvars_by_id
            result = []
            for i, v in gi.copy().items():
                if apikey.check(k, v) and \
                        (not group or \
                            eva.item.item_match(v, [], [group])):
                    r = v.serialize(full=full)
                    result.append(r)
            return sorted(result, key=lambda k: k['id'])

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
        item = eva.lm.controller.get_lvar(i)
        if not item or not apikey.check(k, item): return False
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

    def set(self, k=None, i=None, status=None, value=None):
        item = eva.lm.controller.get_lvar(i)
        if not item or not apikey.check(k, item): return None
        if status and not -1 <= status <= 1: return False
        if value is None: v = 'null'
        else: v = value
        return item.update_set_state(status=status, value=v)

    def reset(self, k=None, i=None):
        return self.set(k, i, 1, '1')

    def clear(self, k=None, i=None):
        item = eva.lm.controller.get_lvar(i)
        if not item or not apikey.check(k, item): return None
        return self.set(k, i, 0 if item.expires > 0 else 1, '0')

    def toggle(self, k=None, i=None):
        item = eva.lm.controller.get_lvar(i)
        if not item or not apikey.check(k, item): return None
        v = item.value
        if v != '0':
            return self.clear(k, i)
        else:
            return self.reset(k, i)

    def run(self,
            k=None,
            i=None,
            args=None,
            priority=None,
            q_timeout=None,
            wait=0,
            uuid=None):
        macro = eva.lm.controller.get_macro(i)
        if not macro or not eva.apikey.check(k, macro): return False
        if args is None:
            ar = []
        else:
            if isinstance(args, list):
                ar = args
            else:
                ar = args.split(' ')
        return eva.lm.controller.exec_macro(
            macro=macro,
            argv=ar,
            priority=priority,
            q_timeout=q_timeout,
            wait=wait,
            action_uuid=uuid)

    def result(self, k=None, uuid=None, item_id=None, group=None, state=None):
        if uuid:
            a = eva.lm.controller.Q.history_get(uuid)
            if not a or not apikey.check(k, a.item): return None
            return a
        else:
            result = []
            if item_id:
                ar = None
                item = eva.lm.controller.get_item(item_id)
                if not apikey.check(k, item): return None
                if item_id.find('/') > -1:
                    if item_id in eva.lm.controller.Q.actions_by_item_full_id:
                        ar = eva.lm.controller.Q.actions_by_item_full_id[
                            item_id]
                else:
                    if item_id in eva.lm.controller.Q.actions_by_item_id:
                        ar = eva.lm.controller.Q.actions_by_item_id[item_id]
                if ar is None: return None
            else:
                ar = eva.lm.controller.Q.actions
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

# dm rules functions

    def _set_rule_prop_batch(self, k, i, data, save):
        rule = eva.lm.controller.get_dm_rule(i)
        if not rule: return False
        enable_after = rule.enabled
        if not self.set_rule_prop(k, i, 'enabled', False):
            return False
        for x, y in data.items():
            if not self.set_rule_prop(k, i, x, y):
                return False
        if not self.set_rule_prop(k, i, 'enabled', enable_after):
            return False
        if save: rule.save()
        return True

    def list_rule_props(self, k=None, i=None):
        item = eva.lm.controller.get_dm_rule(i)
        if not item:
            return None
        if not apikey.check(k, allow = [ 'dm_rule_props' ]) and \
                not apikey.check(k, item):
            return None
        result = item.serialize(props=True)
        if not apikey.check(k, master=True):
            for i in result.copy():
                if i[:9] != 'in_range_' and \
                        i not in [ 'enabled', 'chillout_time', 'condition' ]:
                    del result[i]
        return result

    def set_rule_prop(self, k=None, i=None, p=None, v=None, save=False):
        item = eva.lm.controller.get_dm_rule(i)
        if not item: return None
        if p[:9] == 'in_range_' or p in ['enabled', 'chillout_time']:
            if not apikey.check(k, allow = [ 'dm_rule_props' ]) and \
                    not apikey.check(k, item):
                return None
        else:
            if not apikey.check(k, master=True): return None
        result = item.set_prop(p, v, save)
        if result and item.config_changed and save:
            item.save()
        if p in ['priority', 'description']:
            eva.lm.controller.DM.sort()
        return result

    def list_rules(self, k=None):
        rmas = apikey.check(k, allow=['dm_rules_list'])
        result = []
        for i in eva.lm.controller.DM.rules.copy():
            if rmas or apikey.check(k, i):
                d = i.serialize(info=True)
                if not apikey.check(k, master=True):
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


# master functions for item configuration

    def create_rule(self, k=None, save=False):
        if not apikey.check(k, master=True): return None
        return eva.lm.controller.create_dm_rule(save)

    def destroy_rule(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        return eva.lm.controller.destroy_dm_rule(i)

    def groups_macro(self, k=None):
        result = []
        for i, v in eva.lm.controller.macros_by_id.copy().items():
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
            items = eva.lm.controller.lvars_by_id
        else:
            items = eva.lm.controller.items_by_id
        for i, v in items.copy().items():
            if not group or eva.item.item_match(v, [], [group]):
                result.append(v.serialize(info=True))
        return result

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
        return result

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
        if controller_id.find('/') > -1:
            c = controller_id.split('/')
            if len(c) > 2 or c[0] != 'uc': return None
            _i = c[1]
        else:
            _i = controller_id
        return eva.lm.controller.remove_controller(_i)

    def list_props(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        item = eva.lm.controller.get_item(i)
        return item.serialize(props=True) if item else None

    def list_macro_props(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        item = eva.lm.controller.get_macro(i)
        return item.serialize(props=True) if item else None

    def list_controller_props(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        item = eva.lm.controller.get_controller(i)
        return item.serialize(props=True) if item else None

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
        return eva.lm.controller.create_lvar(
            lvar_id=lvar_id, group=group, save=save)

    def destroy_lvar(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        return eva.lm.controller.destroy_item(i)

    # master functions for lmacro extension management

    def load_ext(self, k=None, i=None, m=None, cfg=None, save=False):
        if not apikey.check(k, master=True): return None
        if not i or not m: return None
        if isinstance(cfg, str):
            _cfg = {}
            props = cfg.split(',')
            for p in props:
                try:
                    name, value = p.split('=')
                    try:
                        value = float(value)
                        if value == int(value):
                            value = int(value)
                    except:
                        pass
                    _cfg[name] = value
                except:
                    eva.core.log_traceback()
                    return None
        else:
            _cfg = cfg
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
            return False

    def list_ext_mods(self, k=None):
        if not apikey.check(k, master=True): return None
        return eva.lm.extapi.list_mods()

    def modinfo_ext(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        return eva.lm.extapi.modinfo(i)

    def modhelp_ext(self, k=None, i=None, c=None):
        if not apikey.check(k, master=True): return None
        return eva.lm.extapi.modhelp(i, c)


class LM_HTTP_API(GenericHTTP_API, LM_API):

    def __init__(self):
        super().__init__()
        if eva.core.development:
            LM_API.dev_lm_i.exposed = True
        LM_HTTP_API.groups.exposed = True
        LM_HTTP_API.state.exposed = True
        LM_HTTP_API.state_history.exposed = True
        LM_HTTP_API.set.exposed = True
        LM_HTTP_API.reset.exposed = True
        LM_HTTP_API.clear.exposed = True
        LM_HTTP_API.toggle.exposed = True
        LM_HTTP_API.run.exposed = True
        LM_HTTP_API.result.exposed = True

        LM_HTTP_API.list_rules.exposed = True
        LM_HTTP_API.list_rule_props.exposed = True
        LM_HTTP_API.set_rule_prop.exposed = True
        LM_HTTP_API.create_rule.exposed = True
        LM_HTTP_API.destroy_rule.exposed = True

        LM_HTTP_API.groups_macro.exposed = True
        LM_HTTP_API.get_config.exposed = True
        LM_HTTP_API.save_config.exposed = True
        LM_HTTP_API.list.exposed = True
        LM_HTTP_API.list_remote.exposed = True
        LM_HTTP_API.list_controllers.exposed = True
        LM_HTTP_API.list_macros.exposed = True
        LM_HTTP_API.create_macro.exposed = True
        LM_HTTP_API.destroy_macro.exposed = True
        LM_HTTP_API.append_controller.exposed = True
        LM_HTTP_API.remove_controller.exposed = True

        LM_HTTP_API.list_props.exposed = True
        LM_HTTP_API.list_macro_props.exposed = True
        LM_HTTP_API.list_controller_props.exposed = True
        LM_HTTP_API.set_prop.exposed = True
        LM_HTTP_API.set_macro_prop.exposed = True
        LM_HTTP_API.set_controller_prop.exposed = True

        LM_HTTP_API.reload_controller.exposed = True

        LM_HTTP_API.create_lvar.exposed = True
        LM_HTTP_API.destroy_lvar.exposed = True

        LM_HTTP_API.load_ext.exposed = True
        LM_HTTP_API.unload_ext.exposed = True
        LM_HTTP_API.list_ext.exposed = True
        LM_HTTP_API.list_ext_mods.exposed = True
        LM_HTTP_API.get_ext.exposed = True
        LM_HTTP_API.modinfo_ext.exposed = True
        LM_HTTP_API.modhelp_ext.exposed = True

    def groups(self, k=None, p=None):
        return super().groups(k, p)

    def state(self, k=None, i=None, full=None, g=None, p='LV'):
        if full:
            _full = True
        else:
            _full = False
        result = super().state(k, i, _full, g, p)
        if result is None:
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
        if i and i.find(',') != -1:
            if not w:
                raise cp_api_error(
                    '"w" param required to process multiple items')
            items = i.split(',')
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

    def set(self, k=None, i=None, s=None, v=None):
        if s is None:
            _s = None
        else:
            try:
                _s = int(s)
            except:
                raise cp_api_error('status is not an integer')
        result = super().set(k, i, _s, v)
        if result is None:
            raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    def reset(self, k=None, i=None):
        if super().reset(k, i):
            return http_api_result_ok()
        else:
            raise cp_api_404()

    def clear(self, k=None, i=None):
        if super().clear(k, i):
            return http_api_result_ok()
        else:
            raise cp_api_404()

    def toggle(self, k=None, i=None):
        if super().toggle(k, i):
            return http_api_result_ok()
        else:
            raise cp_api_404()

    def run(self, k=None, i=None, u=None, a=None, p=None, q=None, w=0):
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
                raise cp_api_error('q_timeout is not an integer')
        else:
            _q = None
        a = super().run(
            k=k, i=i, args=a, priority=_p, q_timeout=_q, wait=_w, uuid=u)
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

    def list_rules(self, k=None):
        return super().list_rules(k)

    def list_rule_props(self, k=None, i=None):
        result = super().list_rule_props(k, i)
        if not result: raise cp_api_404()
        return result

    def set_rule_prop(self, k=None, i=None, p=None, v=None, save=None, _j=None):
        if save:
            _save = True
        else:
            _save = False
        if _j is None:
            return http_api_result_ok() if super().set_rule_prop(
                k, i, p, v, _save) else http_api_result_error()
        else:
            try:
                data = jsonpickle.decode(_j)
            except:
                raise cp_api_error('_j is no JSON')
            return http_api_result_ok() if \
                    self._set_rule_prop_batch(k, i, data, _save) \
                    else http_api_result_error()

    def create_rule(self, k=None, save=None, _j=None):
        cp_need_master(k)
        if save:
            _save = True
        else:
            _save = False
        if not _j:
            _save_ac = _save
        else:
            _save_ac = False
        rule_id = super().create_rule(k, _save_ac)
        if not rule_id: return http_api_result_error()
        if _j is None:
            return http_api_result_ok({'rule_id': rule_id})
        else:
            try:
                data = jsonpickle.decode(_j)
            except:
                raise cp_api_error('_j is no JSON')
            return http_api_result_ok() if \
                    self._set_rule_prop_batch(k, rule_id, data, _save) \
                    else http_api_result_error()

    def destroy_rule(self, k=None, i=None):
        cp_need_master(k)
        return http_api_result_ok() if super().destroy_rule(k, i) \
                else http_api_result_error()

    def groups_macro(self, k=None):
        return super().groups_macro(k)

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

    def list_remote(self, k=None, i=None, g=None, p=None):
        result = super().list_remote(k, i, g, p)
        if result is None: raise cp_api_404()
        return result

    def list_controllers(self, k=None):
        cp_need_master(k)
        result = super().list_controllers(k)
        if not result: raise cp_api_404()
        return result

    def list_macros(self, k=None, g=None):
        result = super().list_macros(k, g)
        if result is None: raise cp_api_404()
        return result

    def create_macro(self, k=None, i=None, g=None, save=None):
        cp_need_master(k)
        return http_api_result_ok() if super().create_macro(k, i, g, save) \
                else http_api_result_error()

    def destroy_macro(self, k=None, i=None):
        cp_need_master(k)
        return http_api_result_ok() if super().destroy_macro(k, i) \
                else http_api_result_error()

    def append_controller(self,
                          k=None,
                          u=None,
                          a=None,
                          m=None,
                          s=None,
                          t=None,
                          save=None):
        cp_need_master(k)
        sv = eva.tools.val_to_boolean(s)
        return http_api_result_ok() if super().append_controller(
            k, u, a, m, sv, t, save) else http_api_result_error()

    def remove_controller(self, k=None, i=None):
        cp_need_master(k)
        return http_api_result_ok() if super().remove_controller(k, i) \
                else http_api_result_error()

    def list_props(self, k=None, i=None):
        cp_need_master(k)
        result = super().list_props(k, i)
        if not result: raise cp_api_404()
        return result

    def list_macro_props(self, k=None, i=None):
        cp_need_master(k)
        result = super().list_macro_props(k, i)
        if not result: raise cp_api_404()
        return result

    def list_controller_props(self, k=None, i=None):
        cp_need_master(k)
        result = super().list_controller_props(k, i)
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

    def set_macro_prop(self, k=None, i=None, p=None, v=None, save=None):
        cp_need_master(k)
        if save:
            _save = True
        else:
            _save = False
        return http_api_result_ok() if super().set_macro_prop(
            k, i, p, v, _save) else http_api_result_error()

    def set_controller_prop(self, k=None, i=None, p=None, v=None, save=None):
        cp_need_master(k)
        if save:
            _save = True
        else:
            _save = False
        return http_api_result_ok() if \
                super().set_controller_prop(k, i, p, v, _save) \
                else http_api_result_error()

    def reload_controller(self, k=None, i=None):
        cp_need_master(k)
        return http_api_result_ok() if super().reload_controller(k, i) \
                else http_api_result_error()

    def create_lvar(self, k=None, i=None, g=None, save=None):
        cp_need_master(k)
        return http_api_result_ok() if super().create_lvar(
            k, i, g, save) else http_api_result_error()

    def destroy_lvar(self, k=None, i=None):
        cp_need_master(k)
        return http_api_result_ok() if super().destroy_lvar(k, i) \
                else http_api_result_error()

    def load_ext(self, k=None, i=None, m=None, c=None, save=False):
        cp_need_master(k)
        result = super().load_ext(k, i, m, c, save)
        return result if result else http_api_result_error()

    def unload_ext(self, k=None, i=None):
        cp_need_master(k)
        return http_api_result_ok() if super().unload_ext(k, i) \
                else http_api_result_error()

    def list_ext(self, k=None, full=None):
        cp_need_master(k)
        result = super().list_ext(k, full)
        if result is None: raise cp_api_error()
        return result

    def list_ext_mods(self, k=None):
        cp_need_master(k)
        return super().list_ext_mods(k)

    def get_ext(self, k=None, i=None):
        cp_need_master(k)
        result = super().get_ext(k, i)
        if result is None: raise cp_api_error()
        if result is False: raise cp_api_404()
        return result

    def modinfo_ext(self, k=None, i=None):
        cp_need_master(k)
        result = super().modinfo_ext(k, i)
        if not result:
            raise cp_api_error()
        else:
            return result

    def modhelp_ext(self, k=None, i=None, c=None):
        cp_need_master(k)
        result = super().modhelp_ext(k, i, c)
        if result is None:
            raise cp_api_error()
        else:
            return result

def start():
    global api
    api = LM_API()
    cherrypy.tree.mount(LM_HTTP_API(), '/lm-api')
    eva.ei.start()
