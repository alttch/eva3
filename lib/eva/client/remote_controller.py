__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.1"

import eva.core
import eva.api
import eva.item
import eva.tools
import eva.apikey
import eva.client.coreapiclient
import eva.client.apiclient
import eva.client.remote_item
import logging
import time
import threading

_warning_time_diff = 1

cloud_manager = False


class RemoteController(eva.item.Item):

    def __init__(self,
                 item_id,
                 item_type,
                 api=None,
                 mqtt_update=None,
                 static=True,
                 enabled=True):
        if item_id == None:
            item_id = ''
        super().__init__(item_id, item_type)
        self.respect_layout = False
        if api:
            self.api = api
            self._key = api._key
        else:
            self.api = eva.client.coreapiclient.CoreAPIClient()
            self.api.set_timeout(eva.core.config.timeout)
            self._key = None
        self.masterkey = None
        self._masterkey = None
        self.product_build = None
        self.version = None
        self.pool = None
        self.mqtt_update = mqtt_update
        self.reload_interval = 300
        self.connected = False
        self.retries = 2
        self.static = static
        self.enabled = enabled
        self.wait_for_autoremove = False

    def api_call(self, func, params=None, timeout=None):
        if not self.api or not self.enabled:
            return eva.client.apiclient.result_not_ready, None
        for tries in range(self.retries + 1):
            (code, result) = self.api.call(
                func, params, timeout, _debug=eva.core.config.debug)
            if code not in [
                    eva.client.apiclient.result_server_error,
                    eva.client.apiclient.result_server_timeout
            ]:
                break
        if func in ['test', 'state']:
            self.connected = code == eva.client.apiclient.result_ok
        if code == eva.client.apiclient.result_forbidden:
            logging.error('Remote controller access forbidden %s' % \
                    self.api._uri)
            return code, None
        elif code != eva.client.apiclient.result_ok and \
                code != eva.client.apiclient.result_func_failed \
                and code != eva.client.apiclient.result_not_found:
            logging.error('Remote controller access error %s, code %u' % \
                    (self.api._uri, code))
            return code, None
        return code, result

    def management_api_call(self, func, params=None, timeout=None):
        if not self.api or not cloud_manager or not self.masterkey:
            return eva.client.apiclient.result_not_ready, None
        p = params.copy() if isinstance(params, dict) else {}
        p['k'] = self.masterkey
        for tries in range(self.retries + 1):
            (code, result) = self.api.call(
                func, p, timeout, _debug=eva.core.config.debug)
            if code not in [
                    eva.client.apiclient.result_server_error,
                    eva.client.apiclient.result_server_timeout
            ]:
                break
        return code, result

    def test(self):
        code, result = self.api_call('test')
        if code or not isinstance(result, dict):
            logging.error('Remote controller {} test failed'.format(
                self.full_id))
            return False
        if not result.get('ok'):
            logging.error('Remote controller access error %s' % self.api._uri)
            return False
        return result

    def matest(self):
        if not self.masterkey:
            logging.error(('Remote controller {} management test aborted: ' +
                           'no masterkey set').format(self.full_id))
            return False
        result = self.management_api_call('test')[1]
        if not isinstance(result, dict):
            logging.error('Remote controller {} management test failed'.format(
                self.full_id))
            return False
        if not result.get('ok'):
            logging.error('Remote controller access error %s' % self.api._uri)
            return False
        if result.get('acl', {}).get('master') != True:
            logging.error(
                'Remote controller API %s has no master access' % self.api._uri)
            return False
        return True

    def load_remote(self, need_type=None):
        result = self.test()
        if not result:
            if not self.static and self.pool and not self.wait_for_autoremove:
                self.wait_for_autoremove = True
                t = threading.Thread(
                    target=eva.api.remove_controller, args=(self.full_id,))
                t.start()
            return False
        if not result.get('ok'):
            logging.error('Remote controller unknown access error %s' % \
                    self.api._uri)
            return False
        if need_type and result.get('product_code') != need_type:
            logging.error('Invalid remote controller type %s' % self.api._uri)
            return False
        time_diff = abs(time.time() - float(result['time']))
        if eva.core.version != result['version']:
            logging.warning('Remote controller EVA version is %s, my: %s' % \
                    (result['version'], eva.core.version))
        self.item_id = result['system']
        self.config_changed = True
        self.set_group(result['product_code'])
        self.product_build = result['product_build']
        logging.info('controller %s loaded' % self.full_id)
        self.version = result['version']
        msg = '%s time diff is %f sec' % (self.full_id, time_diff)
        if time_diff > _warning_time_diff:
            logging.warning(msg)
        else:
            logging.info(msg)
        return True

    def save(self, fname=None):
        return super().save(fname=fname) if self.static else True

    def update_config(self, data):
        if cloud_manager:
            if 'masterkey' in data:
                self.masterkey = eva.apikey.format_key(data['masterkey'])
                self._masterkey = data['masterkey']
        if 'uri' in data:
            self.api.set_uri(data['uri'])
        if 'key' in data:
            self.api.set_key(eva.apikey.format_key(data['key']))
            self._key = data['key']
        if 'timeout' in data:
            self.api.set_timeout(data['timeout'])
        if 'retries' in data:
            self.retries = data['retries']
        if 'ssl_verify' in data:
            self.api.ssl_verify(data['ssl_verify'])
        if 'mqtt_update' in data:
            self.mqtt_update = data['mqtt_update']
        if 'reload_interval' in data:
            self.reload_interval = data['reload_interval']
        if 'enabled' in data:
            self.enabled = data['enabled']
        super().update_config(data)

    def set_modified(self, save):
        super().set_modified(save)
        self.connected = False
        t = threading.Thread(target=self.test)
        t.start()

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
        elif prop == 'masterkey':
            if not cloud_manager or \
                    not self.set_prop('static', 1):
                return False
            if self._masterkey != val:
                self._masterkey = val
                self.masterkey = eva.apikey.format_key(val)
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
                self.api.set_timeout(eva.core.config.timeout)
                self.set_modified(save)
                return True
        elif prop == 'retries':
            if val is not None:
                try:
                    v = int(val)
                    if v < 0: return False
                    self.retries = v
                    self.log_set(prop, val)
                    self.set_modified(save)
                    return True
                except:
                    return False
            return False
        elif prop == 'static':
            try:
                v = eva.tools.val_to_boolean(val)
                if v is False: return False
                if self.static != True:
                    self.static = True
                    self.log_set(prop, True)
                    self.set_modified(save)
                return True
            except:
                return False
        elif prop == 'enabled':
            if not self.set_prop('static', 1): return False
            if val is not None:
                try:
                    v = eva.tools.val_to_boolean(val)
                    if v is None: return False
                    if self.enabled != v:
                        self.enabled = v
                        self.log_set(prop, v)
                        self.set_modified(save)
                        if self.pool:
                            self.pool.enable(self) if v else \
                                    self.pool.disable(self.item_id)
                        if not v:
                            self.connected = False
                    return True
                except:
                    eva.core.log_traceback()
                    return False
            else:
                self.enabled = True
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
        d['static'] = self.static
        d['enabled'] = self.enabled
        if config or props:
            d['retries'] = self.retries
            d['uri'] = ''
            if self.api.protocol_mode == 1:
                d['uri'] = 'mqtt:'
                if self.api._notifier_id:
                    d['uri'] += self.api._notifier_id + ':'
            d['uri'] += self.api._uri
            d['key'] = self._key if self._key is not None else ''
            d['timeout'] = self.api._timeout
            d['ssl_verify'] = self.api._ssl_verify
            d['mqtt_update'] = self.mqtt_update
            d['reload_interval'] = self.reload_interval
            if cloud_manager:
                d['masterkey'] = self._masterkey if \
                        self._masterkey is not None else ''
        if info:
            d['connected'] = self.connected if self.enabled else False
            d['managed'] = True if cloud_manager and self.masterkey else False
            if self.api.protocol_mode == 0:
                d['proto'] = 'http'
            elif self.api.protocol_mode == 1:
                d['proto'] = 'mqtt'
            else:
                d['proto'] = 'unknown'
            d['version'] = self.version
            d['build'] = str(self.product_build)
            d['mqtt_update'] = self.mqtt_update
        d.update(super().serialize(
            full=full, config=config, info=info, props=props, notify=notify))
        return d

    def destroy(self):
        super().destroy()
        if self.pool:
            t = threading.Thread(target=self.pool.remove, args=(self.item_id,))
            t.start()


