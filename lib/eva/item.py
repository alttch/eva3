__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.1"

import copy
import os
import threading
import time
import uuid
import queue
import logging
import rapidjson
import eva.registry

import eva.core
import eva.notify

from eva.tools import format_json
from eva.tools import val_to_boolean
from eva.tools import is_oid
from eva.tools import parse_oid
from eva.tools import fmt_time
from eva.tools import _p_periods
from eva.tools import compare
# from evacpp.evacpp import GenericAction
from eva.generic import GenericAction

from eva.exceptions import ResourceNotFound
from eva.exceptions import FunctionFailed
from eva.exceptions import InvalidParameter
from eva.exceptions import MethodNotImplemented

from eva.generic import ia_status_created
from eva.generic import ia_status_pending
from eva.generic import ia_status_queued
from eva.generic import ia_status_refused
from eva.generic import ia_status_dead
from eva.generic import ia_status_canceled
from eva.generic import ia_status_ignored
from eva.generic import ia_status_running
from eva.generic import ia_status_failed
from eva.generic import ia_status_terminated
from eva.generic import ia_status_completed

from neotasker import task_supervisor
from neotasker import BackgroundEventWorker, BackgroundQueueWorker


class Item(object):

    def __init__(self, item_id=None, item_type=None, item_group=None, oid=None):
        if oid:
            item_type, i = parse_oid(oid)
            if '/' in i:
                item_group, item_id = i.rsplit('/', 1)
            else:
                item_group = 'nogroup'
                item_id = i
        elif item_id is None or item_type is None:
            raise RuntimeError('item init failed, no id provided')
        self.item_id = item_id
        self.item_type = item_type
        self.set_group(item_group if item_group else 'nogroup')
        self.description = ''
        self._destroyed = False
        self.config_changed = False
        self.config_file_exists = False
        self.notify_events = 2  # 2 - all events, 1 - state only, 0 - no

    def set_defaults(self, fields):
        defaults = eva.core.defaults.get(self.item_type, {})
        for f in fields:
            if f in defaults:
                self.set_prop(f, defaults[f])

    def set_group(self, group=None):
        if group:
            self.group = group
        else:
            self.group = 'nogroup'
        if group.startswith('_') or group.endswith('_'):
            raise FunctionFailed(
                f'group name can not start / end with underscores: {group}')
        if '___' in group:
            raise FunctionFailed(f'group name can not contain triple '
                                 f'underscores (reserved): {group}')
        self.full_id = self.group + '/' + self.item_id
        self.oid = self.item_type + ':' + self.full_id

    def update_config(self, data):
        if 'group' in data:
            self.set_group(data['group'])
        if 'description' in data:
            self.description = data['description']
        if 'notify_events' in data:
            self.notify_events = data['notify_events']
        self.config_changed = True

    def set_prop(self, prop, val=None, save=False):
        if prop == 'description':
            if val is None:
                v = ''
            else:
                v = val
            if self.description != v:
                self.description = v
                self.log_set(prop, v)
                self.set_modified(save)
            return True
        elif prop == 'notify_events':
            try:
                v = int(val)
                if v >= 0 and v <= 2:
                    if self.notify_events != v:
                        self.notify_events = v
                        self.log_set(prop, v)
                        self.set_modified(save)
                    return True
                else:
                    raise Exception
            except:
                return False
        return False

    def log_set(self, prop, val):
        logging.info('set %s.%s = %s' % (self.oid, prop, val))

    def item_env(self):
        e = {
            'EVA_ITEM_ID': self.item_id,
            'EVA_ITEM_TYPE': self.item_type,
            'EVA_ITEM_GROUP': self.group,
            'EVA_ITEM_PARENT_GROUP': self.group.split('/')[-1],
            'EVA_ITEM_ID_FULL': self.group + '/' + self.item_id,
            'EVA_ITEM_OID': self.oid
        }
        return e

    def copy(self):
        return copy.copy(self)

    def notify(self,
               retain=None,
               skip_subscribed_mqtt=False,
               for_destroy=False):
        if not self.notify_events:
            return
        try:
            if skip_subscribed_mqtt:
                s = self
            else:
                s = None
            d = self.serialize(notify=True)
            if for_destroy:
                d['destroyed'] = True
            eva.notify.notify('state',
                              data=(self, d),
                              retain=retain,
                              skip_subscribed_mqtt_item=s)
        except:
            eva.core.log_traceback()

    def serialize(self,
                  full=False,
                  config=False,
                  info=False,
                  props=False,
                  notify=False):
        d = {}
        if not props:
            d['id'] = self.item_id
            d['type'] = self.item_type
            d['group'] = self.group
        if not props:
            d['full_id'] = self.group + '/' + self.item_id
            d['oid'] = self.oid
        if full or config or info or props:
            if self.notify_events != 2 or props:
                d['notify_events'] = self.notify_events
            if not config or self.description != '':
                d['description'] = self.description
        if full:
            d['config_changed'] = self.config_changed
        if info:
            d['full_id'] = self.full_id
            d['oid'] = self.oid
        return d

    def get_rkn(self):
        return f'inventory/{self.item_type}/{self.full_id}'

    def get_rskn(self):
        return f'state/{self.item_type}/{self.full_id}'

    def load(self, data=None):
        try:
            if data is None:
                data = eva.registry.key_get(self.get_rkn())
            if data['oid'] != self.oid:
                logging.error(f'{data["oid"]} != {self.oid}')
                raise ValueError('id mismatch')
            self.update_config(data)
            self.config_changed = False
            self.config_file_exists = True
            return True
        except Exception as e:
            logging.error(f'can not load {self.oid}: {e}')
            eva.core.log_traceback()
            return False

    def save(self):
        data = self.serialize(config=True)
        logging.debug(f'Saving {self.oid} configuration')
        try:
            eva.registry.key_set(self.get_rkn(), data)
            self.config_changed = False
            self.config_file_exists = True
            return True
        except Exception as e:
            logging.error(f'can not save {self.oid} config: {e}')
            eva.core.log_traceback()
            return False

    def set_modified(self, save):
        if save:
            self.save()
        else:
            self.config_changed = True

    def start_processors(self):
        logging.debug('%s processors started' % self.oid)

    def stop_processors(self):
        logging.debug('%s processors stopped' % self.oid)

    def destroy(self):
        self._destroyed = True
        self.stop_processors()

    def is_destroyed(self):
        return self._destroyed


class PhysicalItem(Item):

    def __init__(self, item_id=None, item_type=None, **kwargs):
        super().__init__(item_id, item_type, **kwargs)
        self.loc_x = None
        self.loc_y = None
        self.loc_z = None
        self.location = ''

    def update_config(self, data):
        if 'location' in data:
            self.update_loc(data['location'])
        super().update_config(data)

    def set_prop(self, prop, val=None, save=False):
        if prop == 'location':
            if val is None:
                v = ''
            else:
                v = val
            if self.location != v:
                self.update_loc(v)
                self.log_set(prop, v)
                self.set_modified(save)
            return True
        else:
            return super().set_prop(prop, val, save)

    def update_loc(self, loc):
        self.loc_x = None
        self.loc_y = None
        self.loc_z = None
        if loc and loc.find(':') != -1:
            l = loc.split(':')
            try:
                self.loc_x = float(l[0])
                self.loc_y = float(l[1])
                if len(l) > 2:
                    self.loc_z = float(l[2])
            except:
                self.loc_x = None
                self.loc_y = None
                self.loc_z = None
        self.location = loc

    def serialize(self,
                  full=False,
                  config=False,
                  info=False,
                  props=False,
                  notify=False):
        d = {}
        if config or props:
            if self.location != '':
                d['location'] = self.location
            elif props:
                d['location'] = None
        if full:
            d['location'] = self.location
            d['loc_x'] = self.loc_x
            d['loc_y'] = self.loc_y
            d['loc_z'] = self.loc_z
        d.update(super().serialize(full=full,
                                   config=config,
                                   info=info,
                                   props=props,
                                   notify=notify))
        return d


