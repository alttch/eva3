__author__ = "Altertech Group, http://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "See http://www.eva-ics.com/"
__version__ = "3.0.2"

import cherrypy
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
import eva.uc.controller


class UC_API(GenericAPI):

    def dev_uc_a(self, k=None):
        return eva.uc.controller.Q.actions_by_item_full_id

    def dev_uc_i(self, k=None, i=None):
        return eva.uc.controller.dump(i)

    def dev_uc_u(self, k=None, i=None):
        if i:
            return eva.uc.controller.get_unit(i)
        else:
            return eva.uc.controller.units_by_id

    def dev_uc_mu(self, k=None, i=None):
        if i:
            return eva.uc.controller.get_mu(i)
        else:
            return eva.uc.controller.mu_by_id

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
                m = eva.uc.controller.units_by_id
            elif tp == 'S' or tp == 'sensor':
                m = eva.uc.controller.sensors_by_id
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
            return item.serialize(full=full)
        elif tp:
            if tp == 'U' or tp == 'unit':
                gi = eva.uc.controller.units_by_id
            elif tp == 'S' or tp == 'sensor':
                gi = eva.uc.controller.sensors_by_id
            else:
                return None
            result = []
            for i, v in gi.copy().items():
                if apikey.check(k, v) and \
                        (not group or \
                            eva.item.item_match(v, [], [group])):
                    r = v.serialize(full=full)
                    result.append(r)
            return sorted(result, key=lambda k: k['id'])

    def update(self, k=None, i=None, status=None, value=None, force_virtual=0):
        item = eva.uc.controller.get_item(i)
        if not item or not apikey.check(k, item): return False
        return item.update_set_state(
            status=status, value=value, force_virtual=force_virtual)

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
                ar = None
                item = eva.uc.controller.get_item(item_id)
                if not apikey.check(k, item): return None
                if item_id.find('/') > -1:
                    if item_id in eva.uc.controller.Q.actions_by_item_full_id:
                        ar = eva.uc.controller.Q.actions_by_item_full_id[
                            item_id]
                else:
                    if item_id in eva.uc.controller.Q.actions_by_item_id:
                        ar = eva.uc.controller.Q.actions_by_item_id[item_id]
                if ar is None: return None
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
        return item.serialize(config=True) if item else None

    def save_config(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        item = eva.uc.controller.get_item(i)
        return item.save() if item else None

    def list(self, k=None, group=None, tp=None):
        if not apikey.check(k, master=True): return None
        result = []
        if tp == 'U' or tp == 'unit':
            items = eva.uc.controller.units_by_id
        elif tp == 'S' or tp == 'sensor':
            items = eva.uc.controller.sensors_by_id
        elif tp == 'MU' or tp == 'mu':
            items = eva.uc.controller.mu_by_id
        else:
            items = eva.uc.controller.items_by_id
        for i, v in items.copy().items():
            if not group or eva.item.item_match(v, [], [group]):
                result.append(v.serialize(info=True))
        return result

    def list_props(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        item = eva.uc.controller.get_item(i)
        return item.serialize(props=True) if item else None

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
            unit_id=unit_id, group=group, virtual=virtual, save=save)

    def create_sensor(self,
                      k=None,
                      sensor_id=None,
                      group=None,
                      virtual=False,
                      save=False):
        if not apikey.check(k, master=True): return None
        return eva.uc.controller.create_sensor(
            sensor_id=sensor_id, group=group, virtual=virtual, save=save)

    def create_mu(self,
                  k=None,
                  mu_id=None,
                  group=None,
                  virtual=False,
                  save=False):
        if not apikey.check(k, master=True): return None
        return eva.uc.controller.create_mu(
            mu_id=mu_id, group=group, virtual=virtual, save=save)

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


class UC_HTTP_API(GenericHTTP_API, UC_API):

    def __init__(self):
        super().__init__()
        if eva.core.development:
            UC_API.dev_uc_a.exposed = True
            UC_API.dev_uc_i.exposed = True
            UC_API.dev_uc_u.exposed = True
            UC_API.dev_uc_mu.exposed = True
        UC_HTTP_API.groups.exposed = True
        UC_HTTP_API.state.exposed = True
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

        UC_HTTP_API.create_unit.exposed = True
        UC_HTTP_API.create_sensor.exposed = True
        UC_HTTP_API.create_mu.exposed = True

        UC_HTTP_API.clone.exposed = True
        UC_HTTP_API.clone_group.exposed = True

        UC_HTTP_API.destroy.exposed = True

    def groups(self, k=None, p=None):
        return super().groups(k, p)

    def state(self, k=None, i=None, full=None, g=None, p=None):
        if full:
            _full = True
        else:
            _full = False
        result = super().state(k, i, _full, g, p)
        if result is None:
            raise cp_api_404()
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
        try:
            _s = int(s)
        except:
            raise cp_api_error('status is not an integer')
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
            nstatus=_s,
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

    def create_unit(self, k=None, i=None, g=None, virtual=None, save=None):
        cp_need_master(k)
        return http_api_result_ok() if super().create_unit(
            k, i, g, virtual, save) else http_api_result_error()

    def create_sensor(self, k=None, i=None, g=None, virtual=None, save=None):
        cp_need_master(k)
        return http_api_result_ok() if super().create_sensor(
            k, i, g, virtual, save) else http_api_result_error()

    def create_mu(self, k=None, i=None, g=None, virtual=None, save=None):
        cp_need_master(k)
        return http_api_result_ok() if super().create_mu(
            k, i, g, virtual, save) else http_api_result_error()

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


class UC_HTTP_Root:

    @cherrypy.expose
    def index(self):
        raise cherrypy.HTTPRedirect('/uc-ei/')


def start():
    cherrypy.tree.mount(UC_HTTP_API(), '/uc-api')
    cherrypy.tree.mount(
        UC_HTTP_Root(),
        '/',
        config={
            '/favicon.ico': {
                'tools.staticfile.on':
                True,
                'tools.staticfile.filename':
                eva.core.dir_eva + '/lib/eva/i/favicon.ico'
            }
        })

    cherrypy.tree.mount(
        object(),
        '/uc-ei',
        config={
            '/': {
                'tools.staticdir.dir': eva.core.dir_eva + '/uc-ei',
                'tools.staticdir.on': True,
                'tools.staticdir.index': 'index.html',
            }
        })