class RemoteUC(RemoteController):

    def __init__(self, uc_id=None, api=None, mqtt_update=None, static=True):
        super().__init__(uc_id, 'remote_uc', api, mqtt_update, static)
        self.api.set_product('uc')

    def create_remote_unit(self, state):
        return eva.client.remote_item.RemoteUnit(self, state)

    def create_remote_sensor(self, state):
        return eva.client.remote_item.RemoteSensor(self, state)

    def load_units(self):
        if not self.item_id: return None
        code, states = self.api_call('state', {'p': 'U', 'full': True})
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
        code, states = self.api_call('state', {'p': 'S', 'full': True})
        result = []
        if states is not None:
            for s in states:
                u = self.create_remote_sensor(s)
                result.append(u)
            return result
        else:
            return None


class RemoteLM(RemoteController):

    def __init__(self, lm_id=None, api=None, mqtt_update=None, static=True):
        super().__init__(lm_id, 'remote_lm', api, mqtt_update, static)
        self.api.set_product('lm')

    def create_remote_lvar(self, state):
        return eva.client.remote_item.RemoteLVar(self, state)

    def create_remote_macro(self, mcfg):
        m = eva.client.remote_item.RemoteMacro(mcfg['id'], self)
        m.update_config(mcfg)
        return m

    def create_remote_cycle(self, mcfg):
        m = eva.client.remote_item.RemoteCycle(self, mcfg)
        m.update_config(mcfg)
        return m

    def load_lvars(self):
        if not self.item_id: return None
        code, states = self.api_call('state', {'full': True})
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
        code, macros = self.api_call('list_macros')
        result = []
        if macros is not None:
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

    def load_cycles(self, skip_system=False):
        if not self.item_id: return None
        code, cycles = self.api_call('list_cycles')
        result = []
        if cycles is not None:
            for m in cycles:
                if 'id' in m:
                    i = self.create_remote_cycle(m)
                    result.append(i)
            return result
        else:
            return None


