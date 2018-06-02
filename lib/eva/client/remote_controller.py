__author__ = "Altertech Group, http://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "See http://www.eva-ics.com/"
__version__ = "3.0.2"

import eva.core
import eva.item
import eva.tools
import eva.apikey
import eva.client.apiclient
import eva.client.remote_item
import logging
import time
import threading

_warning_time_diff = 1


class RemoteController(eva.item.Item):

    def __init__(self, item_id, item_type, api=None, mqtt_update=None):
        if item_id == None:
            item_id = ''
        super().__init__(item_id, item_type)
        if api:
            self.api = api
            self._key = api._key
        else:
            self.api = eva.client.apiclient.APIClient()
            self.api.set_timeout(eva.core.timeout)
            self._key = None
        self.product_build = None
        self.controller_type = None
        self.version = None
        self.pool = None
        self.mqtt_update = mqtt_update
        self.reload_interval = 10

    def api_call(self, func, params=None, timeout=None):
        if not self.api: return None
        (code, result) = self.api.call(func, params, timeout)
        if code == eva.client.apiclient.result_forbidden:
            logging.error('Remote controller access forbidden %s' % \
                    self.api._uri)
            return None
        elif code != eva.client.apiclient.result_ok and \
                code != eva.client.apiclient.result_func_failed:
            logging.error('Remote controller access error %s, code %u' % \
                    (self.api._uri, code))
            return None
        return result

    def load_remote(self):
        result = self.api_call('test')
        if not result: return False
        if result['result'] != 'OK':
            logging.error('Remote controller unknown access error %s' % \
                    api._uri)
            return False
        time_diff = abs(time.time() - float(result['time']))
        if eva.core.version != result['version']:
            logging.error('Remote controller EVA version is %s, my: %s' % \
                    (result['version'], eva.core.version))
            return False
        self.item_id = result['system']
        self.config_changed = True
        self.set_group(result['product_code'])
        self.product_build = result['product_build']
        logging.info('controller %s loaded' % self.item_id)
        self.version = result['version']
        msg = '%s time diff is %f sec' % (self.item_id, time_diff)
        if time_diff > _warning_time_diff:
            logging.warning(msg)
        else:
            logging.info(msg)
        return True

    def update_config(self, data):
        if 'uri' in data:
            self.api.set_uri(data['uri'])
        if 'key' in data:
            self.api.set_key(eva.apikey.format_key(data['key']))
            self._key = data['key']
        if 'timeout' in data:
            self.api.set_timeout(data['timeout'])
        if 'ssl_verify' in data:
            self.api.ssl_verify(data['ssl_verify'])
        if 'mqtt_update' in data:
            self.mqtt_update = data['mqtt_update']
        if 'reload_interval' in data:
            self.reload_interval = data['reload_interval']
        super().update_config(data)

    def set_prop(self, prop, val=None, save=False):
        if prop == 'uri' and val:
            if self.api._uri != val:
                self.api.set_uri(val)
                self.log_set(prop, val)
                self.set_modified(save)
            return True
        elif prop == 'key':
            if self._key != val:
                self._key = val
                self.api.set_key(eva.apikey.format_key(val))
                self.log_set(prop, '*****')
                self.set_modified(save)
            return True
        elif prop == 'timeout':
            if val is not None:
                try:
                    self.api.set_timeout(int(val))
                    self.log_set(prop, val)
                    self.set_modified(save)
                    return True
                except:
                    return False
            else:
                self.api.set_timeout(eva.core.timeout)
                self.set_modified(save)
                return True
        elif prop == 'ssl_verify':
            if val is not None:
                try:
                    v = eva.tools.val_to_boolean(val)
                    if v is None: return False
                    if self.api._ssl_verify != v:
                        self.api.ssl_verify(v)
                        self.log_set(prop, v)
                        self.set_modified(save)
                    return True
                except:
                    return False
            else:
                self.api.ssl_verify(True)
                self.set_modified(save)
                return True
        elif prop == 'mqtt_update':
            if self.mqtt_update != val:
                self.mqtt_update = val
                if self.pool:
                    self.pool.remove(self.item_id)
                    self.pool.append(self)
                self.log_set(prop, val)
                self.set_modified(save)
            return True
        elif prop == 'reload_interval':
            try:
                v = float(val)
                if self.reload_interval != v:
                    self.reload_interval = v
                    self.log_set(prop, v)
                    self.set_modified(save)
                return True
            except:
                return False
        return super().set_prop(prop, val, save)

    def serialize(self,
                  full=False,
                  config=False,
                  info=False,
                  props=False,
                  notify=False):
        if not self.item_id: return None
        d = {}
        if config or props:
            d['uri'] = self.api._uri
            if self._key is not None: d['key'] = self._key
            d['timeout'] = self.api._timeout
            d['ssl_verify'] = self.api._ssl_verify
            d['mqtt_update'] = self.mqtt_update
            d['reload_interval'] = self.reload_interval
        d.update(super().serialize(
            full=full, config=config, info=info, props=props, notify=notify))
        return d

    def destroy(self):
        super().destroy()
        if self.pool:
            self.pool.remove(self.item_id)