class UpdatableItem(Item):

    def __init__(self, item_id=None, item_type=None, **kwargs):
        super().__init__(item_id, item_type, **kwargs)
        self.update_exec = None
        self.update_interval = 0
        self.update_delay = 0
        self.update_timeout = eva.core.config.timeout
        self._update_timeout = None
        self.update_processor = BackgroundEventWorker(
            o=self,
            on_error=eva.core.log_traceback,
            fn=self._run_update_processor)
        self.update_lock = threading.RLock()
        self.update_scheduler = None
        self.update_scheduler_lock = threading.Lock()
        self.expiration_checker = None
        self.expiration_checker_lock = threading.Lock()
        self._updates_allowed = True
        self.update_xc = None
        # default status: 0 - off, 1 - on, -1 - error
        d = eva.core.defaults.get(item_type, {})
        try:
            self.status = int(d.get('status', 0))
        except ValueError:
            logging.error(f'Invalid default status for {item_type}')
            self.status = 0
        self.value = d.get('value', '')
        if self.value is None:
            self.value = ''
        else:
            self.value = str(self.value)
        self.set_time = time.time()
        self.state_set_time = time.perf_counter()
        self.ieid = [eva.core.get_boot_id(), 1]
        self.expires = 0
        self.mqtt_update = None
        self.mqtt_update_notifier = None
        self.mqtt_update_qos = 1
        self.mqtt_update_topics = ['', 'status', 'value']
        self._mqtt_updates_allowed = True
        self._expire_on_any = False
        self.allow_mqtt_updates_from_controllers = False

    def update_config(self, data):
        if 'expires' in data:
            self.expires = data['expires']
        if 'update_exec' in data:
            self.update_exec = data['update_exec']
        if 'update_interval' in data:
            self.update_interval = data['update_interval']
        if 'update_delay' in data:
            self.update_delay = data['update_delay']
        if 'update_timeout' in data:
            self.update_timeout = data['update_timeout']
            self._update_timeout = data['update_timeout']
        if 'mqtt_update' in data and data['mqtt_update']:
            self.mqtt_update = data['mqtt_update']
            params = data['mqtt_update'].split(':')
            n = params[0]
            notifier = eva.notify.get_notifier(n)
            if not notifier or notifier.notifier_type != 'mqtt':
                logging.error('%s: invalid mqtt notifier %s' % \
                        (self.oid, n))
            else:
                self.mqtt_update_notifier = n
                if len(params) > 1:
                    try:
                        self.mqtt_update_qos = int(params[1])
                    except:
                        logging.error('%s invalid mqtt notifier qos' % \
                                self.oid)
                        eva.core.log_traceback()
        super().update_config(data)

    def set_prop(self, prop, val=None, save=False):
        if prop == 'expires':
            if val is None:
                expires = 0
            else:
                try:
                    expires = float(val)
                except:
                    return False
            if self.expires != expires:
                self.expires = expires
                self.log_set(prop, expires)
                self.set_modified(save)
                if not expires:
                    self.stop_expiration_checker()
                else:
                    self.set_time = time.time()
                    self.start_expiration_checker()
            return True
        elif prop == 'update_exec':
            if self.update_exec != val:
                self.update_exec = val
                self.log_set(prop, val)
                self.set_modified(save)
            return True
        elif prop == 'update_interval':
            if val is None:
                update_interval = 0
            else:
                try:
                    update_interval = float(val)
                except:
                    return False
            if update_interval < 0:
                return False
            if self.update_interval != update_interval:
                self.update_interval = update_interval
                self.log_set(prop, update_interval)
                self.set_modified(save)
                if not update_interval:
                    self.stop_update_scheduler()
                else:
                    self.start_update_scheduler()
            return True
        elif prop == 'update_delay':
            if val is None:
                update_delay = 0
            else:
                try:
                    update_delay = float(val)
                except:
                    return False
            if update_delay < 0:
                return False
            if self.update_delay != update_delay:
                self.update_delay = update_delay
                self.log_set(prop, update_delay)
                self.set_modified(save)
            return True
        elif prop == 'update_timeout':
            if val is None:
                if self._update_timeout is not None:
                    import eva.core
                    self.update_timeout = eva.core.config.timeout
                    self._update_timeout = None
                    self.log_set(prop, None)
                    self.set_modified(save)
            else:
                try:
                    update_timeout = float(val)
                except:
                    return False
                if update_timeout <= 0:
                    return False
                if self._update_timeout != update_timeout:
                    self._update_timeout = update_timeout
                    self.update_timeout = update_timeout
                    self.log_set(prop, update_timeout)
                    self.set_modified(save)
            return True
        elif prop == 'mqtt_update' and self._mqtt_updates_allowed:
            if val is None:
                if self.mqtt_update is not None:
                    self.unsubscribe_mqtt_update()
                    self.mqtt_update = None
                    self.mqtt_update_notifier = None
                    self.mqtt_update_qos = 1
                    self.log_set(prop, None)
                    self.set_modified(save)
            else:
                params = val.split(':')
                n = params[0]
                import eva.notify
                notifier = eva.notify.get_notifier(n)
                if not notifier or notifier.notifier_type != 'mqtt':
                    return False
                if len(params) > 1:
                    try:
                        qos = int(params[1])
                    except:
                        return False
                else:
                    qos = self.mqtt_update_qos
                if self.mqtt_update_notifier != n or \
                        self.mqtt_update_qos != qos:
                    self.unsubscribe_mqtt_update()
                    self.mqtt_update = val
                    self.mqtt_update_notifier = n
                    self.mqtt_update_qos = qos
                    self.subscribe_mqtt_update()
                    self.log_set(prop, val)
                    self.set_modified(save)
            return True
        else:
            return super().set_prop(prop, val, save)

    def start_processors(self):
        self.update_processor.set_name('update_processor:{}'.format(self.oid))
        self.subscribe_mqtt_update()
        self.start_update_processor()
        self.start_update_scheduler()
        self.start_expiration_checker()
        super().start_processors()

    def stop_processors(self):
        self.unsubscribe_mqtt_update()
        self.stop_update_processor()
        self.stop_update_scheduler()
        self.stop_expiration_checker()
        super().stop_processors()

    def subscribe_mqtt_update(self):
        if not self.mqtt_update or \
                not self._mqtt_updates_allowed:
            return False
        notifier = eva.notify.get_notifier(self.mqtt_update_notifier)
        if not notifier or notifier.notifier_type[:4] != 'mqtt':
            return False
        try:
            notifier.update_item_append(self)
        except:
            logging.error('%s mqtt subscribe failed' % self.oid)
            eva.core.log_traceback()
            return False
        return True

    def unsubscribe_mqtt_update(self):
        if not self.mqtt_update or \
                not self._mqtt_updates_allowed:
            return False
        notifier = eva.notify.get_notifier(self.mqtt_update_notifier)
        if not notifier or notifier.notifier_type[:4] != 'mqtt':
            return False
        try:
            notifier.update_item_remove(self)
        except:
            eva.core.log_traceback()
            return False
        return True

    def start_update_processor(self):
        self.update_processor.start()

    def stop_update_processor(self):
        self.update_processor.stop()

    def start_update_scheduler(self):
        with self.update_scheduler_lock:
            if self.update_interval:
                if self.update_scheduler:
                    self.update_scheduler.cancel()
                    self.update_scheduler = None
                self.update_scheduler = task_supervisor.create_async_job(
                    target=self._job_update_scheduler,
                    interval=self.update_interval)

    def stop_update_scheduler(self):
        with self.update_scheduler_lock:
            if self.update_scheduler:
                self.update_scheduler.cancel()
                self.update_scheduler = None

    def start_expiration_checker(self):
        with self.expiration_checker_lock:
            if self.expires and self.status != -1 and \
                    (self.status != 0 or self._expire_on_any):
                if self.expiration_checker:
                    self.expiration_checker.cancel()
                    self.expiration_checker = None
                self.expiration_checker = task_supervisor.create_async_job(
                    target=self._job_expiration_checker,
                    timer=self.expires,
                    number=1)

    def stop_expiration_checker(self):
        with self.expiration_checker_lock:
            if self.expiration_checker:
                self.expiration_checker.cancel()
                self.expiration_checker = None

    def updates_allowed(self):
        return self._updates_allowed

    def disable_updates(self):
        with self.update_lock:
            self._updates_allowed = False

    def enable_updates(self):
        self._updates_allowed = True

    def update_run_args(self):
        return ()

    async def _job_expiration_checker(self):
        logging.debug(f'{self.oid} expired, resetting status/value')
        self.set_expired()

    def is_expired(self):
        return time.perf_counter() - self.state_set_time > self.expires \
                if self.expires else False

    def set_expired(self):
        if self.status == -1 and self.value == '':
            return False
        self.update_set_state(status=-1, value='')
        return True

    def update(self):
        if self.updates_allowed() and not self.is_destroyed():
            self.update_processor.trigger()

    async def _run_update_processor(self, **kwargs):
        eva.core.spawn(self._perform_update, **kwargs)

    def _perform_update(self, **kwargs):
        logging.debug('updating {}'.format(self.oid))
        try:
            if self.update_delay:
                time.sleep(self.update_delay)
            self.update_log_run()
            self.update_before_run()
            xc = self.get_update_xc(**kwargs)
            self.update_xc = xc
            xc.run()
            if xc.exitcode < 0:
                logging.error('update %s terminated' % self.oid)
            elif xc.exitcode > 0:
                logging.error('update %s failed, code %u' % \
                        (self.oid, xc.exitcode))
            else:
                if self.updates_allowed():
                    self.update_after_run(xc.out)
        except:
            logging.error('update %s failed' % self.oid)
            eva.core.log_traceback()

    async def _job_update_scheduler(self):
        if self.updates_allowed():
            logging.debug('{} scheduling update'.format(self.oid))
            await self.update_processor.trigger()

    def get_update_xc(self, **kwargs):
        return eva.runner.ExternalProcess(fname=self.update_exec,
                                          item=self,
                                          env=self.update_env(),
                                          update=True,
                                          args=self.update_run_args(),
                                          timeout=self.update_timeout)

    def update_env(self):
        return {}

    def update_log_run(self):
        logging.debug('performing update for %s' % self.oid)

    def update_before_run(self):
        pass

    def update_expiration(self):
        self.state_set_time = time.perf_counter()
        self.start_expiration_checker()

    def update_after_run(self, update_out):
        if self._destroyed or update_out is False:
            return
        try:
            if isinstance(update_out, str):
                result = update_out.strip()
                if result.find(' ') > -1:
                    status, value = result.split(' ')
                else:
                    status = result
                    value = ''
            else:
                status = update_out[0]
                value = update_out[1]
                # if value is None: value = ''
        except:
            logging.error('update %s returned bad data' % self.oid)
            eva.core.log_traceback()
            return False
        return self.update_set_state(status, value)

    def mqtt_set_state(self, topic, data, notify=True):
        with self.update_lock:
            try:
                if topic is None or \
                        topic == self.item_type + '/' + self.full_id:
                    if not data:
                        return False, None
                    if isinstance(data, str):
                        j = rapidjson.loads(data)
                    else:
                        j = data
                    remote_controller = j.get('c')
                    if (
                            not self.allow_mqtt_updates_from_controllers and
                            remote_controller
                    ) or remote_controller == eva.core.config.controller_name:
                        return None, None
                    result = self.set_state_from_serialized(j,
                                                            from_mqtt=True,
                                                            notify=notify)
                    if not result:
                        return False, None
                    else:
                        return result, j
                elif topic.endswith('/status'):
                    self.update_set_state(status=data)
                elif topic.endswith('/value'):
                    self.update_set_state(value=data)
            except:
                eva.core.log_traceback()

    def set_state_from_serialized(self,
                                  data,
                                  from_mqtt=False,
                                  notify=True,
                                  force_notify=False):
        try:
            s = data.get('status')
            v = data.get('value')
            if s is not None or v is not None:
                t = data.get('set_time', data.get('t'))
                if t:
                    t = float(t)
                else:
                    t = time.time()
                ieid = eva.core.parse_ieid(data.get('ieid'))
                return self.update_set_state(status=s,
                                             value=v,
                                             from_mqtt=from_mqtt,
                                             notify=notify,
                                             force_notify=force_notify,
                                             timestamp=t,
                                             ieid=ieid)
        except:
            eva.core.log_traceback()

    def update_set_state(self,
                         status=None,
                         value=None,
                         from_mqtt=False,
                         notify=True,
                         force_notify=False,
                         update_expiration=True,
                         timestamp=None,
                         ieid=None):
        # returns 2 if need_notify but notify is disabled
        # returns True if updated and notified
        # returns False if update cancelled
        with self.update_lock:
            if ieid is not None:
                if ieid == self.ieid:
                    return True
                elif not eva.core.is_ieid_gt(ieid, self.ieid):
                    return False
            elif timestamp is not None:
                if timestamp < self.set_time:
                    return False
                elif timestamp == self.set_time:
                    return True
            need_notify = False
            if status is not None and status != '':
                try:
                    _s = int(status)
                    if self.status != _s:
                        need_notify = True
                        self.status = _s
                except:
                    logging.info('%s status "%s" is not number, can not set' % \
                            (self.oid, status))
                    eva.core.log_traceback()
                    return False
            if value is not None:
                if self.value != value:
                    need_notify = True
                    self.value = value
            if update_expiration:
                self.update_expiration()
            if need_notify:
                if not timestamp:
                    self.set_time = timestamp
                if not ieid:
                    self.ieid = eva.core.generate_ieid()
            if timestamp:
                self.set_time = timestamp
            if ieid:
                self.ieid = ieid
            if (need_notify and notify) or force_notify:
                self.notify(skip_subscribed_mqtt=from_mqtt)
            elif need_notify:
                return 2
        return True

    def serialize(self,
                  full=False,
                  config=False,
                  info=False,
                  props=False,
                  notify=False):
        d = {}
        if config or props:
            if not config or self.expires:
                d['expires'] = self.expires
            if self.update_exec:
                d['update_exec'] = self.update_exec
            elif props:
                d['update_exec'] = None
            if self._mqtt_updates_allowed:
                if self.mqtt_update:
                    d['mqtt_update'] = self.mqtt_update
                elif props:
                    d['mqtt_update'] = None
            if not config or self.update_interval:
                d['update_interval'] = self.update_interval
            if not config or self.update_delay:
                d['update_delay'] = self.update_delay
            if self._update_timeout:
                d['update_timeout'] = self._update_timeout
            elif props:
                d['update_timeout'] = None
        elif not info:
            d['status'] = self.status
            d['value'] = self.value
            d['set_time'] = self.set_time
            d['ieid'] = self.ieid
        d.update(super().serialize(full=full,
                                   config=config,
                                   info=info,
                                   props=props,
                                   notify=notify))
        return d

    def item_env(self, full=True):
        if self.value is not None:
            value = self.value
        else:
            value = ''
        e = {'EVA_ITEM_STATUS': str(self.status), 'EVA_ITEM_VALUE': str(value)}
        if full:
            e.update(super().item_env())
        return e

    def destroy(self):
        super().destroy()
        self.notify(for_destroy=True)


