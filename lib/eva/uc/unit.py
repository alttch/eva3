__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.1"

import eva.core
import eva.item
import eva.uc.controller
import logging
import threading
import time

from eva.tools import val_to_boolean
from eva.uc.ucitem import UCItem

status_label_off = 'OFF'
status_label_on = 'ON'


class Unit(eva.item.UpdatableItem, eva.item.ActiveItem, eva.item.PhysicalItem,
           UCItem):

    def __init__(self, unit_id):
        super().__init__(unit_id, 'unit')

        self.update_exec_after_action = False
        self.update_state_after_action = True
        self.update_if_action = False
        self.action_always_exec = False
        self.auto_off = 0
        self.nstatus = 0
        self.nvalue = ''
        self.last_action = 0
        self.auto_processor_active = False
        self.auto_processor = None
        # labels have string keys to be JSON compatible
        self.default_status_labels = {
            '0': status_label_off,
            '1': status_label_on
        }
        self.status_labels = self.default_status_labels.copy()

    def status_by_label(self, label):
        if label is None: return None
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
        d.update(super().serialize(
            full=full, config=config, info=info, props=props, notify=notify))
        return d

    def create_action(self,
                      nstatus,
                      nvalue='',
                      priority=None,
                      action_uuid=None):
        return UnitAction(self, nstatus, nvalue, priority, action_uuid)

    def mqtt_action(self, msg):
        eva.uc.controller.exec_mqtt_unit_action(self, msg)

    def update_config(self, data):
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
        super().update_config(data)

    def set_prop(self, prop, val=None, save=False):
        if prop == 'action_always_exec':
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
            if auto_off < 0: return False
            if self.auto_off != auto_off:
                self.auto_off = auto_off
                self.log_set(prop, auto_off)
                self.set_modified(save)
                if not auto_off:
                    self.stop_auto_processor()
                else:
                    self.start_auto_processor()
            return True
        elif prop == 'status_labels' and isinstance(val, dict):
            self.status_labels = val
            self.log_set(prop, 'dict')
            self.set_modified(save)
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
            elif s == '1' and (val is None or val == ''):
                if self.status_labels['1'] != status_label_on:
                    self.status_labels['1'] = status_label_on
                    self.log_set('status_labels[1]', status_label_on)
                    self.set_modified(save)
            elif val is not None and val != '':
                if not s in self.status_labels or self.status_labels[s] != val:
                    self.status_labels[s] = val
                    self.log_set('status_labels[' + s + ']', val)
                    self.set_modified(save)
            else:
                if not s in self.status_labels: return False
                del self.status_labels[s]
            return True
        else:
            return super().set_prop(prop, val, save)

    def start_processors(self):
        super().start_processors()
        self.start_auto_processor()

    def stop_processors(self):
        super().stop_processors()
        self.stop_auto_processor()

    def start_auto_processor(self):
        self.auto_processor_active = True
        if (self.auto_processor and self.auto_processor.is_alive()):
            return
        if not self.auto_off:
            self.auto_processor_active = False
            return
        self.auto_processor = threading.Thread(target = \
                self._t_auto_processor,
                name = '_t_auto_processor_' + self.item_id
                )
        self.auto_processor.start()

    def stop_auto_processor(self):
        if self.auto_processor_active:
            self.auto_processor_active = False
            self.auto_processor.join()

    def _t_auto_processor(self):
        logging.debug('%s auto processor started' % self.oid)
        while self.auto_processor_active and self.auto_off:
            time.sleep(eva.core.config.polldelay)
            if self.last_action and \
                    self.status != 0 and \
                    time.time() - self.last_action > self.auto_off:
                logging.debug('%s auto off after %u seconds' % \
                        (self.oid, self.auto_off))
                self.last_action = time.time()
                eva.uc.controller.exec_unit_action(
                    self, 0, None, wait=eva.core.config.timeout)
        self.auto_processor_active = False
        logging.debug('%s auto processor stopped' % self.oid)

    def action_may_run(self, action):
        nv = action.nvalue
        if nv is None: nv = ''
        return self.action_always_exec or \
            action.nstatus != self.status or \
            nv != self.value

    def action_log_run(self, action):
        logging.info(
            '%s executing action %s pr=%u, status=%s, value="%s"' % \
             (self.oid, action.uuid, action.priority,
                 action.nstatus, action.nvalue))

    def action_run_args(self, action, n2n=True):
        nstatus = str(action.nstatus)
        if action.nvalue is not None:
            nvalue = str(action.nvalue)
        elif n2n:
            nvalue = ''
        else:
            nvalue = None
        return (nstatus, nvalue)

    def action_before_get_task(self):
        self.enable_updates()

    def action_before_run(self, action):
        if not self.update_if_action:
            self.disable_updates()

    def action_after_run(self, action, xc):
        self.last_action = time.time()
        if self.update_exec_after_action: self.do_update()
        self.enable_updates()

    def update_set_state(self,
                         status=None,
                         value=None,
                         from_mqtt=False):
        if self._destroyed: return False
        try:
            if status is not None: _status = int(status)
            else: _status = None
        except:
            logging.error('update %s returned bad data' % self.oid)
            eva.core.log_traceback()
            return False
        if not self.queue_lock.acquire(timeout=eva.core.config.timeout):
            logging.critical('Unit::update_set_state locking broken')
        if self.current_action and self.current_action.is_status_running():
            nstatus = None
            nvalue = None
        else:
            nstatus = _status
            nvalue = value
        self.update_expiration()
        self.set_state(
            status=_status,
            value=value,
            nstatus=nstatus,
            nvalue=nvalue,
            from_mqtt=from_mqtt)
        self.queue_lock.release()
        return True

    def set_state(self,
                  status=None,
                  value=None,
                  nstatus=None,
                  nvalue=None,
                  from_mqtt=False):
        if self._destroyed: return False
        need_notify = False
        if status is not None:
            if self.status != status: need_notify = True
            self.status = status
        if value is not None:
            if value == '': v = ''
            else: v = value
            if self.value != v: need_notify = True
            self.value = v
        if nstatus is not None:
            if self.nstatus != nstatus: need_notify = True
            self.nstatus = nstatus
        if nvalue is not None:
            if nvalue == '': nv = ''
            else: nv = nvalue
            if self.nvalue != nv: need_notify = True
            self.nvalue = nv
        if need_notify:
            logging.debug(
                '%s status = %u, value = "%s", nstatus = %u, nvalue = "%s"' % \
                        (self.oid, self.status, self.value,
                            self.nstatus, self.nvalue))
            if self.status == -1:
                logging.error('%s status is -1 (failed)' % self.oid)
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
        self.unit_action_lock = threading.Lock()
        if not self.unit_action_lock.acquire(timeout=eva.core.config.timeout):
            logging.critical('UnitAction::__init__ locking broken')
            return False
        self.nstatus = nstatus
        self.nvalue = nvalue
        super().__init__(item=unit, priority=priority, action_uuid=action_uuid)
        self.unit_action_lock.release()

    def set_status(self, status, exitcode=None, out=None, err=None, lock=True):
        if lock:
            if not self.unit_action_lock.acquire(
                    timeout=eva.core.config.timeout):
                logging.critical('UnitAction::set_status locking broken')
                return False
        result = super().set_status(
            status=status, exitcode=exitcode, out=out, err=err, lock=lock)
        if not result:
            if lock: self.unit_action_lock.release()
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
            logging.debug(
                'action %s completed, %s %s' % (self.uuid, self.item.oid, smsg))
        if lock: self.unit_action_lock.release()
        return True

    def action_env(self):
        if self.nvalue is not None: nvalue = self.nvalue
        else: nvalue = ''
        e = {'EVA_NSTATUS': str(self.nstatus), 'EVA_NVALUE': str(nvalue)}
        e.update(super().action_env())
        return e

    def serialize(self):
        d = super().serialize()
        d['nstatus'] = self.nstatus
        d['nvalue'] = self.nvalue
        return d