class RemoteUC(RemoteController):

    def __init__(self, uc_id=None, api=None, mqtt_update=None):
        super().__init__(uc_id, 'remote_uc', api, mqtt_update)
        self.controller_type = 'uc'
        self.api.set_product('uc')

    def create_remote_unit(self, state):
        return eva.client.remote_item.RemoteUnit(self, state)

    def create_remote_sensor(self, state):
        return eva.client.remote_item.RemoteSensor(self, state)

    def load_units(self):
        if not self.item_id: return None
        states = self.api_call('state', {'p': 'U'})
        result = []
        if states is not None:
            for s in states:
                u = self.create_remote_unit(s)
                result.append(u)
            return result
        else:
            return None

    def load_sensors(self):
        if not self.item_id: return None
        states = self.api_call('state', {'p': 'S'})
        result = []
        if states is not None:
            for s in states:
                u = self.create_remote_sensor(s)
                result.append(u)
            return result
        else:
            return None


class RemoteLM(RemoteController):

    def __init__(self, lm_id=None, api=None, mqtt_update=None):
        super().__init__(lm_id, 'remote_lm', api, mqtt_update)
        self.controller_type = 'lm'
        self.api.set_product('lm')

    def create_remote_lvar(self, state):
        return eva.client.remote_item.RemoteLVar(self, state)

    def create_remote_macro(self, mcfg):
        m = eva.client.remote_item.RemoteMacro(mcfg['id'], self)
        m.update_config(mcfg)
        return m

    def load_lvars(self):
        if not self.item_id: return None
        states = self.api_call('state')
        result = []
        if states is not None:
            for s in states:
                u = self.create_remote_lvar(s)
                result.append(u)
            return result
        else:
            return None

    def load_macros(self, skip_system=False):
        if not self.item_id: return None
        macros = self.api_call('list_macros')
        result = []
        if macros:
            for m in macros:
                if 'id' in m and (not skip_system or \
                        ('group' in m and \
                            m['group'] != 'system' and \
                            m['group'][:7] != 'system/')):
                    i = self.create_remote_macro(m)
                    result.append(i)
            return result
        else:
            return None

    def load_rules(self):
        if not self.item_id: return None
        rules = self.api_call('list_rules')
        result = []
        if rules:
            for r in rules:
                rule = eva.client.remote_item.RemoteDMRule(self, r['id'])
                result.append(rule)
            return result
        else:
            return None