class RemoteControllerPool(object):

    def __init__(self):
        self.controllers = {}
        self.reload_threads = {}
        self.reload_thread_flags = {}
        self.management_lock = threading.Lock()
        self.item_management_lock = threading.Lock()
        self.action_history_by_id = {}
        self.action_history_lock = threading.Lock()
        self.action_cleaner = None
        self.action_cleaner_active = False
        self.action_cleaner_interval = eva.core.config.action_cleaner_interval

    def cmd(self, controller_id, command, args=None, wait=None, timeout=None):
        if controller_id not in self.controllers:
            return apiclient.result_not_found, None
        c = self.controllers[controller_id]
        p = {'c': command}
        if args is not None: p['a'] = args
        if wait is not None: p['w'] = wait
        if timeout is not None: p['t'] = timeout
        return c.api_call('cmd', p)

    def append(self, controller, need_type=None):
        if controller.load_remote(need_type=need_type) or \
                controller.item_id != '':
            if not self.management_lock.acquire(
                    timeout=eva.core.config.timeout):
                logging.critical('RemoteControllerPool::append locking broken')
                eva.core.critical()
                return False
            if controller.item_id in self.controllers:
                self.management_lock.release()
                logging.error(
                    'Unable to append controller {}, already exists'.format(
                        controller.full_id))
                return False
            self.controllers[controller.item_id] = controller
            controller.pool = self
            if controller.enabled:
                self.start_controller_reload_thread(controller)
            self.management_lock.release()
            return True
        return False

    def remove(self, controller_id):
        if not self.management_lock.acquire(timeout=eva.core.config.timeout):
            logging.critical('RemoteControllerPool::remove locking broken')
            eva.core.critical()
            return False
        if controller_id in self.controllers:
            self.stop_controller_reload_thread(controller_id)
            del (self.controllers[controller_id])
            self.management_lock.release()
            return True
        self.management_lock.release()
        return False

    def enable(self, controller):
        controller_id = controller.item_id
        if controller_id not in self.reload_threads or \
                not self.reload_threads[controller_id].is_alive():
            self.start_controller_reload_thread(controller, lock=True)

    def disable(self, controller_id):
        if controller_id in self.reload_threads and \
                self.reload_threads[controller_id].isAlive():
            self.stop_controller_reload_thread(controller_id)

    def start_controller_reload_thread(self, controller, lock=False):
        t = threading.Thread(
            target=self._t_reload_controller,
            name='_t_reload_controller_' + controller.item_type + '_' +
            controller.item_id,
            args=(controller.item_id,))
        if lock and \
                not self.management_lock.acquire(
                        timeout=eva.core.config.timeout):
            logging.critical(
                'RemoteControllerPool::start_controller_reload_' + \
                        'thread locking broken')
            eva.core.critical()
            return False
        self.reload_thread_flags[controller.item_id] = True
        self.reload_threads[controller.item_id] = t
        self.reload_controller(controller.item_id)
        t.start()
        if lock: self.management_lock.release()

    def stop_controller_reload_thread(self, controller_id, lock=False):
        try:
            if controller_id in self.reload_threads:
                if self.reload_threads[controller_id].is_alive():
                    self.reload_thread_flags[controller_id] = False
                    self.reload_threads[controller_id].join()
                if lock and \
                    not self.management_lock.acquire(
                            timeout=eva.core.config.timeout):
                    logging.critical(
                        'RemoteControllerPool::stop_controller_reload_' + \
                                'thread locking broken')
                    eva.core.critical()
                    return False
                del (self.reload_thread_flags[controller_id])
                del (self.reload_threads[controller_id])
                if lock: self.management_lock.release()
        except:
            if lock: self.management_lock.release()
            eva.core.log_traceback()

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

    def reload_controller(self, controller_id):
        if controller_id == 'ALL':
            success = True
            for c in self.controllers.copy():
                try:
                    if not self.reload_controller(c):
                        raise Exception('reload error')
                except:
                    eva.core.log_traceback()
                    success = False
            return success
        if not controller_id in self.controllers: return None
        controller = self.controllers[controller_id]
        return controller.load_remote()

    def start(self):
        if not eva.core.config.keep_action_history:
            return
        eva.core.stop.append(self.stop)
        self.action_cleaner = threading.Thread(
            target=self._t_action_cleaner,
            name='_t_remote_uc_pool_action_cleaner')
        self.action_cleaner_active = True
        self.action_cleaner.start()

    def stop(self):
        if self.action_cleaner_active:
            self.action_cleaner_active = False
            self.action_cleaner.join()
        for i, c in self.controllers.items():
            if c.item_id in self.reload_threads and \
                self.reload_threads[c.item_id].is_alive():
                self.reload_thread_flags[c.item_id] = False
        for i, c in self.controllers.items():
            if c.item_id in self.reload_threads:
                try:
                    self.reload_threads[c.item_id].join()
                except:
                    pass

    def _t_action_cleaner(self):
        logging.debug('uc pool action cleaner started')
        while self.action_cleaner_active:
            try:
                if not self.action_history_lock.acquire(
                        timeout=eva.core.config.timeout):
                    logging.critical(
                        'RemoteControllerPool::_t_action_cleaner locking broken'
                    )
                    eva.core.critical()
                    continue
                _actions = self.action_history_by_id.copy()
                self.action_history_lock.release()
                for u, a in _actions.items():
                    if a['t'] < time.time(
                    ) - eva.core.config.keep_action_history:
                        logging.debug('action %s too old, removing' % u)
                        self.action_history_remove(a)
            except:
                eva.core.log_traceback()
            i = 0
            while i < self.action_cleaner_interval and \
                    self.action_cleaner_active:
                time.sleep(eva.core.sleep_step)
                i += eva.core.sleep_step
        logging.debug('uc pool action cleaner stopped')

    def action_history_append(self, a):
        if not eva.core.config.keep_action_history:
            return True
        if not self.action_history_lock.acquire(
                timeout=eva.core.config.timeout):
            logging.critical(
                'RemoteControllerPool::action_history_append locking broken')
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
        if not self.action_history_lock.acquire(
                timeout=eva.core.config.timeout):
            logging.critical(
                'RemoteControllerPool::action_history_remove locking broken')
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
        if not self.action_history_lock.acquire(
                timeout=eva.core.config.timeout):
            logging.critical(
                'RemoteControllerPool::action_history_get locking broken')
            eva.core.critical()
            return None
        a = self.action_history_by_id.get(uuid)
        self.action_history_lock.release()
        return a