class ActiveItem(Item):

    def __init__(self, item_id=None, item_type=None, **kwargs):
        super().__init__(item_id, item_type, **kwargs)
        self.queue = queue.PriorityQueue()
        self.current_action = None
        self.action_enabled = False
        # 0 - disallow queue, 1 - allow queue
        # 2 - disallow queue but terminate current action and run new one
        self.action_queue = 0
        self.action_exec = None
        self.action_allow_termination = False
        self.action_timeout = eva.core.config.timeout
        self._action_timeout = None
        self.term_kill_interval = eva.core.config.timeout
        self._term_kill_interval = None
        self.queue_lock = threading.RLock()
        self.action_processor = BackgroundQueueWorker(
            fn=self._run_action_processor, on_error=eva.core.log_traceback)
        self.action_processor.before_queue_get = self.action_before_get_task
        self.action_processor.after_queue_get = self.action_after_get_task
        self.current_action = None
        self.action_xc = None
        self.mqtt_control = None
        self.mqtt_control_notifier = None
        self.mqtt_control_qos = 1
        self._expire_on_any = True

    def q_is_task(self):
        return not self.queue.empty()

    def q_get_task(self, timeout=None):
        return self.queue.get(timeout=timeout)

    def q_get_task_nowait(self):
        return self.queue.get_nowait()

    def q_put_task(self, action):
        if self.action_queue == 2:
            self.kill()
        if not self.queue_lock.acquire(timeout=eva.core.config.timeout):
            logging.critical('ActiveItem::q_put_task locking broken')
            eva.core.critical()
            return False
        try:
            if action.item and not self.action_enabled or (
                    not self.action_queue and \
                            (self.current_action or self.q_is_task())
                            ):
                action.set_refused()
                return False
            if action.item and not action.set_queued():
                return False
            self.action_processor.put_threadsafe(action)
            return True
        finally:
            self.queue_lock.release()

    def q_clean(self, lock=True):
        if lock and \
                not self.queue_lock.acquire(timeout=eva.core.config.timeout):
            logging.critical('ActiveItem::q_clean locking broken')
            eva.core.critical()
            return False
        try:
            i = 0
            while self.q_is_task():
                try:
                    a = self.q_get_task_nowait()
                except:
                    a = None
                if a is not None:
                    a.set_canceled()
                    i += 1
            logging.info('removed %u actions from queue of %s' % (i, self.oid))
            return True
        finally:
            if lock:
                self.queue_lock.release()

    def terminate(self, lock=True):
        if lock and \
                not self.queue_lock.acquire(timeout=eva.core.config.timeout):
            logging.critical('ActiveItem::terminate locking broken')
            eva.core.critical()
            return False
        try:
            if self.action_xc and not self.action_xc.is_finished():
                if not self.action_allow_termination:
                    logging.info('termination of %s denied by config' % \
                            self.oid)
                    return False
                logging.info('requesting to terminate action %s' % \
                        self.current_action.uuid)
                self.action_xc.terminate()
                return True
            return None
        finally:
            if lock:
                self.queue_lock.release()

    def kill(self):
        if not self.queue_lock.acquire(timeout=eva.core.config.timeout):
            logging.critical('ActiveItem::kill locking broken')
            eva.core.critical()
            return False
        try:
            self.q_clean(lock=False)
            self.terminate(lock=False)
            return True
        finally:
            self.queue_lock.release()

    def start_processors(self):
        self.subscribe_mqtt_control()
        self.start_action_processor()
        super().start_processors()

    def stop_processors(self):
        self.unsubscribe_mqtt_control()
        self.stop_action_processor()
        super().stop_processors()

    def start_action_processor(self):
        self.action_processor.set_name('_t_action_processor_' + self.oid)
        self.action_processor.start()

    def stop_action_processor(self):
        self.action_processor.stop()

    def subscribe_mqtt_control(self):
        if not self.mqtt_control:
            return False
        notifier = eva.notify.get_notifier(self.mqtt_control_notifier)
        if not notifier or notifier.notifier_type[:4] != 'mqtt':
            return False
        try:
            notifier.control_item_append(self)
        except:
            eva.core.log_traceback()
            return False
        return True

    def unsubscribe_mqtt_control(self):
        if not self.mqtt_control:
            return False
        notifier = eva.notify.get_notifier(self.mqtt_control_notifier)
        if not notifier or notifier.notifier_type[:4] != 'mqtt':
            return False
        try:
            notifier.control_item_remove(self)
        except:
            eva.core.log_traceback()
            return False
        return True

    def action_may_run(self, action):
        return True

    def action_log_run(self, action):
        logging.info(
            '%s executing action %s pr=%u' % \
             (self.oid, action.uuid, action.priority))

    def action_run_args(self, action):
        return ()

    def action_before_get_task(self):
        pass

    def action_after_get_task(self, action):
        pass

    def action_before_run(self, action):
        pass

    def action_after_run(self, action, xc):
        pass

    def action_after_finish(self, action, xc):
        pass

    def mqtt_action(self, msg):
        pass

    def _run_action_processor(self, a, **kwargs):
        if a.item:
            try:
                if not self.queue_lock.acquire(timeout=eva.core.config.timeout):
                    logging.critical(
                        'ActiveItem::_run_action_processor locking broken')
                    eva.core.critical()
                    return
                # dirty fix for action_queue == 0
                if not self.action_queue:
                    while self.q_is_task():
                        ar = self.q_get_task()
                        ar.set_refused()
                # dirty fix for action_queue == 2
                elif self.action_queue == 2:
                    while self.q_is_task():
                        a = self.q_get_task()
                        if self.q_is_task():
                            a.set_canceled()
                # end
                self.current_action = a
                if not self.action_enabled:
                    self.queue_lock.release()
                    logging.info(
                     '%s actions disabled, canceling action %s' % \
                     (self.oid, a.uuid))
                    a.set_canceled()
                else:
                    if not self.action_may_run(a):
                        self.queue_lock.release()
                        logging.info(
                                '%s ignoring action %s' % \
                                 (self.oid, a.uuid))
                        a.set_ignored()
                    elif a.is_status_queued() and a.set_running():
                        self.action_log_run(a)
                        try:
                            self.action_before_run(a)
                            xc = self.get_action_xc(a)
                            self.action_xc = xc
                            self.queue_lock.release()
                            xc.run()
                        finally:
                            self.action_after_run(a, xc)
                        if xc.exitcode < 0:
                            a.set_terminated(exitcode=xc.exitcode,
                                             out=xc.out,
                                             err=xc.err)
                            logging.error('action %s terminated' % a.uuid)
                        elif xc.exitcode == 0:
                            a.set_completed(exitcode=xc.exitcode,
                                            out=xc.out,
                                            err=xc.err)
                            logging.debug('action %s completed' % a.uuid)
                        else:
                            a.set_failed(exitcode=xc.exitcode,
                                         out=xc.out,
                                         err=xc.err)
                            logging.error('action %s failed, code: %u' % \
                                    (a.uuid, xc.exitcode))
                        self.action_after_finish(a, xc)
                    else:
                        self.queue_lock.release()
            except:
                logging.critical(
                        '%s action processor got an error, restarting' % \
                                (self.oid))
                eva.core.log_traceback()
            if not self.queue_lock.acquire(timeout=eva.core.config.timeout):
                logging.critical(
                    'ActiveItem::_run_action_processor locking broken')
                eva.core.critical()
                return
            self.current_action = None
            self.action_xc = None
            self.queue_lock.release()

    def get_action_xc(self, a):
        return eva.runner.ExternalProcess(fname=self.action_exec,
                                          item=self,
                                          env=a.action_env(),
                                          update=False,
                                          args=self.action_run_args(a),
                                          timeout=self.action_timeout,
                                          tki=self.term_kill_interval)

    def update_config(self, data):
        if 'action_enabled' in data:
            self.action_enabled = data['action_enabled']
        if 'action_exec' in data:
            self.action_exec = data['action_exec']
        if 'mqtt_control' in data and data['mqtt_control'] is not None:
            self.mqtt_control = data['mqtt_control']
            params = data['mqtt_control'].split(':')
            self.mqtt_control_notifier = params[0]
            if len(params) > 1:
                try:
                    self.mqtt_control_qos = int(params[1])
                except:
                    eva.core.log_traceback()
        if 'action_queue' in data:
            self.action_queue = data['action_queue']
        if 'action_allow_termination' in data:
            self.action_allow_termination = \
                            data['action_allow_termination']
        if 'action_timeout' in data:
            self.action_timeout = data['action_timeout']
            self._action_timeout = data['action_timeout']
        if 'term_kill_interval' in data:
            self.term_kill_interval = data['term_kill_interval']
            self._term_kill_interval = data['term_kill_interval']
        super().update_config(data)

    def set_prop(self, prop, val=None, save=False):
        if prop == 'action_enabled':
            v = val_to_boolean(val)
            if v is not None:
                if self.action_enabled != v:
                    self.action_enabled = v
                    self.log_set(prop, v)
                    self.notify()
                    self.set_modified(save)
                return True
            else:
                return False
        elif prop == 'action_exec':
            if self.action_exec != val:
                self.action_exec = val
                self.log_set(prop, val)
                self.set_modified(save)
            return True
        elif prop == 'mqtt_control':
            if val is None:
                if self.mqtt_control is not None:
                    self.unsubscribe_mqtt_control()
                    self.mqtt_control = None
                    self.mqtt_control_notifier = None
                    self.mqtt_control_qos = 1
                    self.log_set(prop, None)
                    self.set_modified(save)
            else:
                params = val.split(':')
                n = params[0]
                import eva.notify
                notifier = eva.notify.get_notifier(n)
                if not notifier or notifier.notifier_type != 'mqtt':
                    return False
                if len(params) > 1:
                    try:
                        qos = int(params[1])
                    except:
                        return False
                else:
                    qos = self.mqtt_control_qos
                if self.mqtt_control_notifier != n or \
                        self.mqtt_control_qos != qos:
                    self.unsubscribe_mqtt_control()
                    self.mqtt_control = val
                    self.mqtt_control_notifier = n
                    self.mqtt_control_qos = qos
                    self.subscribe_mqtt_control()
                    self.log_set(prop, val)
                    self.set_modified(save)
            return True
        elif prop == 'action_queue':
            try:
                v = int(val)
            except:
                return False
            if not 0 <= v <= 2:
                return False
            if self.action_queue != v:
                self.action_queue = v
                self.log_set(prop, v)
                self.set_modified(save)
            return True
        elif prop == 'action_allow_termination':
            v = val_to_boolean(val)
            if v is not None:
                if self.action_allow_termination != v:
                    self.action_allow_termination = v
                    self.log_set(prop, v)
                    self.set_modified(save)
                return True
            else:
                return False
        elif prop == 'action_timeout':
            if val is None:
                if self._action_timeout is not None:
                    import eva.core
                    self.action_timeout = eva.core.config.timeout
                    self._action_timeout = None
                    self.log_set(prop, None)
                    self.set_modified(save)
            else:
                try:
                    action_timeout = float(val)
                except:
                    return False
                if action_timeout <= 0:
                    return False
                if self._action_timeout != action_timeout:
                    self._action_timeout = action_timeout
                    self.action_timeout = action_timeout
                    self.log_set(prop, action_timeout)
                    self.set_modified(save)
            return True
        elif prop == 'term_kill_interval':
            if val is None:
                if self._term_kill_interval is not None:
                    import eva.core
                    self.term_kill_interval = eva.core.config.timeout
                    self._term_kill_interval = None
                    self.log_set(prop, None)
                    self.set_modified(save)
            else:
                try:
                    term_kill_interval = float(val)
                except:
                    return False
                if term_kill_interval <= 0:
                    return False
                if self._term_kill_interval != term_kill_interval:
                    self._term_kill_interval = term_kill_interval
                    self.term_kill_interval = term_kill_interval
                    self.log_set(prop, term_kill_interval)
                    self.set_modified(save)
            return True
        else:
            return super().set_prop(prop, val, save)

    def serialize(self,
                  full=False,
                  config=False,
                  info=False,
                  props=False,
                  notify=False):
        d = {}
        if not info:
            if not config or self.action_enabled:
                d['action_enabled'] = self.action_enabled
        if config or props:
            if self.action_exec:
                d['action_exec'] = self.action_exec
            elif props:
                d['action_exec'] = None
            if self.mqtt_control:
                d['mqtt_control'] = self.mqtt_control
            elif props:
                d['mqtt_control'] = None
            if not config or self.action_queue:
                d['action_queue'] = self.action_queue
            if not config or self.action_allow_termination:
                d['action_allow_termination'] = self.action_allow_termination
            if self._action_timeout:
                d['action_timeout'] = self._action_timeout
            elif props:
                d['action_timeout'] = None
            if self._term_kill_interval:
                d['term_kill_interval'] = self._term_kill_interval
            elif props:
                d['term_kill_interval'] = None
        d.update(super().serialize(full=full,
                                   config=config,
                                   info=info,
                                   props=props,
                                   notify=notify))
        return d

    def disable_actions(self):
        if not self.action_enabled:
            return True
        self.update_config({'action_enabled': False})
        self.ieid = eva.core.generate_ieid()
        logging.info('%s actions disabled' % self.oid)
        self.notify()
        if eva.core.config.auto_save:
            self.save()
        return True

    def enable_actions(self):
        if self.action_enabled:
            return True
        self.update_config({'action_enabled': True})
        self.ieid = eva.core.generate_ieid()
        logging.info('%s actions enabled' % self.oid)
        self.notify()
        if eva.core.config.auto_save:
            self.save()
        return True

    def destroy(self):
        self.action_enabled = None
        super().destroy()