class RemoteControllerPool(object):

    def __init__(self):
        self.controllers = {}
        self.reload_threads = {}
        self.reload_thread_flags = {}

    def cmd(self, controller_id, command, args=None, wait=None, timeout=None):
        if controller_id not in self.controllers: return None
        c = self.controllers[controller_id]
        p = {'c': command}
        _args = None
        if isinstance(args, str):
            _args = args
        elif isinstance(args, list):
            _args = ' '.join(args)
        if _args is not None: p['a'] = _args
        if wait is not None: p['w'] = wait
        if timeout is not None: p['t'] = timeout
        return c.api_call('cmd', p)

    def append(self, controller):
        if controller.load_remote() or controller.item_id != '':
            if controller.item_id in self.controllers: return False
            self.controllers[controller.item_id] = controller
            controller.pool = self
            t = threading.Thread(
                target=self._t_reload_controller,
                name='_t_reload_controller_' + controller.item_id,
                args=(controller.item_id,))
            self.reload_thread_flags[controller.item_id] = True
            self.reload_threads[controller.item_id] = t
            self.reload_controller(controller.item_id)
            t.start()
            return True
        return False

    def _t_reload_controller(self, controller_id):
        logging.debug('%s reload thread started' % controller_id)
        while self.reload_thread_flags[controller_id]:
            if self.controllers[controller_id].reload_interval > 0:
                i = 0
                while i < self.controllers[controller_id].reload_interval and \
                        self.reload_thread_flags[controller_id]:
                    time.sleep(eva.core.sleep_step)
                    i += eva.core.sleep_step
                try:
                    self.reload_controller(controller_id)
                except:
                    logging.error('%s reload error' % controller_id)
                    eva.core.log_traceback()
            else:
                time.sleep(eva.core.sleep_step)
        logging.debug('%s reload thread stopped' % controller_id)
        return

    def remove(self, controller_id):
        if controller_id in self.controllers:
            try:
                if self.reload_threads[controller_id].is_alive():
                    self.reload_thread_flags[controller_id] = False
                    self.reload_threads[controller_id].join()
                del (self.reload_thread_flags[controller_id])
                del (self.reload_threads[controller_id])
                del (self.controllers[controller_id])
                return True
            except:
                eva.core.log_traceback()
        return False

    def reload_controller(self, controller_id):
        pass

    def shutdown(self):
        for i, c in self.controllers.items():
            if self.reload_threads[c.item_id].is_alive():
                self.reload_thread_flags[c.item_id] = False
        for i, c in self.controllers.items():
            self.reload_threads[c.item_id].join()


