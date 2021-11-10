__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.2"

import eva.core
import eva.api
import eva.item
import eva.tools
import eva.apikey
import eva.client.coreapiclient
import eva.client.remote_item
import logging
import time
import ssl
import threading
import websocket
import rapidjson
import msgpack
import uuid
import random
from eva.client import apiclient
from neotasker import BackgroundIntervalWorker, BackgroundWorker
from eva.types import CT_JSON, CT_MSGPACK

# import eva.debuglock

# websocket.enableTrace(True)

_warning_time_diff = 1

cloud_manager = False

ws_ping_message = eva.client.apiclient.pack_msgpack({'s': 'ping'})


class WebSocketPingerWorker(BackgroundIntervalWorker):

    def __init__(self, **kwargs):
        super().__init__(on_error=eva.core.log_traceback, **kwargs)

    def run(*args, **kwargs):
        controller = kwargs.get('controller')
        try:
            logging.debug('WS {}: PING'.format(controller.oid))
            ws = kwargs['o']
            ws.send(ws_ping_message, opcode=0x2)
            ws.send('')
        except:
            eva.core.log_traceback()


class WebSocketWorker(BackgroundWorker):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.need_reload_flag = False
        self.retries_made = 0
        self.pinger = None
        self.ws = None
        self.controller = kwargs.get('controller')
        self.pool = kwargs.get('pool')

    def need_reload(self):
        return self.need_reload_flag

    def wait(self):
        self.need_reload_flag = False
        # don't use threading.event, reload interval can be changed during wait
        eva.core.wait_for(self.need_reload,
                          self.controller.get_reload_interval,
                          delay=eva.core.sleep_step)

    def clear_ws(self):
        try:
            self.ws.close()
        except:
            pass
        self.ws = None

    def stop_ping(self):
        if self.pinger:
            self.pinger.stop(wait=False)

    def start_ping(self):
        if not self.pool.management_lock.acquire(
                timeout=eva.core.config.timeout):
            logging.critical(
                'WebSocketWorker::start_ping ' + \
                        'locking broken')
            eva.core.critical()
            return False
        try:
            self.pinger = WebSocketPingerWorker(name='ws_pinger:' +
                                                self.controller.oid,
                                                interval=5,
                                                o=self.ws)
            self.pinger.start(controller=self.controller)
        finally:
            self.pool.management_lock.release()
        return True

    def stop(self, *args, **kwargs):
        super().stop(*args, **kwargs)
        self.stop_ping()
        try:
            self.ws.close()
        except:
            pass

    def set_controller_connected(self, state, graceful_shutdown=False):
        if not self.is_active():
            return
        self.controller.set_connected(state,
                                      graceful_shutdown=graceful_shutdown)

    def run(self, *args, **kwargs):

        def create_connection(controller):
            uri = 'ws' + controller.api._uri[4:]
            logging.debug('WS {}: connecting'.format(controller.oid))
            ws_uri = '{}/ws?k={}&c={}'.format(uri, controller.api._key,
                                              CT_MSGPACK)
            if controller.ws_buf_ttl:
                ws_uri += f'&buf_ttl={controller.ws_buf_ttl}'
            ws = websocket.create_connection(
                ws_uri,
                timeout=round(controller.api._timeout),
                enable_multithread=True,
                sslopt={"cert_reqs": ssl.CERT_NONE}
                if not controller.api._ssl_verify else None)
            ws.settimeout(5 + eva.core.config.timeout)
            if controller.ws_state_events:
                try:
                    ws.send(eva.client.apiclient.pack_msgpack({'s': 'state'}),
                            opcode=0x2)
                    ws.send('')
                except:
                    try:
                        ws.close()
                    except:
                        pass
                    raise
            logging.debug('WS {}: connected'.format(controller.oid))
            return ws

        if not self.ws:
            try:
                self.ws = create_connection(self.controller)
                logging.info('WS: controller connected {}'.format(
                    self.controller.oid))
                self.retries_made = 0
                self.set_controller_connected(True)
                self.start_ping()
            except:
                self.clear_ws()
                logfunc = logging.error if \
                        self.controller.connected else logging.debug
                logfunc('WS {}: connection error'.format(self.controller.oid))
                self.set_controller_connected(False)
                time.sleep(eva.core.sleep_step)
                eva.core.log_traceback()
                self.retries_made += 1
                if self.retries_made > self.controller.retries:
                    self.wait()
                return
        try:
            logging.debug('WS {}: waiting for data frame'.format(
                self.controller.oid))
            frame = self.ws.recv_frame()
            self.set_controller_connected(True)
            logging.debug('WS {}: processing data frame'.format(
                self.controller.oid))
            if frame.opcode == websocket.ABNF.OPCODE_PING:
                self.ws.pong(frame.data)
            elif frame.opcode == websocket.ABNF.OPCODE_CLOSE:
                self.stop_ping()
                if eva.core.is_shutdown_requested():
                    return
                logging.warning('Remote controller {} closed connection'.format(
                    self.controller.oid))
                self.set_controller_connected(False, graceful_shutdown=True)
                self.clear_ws()
                self.wait()
            else:
                try:
                    try:
                        data = msgpack.loads(frame.data, raw=False)
                    except:
                        data = rapidjson.loads(frame.data.decode())
                    if data.get('s') == 'server' and data.get('d') == 'restart':
                        self.stop_ping()
                        if eva.core.is_shutdown_requested():
                            return
                        logging.warning(
                            'Remote controller {} is being restarting'.format(
                                self.controller.oid))
                        self.set_controller_connected(False,
                                                      graceful_shutdown=True)
                        self.clear_ws()
                        self.wait()
                    else:
                        self.pool.process_ws_data(data, self.controller)
                except:
                    logging.warning('WS {}: Invalid data frame received'.format(
                        self.controller.oid))
                    eva.core.log_traceback()
        except:
            logging.error('Remote controller {} is gone'.format(
                self.controller.oid))
            self.stop_ping()
            self.set_controller_connected(False)
            eva.core.log_traceback()
            self.clear_ws()