ia_status_names = [
    'created', 'pending', 'queued', 'refused', 'dead', 'canceled', 'ignored',
    'running', 'failed', 'terminated', 'completed'
]

ia_default_priority = 100


class ItemAction(GenericAction):

    def __init__(self, item, priority=None, action_uuid=None):
        super().__init__()
        self.item_action_lock = threading.RLock()
        if not self.item_action_lock.acquire(timeout=eva.core.config.timeout):
            logging.critical('ItemAction::__init___ locking broken')
            eva.core.critical()
            return False
        if priority:
            self.priority = priority
        else:
            self.priority = ia_default_priority
        self.time = {ia_status_created: time.time()}
        self.item = item
        if action_uuid:
            self.uuid = action_uuid
        else:
            self.uuid = str(uuid.uuid4())
        self.exitcode = None
        self.out = ''
        self.err = ''
        if item:
            logging.debug('action %s created, %s: %s' % \
                (self.uuid, self.item.item_type,
                    self.item.full_id))
            if self.item.notify_events > 1 and eva.notify.is_action_subscribed(
            ):
                eva.notify.notify('action', (self, self.serialize()))
        self.item_action_lock.release()

    def __cmp__(self, other):
        return compare(self.priority, other.priority) if \
                other is not None else 1

    def __lt__(self, other):
        return (self.priority < other.priority) if \
                other is not None else True

    def __gt__(self, other):
        return (self.priority > other.priority) if \
                other is not None else True

    def get_status_name(self):
        return ia_status_names[self.get_status()]

    def _set_status_only(self, status):
        super().set_status(status)

    def set_status(self, status, exitcode=None, out=None, err=None):
        if not self.item_action_lock.acquire(timeout=eva.core.config.timeout):
            logging.critical('ItemAction::set_status locking broken')
            eva.core.critical()
            return False
        try:
            if self.is_status_dead():
                return False
            if status == ia_status_dead and \
                    not self.is_status_created() and \
                    not self.is_status_pending():
                return False
            s = self.get_status()
            if status == ia_status_canceled and ( \
                    s == ia_status_running or \
                    s == ia_status_failed or \
                    s == ia_status_terminated or \
                    s == ia_status_completed):
                return False
            super().set_status(status)
            self.time[status] = time.time()
            if exitcode is not None:
                self.exitcode = exitcode
            if out is not None:
                self.out = out
            if err is not None:
                self.err = err
            logging.debug('action %s new status: %s' % \
                    (self.uuid, ia_status_names[status]))
            if self.item.notify_events > 1 and eva.notify.is_action_subscribed(
            ):
                eva.notify.notify('action', (self, self.serialize()))
            return True
        finally:
            self.item_action_lock.release()

    def set_pending(self):
        return self.set_status(ia_status_pending)

    def set_queued(self):
        return self.set_status(ia_status_queued)

    def set_refused(self):
        return self.set_status(ia_status_refused)

    def set_dead(self):
        return self.set_status(ia_status_dead)

    def set_canceled(self):
        return self.set_status(ia_status_canceled)

    def set_ignored(self):
        return self.set_status(ia_status_ignored)

    def set_running(self):
        return self.set_status(ia_status_running)

    def set_failed(self, exitcode=None, out=None, err=None):
        return self.set_status(ia_status_failed, exitcode, out, err)

    def set_terminated(self, exitcode=None, out=None, err=None):
        return self.set_status(ia_status_terminated, exitcode, out, err)

    def set_completed(self, exitcode=None, out=None, err=None):
        return self.set_status(ia_status_completed, exitcode, out, err)

    def action_env(self):
        return {}

    def kill(self):
        if not self.item_action_lock.acquire(timeout=eva.core.config.timeout):
            logging.critical('ItemAction::terminate locking broken')
            eva.core.critical()
            return False
        try:
            if not self.item.queue_lock.acquire(
                    timeout=eva.core.config.timeout):
                logging.critical('ItemAction::terminate locking(2) broken')
                eva.core.critical()
                return False
            try:
                if self.is_finished():
                    return None
                if self.is_status_running():
                    result = self.item.terminate(lock=False)
                else:
                    result = self.set_status(ia_status_canceled)
                return result
            finally:
                self.item.queue_lock.release()
        finally:
            self.item_action_lock.release()

    def serialize(self):
        if not self.item_action_lock.acquire(timeout=eva.core.config.timeout):
            logging.critical('ItemAction::set_status locking broken')
            eva.core.critical()
            return False
        try:
            d = {}
            d['uuid'] = self.uuid
            d['status'] = ia_status_names[self.get_status()]
            d['finished'] = self.is_finished()
            d['priority'] = self.priority
            d['exitcode'] = self.exitcode
            d['out'] = self.out
            d['err'] = self.err
            d['item_id'] = self.item.item_id
            d['item_group'] = self.item.group
            d['item_type'] = self.item.item_type
            d['item_oid'] = self.item.oid
            d['time'] = {}
            t_max = 0
            for i, v in self.time.items():
                d['time'][ia_status_names[i]] = v
                if v > t_max:
                    t_max = v
            d['finished_in'] = round(t_max - self.time[ia_status_created], 7) \
                    if self.is_finished() else None
            return d
        finally:
            self.item_action_lock.release()


