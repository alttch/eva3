__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.1"

import eva.core
import eva.item
import eva.lm.controller
import logging
import time
import threading


class LVar(eva.item.VariableItem):

    def __init__(self, var_id):
        super().__init__(var_id, 'lvar')
        self._snmp_traps_allowed = False
        self._drivers_allowed = False
        self._modbus_allowed = False
        self.status = 1
        self.mqtt_update_topics.append('set_time')
        self.prv_value = None
        self.prv_status = 1
        self.update_lock = threading.RLock()

    def increment(self):
        return self._increment_decrement(op=1)

    def decrement(self):
        return self._increment_decrement(op=-1)

    def _increment_decrement(self, op=1):
        if not self.update_lock.acquire(timeout=eva.core.config.timeout):
            logging.critical('LVar::_increment_decrement locking broken')
            eva.core.critical()
            return False
        try:
            if self.value != '':
                try:
                    v = int(self.value)
                except:
                    return False
            else:
                v = 0
            return self.update_set_state(value=v + op)
        except:
            eva.core.log_traceback()
            return False
        finally:
            self.update_lock.release()

    def notify(self, skip_subscribed_mqtt=False, for_destroy=False):
        super().notify(
            skip_subscribed_mqtt=skip_subscribed_mqtt, for_destroy=for_destroy)
        if eva.core.config.db_update == 1:
            eva.lm.controller.save_lvar_state(self)

    def mqtt_set_state(self, topic, data):
        j = super().mqtt_set_state(topic, data)
        if j:
            try:
                if 'set_time' in j:
                    self.set_time = float(j['set_time'])
                    self.notify(skip_subscribed_mqtt=True)
            except:
                eva.core.log_traceback()

    def update_set_state(self, status=None, value=None, from_mqtt=False):
        if not self.status and status != 1: return False
        if not self.update_lock.acquire(timeout=eva.core.config.timeout):
            logging.critical('LVar::update_set_state locking broken')
            eva.core.critical()
            return False
        try:
            t = self.set_time
            _status = self.status
            _value = self.value
            if super().update_set_state(
                    status=status, value=value, from_mqtt=from_mqtt):
                if t != self.set_time:
                    self.notify(skip_subscribed_mqtt=from_mqtt)
                self.prv_status = _status
                self.prv_value = _value
                eva.lm.controller.pdme(self)
                return True
            return False
        finally:
            self.update_lock.release()

    def set_prop(self, prop, val=None, save=False):
        if super().set_prop(prop=prop, val=val, save=save):
            if prop == 'expires': self.notify()
            return True
        return False

    def set(self, value=None):
        self.update_set_state(status=1, value=value)
        logging.debug('%s set, expires: %f' % \
                (self.oid, self.set_time + self.expires))
        if value is not None:
            logging.debug('%s value = "%s"' % \
                    (self.oid, self.value))

    def set_expired(self):
        if super().set_expired():
            if self.status == -1:
                logging.info('%s expired' % self.oid)

    def serialize(self,
                  full=False,
                  config=False,
                  info=False,
                  props=False,
                  notify=False):
        d = super().serialize(
            full=full, config=config, info=info, props=props, notify=notify)
        d['expires'] = self.expires
        d['set_time'] = self.set_time
        return d

    def destroy(self):
        self.expires = None
        self.set_time = None
        super().destroy()
