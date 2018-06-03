__author__ = "Altertech Group, http://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "See http://www.eva-ics.com/"
__version__ = "3.0.2"

import cherrypy
import os
import glob
import logging
from cherrypy.lib.static import serve_file
from eva.tools import format_json
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
from eva.api import session_timeout
from eva.api import http_real_ip
from eva import apikey
import eva.sfa.controller

from PIL import Image


def cp_need_dm_rules_list(k):
    if not eva.apikey.check(k, allow=['dm_rules_list']):
        raise cp_forbidden_key()


def cp_need_dm_rule_props(k):
    if not eva.apikey.check(k, allow=['dm_rule_props']):
        raise cp_forbidden_key()


class SFA_API(GenericAPI):

    def state(self, k=None, i=None, group=None, tp=None):
        if not tp: return None
        if tp == 'U' or tp == 'unit':
            gi = eva.sfa.controller.uc_pool.units
        elif tp == 'S' or tp == 'sensor':
            gi = eva.sfa.controller.uc_pool.sensors
        elif tp == 'LV' or tp == 'lvar':
            gi = eva.sfa.controller.lm_pool.lvars
        else:
            return None
        if i:
            if i in gi and apikey.check(k, gi[i]):
                return gi[i].serialize()
            else:
                return None
        result = []
        for i, v in gi.copy().items():
            if apikey.check(k, v) and \
                    (not group or \
                        eva.item.item_match(v, [], [group])):
                r = v.serialize()
                result.append(r)
        return sorted(result, key=lambda k: k['id'])

    def groups(self, k=None, tp=None):
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
            if apikey.check(k, v) and v.group not in result:
                result.append(v.group)
        return sorted(result)

    def action(self,
               k=None,
               i=None,
               action_uuid=None,
               nstatus=None,
               nvalue='',
               priority=None,
               wait=0):
        unit = eva.sfa.controller.uc_pool.get_unit(i)
        if not unit or not apikey.check(k, unit): return None
        return eva.sfa.controller.uc_pool.action(
            unit_id=i,
            status=nstatus,
            value=nvalue,
            wait=wait,
            uuid=action_uuid,
            priority=priority)

    def disable_actions(self, k=None, i=None):
        unit = eva.sfa.controller.uc_pool.get_unit(i)
        if not unit or not apikey.check(k, unit): return None
        return eva.sfa.controller.uc_pool.disable_actions(unit_id=i)

    def enable_actions(self, k=None, i=None):
        unit = eva.sfa.controller.uc_pool.get_unit(i)
        if not unit or not apikey.check(k, unit): return None
        return eva.sfa.controller.uc_pool.enable_actions(unit_id=i)

    def terminate(self, k=None, i=None):
        unit = eva.sfa.controller.uc_pool.get_unit(i)
        if not unit or not apikey.check(k, unit): return None
        return eva.sfa.controller.uc_pool.terminate(unit_id=i)

    def kill(self, k=None, i=None):
        unit = eva.sfa.controller.uc_pool.get_unit(i)
        if not unit or not apikey.check(k, unit): return None
        return eva.sfa.controller.uc_pool.kill(unit_id=i)

    def q_clean(self, k=None, i=None):
        unit = eva.sfa.controller.uc_pool.get_unit(i)
        if not unit or not apikey.check(k, unit): return None
        return eva.sfa.controller.uc_pool.q_clean(unit_id=i)

    def set(self, k=None, i=None, status=None, value=None):
        lvar = eva.sfa.controller.lm_pool.get_lvar(i)
        if not lvar or not apikey.check(k, lvar): return None
        return eva.sfa.controller.lm_pool.set(
            lvar_id=i, status=status, value=value)

    def reset(self, k=None, i=None):
        return self.set(k, i, 1, "1")

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

    def run(self, k=None, i=None, args=None, priority=None, wait=0, uuid=None):
        macro = eva.sfa.controller.lm_pool.get_macro(i)
        if not macro or not eva.apikey.check(k, macro): return False
        return eva.sfa.controller.lm_pool.run(
            macro=i, args=args, priority=priority, wait=wait, uuid=uuid)

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
                mqtt_update=mqtt_update,
                ssl_verify=ssl_verify,
                timeout=timeout,
                save=save)
            if group is not None and not result:
                return result
            elif result:
                return result
        if group == 'lm' or group is None:
            return eva.sfa.controller.append_lm(
                uri=uri,
                key=key,
                mqtt_update=mqtt_update,
                ssl_verify=ssl_verify,
                timeout=timeout,
                save=save)
            if group is not None and not result:
                return result
            elif result:
                return result
        return False

    def remove_controller(self, k=None, controller_id=None):
        if not apikey.check(k, master=True) or not controller_id:
            return False
        if not controller_id or controller_id.find('/') == -1: return False
        try:
            ct, ci = controller_id.split('/')
        except:
            return False
        if ct == 'uc':
            return eva.sfa.controller.remove_uc(ci)
        if ct == 'lm':
            return eva.sfa.controller.remove_lm(ci)
        return False

    def list_controller_props(self, k=None, i=None):
        if not apikey.check(k, master=True): return None
        item = eva.sfa.controller.get_controller(i)
        return item.serialize(props=True) if item else None

    def set_controller_prop(self, k=None, i=None, p=None, v=None, save=False):
        if not apikey.check(k, master=True): return None
        controller = eva.sfa.controller.get_controller(i)
        if controller:
            result = controller.set_prop(p, v, save)
            if result and controller.config_changed and save:
                controller.save()
            return result
        else:
            return None

    def reload_controller(self, k=None, i=None):
        if not apikey.check(k, master=True): return False
        if not i or i.find('/') == -1: return False
        try:
            ct, ci = i.split('/')
        except:
            return False
        if ct == 'uc':
            return eva.sfa.controller.uc_pool.reload_controller(ci)
        if ct == 'lm':
            return eva.sfa.controller.lm_pool.reload_controller(ci)
        return False

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
            # result[c_fid] = {}
            if items_uc:
                for x in items_uc:
                    for a, v in x.copy().items():
                        if not group or eva.item.item_match(v, [], [group]):
                            result.append(v.serialize())
            if items_lm:
                for x in items_lm:
                    for a, v in x.copy().items():
                        if not group or eva.item.item_match(v, [], [group]):
                            result.append(v.serialize())
        else:
            for x in items_uc:
                for c, d in x.copy().items():
                    for a, v in d.copy().items():
                        if not group or eva.item.item_match(v, [], [group]):
                            result.append(v.serialize())
            for x in items_lm:
                for c, d in x.copy().items():
                    for a, v in d.copy().items():
                        if not group or eva.item.item_match(v, [], [group]):
                            result.append(v.serialize())
        return result

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
        if not rule: return None
        if p[:9] == 'in_range_' or p in ['enabled', 'chillout_time']:
            if not apikey.check(k, allow = [ 'dm_rule_props' ]) and \
                    not apikey.check(k, rule):
                return None
        else:
            if not apikey.check(k, master=True): return None
        return eva.sfa.controller.lm_pool.set_rule_prop(i, p, v, save)