class MultiUpdate(UpdatableItem):

    def __init__(self, mu_id=None, **kwargs):
        super().__init__(mu_id, 'mu', **kwargs)
        self.items_to_update = []
        self._update_run_args = ()
        self.update_allow_check = True
        self.get_item_func = None
        self._mqtt_updates_allowed = False

    def updates_allowed(self):
        if not self.update_allow_check:
            return True
        for i in self.items_to_update:
            if not i.updates_allowed():
                return False
        return True

    def update_after_run(self, update_out):
        if self._destroyed:
            return
        if isinstance(update_out, str):
            result = update_out.strip().split('\n')
        elif isinstance(update_out, list):
            result = update_out
        else:
            result = [update_out]
        if len(result) < len(self.items_to_update):
            logging.warning(
                    '%s have %u items to update, got only %u in result' % \
                    (self.oid, len(self.items_to_update),
                        len(result)))
        for i in range(0, min(len(result), len(self.items_to_update))):
            self.items_to_update[i].update_after_run(result[i])

    def update_config(self, data):
        super().update_config(data)
        if 'update_allow_check' in data:
            self.update_allow_check = data['update_allow_check']
        if 'items' in data:
            for i in data['items']:
                item = self.get_item_func(i)
                if item:
                    self.append(item)
                    pass
                else:
                    logging.warning(
                            '%s can not add %s, item not found' % \
                                    (self.oid, i))

    def set_prop(self, prop, val=None, save=False):
        if prop == 'update_allow_check':
            val = val_to_boolean(val)
            if val is not None:
                if self.update_allow_check != val:
                    self.update_allow_check = val
                    self.log_set(prop, val)
                    self.set_modified(save)
                return True
            else:
                return False
        else:
            return super().set_prop(prop, val, save)

    def append(self, item):
        if not item in self.items_to_update:
            self.items_to_update.append(item)
            self.set_update_run_args()
            return True
        else:
            return False

    def remove(self, item):
        if not item in self.items_to_update:
            logging.debug(
                '%s can not remove %s, doesn\'t exist in the update list' % \
                                (self.oid, item.full_id))
            return False
        self.items_to_update.remove(item)
        self.set_update_run_args()
        return True

    def update_run_args(self):
        return self._update_run_args

    def set_update_run_args(self):
        ids = []
        for i in self.items_to_update:
            ids.append(i.item_id)
        self._update_run_args = (','.join(ids),)

    def serialize(self,
                  full=False,
                  config=False,
                  info=False,
                  props=False,
                  notify=False):
        d = super().serialize(full=full,
                              config=config,
                              info=info,
                              props=props,
                              notify=notify)
        if 'mqtt_update' in d:
            del d['mqtt_update']
        if 'expires' in d:
            del d['expires']
        if config or props:
            if not config or not self.update_allow_check:
                d['update_allow_check'] = self.update_allow_check
            ids = []
            if not config or self.items_to_update:
                for i in self.items_to_update:
                    ids.append(i.oid)
                d['items'] = ids
        return d

    def destroy(self):
        self._destroyed = True
        self.stop_processors()