class RemoteUCPool(RemoteControllerPool):

    def __init__(self):
        super().__init__()
        self.units = {}
        self.units_by_controller = {}
        self.controllers_by_unit = {}
        self.sensors = {}
        self.sensors_by_controller = {}

    def append(self, controller):
        return super().append(controller, need_type='uc')

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
               q=None,
               priority=None):
        if not unit_id in self.controllers_by_unit:
            return apiclient.result_not_found, None
        uc = self.controllers_by_unit[unit_id]
        p = {'i': unit_id, 's': status}
        if value is not None: p['v'] = value
        if wait: p['w'] = wait
        if uuid: p['u'] = uuid
        if priority: p['p'] = priority
        if q: p['q'] = q
        code, result = uc.api_call('action', p)
        if not code and result and \
                'item_id' in result and \
                'item_group' in result and \
                'uuid' in result:
            a = {
                'uuid': result['uuid'],
                'i': '%s/%s' % (result['item_group'], result['item_id']),
                't': time.time()
            }
            self.action_history_append(a)
        return code, result

    def action_toggle(self, unit_id, wait=0, uuid=None, q=None, priority=None):
        if not unit_id in self.controllers_by_unit:
            return apiclient.result_not_found, None
        uc = self.controllers_by_unit[unit_id]
        p = {'i': unit_id}
        if wait: p['w'] = wait
        if uuid: p['u'] = uuid
        if priority: p['p'] = priority
        if q: p['q'] = q
        code, result = uc.api_call('action_toggle', p)
        if not code and result and \
                'item_id' in result and \
                'item_group' in result and \
                'uuid' in result:
            a = {
                'uuid': result['uuid'],
                'i': '%s/%s' % (result['item_group'], result['item_id']),
                't': time.time()
            }
            self.action_history_append(a)
        return code, result

    def result(self, unit_id=None, uuid=None, group=None, status=None):
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
        if group: p['g'] = group
        if status: p['s'] = status
        if not i or not i in self.controllers_by_unit:
            return apiclient.result_not_found, None
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
        if not i or not i in self.controllers_by_unit:
            return apiclient.result_not_found, None
        uc = self.controllers_by_unit[i]
        return uc.api_call('terminate', p)

    def q_clean(self, unit_id):
        if not unit_id in self.controllers_by_unit:
            return apiclient.result_not_found, None
        uc = self.controllers_by_unit[unit_id]
        p = {'i': unit_id}
        return uc.api_call('q_clean', p)

    def kill(self, unit_id):
        if not unit_id in self.controllers_by_unit:
            return apiclient.result_not_found, None
        uc = self.controllers_by_unit[unit_id]
        p = {'i': unit_id}
        return uc.api_call('kill', p)

    def disable_actions(self, unit_id):
        if not unit_id in self.controllers_by_unit:
            return apiclient.result_not_found, None
        uc = self.controllers_by_unit[unit_id]
        p = {'i': unit_id}
        return uc.api_call('disable_actions', p)

    def enable_actions(self, unit_id):
        if not unit_id in self.controllers_by_unit:
            return apiclient.result_not_found, None
        uc = self.controllers_by_unit[unit_id]
        p = {'i': unit_id}
        return uc.api_call('enable_actions', p)

    def disable(self, controller_id):
        super().disable(controller_id)
        self.remove(controller_id, full=False)

    def remove(self, controller_id, full=True):
        if full and not super().remove(controller_id): return False
        if not self.item_management_lock.acquire(
                timeout=eva.core.config.timeout):
            logging.critical('RemoteUCPool::remove locking broken')
            eva.core.critical()
            return False
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
        self.item_management_lock.release()
        return True

    def reload_controller(self, controller_id):
        result = super().reload_controller(controller_id)
        if not result: return result
        if controller_id == 'ALL': return True
        uc = self.controllers[controller_id]
        if not self.item_management_lock.acquire(
                timeout=eva.core.config.timeout):
            logging.critical('RemoteUCPool::reload_controller locking broken')
            eva.core.critical()
            return False
        try:
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
                    else:
                        self.units[u.full_id].status = u.status
                        self.units[u.full_id].value = u.value
                        self.units[u.full_id].nstatus = u.nstatus
                        self.units[u.full_id].nvalue = u.nvalue
                    p[u.full_id] = u
                    _u = self.get_unit(u.full_id)
                    if _u: _u.update_config(u.serialize(config=True))
                if controller_id in self.units_by_controller:
                    for i in self.units_by_controller[
                            controller_id].copy().keys():
                        if i not in p:
                            self.units[i].destroy()
                            try:
                                del (self.units[i])
                                del (self.controllers_by_unit[i])
                                del (self.units_by_controller[controller_id][i])
                            except:
                                eva.core.log_traceback()
                    for u in units:
                        if u.full_id not in self.units_by_controller[
                                controller_id].keys():
                            self.units_by_controller[controller_id][
                                u.full_id] = u
                else:
                    self.units_by_controller[controller_id] = p
                logging.debug(
                    'Loaded %u units from %s' % (len(p), controller_id))
            else:
                logging.error('Failed to reload units from %s' % controller_id)
                self.item_management_lock.release()
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
                    else:
                        self.sensors[u.full_id].status = u.status
                        self.sensors[u.full_id].value = u.value
                    p[u.full_id] = u
                    _u = self.get_sensor(u.full_id)
                    if _u: _u.update_config(u.serialize(config=True))
                if controller_id in self.sensors_by_controller:
                    for i in self.sensors_by_controller[
                            controller_id].copy().keys():
                        if i not in p:
                            self.sensors[i].destroy()
                            try:
                                del (self.sensors[i])
                                del (self.sensors_by_controller[controller_id][
                                    i])
                            except:
                                eva.core.log_traceback()
                    for u in sensors:
                        if u.full_id not in self.sensors_by_controller[
                                controller_id].keys():
                            self.sensors_by_controller[controller_id][
                                u.full_id] = u
                else:
                    self.sensors_by_controller[controller_id] = p
                logging.debug('Loaded %u sensors from %s' % \
                        (len(p), controller_id))
            else:
                logging.error(
                    'Failed to reload sensors from %s' % controller_id)
                self.item_management_lock.release()
                return False
        except:
            logging.error('failed to reload controller ' + controller_id)
            eva.core.log_traceback()
            self.item_management_lock.release()
            return False
        self.item_management_lock.release()
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

    def manage_device(self,
                      controller_id,
                      device_func,
                      device_tpl,
                      cfg=None,
                      save=None):
        if controller_id.find('/') == -1:
            _controller_id = controller_id
        else:
            try:
                t, _controller_id = controller_id.split('/')
                if t != 'uc': return None
            except:
                return None
        if _controller_id not in self.controllers:
            return apiclient.result_not_found, None
        c = self.controllers[_controller_id]
        p = {'t': device_tpl}
        if save:
            p['save'] = 1
        if cfg:
            if isinstance(cfg, dict):
                a = []
                for k, v in cfg.items():
                    a.append('%s=%s' % (k, v))
                p['c'] = ','.join(a)
            elif isinstance(cfg, str):
                p['c'] = cfg
        return c.api_call(device_func, p)

    def deploy_device(self, controller_id, device_tpl, cfg=None, save=None):
        return self.manage_device(
            controller_id=controller_id,
            device_func='deploy_device',
            device_tpl=device_tpl,
            cfg=cfg,
            save=save)

    def update_device(self, controller_id, device_tpl, cfg=None, save=None):
        return self.manage_device(
            controller_id=controller_id,
            device_func='update_device',
            device_tpl=device_tpl,
            cfg=cfg,
            save=save)

    def undeploy_device(self, controller_id, device_tpl, cfg=None):
        return self.manage_device(
            controller_id=controller_id,
            device_func='undeploy_device',
            device_tpl=device_tpl,
            cfg=cfg)