class SFA_HTTP_API(GenericHTTP_API, SFA_API):

    def __init__(self):
        super().__init__()
        SFA_HTTP_API.state.exposed = True
        SFA_HTTP_API.state_all.exposed = True
        SFA_HTTP_API.groups.exposed = True
        SFA_HTTP_API.action.exposed = True
        SFA_HTTP_API.terminate.exposed = True
        SFA_HTTP_API.kill.exposed = True
        SFA_HTTP_API.q_clean.exposed = True
        SFA_HTTP_API.disable_actions.exposed = True
        SFA_HTTP_API.enable_actions.exposed = True

        SFA_HTTP_API.set.exposed = True
        SFA_HTTP_API.reset.exposed = True

        SFA_HTTP_API.list_macros.exposed = True
        SFA_HTTP_API.groups_macro.exposed = True
        SFA_HTTP_API.run.exposed = True

        SFA_HTTP_API.list_controllers.exposed = True
        SFA_HTTP_API.append_controller.exposed = True
        SFA_HTTP_API.remove_controller.exposed = True
        SFA_HTTP_API.list_controller_props.exposed = True
        SFA_HTTP_API.set_controller_prop.exposed = True
        SFA_HTTP_API.reload_controller.exposed = True

        SFA_HTTP_API.list_remote.exposed = True

        SFA_HTTP_API.list_rule_props.exposed = True
        SFA_HTTP_API.set_rule_prop.exposed = True

    def state_all(self, k=None):
        result = []
        for p in ['U', 'S', 'LV']:
            try:
                result += self.state(k, p=p)
            except:
                pass
        return sorted(
            sorted(result, key=lambda k: k['id']), key=lambda k: k['type'])

    def state(self, k=None, i=None, g=None, p=None):
        result = super().state(k, i, g, p)
        if not result:
            raise cp_api_404()
        return result

    def groups(self, k=None, p=None):
        return super().groups(k, p)

    def list_controllers(self, k=None, g=None):
        cp_need_master(k)
        result = super().list_controllers(k, g)
        if not result: raise cp_api_404()
        return result

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
            k=k, i=i, action_uuid=u, nstatus=_s, nvalue=v, priority=_p, wait=_w)
        if not a:
            raise cp_api_404()
        return a

    def terminate(self, k=None, i=None):
        result = super().terminate(k, i)
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

    def list_macros(self, k=None, i=None, g=None):
        result = super().list_macros(k, i, g)
        if result is None: raise cp_api_404()
        return result

    def groups_macro(self, k=None):
        return super().groups_macro(k)

    def run(self, k=None, i=None, u=None, a=None, p=None, w=0):
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
        a = super().run(k=k, i=i, args=a, priority=_p, wait=_w, uuid=u)
        if not a:
            raise cp_api_404()
        return a

    def append_controller(self,
                          k=None,
                          u=None,
                          a=None,
                          g=None,
                          m=None,
                          s=None,
                          t=None,
                          save=None):
        cp_need_master(k)
        sv = eva.tools.val_to_boolean(s)
        return http_api_result_ok() if super().append_controller(
            k, u, a, g, m, sv, t, save) else http_api_result_error()

    def remove_controller(self, k=None, i=None):
        cp_need_master(k)
        return http_api_result_ok() if super().remove_controller(k, i) \
                else http_api_result_error()

    def list_controller_props(self, k=None, i=None):
        cp_need_master(k)
        result = super().list_controller_props(k, i)
        if not result: raise cp_api_404()
        return result

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