class VariableItem(UpdatableItem):

    def update_set_state(self,
                         status=None,
                         value=None,
                         from_mqtt=False,
                         force_notify=False,
                         force_update=False,
                         update_expiration=True,
                         notify=True,
                         timestamp=None,
                         ieid=None):
        # returns 2 if need_notify but notify is disabled
        # returns True if updated and notified
        # returns False if update cancelled
        if self._destroyed:
            return False
        with self.update_lock:
            if ieid is not None:
                if ieid == self.ieid:
                    return True
                elif not eva.core.is_ieid_gt(ieid, self.ieid):
                    return False
            elif timestamp is not None:
                if timestamp < self.set_time:
                    return False
                elif timestamp == self.set_time:
                    return True
                else:
                    self.set_time = timestamp
            try:
                if status is not None:
                    _status = int(status)
                else:
                    _status = None
            except:
                logging.error('update %s returned bad data' % self.oid)
                eva.core.log_traceback()
                return False
            if not force_update and not self.status and _status is None:
                logging.debug('%s skipping update - it\'s not active' % \
                        self.oid)
                return False
            need_notify = False
            if _status is not None:
                if self.status != _status:
                    need_notify = True
                self.status = _status
            if value is not None and (self.status or force_update):
                if self.value != value:
                    need_notify = True
                self.value = value
                if self.status == -1 and _status is None and \
                        value != '' and not force_update:
                    self.status = 1
                    need_notify = True
            if update_expiration:
                self.update_expiration()
            if need_notify:
                self.set_time = timestamp if timestamp else time.time()
                if ieid is None:
                    self.ieid = eva.core.generate_ieid()
            if ieid:
                self.ieid = ieid
            if (need_notify and notify) or force_notify:
                logging.debug(
                    '%s status = %u, value = "%s"' % \
                            (self.oid, self.status, self.value))
                self.notify(skip_subscribed_mqtt=from_mqtt)
            elif need_notify:
                return 2
            return True

    def is_expired(self):
        if not self.status:
            return False
        return super().is_expired()