class RemoteController(eva.item.Item):

    def __init__(self,
                 item_id,
                 item_type,
                 api=None,
                 mqtt_update=None,
                 static=True,
                 enabled=True,
                 ws_state_events=True,
                 ws_buf_ttl=0,
                 **kwargs):
        if item_id == None:
            item_id = ''
        super().__init__(item_id, item_type, **kwargs)
        if api:
            self.api = api
            self._key = api._key
        else:
            self.api = eva.client.coreapiclient.CoreAPIClient()
            self.api.set_timeout(eva.core.config.timeout / 2)
            self._key = None
        self.masterkey = None
        self._masterkey = None
        self.product_build = None
        self.version = None
        self.pool = None
        self.mqtt_update = mqtt_update
        self.reload_interval = 30
        self.connected = False
        self.retries = 0
        self.static = static
        self.enabled = enabled
        self.wait_for_autoremove = False
        self.last_reload_time = 0
        self.set_mqtt_notifier()
        self.ws_state_events = ws_state_events
        self.ws_buf_ttl = ws_buf_ttl

    def get_rkn(self):
        if self.item_id:
            return (f'data/{eva.core.product.code}'
                    f'/{self.item_type}/{self.item_id}')
        else:
            raise RuntimeError('controller object not configured')

    def set_connected(self, state, graceful_shutdown=False):
        if graceful_shutdown:
            self.last_reload_time = time.perf_counter()
        self.connected = state
        if graceful_shutdown:
            logging.debug(self.oid + ' marked down')

    def server_event_handler(self, data, topic, qos, retain):
        if not data:
            return True
        try:
            try:
                j = msgpack.loads(data, raw=False)
            except:
                j = rapidjson.loads(data)
        except:
            logging.warning(self.oid + ' invalid server event data')
            return False
        try:
            event = j.get('e')
            if event == 'restart':
                self.set_connected(False, graceful_shutdown=True)
            elif event == 'leaving':
                logging.warning(self.oid + ' requested to leave the pool')
                if self.pool and not self.wait_for_autoremove:
                    self.wait_for_autoremove = True
                    eva.core.spawn(eva.api.remove_controller, self.full_id)
        except:
            eva.core.log_traceback()

    def register_mqtt(self):
        if self.mqtt_notifier:
            self.mqtt_notifier.handler_append('controller/{}/{}/events'.format(
                self.group, self.item_id),
                                              self.server_event_handler,
                                              qos=self.mqtt_notifier_qos)

    def unregister_mqtt(self):
        if self.mqtt_notifier:
            self.mqtt_notifier.handler_remove(
                'controller/{}/{}/events'.format(self.group, self.item_id),
                self.server_event_handler)

    def set_mqtt_notifier(self):
        self.mqtt_notifier = None
        self.mqtt_notifier_qos = None
        if self.mqtt_update:
            try:
                params = self.mqtt_update.split(':')
                n = params[0]
                notifier = eva.notify.get_notifier(n)
                if not notifier or notifier.notifier_type not in [
                        'mqtt', 'psrt'
                ]:
                    logging.error('%s: invalid mqtt/psrt notifier %s' % \
                            (self.oid, n))
                else:
                    self.mqtt_notifier = notifier
                    if len(params) > 1:
                        try:
                            self.mqtt_notifier_qos = int(params[1])
                        except:
                            logging.error('%s invalid mqtt notifier qos' % \
                                    self.oid)
                            eva.core.log_traceback()
            except:
                eva.core.log_traceback()

    def api_call(self, func, params=None, timeout=None):
        if not self.api or not self.enabled:
            return eva.client.apiclient.result_not_ready, None
        for tries in range(self.retries + 1):
            (code, result) = self.api.call(func,
                                           params,
                                           timeout,
                                           _debug=eva.core.config.debug)
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
            if not eva.core.is_shutdown_requested():
                logging.error('Remote controller access error %s, code %u' %
                              (self.api._uri, code))
            return code, None
        return code, result

    def management_api_call(self, func, params=None, timeout=None):
        if not self.api or not cloud_manager or not self.masterkey:
            return eva.client.apiclient.result_not_ready, None
        p = params.copy() if isinstance(params, dict) else {}
        p['k'] = self.masterkey
        for tries in range(self.retries + 1):
            (code, result) = self.api.call(func,
                                           p,
                                           timeout,
                                           _debug=eva.core.config.debug)
            if code not in [
                    eva.client.apiclient.result_server_error,
                    eva.client.apiclient.result_server_timeout
            ]:
                break
        return code, result

    def test(self):
        code, result = self.api_call('test')
        if code or not isinstance(result, dict):
            if eva.core.is_shutdown_requested():
                return False
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
            logging.error('Remote controller API %s has no master access' %
                          self.api._uri)
            return False
        return True

    def load_remote(self, need_type=None):
        if not self.enabled:
            return False
        result = self.test()
        if not result:
            if not self.static and self.pool and not self.wait_for_autoremove:
                self.wait_for_autoremove = True
                eva.core.spawn(eva.api.remove_controller, self.full_id)
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
            logging.warning(
                'Remote controller {} EVA version is {}, my: {}'.format(
                    self.full_id, result['version'], eva.core.version))
        self.item_id = result['system']
        if self.group != result['product_code']:
            self.set_group(result['product_code'])
            self.config_changed = True
        else:
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

    def save(self):
        if not self.item_id:
            return False
        else:
            return super().save() if self.static else True

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
            self.set_mqtt_notifier()
        if 'reload_interval' in data:
            self.reload_interval = data['reload_interval']
        if 'enabled' in data:
            self.enabled = data['enabled']
        if 'ws_state_events' in data:
            self.ws_state_events = data['ws_state_events']
        if 'ws_buf_ttl' in data:
            self.ws_buf_ttl = data['ws_buf_ttl']
        if 'compress' in data:
            self.api.use_compression = data['compress']
        super().update_config(data)

    def set_modified(self, save):
        super().set_modified(save)
        self.connected = False
        if self.enabled:
            eva.core.spawn(self.test)

    def get_reload_interval(self):
        return self.reload_interval

    def set_prop(self, prop, val=None, save=False):
        if prop == 'notify_events':
            return False
        elif prop == 'uri' and val:
            if self.api._uri != val:
                self.api.set_uri(val)
                self.log_set(prop, val)
                self.set_modified(save)
            return True
        elif prop == 'compress':
            try:
                v = eva.tools.val_to_boolean(val)
                if v is None:
                    v = False
                if v and self.api.protocol_mode != 1:
                    logging.warning(
                        'API compression is supported with MQTT only')
                if self.api.use_compression != v:
                    self.api.use_compression = v
                    self.log_set(prop, v)
                    self.set_modified(save)
                return True
            except:
                return False
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
                    self.api.set_timeout(float(val))
                    self.log_set(prop, val)
                    self.set_modified(save)
                    return True
                except:
                    return False
            else:
                self.api.set_timeout(eva.core.config.timeout / 2)
                self.set_modified(save)
                return True
        elif prop == 'retries':
            if val is not None:
                try:
                    v = int(val)
                    if v < 0:
                        return False
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
                if v is False:
                    return False
                if self.static != True:
                    self.static = True
                    self.log_set(prop, True)
                    self.set_modified(save)
                return True
            except:
                return False
        elif prop == 'ws_state_events':
            try:
                v = eva.tools.val_to_boolean(val)
                if v is None:
                    v = True
                if self.ws_state_events != v:
                    self.ws_state_events = v
                    if self.pool:
                        self.pool.remove(self.item_id)
                        self.pool.append(self)
                    self.log_set(prop, v)
                    self.set_modified(save)
                return True
            except:
                return False
        elif prop == 'ws_buf_ttl':
            try:
                if val is None:
                    v = 0
                else:
                    v = float(val)
                    if v < 0:
                        return False
                if self.ws_buf_ttl != v:
                    self.ws_buf_ttl = v
                    if self.pool:
                        self.pool.remove(self.item_id)
                        self.pool.append(self)
                    self.log_set(prop, v)
                    self.set_modified(save)
                return True
            except:
                return False
        elif prop == 'enabled':
            if not self.set_prop('static', 1):
                return False
            if val is not None:
                try:
                    v = eva.tools.val_to_boolean(val)
                    if v is None:
                        return False
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
                    if v is None:
                        return False
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
                self.set_mqtt_notifier()
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
                    if self.pool:
                        self.pool.restart_controller_reload_worker(self.item_id)
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
        if not self.item_id:
            return None
        d = {}
        d['static'] = self.static
        d['enabled'] = self.enabled
        d['compress'] = self.api.use_compression
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
            d['ws_state_events'] = self.ws_state_events
            d['ws_buf_ttl'] = self.ws_buf_ttl
        if info:
            d['connected'] = self.connected if self.enabled else False
            d['managed'] = True if cloud_manager and self.masterkey else False
            if self.api.protocol_mode == 0:
                d['proto'] = 'http'
            elif self.api.protocol_mode == 1:
                try:
                    d['proto'] = eva.notify.get_notifier(
                        self.api._notifier_id).notifier_type
                except:
                    d['proto'] = 'unknown'
            else:
                d['proto'] = 'unknown'
            d['version'] = self.version
            d['build'] = str(self.product_build)
            d['mqtt_update'] = self.mqtt_update
        d.update(super().serialize(full=full,
                                   config=config,
                                   info=info,
                                   props=props,
                                   notify=notify))
        if 'notify_events' in d:
            del d['notify_events']
        return d

    def destroy(self):
        super().destroy()
        if self.pool:
            eva.core.spawn(self.pool.remove, self.item_id)


