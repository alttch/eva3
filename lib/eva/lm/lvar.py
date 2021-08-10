__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"

import eva.core
import eva.item
import eva.lm.controller
import logging
import time
import threading

from eva.tools import val_to_boolean

LOGIC_NORMAL = 0
LOGIC_SIMPLE = 1


class LVar(eva.item.VariableItem):

    fields = [
        'description',
        'expires',
        'logic',
        'mqtt_update',
        'notify_events',
        'update_delay',
        'update_exec',
        'update_interval',
        'update_timeout',
    ]

    def __init__(self, var_id=None, create=False, **kwargs):
        super().__init__(var_id, 'lvar', **kwargs)
        self.status = 1
        self.mqtt_update_topics.append('set_time')
        self.prv_value = None
        self.prv_status = 1
        self.update_lock = threading.RLock()
        self.logic = LOGIC_NORMAL
        if create:
            self.set_defaults(self.fields)

    def update_config(self, data):
        if 'logic' in data:
            self.logic = data['logic']
        super().update_config(data)

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

    def notify(self,
               skip_subscribed_mqtt=False,
               for_destroy=False,
               skip_db=False):
        super().notify(skip_subscribed_mqtt=skip_subscribed_mqtt,
                       for_destroy=for_destroy)
        if eva.core.config.db_update == 1 and not skip_db:
            eva.lm.controller.save_lvar_state(self)

    def update_expiration(self):
        if self.expires:
            self.set_time = time.time()
            self.ieid = eva.core.generate_ieid()
        super().update_expiration()

    def update_set_state(self,
                         status=None,
                         value=None,
                         from_mqtt=False,
                         force_notify=False,
                         notify=True,
                         timestamp=None):
        if not self.status and status != 1 and self.logic != LOGIC_SIMPLE:
            return False
        if not self.update_lock.acquire(timeout=eva.core.config.timeout):
            logging.critical('LVar::update_set_state locking broken')
            eva.core.critical()
            return False
        try:
            _status = self.status
            _value = self.value
            if super().update_set_state(status=status,
                                        value=value,
                                        from_mqtt=from_mqtt,
                                        force_notify=force_notify or
                                        self.expires,
                                        force_update=self.logic == LOGIC_SIMPLE,
                                        notify=notify,
                                        timestamp=timestamp):
                self.prv_status = _status
                self.prv_value = _value
                eva.lm.controller.pdme(self)
                return True
            return False
        finally:
            self.update_lock.release()

    def set_prop(self, prop, val=None, save=False):
        if prop == 'logic':
            if val is None or val == '':
                val = 'normal'
            elif val not in ['normal', 'simple', 'n', 's']:
                return False
            if val in ['normal', 'n']:
                logic = LOGIC_NORMAL
            elif val in ['simple', 's']:
                logic = LOGIC_SIMPLE
            if self.logic != logic:
                self.logic = logic
                self.log_set(prop, logic)
                self.set_modified(save)
            return True
        elif super().set_prop(prop=prop, val=val, save=save):
            if prop == 'expires':
                self.ieid = eva.core.generate_ieid()
                self.notify()
                if eva.core.config.db_update == 1:
                    self.save()
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
        if self.logic == LOGIC_SIMPLE:
            super().update_set_state(value='',
                                     force_update=self.logic == LOGIC_SIMPLE,
                                     update_expiration=False)
            logging.info('%s expired' % self.oid)
        elif super().set_expired():
            if self.status == -1:
                logging.info('%s expired' % self.oid)

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
        if props:
            d['logic'] = 'simple' if self.logic == LOGIC_SIMPLE else 'normal'
        elif config:
            d['logic'] = self.logic
        d['expires'] = self.expires
        if not config and not props:
            d['set_time'] = self.set_time
        return d

    def destroy(self):
        self.expires = None
        self.set_time = None
        super().destroy()

    def is_expired(self):
        if self.logic == 'simple':
            return False
        else:
            return super().is_expired()