def oid_match(oid, item_ids=None, groups=None):
    if (groups and '#' in groups) or '#' in item_ids:
        return True
    if '/' not in oid or not is_oid(oid):
        return False
    item_type, iid = parse_oid(oid)
    item_group, item_id = iid.rsplit('/', 1)
    if '#' in iid or '+' in iid:
        for grp in groups:
            if is_oid(grp):
                rt, g = parse_oid(grp)
                if rt != item_type:
                    continue
            else:
                g = grp
            if g == item_group:
                return True
            p = g.find('#')
            if p > -1 and g[:p] == item_group[:p]:
                return True
            if g.find('+') > -1:
                g1 = g.split('/')
                g2 = item_group.split('/')
                g2.append(item_id)
                if len(g1) == len(g2):
                    match = True
                    for i in range(0, len(g1)):
                        if g1[i] != '+' and g1[i] != g2[i]:
                            match = False
                            break
                    if match:
                        return True
        return False
    else:
        if (groups and item_group in groups) or oid in item_ids:
            return True
        if groups:
            for grp in groups:
                if is_oid(grp):
                    rt, g = parse_oid(grp)
                    if rt != item_type:
                        continue
                else:
                    g = grp
                if g == item_group:
                    return True
                p = g.find('#')
                if p > -1 and g[:p] == item_group[:p]:
                    return True
                if g.find('+') > -1:
                    g1 = g.split('/')
                    g2 = item_group.split('/')
                    if len(g1) == len(g2):
                        match = True
                        for i in range(0, len(g1)):
                            if g1[i] != '+' and g1[i] != g2[i]:
                                match = False
                                break
                        if match:
                            return True
        return False


def item_match(item, item_ids, groups=None):
    try:
        if (groups and ('#' in groups) or (item.group in groups)) \
                or '#' in item_ids or \
                item.oid in item_ids or \
                (not eva.core.config.enterprise_layout and \
                item.item_id in item_ids):
            return True
        if groups:
            for grp in groups:
                if is_oid(grp):
                    rt, g = parse_oid(grp)
                    if rt != item.item_type:
                        continue
                else:
                    g = grp
                if g == item.group:
                    return True
                p = g.find('#')
                if p > -1 and g[:p] == item.group[:p]:
                    return True
                if '+' in g:
                    g1 = g.split('/')
                    g2 = item.group.split('/')
                    match = True
                    for i in range(0, len(g1)):
                        try:
                            if g1[i] == '#' and g2[i]:
                                break
                            elif g1[i] != '+' and g1[i] != g2[i]:
                                raise IndexError
                            g2[i]
                        except IndexError:
                            match = False
                            break
                    if match:
                        return True
        return False
    except:
        logging.error(
            f'Item match error, item: {item}, ids: {item_ids}, groups: {groups}'
        )
        raise


# val_prefixes = {
# 'k': 1000,
# 'kb': 1024,
# 'M': 1000 * 1000,
# 'Mb': 1024 * 1024,
# 'G': 1000 * 1000 * 1000,
# 'Gb': 1024 * 1024 * 1024,
# 'T': 1000 * 1000 * 1000 * 1000,
# 'Tb': 1024 * 1024 * 1024 * 1024,
# 'P': 1000 * 1000 * 1000 * 1000 * 1000,
# 'Pb': 1024 * 1024 * 1024 * 1024 * 1024,
# 'E': 1000 * 1000 * 1000 * 1000 * 1000 * 1000,
# 'Eb': 1024 * 1024 * 1024 * 1024 * 1024 * 1024,
# 'Z': 1000 * 1000 * 1000 * 1000 * 1000 * 1000 * 1000,
# 'Zb': 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024,
# 'Y': 1000 * 1000 * 1000 * 1000 * 1000 * 1000 * 1000 * 1000,
# 'Yb': 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024
# }