class RemoteUC(RemoteController):

    def __init__(self, uc_id=None, api=None, mqtt_update=None, static=True):
        super().__init__(uc_id, 'remote_uc', api, mqtt_update, static)
        self.api.set_product('uc')
        self.set_group('uc')

    def create_remote_unit(self, state):
        return eva.client.remote_item.RemoteUnit(self, state)

    def create_remote_sensor(self, state):
        return eva.client.remote_item.RemoteSensor(self, state)

    def load_units(self):
        if not self.item_id:
            return None
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
        if not self.item_id:
            return None
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
        self.set_group('lm')

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
        if not self.item_id:
            return None
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
        if not self.item_id:
            return None
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
        if not self.item_id:
            return None
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

    def __init__(self, id=None):
        self.ctype = ''
        self.controllers = {}
        self.reload_workers = {}
        self.websocket_workers = {}
        self.management_lock = threading.Lock()
        self.item_management_lock = threading.Lock()
        self.action_history_by_id = {}
        self.action_history_lock = threading.Lock()
        self.id = id if id is not None else str(uuid.uuid4())
        self.action_cleaner = BackgroundIntervalWorker(
            name=f'{self.id}:action_cleaner',
            fn=self._run_action_cleaner,
            on_error=eva.core.log_traceback,
            loop='cleaners',
            delay=eva.core.config.action_cleaner_interval)
        self.pending = []
        self.pending_lock = threading.RLock()
        self.triggered = {}

    def cmd(self,
            controller_id,
            command,
            args=None,
            wait=None,
            timeout=None,
            stdin_data=None):
        if controller_id not in self.controllers:
            return eva.client.apiclient.result_not_found, None
        c = self.controllers[controller_id]
        p = {'c': command}
        if args is not None:
            p['a'] = args
        if wait is not None:
            p['w'] = wait
        if timeout is not None:
            p['t'] = timeout
        if stdin_data is not None:
            p['s'] = stdin_data
        return c.api_call('cmd', p)

    def append(self, controller, need_type=None):
        try:
            with self.pending_lock:
                if controller.api._uri in self.pending:
                    logging.debug(
                        f'Skipping adding {controller.api._uri} into pool, '
                        f'already pending')
                    return False
                else:
                    self.pending.append(controller.api._uri)
            try:
                if controller.load_remote(need_type=need_type) or \
                        controller.item_id != '':
                    if not self.management_lock.acquire(
                            timeout=eva.core.config.timeout):
                        logging.critical(
                            f'RemoteControllerPool::append locking broken'
                            f' ({controller.api._uri})')
                        eva.core.critical()
                        return False
                    try:
                        if controller.item_id in self.controllers:
                            logging.error(
                                'Unable to append controller {}, already exists'
                                .format(controller.full_id))
                            return False
                        self.controllers[controller.item_id] = controller
                        controller.pool = self
                        if controller.enabled:
                            return self.start_controller_reload_worker(
                                controller)
                        else:
                            return True
                    finally:
                        self.management_lock.release()
                return False
            finally:
                try:
                    with self.pending_lock:
                        self.pending.remove(controller.api._uri)
                except ValueError:
                    pass
        except:
            eva.core.log_traceback()

    def remove(self, controller_id):
        if not self.management_lock.acquire(timeout=eva.core.config.timeout):
            logging.critical('RemoteControllerPool::remove locking broken')
            eva.core.critical()
            return False
        try:
            try:
                del self.triggered[controller_id]
            except:
                pass
            if controller_id in self.controllers:
                self.stop_controller_reload_worker(controller_id, lock=False)
                del (self.controllers[controller_id])
                return True
            else:
                return False
        finally:
            self.management_lock.release()

    def enable(self, controller):
        controller_id = controller.item_id
        if controller_id not in self.reload_workers or \
                not self.reload_workers[controller_id].is_active():
            self.start_controller_reload_worker(controller, lock=True)

    def disable(self, controller_id):
        if controller_id in self.reload_workers and \
                self.reload_workers[controller_id].is_active():
            self.stop_controller_reload_worker(controller_id)

    def restart_controller_reload_worker(self, controller_id):
        worker = self.reload_workers.get(controller_id)
        controller = self.controllers[controller_id]
        if worker:
            if controller.reload_interval > 0:
                worker.restart(
                    _interval=self.controllers[controller_id].reload_interval)
            else:
                worker.stop()

    def start_controller_reload_worker(self, controller, lock=False):
        w = BackgroundIntervalWorker(name='reload_controller:' +
                                     controller.item_type + '/' +
                                     controller.item_id,
                                     interval=controller.reload_interval,
                                     o=controller,
                                     fn=self._run_reload_controller)
        if lock and \
                not self.management_lock.acquire(
                        timeout=eva.core.config.timeout):
            logging.critical(
                'RemoteControllerPool::start_controller_reload_' + \
                        'thread locking broken')
            eva.core.critical()
            return False
        try:
            if eva.core.is_shutdown_requested():
                return False
            self.reload_workers[controller.item_id] = w
            w.start()
            if not controller.mqtt_update and controller.api._uri.startswith(
                    'http'):
                worker = WebSocketWorker(name='ws_client:' + controller.oid,
                                         controller=controller,
                                         pool=self,
                                         o=self)
                self.websocket_workers[controller.item_id] = worker
                worker.start()
            else:
                controller.register_mqtt()
            return True
        except:
            eva.core.log_traceback()
        finally:
            if lock:
                self.management_lock.release()

    def process_ws_data(self, data, controller):
        if data['s'] == 'state':
            self.process_state(data['d'], controller)

    def stop_controller_reload_worker(self, controller_id, lock=True):
        if lock and not self.management_lock.acquire(
                timeout=eva.core.config.timeout):
            logging.critical(
                'RemoteControllerPool::stop_controller_reload_' + \
                        'thread locking broken')
            eva.core.critical()
            return False
        try:
            if controller_id in self.websocket_workers:
                try:
                    self.websocket_workers[controller_id].stop(wait=False)
                    del self.websocket_workers[controller_id]
                except:
                    eva.core.log_traceback()
            else:
                self.controllers[controller_id].unregister_mqtt()
            try:
                if controller_id in self.reload_workers:
                    self.reload_workers[controller_id].stop()
                    del (self.reload_workers[controller_id])
            except:
                eva.core.log_traceback()
        finally:
            if lock:
                self.management_lock.release()

    def _run_reload_controller(self, o, **kwargs):
        try:
            self.reload_controller(o.item_id)
        except:
            logging.error('%s reload error' % o.oid)
            eva.core.log_traceback()

    def manually_reload_controller(self, controller_id):
        worker = self.reload_workers.get(controller_id)
        if worker:
            worker.trigger_threadsafe(skip=True)
        return self.reload_controller(controller_id)

    def _t_trigger_reload_controller(self, controller_id, with_delay=False):
        try:
            if with_delay:
                time.sleep(2 + random.randint(0, 200) / 100)
            worker = self.reload_workers.get(controller_id)
            if worker:
                worker.trigger_threadsafe()
        except Exception as e:
            eva.core.log_traceback()

    def trigger_reload_controller(self, controller_id, with_delay=True):
        with self.management_lock:
            if controller_id not in self.controllers:
                logging.warning(
                    f'trigger event '
                    f'for non-existing controller: {self.ctype}/{controller_id}'
                )
                return
            last_triggered = self.triggered.get(controller_id, 0)
            t = time.perf_counter()
            if last_triggered + self.controllers[
                    controller_id].reload_interval > t:
                logging.warning(f'{self.ctype}/{controller_id} triggered '
                                f'too frequently. refusing')
                return
            self.triggered[controller_id] = t
        eva.core.spawn(self._t_trigger_reload_controller,
                       controller_id,
                       with_delay=with_delay)

    def reload_controller(self, controller_id):
        if controller_id == 'ALL':
            success = True
            for c in self.controllers.copy():
                if self.controllers[c].enabled:
                    try:
                        if not self.reload_controller(c):
                            raise Exception('reload error')
                    except:
                        eva.core.log_traceback()
                        success = False
            return success
        if not controller_id in self.controllers:
            return None
        controller = self.controllers[controller_id]
        controller.last_reload_time = time.perf_counter()
        result = controller.load_remote()
        if result and controller_id in self.websocket_workers:
            self.websocket_workers[controller_id].need_reload_flag = True
        return result

    def start(self):
        eva.core.stop.append(self.stop)
        if eva.core.config.keep_action_history:
            self.action_cleaner.start()

    def stop(self):
        if eva.core.config.keep_action_history:
            self.action_cleaner.stop()
        for i, c in self.controllers.items():
            self.stop_controller_reload_worker(c.item_id, lock=False)
        for i, c in self.controllers.items():
            if c.item_id in self.reload_workers:
                try:
                    self.reload_workers[c.item_id].join()
                except:
                    pass

    async def _run_action_cleaner(self, **kwargs):
        if not self.action_history_lock.acquire(
                timeout=eva.core.config.timeout):
            logging.critical(
                'RemoteControllerPool::_t_action_cleaner locking broken')
            eva.core.critical()
            return
        _actions = self.action_history_by_id.copy()
        self.action_history_lock.release()
        for u, a in _actions.items():
            if a['t'] < time.time() - eva.core.config.keep_action_history:
                logging.debug('action %s too old, removing' % u)
                self.action_history_remove(a)

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ctype = 'uc'
        self.units = {}
        self.units_by_controller = {}
        self.controllers_by_unit = {}
        self.sensors = {}
        self.sensors_by_controller = {}

    def process_state(self, states, controller):
        if not self.item_management_lock.acquire(
                timeout=eva.core.config.timeout):
            logging.critical('RemoteUCPool::process_state locking broken')
            eva.core.critical()
            return False
        timestamp = time.time()
        try:
            for s in states if isinstance(states, list) else [states]:
                if s['type'] == 'unit':
                    if s['full_id'] in self.units:
                        u = self.units[s['full_id']]
                        result = u.update_set_state(
                            status=s['status'],
                            value=s['value'],
                            notify=False,
                            timestamp=float(
                                s.get('set_time', s.get('t', timestamp))),
                            ieid=eva.core.parse_ieid(s.get('ieid')))
                        if result:
                            need_notify = u.update_nstate(nstatus=s['nstatus'],
                                                          nvalue=s['nvalue'])
                            if u.action_enabled != s['action_enabled']:
                                u.action_enabled = s['action_enabled']
                                need_notify = True
                            if result == 2 or need_notify:
                                u.notify()
                    else:
                        logging.debug(
                            'WS state for {} skipped, not found'.format(
                                s['oid']))
                elif s['type'] == 'sensor':
                    if s['full_id'] in self.sensors:
                        self.sensors[s['full_id']].update_set_state(
                            status=s['status'],
                            value=s['value'],
                            timestamp=float(
                                s.get('set_time', s.get('t', timestamp))),
                            ieid=eva.core.parse_ieid(s.get('ieid')))
                    else:
                        logging.debug(
                            'WS state for {} skipped, not found'.format(
                                s['oid']))
                else:
                    logging.warning('WS: unknown item type from {}: {}'.format(
                        controller.oid, s['type']))
        finally:
            self.item_management_lock.release()

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
        if value is not None:
            p['v'] = value
        if wait:
            p['w'] = wait
        if uuid:
            p['u'] = uuid
        if priority:
            p['p'] = priority
        if q:
            p['q'] = q
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
        if wait:
            p['w'] = wait
        if uuid:
            p['u'] = uuid
        if priority:
            p['p'] = priority
        if q:
            p['q'] = q
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
        if group:
            p['g'] = group
        if status:
            p['s'] = status
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
        if full and not super().remove(controller_id):
            return False
        if not self.item_management_lock.acquire(
                timeout=eva.core.config.timeout):
            logging.critical('RemoteUCPool::remove locking broken')
            eva.core.critical()
            return False
        try:
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
        finally:
            self.item_management_lock.release()

    def reload_controller(self, controller_id):
        result = super().reload_controller(controller_id)
        if not result:
            return result
        if controller_id == 'ALL':
            return True
        try:
            uc = self.controllers[controller_id]
        except KeyError:
            # controller removed from pool
            logging.error('Failed to reload %s, not found in pool' %
                          controller_id)
            return False
        try:
            units = uc.load_units()
            if units is None:
                logging.error('Failed to reload units from %s' % controller_id)
                return False
            sensors = uc.load_sensors()
            if sensors is None:
                logging.error('Failed to reload sensors from %s' %
                              controller_id)
                return False
            if not self.item_management_lock.acquire(
                    timeout=eva.core.config.timeout):
                logging.critical(
                    'RemoteUCPool::reload_controller locking broken')
                eva.core.critical()
                return False
            try:
                timestamp = time.time()
                p = {}
                for u in units:
                    if u.full_id in self.units and u.controller != uc:
                        self.units[u.full_id].destroy()
                    if not u.full_id in self.units or \
                            self.units[u.full_id].is_destroyed():
                        self.units[u.full_id] = u
                        self.controllers_by_unit[u.full_id] = uc
                        u.start_processors()
                        u.notify(skip_subscribed_mqtt=True)
                    else:
                        unit = self.units[u.full_id]
                        result = unit.update_set_state(
                            status=u.status,
                            value=u.value,
                            notify=False,
                            timestamp=u.set_time if u.set_time else timestamp,
                            ieid=u.ieid)
                        if result:
                            need_notify = unit.update_nstate(nstatus=u.nstatus,
                                                             nvalue=u.nvalue)
                            if unit.action_enabled != u.action_enabled:
                                unit.action_enabled = u.action_enabled
                                need_notify = True
                            if result == 2 or need_notify:
                                unit.notify()
                    p[u.full_id] = u
                    _u = self.get_unit(u.full_id)
                    if _u:
                        _u.update_config(u.serialize(config=True))
                if controller_id in self.units_by_controller:
                    for i in self.units_by_controller[controller_id].copy(
                    ).keys():
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
                logging.debug('Loaded %u units from %s' %
                              (len(p), controller_id))
                timestamp = time.time()
                p = {}
                for u in sensors:
                    if u.full_id in self.sensors and u.controller != uc:
                        self.sensors[u.full_id].destroy()
                    if not u.full_id in self.sensors or \
                            self.sensors[u.full_id].is_destroyed():
                        self.sensors[u.full_id] = u
                        u.start_processors()
                        u.notify(skip_subscribed_mqtt=True)
                    else:
                        self.sensors[u.full_id].update_set_state(
                            status=u.status,
                            value=u.value,
                            timestamp=u.set_time if u.set_time else timestamp,
                            ieid=u.ieid)
                    p[u.full_id] = u
                    _u = self.get_sensor(u.full_id)
                    if _u:
                        _u.update_config(u.serialize(config=True))
                if controller_id in self.sensors_by_controller:
                    for i in self.sensors_by_controller[controller_id].copy(
                    ).keys():
                        if i not in p:
                            self.sensors[i].destroy()
                            try:
                                del (self.sensors[i])
                                del (self.sensors_by_controller[controller_id]
                                     [i])
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
                return True
            finally:
                self.item_management_lock.release()
        except:
            logging.error('failed to reload controller ' + controller_id)
            eva.core.log_traceback()
            return False

    def cmd(self,
            controller_id,
            command,
            args=None,
            wait=None,
            timeout=None,
            stdin_data=None):
        if controller_id.find('/') == -1:
            _controller_id = controller_id
        else:
            try:
                t, _controller_id = controller_id.split('/')
                if t != 'uc':
                    return None
            except:
                return None
        return super().cmd(controller_id=_controller_id,
                           command=command,
                           args=args,
                           wait=wait,
                           timeout=timeout,
                           stdin_data=stdin_data)

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
                if t != 'uc':
                    return None
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
        return self.manage_device(controller_id=controller_id,
                                  device_func='deploy_device',
                                  device_tpl=device_tpl,
                                  cfg=cfg,
                                  save=save)

    def update_device(self, controller_id, device_tpl, cfg=None, save=None):
        return self.manage_device(controller_id=controller_id,
                                  device_func='update_device',
                                  device_tpl=device_tpl,
                                  cfg=cfg,
                                  save=save)

    def undeploy_device(self, controller_id, device_tpl, cfg=None):
        return self.manage_device(controller_id=controller_id,
                                  device_func='undeploy_device',
                                  device_tpl=device_tpl,
                                  cfg=cfg)


