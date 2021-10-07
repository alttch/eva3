__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.1"

import eva.core
import eva.item
import eva.uc.controller
import eva.uc.driverapi
import eva.uc.modbus
import logging
import threading
import time
import eva.runner

from eva.tools import safe_int
from eva.tools import val_to_boolean
from eva.tools import dict_from_str
from eva.uc.ucitem import UCItem

from neotasker import task_supervisor

status_label_off = 'OFF'
status_label_on = 'ON'


class Unit(UCItem, eva.item.UpdatableItem, eva.item.ActiveItem,
           eva.item.PhysicalItem):

    fields = [
        'action_allow_termination',
        'action_always_exec',
        'action_driver_config',
        'action_enabled',
        'action_exec',
        'action_queue',
        'action_timeout',
        'auto_off',
        'description',
        'expires',
        'location',
        'maintenance_duration',
        'modbus_status',
        'modbus_value',
        'mqtt_control',
        'mqtt_update',
        'notify_events',
        'snmp_trap',
        'term_kill_interval',
        'update_delay',
        'update_driver_config',
        'update_exec',
        'update_exec_after_action',
        'update_if_action',
        'update_interval',
        'update_state_after_action',
        'update_timeout',
        'value_condition',
        'value_in_range_max',
        'value_in_range_max_eq',
        'value_in_range_min',
        'value_in_range_min_eq',
    ]

    def __init__(self, unit_id=None, create=False, **kwargs):
        self.action_driver_config = None
        super().__init__(unit_id, 'unit', **kwargs)

        self.update_exec_after_action = False
        self.update_state_after_action = True
        self.update_if_action = False
        self.action_always_exec = False
        self.auto_off = 0
        self.nstatus = self.status
        self.nvalue = self.value
        self.last_action = 0
        self.auto_processor = None
        self.auto_processor_lock = threading.RLock()
        self.modbus_status = None
        # labels have string keys to be JSON compatible
        self.default_status_labels = {
            '0': status_label_off,
            '1': status_label_on
        }
        self.status_labels = self.default_status_labels.copy()
        if create:
            self.set_defaults(self.fields)

    def status_by_label(self, label):
        if label is None:
            return None
        for k, v in self.status_labels.copy().items():
            if v.lower() == label.lower():
                try:
                    return int(k)
                except:
                    return None
        return None

    def serialize(self,
                  full=False,
                  config=False,
                  info=False,
                  props=False,
                  notify=False):
        d = {}
        if config or props:
            if not config or self.action_always_exec:
                d['action_always_exec'] = self.action_always_exec
            if not config or self.update_exec_after_action:
                d['update_exec_after_action'] = self.update_exec_after_action
            if not config or not self.update_state_after_action:
                d['update_state_after_action'] = self.update_state_after_action
            if not config or self.update_if_action:
                d['update_if_action'] = self.update_if_action
            if not config or self.auto_off:
                d['auto_off'] = self.auto_off
            if self.action_driver_config:
                d['action_driver_config'] = self.action_driver_config
            elif props:
                d['action_driver_config'] = None
            if not config or self.modbus_status:
                d['modbus_status'] = self.modbus_status
            if not config or \
                    (self.status_labels.keys() != \
                        self.default_status_labels.keys()) or \
                    self.status_labels['0'] != status_label_off or \
                    self.status_labels['1'] != status_label_on:
                d['status_labels'] = self.status_labels
        elif full:
            d['status_labels'] = sorted([ { 'status': int(x),
                'label': self.status_labels[x] } \
                    for x in self.status_labels ], key = lambda k: k['status'])
        if not info and not props and not config:
            d['nstatus'] = self.nstatus
            d['nvalue'] = self.nvalue
        d.update(super().serialize(full=full,
                                   config=config,
                                   info=info,
                                   props=props,
                                   notify=notify))
        return d

    def register_modbus_status_updates(self):
        if self.modbus_status:
            try:
                eva.uc.modbus.register_handler(self.modbus_status[1:],
                                               self.modbus_update_status,
                                               register=self.modbus_status[0])
            except:
                eva.core.log_traceback()

    def unregister_modbus_status_updates(self):
        if self.modbus_status:
            try:
                eva.uc.modbus.unregister_handler(self.modbus_status[1:],
                                                 self.modbus_update_status,
                                                 register=self.modbus_status[0])
            except:
                eva.core.log_traceback()

    def modbus_update_status(self, addr, values):
        v = values[0]
        if v is True:
            v = 1
        elif v is False:
            v = 0
        self.update_set_state(status=v)

    def create_action(self,
                      nstatus,
                      nvalue='',
                      priority=None,
                      action_uuid=None):
        return UnitAction(self, nstatus, nvalue, priority, action_uuid)

    def mqtt_action(self, msg):
        eva.uc.controller.exec_mqtt_unit_action(self, msg)

    def update_config(self, data):
        if 'action_driver_config' in data:
            self.action_driver_config = data['action_driver_config']
        if 'action_always_exec' in data:
            self.action_always_exec = data['action_always_exec']
        if 'update_exec_after_action' in data:
            self.update_exec_after_action = \
                    data['update_exec_after_action']
        if 'update_state_after_action' in data:
            self.update_state_after_action = \
                    data['update_state_after_action']
        if 'update_if_action' in data:
            self.update_if_action = data['update_if_action']
        if 'auto_off' in data:
            self.auto_off = data['auto_off']
        if 'status_labels' in data:
            self.status_labels = data['status_labels']
        if 'modbus_status' in data:
            self.modbus_status = data['modbus_status']
        super().update_config(data)

    def set_prop(self, prop, val=None, save=False):
        if prop == 'action_exec':
            if self.action_exec != val:
                if val and val[0] == '|':
                    d = eva.uc.driverapi.get_driver(val[1:])
                    if not d:
                        logging.error(
                            'Can not set ' + \
                                '%s.action_exec = %s, no such driver'
                                % (self.oid, val))
                        return False
                self.action_exec = val
                self.log_set(prop, val)
                self.set_modified(save)
            return True
        elif prop == 'action_driver_config':
            if val is None:
                self.action_driver_config = None
                self.log_set(prop, None)
                self.set_modified(save)
                return True
            else:
                try:
                    v = dict_from_str(val)
                except:
                    eva.core.log_traceback()
                    return False
                self.action_driver_config = v
                self.log_set(prop, 'dict')
                self.set_modified(save)
                return True
        elif prop == 'modbus_status':
            if self.modbus_status == val:
                return True
            if val is None:
                self.unregister_modbus_status_updates()
                self.modbus_status = None
            else:
                if val[0] not in ['h', 'c']:
                    return False
                try:
                    addr = safe_int(val[1:])
                    if addr > eva.uc.modbus.slave_reg_max or addr < 0:
                        return False
                except:
                    return False
                self.unregister_modbus_status_updates()
                self.modbus_status = val
                self.modbus_update_status(addr,
                                          eva.uc.modbus.get_data(addr, val[0]))
                self.register_modbus_status_updates()
            self.log_set('modbus_status', val)
            self.set_modified(save)
            return True
        elif prop == 'action_always_exec':
            v = val_to_boolean(val)
            if v is not None:
                if self.action_always_exec != v:
                    self.action_always_exec = v
                    self.log_set(prop, v)
                    self.set_modified(save)
                return True
            else:
                return False
        elif prop == 'update_exec_after_action':
            v = val_to_boolean(val)
            if v is not None:
                if self.update_exec_after_action != v:
                    self.update_exec_after_action = v
                    self.log_set(prop, v)
                    self.set_modified(save)
                return True
            else:
                return False
        elif prop == 'update_state_after_action':
            v = val_to_boolean(val)
            if v is not None:
                if self.update_state_after_action != v:
                    self.update_state_after_action = v
                    self.log_set(prop, v)
                    self.set_modified(save)
                return True
            else:
                return False
        elif prop == 'update_if_action':
            v = val_to_boolean(val)
            if v is not None:
                if self.update_if_action != v:
                    self.update_if_action = v
                    self.log_set(prop, v)
                    self.set_modified(save)
                return True
            else:
                return False
        elif prop == 'auto_off':
            if val is None:
                auto_off = 0
            else:
                try:
                    auto_off = float(val)
                except:
                    return False
            if auto_off < 0:
                return False
            if self.auto_off != auto_off:
                self.auto_off = auto_off
                self.log_set(prop, auto_off)
                self.set_modified(save)
                if self.auto_off == 0:
                    self.stop_auto_processor()
                else:
                    self.start_auto_processor()
            return True
        elif prop == 'status_labels' and isinstance(val, dict):
            self.status_labels = val
            self.log_set(prop, 'dict')
            self.set_modified(save)
            self.ieid = eva.core.generate_ieid()
            return True
        elif prop[:7] == 'status:':
            try:
                s = int(prop.split(':')[1])
            except:
                return False
            s = str(s)
            if s == '0' and (val is None or val == ''):
                if self.status_labels['0'] != status_label_off:
                    self.status_labels['0'] = status_label_off
                    self.log_set('status_labels[0]', status_label_off)
                    self.set_modified(save)
                    self.ieid = eva.core.generate_ieid()
            elif s == '1' and (val is None or val == ''):
                if self.status_labels['1'] != status_label_on:
                    self.status_labels['1'] = status_label_on
                    self.log_set('status_labels[1]', status_label_on)
                    self.set_modified(save)
                    self.ieid = eva.core.generate_ieid()
            elif val is not None and val != '':
                if not s in self.status_labels or self.status_labels[s] != val:
                    self.status_labels[s] = val
                    self.log_set('status_labels[' + s + ']', val)
                    self.set_modified(save)
                    self.ieid = eva.core.generate_ieid()
            else:
                if not s in self.status_labels:
                    return False
                del self.status_labels[s]
                self.set_modified(save)
                self.ieid = eva.core.generate_ieid()
            return True
        else:
            return super().set_prop(prop, val, save)

    def start_processors(self):
        super().start_processors()
        self.register_modbus_status_updates()

    def stop_processors(self):
        super().stop_processors()
        self.unregister_modbus_status_updates()
        self.stop_auto_processor()

    def start_auto_processor(self):
        with self.auto_processor_lock:
            self.stop_auto_processor()
            if self.auto_off and self.status > 0:
                self.auto_processor = task_supervisor.create_async_job(
                    target=self._job_auto_off, number=1, timer=self.auto_off)

    def stop_auto_processor(self):
        with self.auto_processor_lock:
            if self.auto_processor:
                self.auto_processor.cancel()
                self.auto_processor = None

    async def _job_auto_off(self):
        with self.auto_processor_lock:
            logging.debug('%s auto off after %u seconds' % \
                        (self.oid, self.auto_off))
            # self.last_action = time.time()
            eva.core.spawn(eva.uc.controller.exec_unit_action,
                           self,
                           0,
                           None,
                           wait=eva.core.config.timeout)
            self.auto_processor = None

    def get_action_xc(self, a):
        if self.action_exec and self.action_exec[0] == '|':
            return eva.runner.DriverCommand(item=self,
                                            state=self.action_run_args(a),
                                            timeout=self.action_timeout,
                                            tki=self.term_kill_interval,
                                            _uuid=a.uuid)
        else:
            return super().get_action_xc(a)

    def action_may_run(self, action):
        nv = action.nvalue
        if not self.is_value_valid(nv):
            action.set_failed(exitcode=-20, err='value out of range')
            return False
        else:
            return self.action_always_exec or \
            action.nstatus != self.status or \
            (nv is not None and nv != self.value)

    def action_log_run(self, action):
        logging.info(
            '%s executing action %s pr=%u, status=%s, value="%s"' % \
             (self.oid, action.uuid, action.priority,
                 action.nstatus, action.nvalue))

    def action_run_args(self, action):
        nstatus = str(action.nstatus)
        if action.nvalue is not None:
            nvalue = str(action.nvalue)
        else:
            nvalue = self.value
        return (nstatus, nvalue)

    def action_before_run(self, action):
        if not self.update_if_action:
            self.disable_updates()

    def action_after_run(self, action, xc):
        self.last_action = time.time()
        self.enable_updates()
        if self.update_exec_after_action:
            self.update_processor.trigger_threadsafe(force=True)

    def update_set_state(self,
                         status=None,
                         value=None,
                         from_mqtt=False,
                         force_notify=False,
                         timestamp=None,
                         ieid=None):
        if self._destroyed:
            return False
        with self.update_lock:
            if not self.updates_allowed():
                return False
            if self.is_maintenance_mode():
                logging.info('Ignoring {} update in maintenance mode'.format(
                    self.oid))
                return False
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
            try:
                if status is not None:
                    _status = int(status)
                else:
                    _status = None
            except:
                logging.error('update %s returned invalid data' % self.oid)
                eva.core.log_traceback()
                return False
            if not self.queue_lock.acquire(timeout=eva.core.config.timeout):
                logging.critical('Unit::update_set_state locking broken')
            try:
                if self.current_action and self.current_action.is_status_running(
                ):
                    nstatus = None
                    nvalue = None
                else:
                    nstatus = _status
                    nvalue = value
                if not self.is_value_valid(value):
                    logging.error('Unit {} got invalid value {}'.format(
                        self.oid, value))
                    _status = -1
                    nstatus = -1
                    value = None
                    nvalue = None
                else:
                    self.update_expiration()
                self.set_state(status=_status,
                               value=value,
                               nstatus=nstatus,
                               nvalue=nvalue,
                               from_mqtt=from_mqtt,
                               timestamp=timestamp,
                               ieid=ieid)
            finally:
                self.queue_lock.release()
            return True

    def set_state(self,
                  status=None,
                  value=None,
                  nstatus=None,
                  nvalue=None,
                  from_mqtt=False,
                  timestamp=None,
                  ieid=None):
        if self._destroyed:
            return False
        need_notify = False
        state_changed = False
        if status is not None:
            if self.status != status:
                need_notify = True
                state_changed = True
                self.status = status
            self.start_auto_processor()
        if value is not None:
            if self.value != value:
                need_notify = True
                state_changed = True
                self.value = value
        if nstatus is not None:
            if self.nstatus != nstatus:
                need_notify = True
                self.nstatus = nstatus
        if nvalue is not None:
            if self.nvalue != nvalue:
                need_notify = True
                self.nvalue = nvalue
        if need_notify:
            logging.debug(
                '%s%s status = %u, value = "%s", nstatus = %u, nvalue = "%s"' %\
                    (self.oid, ' (mqtt update)' if \
                    from_mqtt else '', self.status, self.value,
                            self.nstatus, self.nvalue))
            if self.status == -1:
                logging.error('%s status is -1 (failed)' % self.oid)
            if state_changed:
                self.set_time = timestamp if timestamp else time.time()
            self.ieid = ieid if ieid else eva.core.generate_ieid()
            self.notify(skip_subscribed_mqtt=from_mqtt)
        return True

    def set_expired(self):
        if super().set_expired():
            self.nstatus = self.status
            self.nvalue = self.value
            if eva.core.config.db_update == 1:
                eva.uc.controller.save_item_state(self)

    def reset_nstate(self):
        self.set_state(nstatus=self.status, nvalue=self.value)

    def set_state_to_n(self):
        self.set_state(status=self.nstatus, value=self.nvalue)

    def destroy(self):
        self.nstatus = None
        self.nvalue = None
        self.action_enabled = None
        super().destroy()