class RemoteUCPool(RemoteControllerPool):

    def __init__(self):
        super().__init__()
        self.units = {}
        self.units_by_controller = {}
        self.controllers_by_unit = {}
        self.sensors = {}
        self.sensors_by_controller = {}
        self.action_history_by_id = {}
        self.action_history_lock = threading.Lock()
        self.action_cleaner = None
        self.action_cleaner_active = False
        self.action_cleaner_delay = 3600

    def start(self):
        if not eva.core.keep_action_history:
            return
        eva.core.append_stop_func(self.stop)
        self.action_cleaner = threading.Thread(
            target=self._t_action_cleaner,
            name='_t_remote_uc_pool_action_cleaner')
        self.action_cleaner_active = True
        self.action_cleaner.start()

    def stop(self):
        if self.action_cleaner_active:
            self.action_cleaner_active = False
            self.action_cleaner.join()

    def _t_action_cleaner(self):
        logging.debug('uc pool action cleaner started')
        while self.action_cleaner_active:
            try:
                if not self.action_history_lock.acquire(
                        timeout=eva.core.timeout):
                    logging.critical(
                        'RemoteUCPool::_t_action_cleaner locking broken')
                    eva.core.critical()
                    continue
                _actions = self.action_history_by_id.copy()
                self.action_history_lock.release()
                for u, a in _actions.items():
                    if a['t'] < time.time() - eva.core.keep_action_history:
                        logging.debug('action %s too old, removing' % u)
                        self.action_history_remove(a)
            except:
                eva.core.log_traceback()
            i = 0
            while i < self.action_cleaner_delay and \
                    self.action_cleaner_active:
                time.sleep(eva.core.sleep_step)
                i += eva.core.sleep_step
        logging.debug('uc pool action cleaner stopped')

    def get_unit(self, unit_id):
        return self.units[unit_id] if unit_id in self.units \
                else None

    def get_sensor(self, sensor_id):
        return self.sensors[sensor_id] if sensor_id in self.sensors \
                else None

    def action(self,
               unit_id,
               status,
               value=None,
               wait=0,
               uuid=None,
               priority=None):
        if not unit_id in self.controllers_by_unit: return None
        uc = self.controllers_by_unit[unit_id]
        p = {'i': unit_id, 's': status}
        if value is not None: p['v'] = value
        if wait: p['w'] = wait
        if uuid: p['u'] = uuid
        if priority: p['p'] = priority
        result = uc.api_call('action', p)
        if result and \
                'item_id' in result and \
                'item_group' in result and \
                'uuid' in result:
            a = {
                'uuid': result['uuid'],
                'i': '%s/%s' % (result['item_group'], result['item_id']),
                't': time.time()
            }
            self.action_history_append(a)
        return result

    def action_history_append(self, a):
        if not eva.core.keep_action_history:
            return True
        if not self.action_history_lock.acquire(timeout=eva.core.timeout):
            logging.critical(
                'RemoteUCPool::action_history_append locking broken')
            eva.core.critical()
            return False
        try:
            self.action_history_by_id[a['uuid']] = a
        except:
            eva.core.log_traceback()
            self.action_history_lock.release()
            return False
        self.action_history_lock.release()
        return True

    def action_history_remove(self, a):
        if not self.action_history_lock.acquire(timeout=eva.core.timeout):
            logging.critical(
                'RemoteUCPool::action_history_remove locking broken')
            eva.core.critical()
            return False
        try:
            del self.action_history_by_id[a['uuid']]
        except:
            eva.core.log_traceback()
            self.action_history_lock.release()
            return False
        self.action_history_lock.release()
        return True

    def action_history_get(self, uuid):
        if not self.action_history_lock.acquire(timeout=eva.core.timeout):
            logging.critical('RemoteUCPool::action_history_get locking broken')
            eva.core.critical()
            return None
        a = self.action_history_by_id.get(uuid)
        self.action_history_lock.release()
        return a

    def result(self, unit_id=None, uuid=None):
        if unit_id:
            i = unit_id
            p = {'i': unit_id}
        elif uuid:
            a = self.action_history_get(uuid)
            if a:
                i = a['i']
                p = {'u': uuid}
            else:
                i = None
        else:
            i = None
        if not i or not i in self.controllers_by_unit: return None
        uc = self.controllers_by_unit[i]
        return uc.api_call('result', p)

    def terminate(self, unit_id=None, uuid=None):
        if unit_id:
            i = unit_id
            p = {'i': unit_id}
        elif uuid:
            a = self.action_history_get(uuid)
            if a:
                i = a['i']
                p = {'u': uuid}
            else:
                i = None
        else:
            i = None
        if not i or not i in self.controllers_by_unit: return None
        uc = self.controllers_by_unit[i]
        return uc.api_call('terminate', p)

    def q_clean(self, unit_id):
        if not unit_id in self.controllers_by_unit: return None
        uc = self.controllers_by_unit[unit_id]
        p = {'i': unit_id}
        return uc.api_call('q_clean', p)

    def kill(self, unit_id):
        if not unit_id in self.controllers_by_unit: return None
        uc = self.controllers_by_unit[unit_id]
        p = {'i': unit_id}
        return uc.api_call('kill', p)

    def disable_actions(self, unit_id):
        if not unit_id in self.controllers_by_unit: return None
        uc = self.controllers_by_unit[unit_id]
        p = {'i': unit_id}
        return uc.api_call('disable_actions', p)

    def enable_actions(self, unit_id):
        if not unit_id in self.controllers_by_unit: return None
        uc = self.controllers_by_unit[unit_id]
        p = {'i': unit_id}
        return uc.api_call('enable_actions', p)

    def remove(self, controller_id):
        if not super().remove(controller_id): return False
        if controller_id in self.units_by_controller:
            for i in self.units_by_controller[controller_id].keys():
                try:
                    self.units[i].destroy()
                    del (self.units[i])
                    del (self.controllers_by_unit[i])
                except:
                    eva.core.log_traceback()
            try:
                del (self.units_by_controller[controller_id])
            except:
                eva.core.log_traceback()
        if controller_id in self.sensors_by_controller:
            for i in self.sensors_by_controller[controller_id].keys():
                try:
                    self.sensors[i].destroy()
                    del (self.sensors[i])
                except:
                    eva.core.log_traceback()
            try:
                del (self.sensors_by_controller[controller_id])
            except:
                eva.core.log_traceback()
        return True

    def reload_controller(self, controller_id):
        if not controller_id in self.controllers: return False
        uc = self.controllers[controller_id]
        units = uc.load_units()
        if units is not None:
            p = {}
            for u in units:
                if u.full_id in self.units and u.controller != uc:
                    self.units[u.full_id].destroy()
                if not u.full_id in self.units or \
                        self.units[u.full_id].is_destroyed():
                    self.units[u.full_id] = u
                    self.controllers_by_unit[u.full_id] = uc
                    u.start_processors()
                p[u.full_id] = u
            if controller_id in self.units_by_controller:
                for i in self.units_by_controller[controller_id].keys():
                    if i not in p:
                        self.units[i].destroy()
                        try:
                            del (self.units[i])
                            del (self.controllers_by_unit[i])
                        except:
                            eva.core.log_traceback()
            self.units_by_controller[controller_id] = p
            logging.debug('Loaded %u units from %s' % (len(p), controller_id))
        else:
            logging.error('Failed to reload units from %s' % controller_id)
            return False
        sensors = uc.load_sensors()
        if sensors is not None:
            p = {}
            for u in sensors:
                if u.full_id in self.sensors and u.controller != uc:
                    self.sensors[u.full_id].destroy()
                if not u.full_id in self.sensors or \
                        self.sensors[u.full_id].is_destroyed():
                    self.sensors[u.full_id] = u
                    u.start_processors()
                p[u.full_id] = u
            if controller_id in self.sensors_by_controller:
                for i in self.sensors_by_controller[controller_id].keys():
                    if i not in p:
                        self.sensors[i].destroy()
                        try:
                            del (self.sensors[i])
                        except:
                            eva.core.log_traceback()
            self.sensors_by_controller[controller_id] = p
            logging.debug('Loaded %u sensors from %s' % \
                    (len(p), controller_id))
        else:
            logging.error('Failed to reload sensors from %s' % controller_id)
            return False
        return True

    def cmd(self, controller_id, command, args=None, wait=None, timeout=None):
        if controller_id.find('/') == -1:
            _controller_id = controller_id
        else:
            try:
                t, _controller_id = controller_id.split('/')
                if t != 'uc': return None
            except:
                return None
        return super().cmd(
            controller_id=_controller_id,
            command=command,
            args=args,
            wait=wait,
            timeout=timeout)