class RemoteLMPool(RemoteControllerPool):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ctype = 'lm'
        self.lvars = {}
        self.lvars_by_controller = {}
        self.controllers_by_lvar = {}

        self.macros = {}
        self.macros_by_controller = {}
        self.controllers_by_macro = {}

        self.cycles = {}
        self.cycles_by_controller = {}
        self.controllers_by_cycle = {}

    def process_state(self, states, controller):
        if not self.item_management_lock.acquire(
                timeout=eva.core.config.timeout):
            logging.critical('RemoteLMPool::process_state locking broken')
            eva.core.critical()
            return False
        try:
            for s in states if isinstance(states, list) else [states]:
                if s['type'] == 'lvar':
                    _u = self.get_lvar(s['full_id'])
                    if _u:
                        _u.set_state_from_serialized(s)
                    else:
                        logging.debug(
                            'WS state for {} skipped, not found'.format(
                                s['oid']))
                elif s['type'] == 'lcycle':
                    _u = self.get_cycle(s['full_id'])
                    if _u:
                        _u.set_state_from_serialized(s)
                    else:
                        logging.debug(
                            'WS state for {} skipped, not found'.format(
                                s['oid']))
                elif s['type'] not in ['unit', 'sensor']:
                    logging.warning('WS: unknown item type from {}: {}'.format(
                        controller.oid, s['type']))
        finally:
            self.item_management_lock.release()

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
        if status is not None:
            p['s'] = status
        if value is not None:
            p['v'] = value
        return lm.api_call('set', p)

    def reset(self, lvar_id):
        if not lvar_id in self.controllers_by_lvar:
            return apiclient.result_not_found, None
        lm = self.controllers_by_lvar[lvar_id]
        p = {'i': lvar_id}
        return lm.api_call('reset', p)

    def clear(self, lvar_id):
        if not lvar_id in self.controllers_by_lvar:
            return apiclient.result_not_found, None
        lm = self.controllers_by_lvar[lvar_id]
        p = {'i': lvar_id}
        return lm.api_call('clear', p)

    def toggle(self, lvar_id):
        if not lvar_id in self.controllers_by_lvar:
            return apiclient.result_not_found, None
        lm = self.controllers_by_lvar[lvar_id]
        p = {'i': lvar_id}
        return lm.api_call('toggle', p)

    def increment(self, lvar_id):
        if not lvar_id in self.controllers_by_lvar:
            return apiclient.result_not_found, None
        lm = self.controllers_by_lvar[lvar_id]
        p = {'i': lvar_id}
        return lm.api_call('increment', p)

    def decrement(self, lvar_id):
        if not lvar_id in self.controllers_by_lvar:
            return apiclient.result_not_found, None
        lm = self.controllers_by_lvar[lvar_id]
        p = {'i': lvar_id}
        return lm.api_call('decrement', p)

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
        if args:
            p['a'] = args
        if kwargs:
            p['kw'] = kwargs
        if wait:
            p['w'] = wait
        if uuid:
            p['u'] = uuid
        if priority:
            p['p'] = priority
        if q_timeout:
            p['q'] = q_timeout
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
        if group:
            p['g'] = group
        if status:
            p['s'] = status
        if not i or not i in self.controllers_by_macro:
            return apiclient.result_not_found, None
        lm = self.controllers_by_macro[i]
        return lm.api_call('result', p)

    def disable(self, controller_id):
        super().disable(controller_id)
        self.remove(controller_id, full=False)

    def remove(self, controller_id, full=True):
        if full and not super().remove(controller_id):
            return False
        if not self.item_management_lock.acquire(
                timeout=eva.core.config.timeout):
            logging.critical('RemoteLMPool::remove locking broken')
            eva.core.critical()
            return False
        try:
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
            return True
        finally:
            self.item_management_lock.release()

    def reload_controller(self, controller_id):
        result = super().reload_controller(controller_id)
        if not result:
            return result
        if controller_id == 'ALL':
            return True
        lm = self.controllers[controller_id]
        try:
            lvars = lm.load_lvars()
            if lvars is None:
                logging.error('Failed to reload lvars from %s' % controller_id)
                return False
            macros = lm.load_macros(skip_system=True)
            if macros is None:
                logging.error('Failed to reload macros from %s' % controller_id)
                return False
            cycles = lm.load_cycles()
            if cycles is None:
                logging.error('Failed to reload cycles from %s' % controller_id)
                return False
            if not self.item_management_lock.acquire(
                    timeout=eva.core.config.timeout):
                logging.critical(
                    'RemoteLMPool::reload_controller locking broken')
                eva.core.critical()
                return False
            try:
                timestamp = time.time()
                p = {}
                for u in lvars:
                    if u.full_id in self.lvars and u.controller != lm:
                        self.lvars[u.full_id].destroy()
                    if not u.full_id in self.lvars or \
                            self.lvars[u.full_id].is_destroyed():
                        self.lvars[u.full_id] = u
                        self.controllers_by_lvar[u.full_id] = lm
                        u.start_processors()
                        u.notify(skip_subscribed_mqtt=True)
                    p[u.full_id] = u
                    _u = self.get_lvar(u.full_id)
                    if _u:
                        _u.set_state_from_serialized(u.serialize())
                if controller_id in self.lvars_by_controller:
                    for i in self.lvars_by_controller[controller_id].copy(
                    ).keys():
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
                logging.debug('Loaded %u lvars from %s' %
                              (len(p), controller_id))
                p = {}
                for u in macros:
                    if u.full_id in self.macros and u.controller != lm:
                        self.macros[u.full_id].destroy()
                    if not u.full_id in self.macros or \
                            self.macros[u.full_id].is_destroyed():
                        self.macros[u.full_id] = u
                        self.controllers_by_macro[u.full_id] = lm
                        u.start_processors()
                        u.notify(skip_subscribed_mqtt=True)
                    p[u.full_id] = u
                    _u = self.get_macro(u.full_id)
                    if _u:
                        _u.update_config(u.serialize(config=True))
                if controller_id in self.macros_by_controller:
                    for i in self.macros_by_controller[controller_id].copy(
                    ).keys():
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
                logging.debug('Loaded %u macros from %s' %
                              (len(p), controller_id))
                p = {}
                for u in cycles:
                    if u.full_id in self.cycles and u.controller != lm:
                        self.cycles[u.full_id].destroy()
                    if not u.full_id in self.cycles or \
                            self.cycles[u.full_id].is_destroyed():
                        self.cycles[u.full_id] = u
                        self.controllers_by_cycle[u.full_id] = lm
                        u.start_processors()
                        u.notify(skip_subscribed_mqtt=True)
                    p[u.full_id] = u
                    _u = self.get_cycle(u.full_id)
                    if _u:
                        _u.set_state_from_serialized(u.serialize())
                if controller_id in self.cycles_by_controller:
                    for i in self.cycles_by_controller[controller_id].copy(
                    ).keys():
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
                logging.debug('Loaded %u cycles from %s' %
                              (len(p), controller_id))
                return True
            finally:
                self.item_management_lock.release()
        except:
            logging.error('failed to reload controller ' + controller_id)
            eva.core.log_traceback()
            return False
