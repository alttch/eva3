__author__ = "Altertech Group, http://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2017 Altertech Group"
__license__ = "See http://www.eva-ics.com/"
__version__ = "3.0.1"

import eva.core
import eva.item
import eva.lm.controller
import logging
import time
import threading


class LVar(eva.item.VariableItem):

    def __init__(self, var_id):
        super().__init__(var_id, 'lvar')
        self._virtual_allowed = False
        self._snmp_traps_allowed = False
        self.status = 1
        self.mqtt_update_topics.append('set_time')
        self.prv_value = None
        self.prv_status = 1
        self.update_lock = threading.Lock()

    def notify(self, skip_subscribed_mqtt=False):
        super().notify(skip_subscribed_mqtt=skip_subscribed_mqtt)
        if eva.core.db_update == 1: eva.lm.controller.save_lvar_state(self)

    def mqtt_set_state(self, topic, data):
        super().mqtt_set_state(topic, data)
        try:
            if topic.endswith('/set_time'):
                self.set_time = float(data)
                self.notify(skip_subscribed_mqtt=True)
        except:
            eva.core.log_traceback()

    def update_set_state(self,
                         status=None,
                         value=None,
                         from_mqtt=False,
                         force_virtual=False):
        if not self.status and status != 1: return False
        if not self.update_lock.acquire(timeout=eva.core.timeout):
            logging.critical('LVar::update_set_state locking broken')
            return False
        t = self.set_time
        _status = self.status
        _value = self.value
        if super().update_set_state(
                status=status,
                value=value,
                from_mqtt=from_mqtt,
                force_virtual=force_virtual):
            if t != self.set_time:
                self.notify(skip_subscribed_mqtt=from_mqtt)
            self.prv_status = _status
            self.prv_value = _value
            eva.lm.controller.pdme(self)
            self.update_lock.release()
            return True
        self.update_lock.release()
        return False

    def set_prop(self, prop, val=None, save=False):
        if super().set_prop(prop=prop, val=val, save=save):
            if prop == 'expires': self.notify()
            return True
        return False

    def set(self, value=None, force_virtual=False):
        self.update_set_state(
            status=1, value=value, force_virtual=force_virtual)
        logging.debug('%s set, expires: %f' % \
                (self.full_id, self.set_time + self.expires))
        if value is not None:
            logging.debug('%s value = "%s"' % \
                    (self.full_id, self.value))

    def set_expired(self):
        if super().set_expired():
            if self.status == -1:
                logging.info('%s expired', self.full_id)

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