class UnitAction(eva.item.ItemAction):

    def __init__(self,
                 unit,
                 nstatus,
                 nvalue=None,
                 priority=None,
                 action_uuid=None):
        self.unit_action_lock = threading.RLock()
        if not self.unit_action_lock.acquire(timeout=eva.core.config.timeout):
            logging.critical('UnitAction::__init__ locking broken')
            return False
        self.nstatus = nstatus
        self.nvalue = nvalue
        super().__init__(item=unit, priority=priority, action_uuid=action_uuid)
        self.unit_action_lock.release()

    def set_status(self, status, exitcode=None, out=None, err=None):
        if not self.unit_action_lock.acquire(timeout=eva.core.config.timeout):
            logging.critical('UnitAction::set_status locking broken')
            return False
        try:
            result = super().set_status(status=status,
                                        exitcode=exitcode,
                                        out=out,
                                        err=err)
            if not result:
                self.unit_action_lock.release()
                return False
            if self.is_status_running():
                self.item.set_state(nstatus=self.nstatus, nvalue=self.nvalue)
            elif self.is_status_failed() or self.is_status_terminated():
                self.item.reset_nstate()
            elif self.is_status_completed():
                if self.item.update_exec_after_action:
                    smsg = 'status will be set by update'
                elif not self.item.update_state_after_action:
                    smsg = 'status will be set by external'
                else:
                    self.item.update_expiration()
                    self.item.set_state_to_n()
                    smsg = 'status=%u value="%s"' % (self.item.status,
                                                     self.item.value)
                logging.debug('action %s completed, %s %s' %
                              (self.uuid, self.item.oid, smsg))
            return True
        finally:
            self.unit_action_lock.release()

    def action_env(self):
        if self.nvalue is not None:
            nvalue = self.nvalue
        else:
            nvalue = ''
        e = {'EVA_NSTATUS': str(self.nstatus), 'EVA_NVALUE': str(nvalue)}
        e.update(super().action_env())
        return e

    def serialize(self):
        if not self.unit_action_lock.acquire(timeout=eva.core.config.timeout):
            logging.critical('UnitAction::set_status locking broken')
            return False
        try:
            d = super().serialize()
            d['nstatus'] = self.nstatus
            d['nvalue'] = self.nvalue
            return d
        finally:
            self.unit_action_lock.release()