val_prefixes = {
    'k': 1000,
    'kb': 1024,
    'M': 1000000,
    'Mb': 1048576,
    'G': 1000000000,
    'Gb': 1073741824,
    'T': 1000000000000,
    'Tb': 1099511627776,
    'P': 1000000000000000,
    'Pb': 1125899906842624,
    'E': 1000000000000000000,
    'Eb': 1152921504606846976,
    'Z': 1000000000000000000000,
    'Zb': 1180591620717411303424,
    'Y': 1000000000000000000000000,
    'Yb': 1208925819614629174706176
}


def get_state_history(a=None,
                      oid=None,
                      t_start=None,
                      t_end=None,
                      limit=None,
                      prop=None,
                      time_format=None,
                      fill=None,
                      fmt=None,
                      xopts=None,
                      tz=None):
    import dateutil
    import pandas as pd
    import math
    from datetime import datetime

    if oid is None:
        raise ResourceNotFound
    n = eva.notify.get_stats_notifier(a)
    if not n:
        raise ResourceNotFound('notifier')
    if n.state_storage not in ['sql', 'tsdb', 'sql+tsdb']:
        raise MethodNotImplemented
    if fill:
        tf = 'iso'
        if not t_start:
            t_start = time.time() - 86400
    else:
        tf = time_format
    t_start = fmt_time(t_start)
    t_end = fmt_time(t_end)
    try:
        n_time_format = tf if not t_start or not fill else 'dt_utc'
        result = n.get_state(oid=oid,
                             t_start=t_start,
                             t_end=t_end,
                             fill=fill.split(':', 1)[0] if fill else None,
                             limit=limit,
                             prop=prop,
                             time_format=n_time_format,
                             xopts=xopts,
                             tz=tz)
    except:
        raise FunctionFailed
    if n.state_storage == 'sql' or (n.state_storage == 'sql+tsdb' and
                                    fill is None):
        parse_df = True
        parse_tsdb = False
    else:
        parse_df = False
        parse_tsdb = True
    if ((t_start and fill) or parse_tsdb) and result:
        if not tz:
            import pytz
            tz = pytz.timezone(time.tzname[0])
        if t_start:
            try:
                t_s = float(t_start)
            except:
                try:
                    t_s = dateutil.parser.parse(t_start).timestamp()
                except:
                    raise InvalidParameter('time format is unknown')
        if t_end:
            try:
                t_e = float(t_end)
            except:
                try:
                    t_e = dateutil.parser.parse(t_end).timestamp()
                except:
                    raise InvalidParameter('time format is unknown')
        else:
            t_e = time.time()
        if t_e > time.time():
            t_e = time.time()
        if fill and fill.find(':') != -1:
            _fill, _pc = fill.split(':', 1)
            if _pc.find(':') != -1:
                _divider, _pc = _pc.split(':')
                try:
                    _divider = pow(10, int(_divider))
                except:
                    if not _divider in val_prefixes:
                        raise FunctionFailed(
                            'Prefix unknown: {}'.format(_divider))
                    _divider = val_prefixes[_divider]
            else:
                _divider = None
            _pc = pow(10, int(_pc))
        else:
            _fill = fill
            _pc = None
            _divider = None
        try:
            if parse_df:
                df = pd.DataFrame(result)
                df = df.set_index('t')
                sp1 = df.resample(_fill).mean()
                sp2 = df.resample(_fill).pad()
                sp = sp1.fillna(sp2).to_dict(orient='split')
            else:
                sp = result
            result = []
            for i in range(0, len(sp['index']) if parse_df else len(sp)):
                t = sp['index'][i].timestamp() if parse_df else sp[i][0]
                if time_format == 'iso' and n_time_format != 'iso':
                    t = datetime.fromtimestamp(t, tz).isoformat()
                r = {'t': t}
                if parse_df:
                    if 'status' in sp['columns'] and 'value' in sp['columns']:
                        try:
                            r['status'] = int(sp['data'][i][0])
                        except:
                            r['status'] = None
                        r['value'] = sp['data'][i][1]
                    elif 'status' in sp['columns']:
                        try:
                            r['status'] = int(sp['data'][i][0])
                        except:
                            r['status'] = None
                    elif 'value' in sp['columns']:
                        r['value'] = sp['data'][i][0]
                else:
                    if prop:
                        if prop in ['status', 'S']:
                            try:
                                r['status'] = int(sp[i][1])
                            except:
                                r['status'] = None
                        elif prop in ['value', 'V']:
                            r['value'] = sp[i][1]
                    else:
                        try:
                            r['status'] = int(sp[i][1])
                        except:
                            r['status'] = None
                        r['value'] = sp[i][2]
                if 'value' in r and isinstance(r['value'], float):
                    if math.isnan(r['value']):
                        r['value'] = None
                    elif _pc:
                        if _divider:
                            r['value'] = r['value'] / _divider
                        r['value'] = math.floor(r['value'] * _pc) / _pc
                result.append(r)
        except pd.core.base.DataError:
            result = []
        except FunctionFailed:
            raise
        except:
            eva.core.log_traceback()
            raise FunctionFailed
    # check dataframe, fill till t_e if not filled
    try:
        if fill and (not limit or len(result) < limit):
            if time_format == 'iso':
                r_ts = dateutil.parser.parse(result[-1]['t']).timestamp()
            else:
                r_ts = result[-1]['t']
            if len(result) > 1:
                if time_format == 'iso':
                    per = r_ts - dateutil.parser.parse(
                        result[-2]['t']).timestamp()
                else:
                    per = r_ts - result[-2]['t']
            else:
                per = int(_fill[:-1]) * _p_periods[_fill[-1].upper()]
            while True:
                r_ts += per
                if r_ts > t_e:
                    break
                lf = result[-1].copy()
                if time_format == 'iso':
                    lf['t'] = datetime.fromtimestamp(r_ts, tz).isoformat()
                else:
                    lf['t'] = r_ts
                result.append(lf)
    except:
        pass
    # convert to list if required
    if limit is not None:
        result = result[-1 * int(limit):]
    if not fmt or fmt == 'list':
        res = {'t': []}
        for r in result:
            res['t'].append(r['t'])
            if 'status' in r:
                if 'status' in res:
                    res['status'].append(r['status'])
                else:
                    res['status'] = [r['status']]
            if 'value' in r:
                if 'value' in res:
                    res['value'].append(r['value'])
                else:
                    res['value'] = [r['value']]
        result = res
    elif fmt == 'dict':
        pass
    else:
        raise InvalidParameter('Invalid result format {}'.format(fmt))
    return result


def get_state_log(a=None,
                  oid=None,
                  t_start=None,
                  t_end=None,
                  limit=None,
                  time_format=None,
                  xopts=None,
                  tz=None):
    if oid is None:
        raise ResourceNotFound
    n = eva.notify.get_stats_notifier(a)
    if not n:
        raise ResourceNotFound('notifier')
    if n.state_storage not in ['sql', 'sql+tsdb'] and ('#' in oid or
                                                       '+' in oid):
        raise MethodNotImplemented(
            'state log by mask is supported by SQL notifiers only')

    t_start = fmt_time(t_start)
    t_end = fmt_time(t_end)
    try:
        return n.get_state_log(oid=oid,
                               t_start=t_start,
                               t_end=t_end,
                               limit=limit,
                               time_format=time_format,
                               xopts=xopts,
                               tz=tz)
    except:
        raise FunctionFailed