class SFA_HTTP_Root:

    @cherrypy.expose
    def index(self, **kwargs):
        q = cherrypy.request.query_string
        if q: q = '?' + q
        raise cherrypy.HTTPRedirect('/ui/' + q)

    def _no_cache(self):
        cherrypy.response.headers['Expires'] = 'Sun, 19 Nov 1978 05:00:00 GMT'
        cherrypy.response.headers['Cache-Control'] = \
            'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
        cherrypy.response.headers['Pragma'] = 'no-cache'

    @cherrypy.expose
    def pvt(self, k=None, f=None, c=None, ic=None, nocache=None):
        if k is None:
            _k = cherrypy.session.get('k')
            if _k is None: _k = eva.apikey.key_by_ip_address(http_real_ip())
        else:
            _k = k
        _r = '%s@%s' % (apikey.key_id(k), http_real_ip())
        if f is None or f == '' or f.find('..') != -1 or f[0] == '/':
            raise cp_api_404()
        if not apikey.check(_k, pvt_file=f, ip=http_real_ip()):
            logging.warning('pvt %s file %s access forbidden' % (_r, f))
            raise cp_forbidden_key()
        _f = eva.core.dir_eva + '/pvt/' + f
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
                            'created': os.path.getctime(x),
                            'modified': os.path.getmtime(x)
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
    cherrypy.tree.mount(SFA_HTTP_API(), '/sfa-api')
    cherrypy.tree.mount(
        SFA_HTTP_Root(),
        '/',
        config={
            '/': {
                'tools.sessions.on': True,
                'tools.sessions.timeout': session_timeout
            },
            '/favicon.ico': {
                'tools.staticfile.on':
                True,
                'tools.staticfile.filename':
                eva.core.dir_eva + '/lib/eva/i/favicon.ico'
            }
        })

    cherrypy.tree.mount(
        object(),
        '/ui',
        config={
            '/': {
                'tools.staticdir.dir': eva.core.dir_eva + '/ui',
                'tools.staticdir.on': True,
                'tools.staticdir.index': 'index.html',
            }
        })