class RemoteLMPool(RemoteControllerPool):

    def __init__(self):
        super().__init__()
        self.lvars = {}
        self.lvars_by_controller = {}
        self.controllers_by_lvar = {}

        self.macros = {}
        self.macros_by_controller = {}
        self.controllers_by_macro = {}

        self.rules = {}
        self.rules_by_controller = {}
        self.controllers_by_rule = {}

    def get_lvar(self, lvar_id):
        return self.lvars[lvar_id] if lvar_id in self.lvars \
                else None

    def get_dm_rule(self, rule_id):
        return self.rules[rule_id] if rule_id in self.rules \
                else None

    def get_macro(self, macro_id):
        return self.macros[macro_id] if macro_id in self.macros \
                else None

    def set(self, lvar_id, status=None, value=None):
        if not lvar_id in self.controllers_by_lvar: return None
        lm = self.controllers_by_lvar[lvar_id]
        p = {'i': lvar_id}
        if status is not None: p['s'] = status
        if value is not None: p['v'] = value
        return lm.api_call('set', p)

    def list_rule_props(self, rule_id):
        if not rule_id in self.controllers_by_rule: return None
        lm = self.controllers_by_rule[rule_id]
        p = {'i': rule_id}
        return lm.api_call('list_rule_props', p)

    def set_rule_prop(self, rule_id, prop, val, save):
        if not rule_id in self.controllers_by_rule: return None
        lm = self.controllers_by_rule[rule_id]
        p = {'i': rule_id}
        p['p'] = prop
        p['v'] = val
        if save:
            p['save'] = '1'
        return lm.api_call('set_rule_prop', p)

    def run(self, macro, args=None, wait=0, uuid=None, priority=None):
        if not macro in self.controllers_by_macro: return None
        lm = self.controllers_by_macro[macro]
        p = {'i': macro}
        if args: p['a'] = args
        if wait: p['w'] = wait
        if uuid: p['u'] = uuid
        if priority: p['p'] = priority
        return lm.api_call('run', p)

    def remove(self, controller_id):
        if not super().remove(controller_id): return False
        if controller_id in self.lvars_by_controller:
            for i in self.lvars_by_controller[controller_id].keys():
                try:
                    self.lvars[i].destroy()
                    del (self.lvars[i])
                    del (self.controllers_by_lvar[i])
                except:
                    eva.core.log_traceback()
            try:
                del (self.lvars_by_controller[controller_id])
            except:
                eva.core.log_traceback()
        if controller_id in self.macros_by_controller:
            for i in self.macros_by_controller[controller_id].keys():
                try:
                    self.macros[i].destroy()
                    del (self.macros[i])
                    del (self.controllers_by_macro[i])
                except:
                    eva.core.log_traceback()
            try:
                del (self.macros_by_controller[controller_id])
            except:
                eva.core.log_traceback()
        if controller_id in self.rules_by_controller:
            for i in self.rules_by_controller[controller_id].keys():
                try:
                    del (self.rules[i])
                    del (self.controllers_by_rule[i])
                except:
                    eva.core.log_traceback()
            try:
                del (self.rules_by_controller[controller_id])
            except:
                eva.core.log_traceback()
        return True

    def reload_controller(self, controller_id):
        if not controller_id in self.controllers: return False
        lm = self.controllers[controller_id]
        lvars = lm.load_lvars()
        if lvars is not None:
            p = {}
            for u in lvars:
                if u.full_id in self.lvars and u.controller != lm:
                    self.lvars[u.full_id].destroy()
                if not u.full_id in self.lvars or \
                        self.lvars[u.full_id].is_destroyed():
                    self.lvars[u.full_id] = u
                    self.controllers_by_lvar[u.full_id] = lm
                    u.start_processors()
                p[u.full_id] = u
            if controller_id in self.lvars_by_controller:
                for i in self.lvars_by_controller[controller_id].keys():
                    if i not in p:
                        self.lvars[i].destroy()
                        try:
                            del (self.lvars[i])
                            del (self.controllers_by_lvar[i])
                        except:
                            eva.core.log_traceback()
            self.lvars_by_controller[controller_id] = p
            logging.debug('Loaded %u lvars from %s' % (len(p), controller_id))
        else:
            logging.error('Failed to reload lvars from %s' % controller_id)
            return False
        macros = lm.load_macros(skip_system=True)
        if macros is not None:
            p = {}
            for u in macros:
                if u.full_id in self.macros and u.controller != lm:
                    self.macros[u.full_id].destroy()
                if not u.full_id in self.macros or \
                        self.macros[u.full_id].is_destroyed():
                    self.macros[u.full_id] = u
                    self.controllers_by_macro[u.full_id] = lm
                    u.start_processors()
                p[u.full_id] = u
            if controller_id in self.macros_by_controller:
                for i in self.macros_by_controller[controller_id].keys():
                    if i not in p:
                        self.macros[i].destroy()
                        try:
                            del (self.macros[i])
                            del (self.controllers_by_macro[i])
                        except:
                            eva.core.log_traceback()
            self.macros_by_controller[controller_id] = p
            logging.debug('Loaded %u macros from %s' % (len(p), controller_id))
        else:
            logging.error('Failed to reload macros from %s' % controller_id)
            return False
        rules = lm.load_rules()
        if rules is not None:
            p = {}
            for u in rules:
                if u.item_id in self.rules and u.controller != lm:
                    self.rules[u.item_id].destroy()
                if not u.item_id in self.rules:
                    self.rules[u.item_id] = u
                    self.controllers_by_rule[u.item_id] = lm
                p[u.item_id] = u
            if controller_id in self.rules_by_controller:
                for i in self.rules_by_controller[controller_id].keys():
                    if i not in p:
                        try:
                            del (self.rules[i])
                            del (self.controllers_by_rule[i])
                        except:
                            eva.core.log_traceback()
            self.rules_by_controller[controller_id] = p
            logging.debug('Loaded %u DM rules from %s' % \
                    (len(p), controller_id))
        return True