class RemoteLMPool(RemoteControllerPool):

    def __init__(self):
        super().__init__()
        self.lvars = {}
        self.lvars_by_controller = {}
        self.controllers_by_lvar = {}

        self.macros = {}
        self.macros_by_controller = {}
        self.controllers_by_macro = {}

        self.cycles = {}
        self.cycles_by_controller = {}
        self.controllers_by_cycle = {}

    def append(self, controller):
        return super().append(controller, need_type='lm')

    def get_lvar(self, lvar_id):
        return self.lvars[lvar_id] if lvar_id in self.lvars \
                else None

    def get_macro(self, macro_id):
        return self.macros[macro_id] if macro_id in self.macros \
                else None

    def get_cycle(self, cycle_id):
        return self.cycles[cycle_id] if cycle_id in self.cycles \
                else None

    def set(self, lvar_id, status=None, value=None):
        if not lvar_id in self.controllers_by_lvar:
            return apiclient.result_not_found, None
        lm = self.controllers_by_lvar[lvar_id]
        p = {'i': lvar_id}
        if status is not None: p['s'] = status
        if value is not None: p['v'] = value
        return lm.api_call('set', p)

    def reset(self, lvar_id):
        if not lvar_id in self.controllers_by_lvar:
            return apiclient.result_not_found, None
        lm = self.controllers_by_lvar[lvar_id]
        p = {'i': lvar_id}
        return lm.api_call('reset', p)

    def toggle(self, lvar_id):
        if not lvar_id in self.controllers_by_lvar:
            return apiclient.result_not_found, None
        lm = self.controllers_by_lvar[lvar_id]
        p = {'i': lvar_id}
        return lm.api_call('toggle', p)

    def clear(self, lvar_id):
        if not lvar_id in self.controllers_by_lvar:
            return apiclient.result_not_found, None
        lm = self.controllers_by_lvar[lvar_id]
        p = {'i': lvar_id}
        return lm.api_call('clear', p)

    def run(self,
            macro,
            args=None,
            kwargs=None,
            wait=0,
            uuid=None,
            priority=None,
            q_timeout=None):
        if not macro in self.controllers_by_macro:
            return apiclient.result_not_found, None
        lm = self.controllers_by_macro[macro]
        p = {'i': macro}
        if args: p['a'] = args
        if kwargs: p['kw'] = kwargs
        if wait: p['w'] = wait
        if uuid: p['u'] = uuid
        if priority: p['p'] = priority
        if q_timeout: p['q'] = q_timeout
        code, result = lm.api_call('run', p)
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
        return code, result

    def result(self, macro_id=None, uuid=None, group=None, status=None):
        if macro_id:
            i = macro_id
            p = {'i': macro_id}
        elif uuid:
            a = self.action_history_get(uuid)
            if a:
                i = a['i']
                p = {'u': uuid}
            else:
                i = None
        else:
            i = None
        if group: p['g'] = group
        if status: p['s'] = status
        if not i or not i in self.controllers_by_macro:
            return apiclient.result_not_found, None
        lm = self.controllers_by_macro[i]
        return lm.api_call('result', p)

    def disable(self, controller_id):
        super().disable(controller_id)
        self.remove(controller_id, full=False)

    def remove(self, controller_id, full=True):
        if full and not super().remove(controller_id): return False
        if not self.item_management_lock.acquire(
                timeout=eva.core.config.timeout):
            logging.critical('RemoteLMPool::remove locking broken')
            eva.core.critical()
            return False
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
        if controller_id in self.cycles_by_controller:
            for i in self.cycles_by_controller[controller_id].keys():
                try:
                    self.cycles[i].destroy()
                    del (self.cycles[i])
                    del (self.controllers_by_cycle[i])
                except:
                    eva.core.log_traceback()
            try:
                del (self.cycles_by_controller[controller_id])
            except:
                eva.core.log_traceback()
        self.item_management_lock.release()
        return True

    def reload_controller(self, controller_id):
        result = super().reload_controller(controller_id)
        if not result: return result
        if controller_id == 'ALL': return True
        lm = self.controllers[controller_id]
        if not self.item_management_lock.acquire(
                timeout=eva.core.config.timeout):
            logging.critical('RemoteLMPool::reload_controller locking broken')
            eva.core.critical()
            return False
        try:
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
                    _u = self.get_lvar(u.full_id)
                    if _u: _u.update_config(u.serialize(config=True))
                if controller_id in self.lvars_by_controller:
                    for i in self.lvars_by_controller[
                            controller_id].copy().keys():
                        if i not in p:
                            self.lvars[i].destroy()
                            try:
                                del (self.lvars[i])
                                del (self.controllers_by_lvar[i])
                                del (self.lvars_by_controller[controller_id][i])
                            except:
                                eva.core.log_traceback()
                    for u in lvars:
                        if u.full_id not in self.lvars_by_controller[
                                controller_id].keys():
                            self.lvars_by_controller[controller_id][
                                u.full_id] = u
                else:
                    self.lvars_by_controller[controller_id] = p
                logging.debug(
                    'Loaded %u lvars from %s' % (len(p), controller_id))
            else:
                logging.error('Failed to reload lvars from %s' % controller_id)
                self.item_management_lock.release()
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
                    _u = self.get_macro(u.full_id)
                    if _u: _u.update_config(u.serialize(config=True))
                if controller_id in self.macros_by_controller:
                    for i in self.macros_by_controller[
                            controller_id].copy().keys():
                        if i not in p:
                            self.macros[i].destroy()
                            try:
                                del (self.macros[i])
                                del (self.controllers_by_macro[i])
                                del (
                                    self.macros_by_controller[controller_id][i])
                            except:
                                eva.core.log_traceback()
                    for u in macros:
                        if u.full_id not in self.macros_by_controller[
                                controller_id].keys():
                            self.macros_by_controller[controller_id][
                                u.full_id] = u
                else:
                    self.macros_by_controller[controller_id] = p
                logging.debug(
                    'Loaded %u macros from %s' % (len(p), controller_id))
            else:
                logging.error('Failed to reload macros from %s' % controller_id)
                self.item_management_lock.release()
                return False
            cycles = lm.load_cycles()
            if cycles is not None:
                p = {}
                for u in cycles:
                    if u.full_id in self.cycles and u.controller != lm:
                        self.cycles[u.full_id].destroy()
                    if not u.full_id in self.cycles or \
                            self.cycles[u.full_id].is_destroyed():
                        self.cycles[u.full_id] = u
                        self.controllers_by_cycle[u.full_id] = lm
                        u.start_processors()
                    p[u.full_id] = u
                    _u = self.get_cycle(u.full_id)
                    if _u: _u.update_config(u.serialize(config=True))
                if controller_id in self.cycles_by_controller:
                    for i in self.cycles_by_controller[
                            controller_id].copy().keys():
                        if i not in p:
                            self.cycles[i].destroy()
                            try:
                                del (self.cycles[i])
                                del (self.controllers_by_cycle[i])
                                del (
                                    self.cycles_by_controller[controller_id][i])
                            except:
                                eva.core.log_traceback()
                    for u in cycles:
                        if u.full_id not in self.cycles_by_controller[
                                controller_id].keys():
                            self.cycles_by_controller[controller_id][
                                u.full_id] = u
                else:
                    self.cycles_by_controller[controller_id] = p
                logging.debug(
                    'Loaded %u cycles from %s' % (len(p), controller_id))
            else:
                logging.error('Failed to reload cycles from %s' % controller_id)
                self.item_management_lock.release()
                return False
        except:
            logging.error('failed to reload controller ' + controller_id)
            eva.core.log_traceback()
            self.item_management_lock.release()
            return False
        self.item_management_lock.release()
        return True
