__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.1"

import copy
import os
import threading
import time
import uuid
import queue
import logging
import jsonpickle
import eva.core

from eva.tools import format_json
from eva.tools import val_to_boolean
from eva.tools import dict_from_str
from eva.tools import is_oid
from eva.tools import parse_oid
from eva.tools import safe_int
# from evacpp.evacpp import GenericAction
from eva.generic import GenericAction

from eva.exceptions import ResourceNotFound
from eva.exceptions import FunctionFailed
from eva.exceptions import InvalidParameter

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


class Item(object):

    def __init__(self, item_id, item_type):
        self.item_id = item_id
        self.item_type = item_type
        self.set_group('nogroup')
        self.description = ''
        self._destroyed = False
        self.config_changed = False
        self.config_file_exists = False
        # generate long config names or use IDs in enterprise layout
        self.respect_layout = True

    def set_group(self, group=None):
        if group: self.group = group
        else: self.group = 'nogroup'
        self.full_id = self.group + '/' + self.item_id
        self.oid = self.item_type + ':' + self.full_id

    def update_config(self, data):
        if 'group' in data:
            self.set_group(data['group'])
        if 'description' in data:
            self.description = data['description']
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

    def notify(self, retain=None, skip_subscribed_mqtt=False):
        try:
            if skip_subscribed_mqtt: s = self
            else: s = None
            d = self.serialize(notify=True)
            eva.notify.notify(
                'state',
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
            if not config or self.description != '':
                d['description'] = self.description
        if full:
            d['config_changed'] = self.config_changed
        if info:
            d['full_id'] = self.full_id
            d['oid'] = self.oid
        return d

    def get_fname(self, fname=None):
        if fname:
            return fname
        else:
            _id = self.full_id.replace('/', '___') if \
                eva.core.config.enterprise_layout and self.respect_layout else \
                        self.item_id
            return eva.core.format_cfg_fname(eva.core.product.code + \
                    '_%s.d/' % self.item_type + _id + '.json', \
                    cfg = None, runtime = True)

    def load(self, fname=None):
        fname_full = self.get_fname(fname)
        try:
            raw = ''.join(open(fname_full).readlines())
        except:
            logging.error('can not load %s config from %s' % \
                                    (self.oid,fname_full))
            eva.core.log_traceback()
            return False
        try:
            data = jsonpickle.decode(raw)
            if data['id'] != self.item_id:
                raise Exception('id mismatch, file %s' % \
                            fname_full)
            self.update_config(data)
        except:
            logging.error(
                   'can not load %s config from %s, bad config format' % \
                                    (self.oid,fname_full)
                            )
            eva.core.log_traceback()
            return False
        self.config_changed = False
        self.config_file_exists = True
        return True

    def save(self, fname=None):
        u = self.serialize(config=True)
        fname_full = self.get_fname(fname)
        data = self.serialize(config=True)
        logging.debug('Saving %s configuration' % self.oid)
        try:
            open(fname_full, 'w').write(format_json(data, minimal=False))
            self.config_changed = False
        except:
            logging.error('can not save %s config into %s' % \
                (self.oid,fname_full))
            eva.core.log_traceback()
            return False
        self.config_file_exists = True
        return True

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

    def __init__(self, item_id, item_type):
        super().__init__(item_id, item_type)
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
            if val is None: v = ''
            else: v = val
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
        d.update(super().serialize(
            full=full, config=config, info=info, props=props, notify=notify))
        return d


class UpdatableItem(Item):

    def __init__(self, item_id, item_type):
        super().__init__(item_id, item_type)
        self.update_exec = None
        self.update_interval = 0
        self.update_delay = 0
        self.update_timeout = eva.core.config.timeout
        self._update_timeout = None
        self.update_processor = None
        self.update_scheduler = None
        self.expiration_checker = None
        self.update_processor_active = False
        self.update_scheduler_active = False
        self.expiration_checker_active = False
        self._updates_allowed = True
        self.need_update = threading.Event()
        self.update_xc = None
        # default status: 0 - off, 1 - on, -1 - error
        self.status = 0
        self.value = ''
        self.set_time = time.time()
        self.expires = 0
        self.snmp_trap = None
        self.update_driver_config = None
        self.mqtt_update = None
        self.mqtt_update_notifier = None
        self.mqtt_update_qos = 1
        self.mqtt_update_topics = ['', 'status', 'value']
        self.modbus_status = None
        self.modbus_value = None
        self.virtual = False
        self._virtual_allowed = True
        self._mqtt_updates_allowed = True
        self._snmp_traps_allowed = True
        self._drivers_allowed = True
        self._modbus_allowed = True
        self._modbus_status_allowed = True
        self._expire_on_any = False
        self.mqtt_update_timestamp = 0

    def update_config(self, data):
        if 'modbus_status' in data and \
                self._modbus_allowed and self._modbus_status_allowed:
            self.modbus_status = data['modbus_status']
        if 'modbus_value' in data and self._modbus_allowed:
            self.modbus_value = data['modbus_value']
        if 'virtual' in data and self._virtual_allowed:
            self.virtual = data['virtual']
        if 'snmp_trap' in data:
            self.snmp_trap = data['snmp_trap']
        if 'update_driver_config' in data:
            self.update_driver_config = data['update_driver_config']
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
        if prop == 'virtual' and self._virtual_allowed:
            v = val_to_boolean(val)
            if v is not None:
                if self.virtual != v:
                    self.virtual = v
                    self.log_set(prop, v)
                    self.set_modified(save)
                return True
            else:
                return False
        elif prop == 'expires':
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
                    self.start_expiration_checker()
            return True
        elif prop == 'update_exec':
            if self.update_exec != val:
                if val and val[0] == '|':
                    if self._drivers_allowed:
                        import eva.uc.driverapi
                        d = eva.uc.driverapi.get_driver(val[1:])
                        if not d:
                            logging.error(
                                'Can not set ' + \
                                    '%s.update_exec = %s, no such driver'
                                    % (self.oid, val))
                            return False
                    else:
                        return False
                if not val:
                    self.unregister_driver_updates()
                self.update_exec = val
                self.log_set(prop, val)
                self.set_modified(save)
                if val and val[0] == '|':
                    self.register_driver_updates()
            return True
        elif prop == 'update_interval':
            if val is None:
                update_interval = 0
            else:
                try:
                    update_interval = float(val)
                except:
                    return False
            if update_interval < 0: return False
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
                if self.update_delay:
                    self.update_delay = 0
                    self.log_set(prop, 0)
                    self.set_modified(save)
            else:
                try:
                    update_delay = float(val)
                except:
                    return False
                if update_delay < 0: return False
                if self.update_delay != update_delay:
                    self.update_delay = update_delay
                    self.log_set(prop, update_delay)
                    self.set_modified(save)
            return True
        elif prop == 'update_timeout':
            if val is None:
                if self._update_timeout is not None:
                    self.update_timeout = eva.core.config.timeout
                    self._update_timeout = None
                    self.log_set(prop, None)
                    self.set_modified(save)
            else:
                try:
                    update_timeout = float(val)
                except:
                    return False
                if update_timeout <= 0: return False
                if self._update_timeout != update_timeout:
                    self._update_timeout = update_timeout
                    self.update_timeout = update_timeout
                    self.log_set(prop, update_timeout)
                    self.set_modified(save)
            return True
        elif prop == 'snmp_trap' and self._snmp_traps_allowed:
            if val is None:
                self.snmp_trap = None
                self.unsubscribe_snmp_traps()
                self.log_set(prop, None)
                self.set_modified(save)
                return True
            elif isinstance(val, dict):
                self.snmp_trap = val
                self.subscribe_snmp_traps()
                self.log_set('snmp_trap', 'dict')
                self.set_modified(save)
                return True
            return False
        elif prop == 'update_driver_config' and self._drivers_allowed:
            if val is None:
                self.update_driver_config = None
                self.log_set(prop, None)
                self.set_modified(save)
                return True
            else:
                try:
                    v = dict_from_str(val)
                except:
                    eva.core.log_traceback()
                    return False
                self.update_driver_config = v
                self.log_set(prop, 'dict')
                self.set_modified(save)
                return True
        elif prop == 'modbus_status' and self._modbus_allowed and \
                self._modbus_status_allowed:
            import eva.uc.modbus
            if self.modbus_status == val: return True
            if val is None:
                self.unregister_modbus_status_updates()
                self.modbus_status = None
            else:
                if val[0] not in ['h', 'c']: return False
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
        elif prop == 'modbus_value' and self._modbus_allowed:
            import eva.uc.modbus
            if self.modbus_value == val: return True
            if val is None:
                self.unregister_modbus_value_updates()
                self.modbus_value = None
            else:
                if val[0] not in ['h', 'c']: return False
                try:
                    addr = safe_int(val[1:])
                    if addr > eva.uc.modbus.slave_reg_max or addr < 0:
                        return False
                except:
                    return False
                self.unregister_modbus_value_updates()
                self.modbus_value = val
                self.modbus_update_value(addr,
                                         eva.uc.modbus.get_data(addr, val[0]))
                self.register_modbus_value_updates()
            self.log_set('modbus_value', val)
            self.set_modified(save)
            return True
        elif prop == 'snmp_trap.ident_vars' and self._snmp_traps_allowed:
            if val is None:
                if self.snmp_trap and 'ident_vars' in self.snmp_trap:
                    del self.snmp_trap['ident_vars']
                    if not self.snmp_trap: self.unsubscribe_snmp_traps()
                    self.log_set('snmp_trap.ident_vars', None)
                    self.set_modified(save)
                return True
            else:
                ivars = {}
                try:
                    for x in val.split(','):
                        k, v = x.split('=')
                        ivars[k] = v
                except:
                    return False
                if not self.snmp_trap: self.snmp_trap = {}
                self.snmp_trap['ident_vars'] = ivars
                self.subscribe_snmp_traps()
                self.log_set('snmp_trap.ident_vars', val)
                self.set_modified(save)
                return True
        elif prop == 'snmp_trap.set_down' and self._snmp_traps_allowed:
            if val is None:
                if self.snmp_trap and 'set_down' in self.snmp_trap:
                    del self.snmp_trap['set_down']
                    if not self.snmp_trap: self.unsubscribe_snmp_traps()
                    self.log_set('snmp_trap.set_down', None)
                    self.set_modified(save)
                return True
            else:
                ivars = {}
                try:
                    for x in val.split(','):
                        k, v = x.split('=')
                        ivars[k] = v
                except:
                    return False
                if not self.snmp_trap: self.snmp_trap = {}
                self.snmp_trap['set_down'] = ivars
                self.log_set('snmp_trap.set_down', val)
                self.subscribe_snmp_traps()
                self.set_modified(save)
                return True
        elif prop == 'snmp_trap.set_status' and self._snmp_traps_allowed:
            if val is None:
                if self.snmp_trap and 'set_status' in self.snmp_trap:
                    del self.snmp_trap['set_status']
                    if not self.snmp_trap: self.unsubscribe_snmp_traps()
                    self.log_set('snmp_trap.set_status', None)
                    self.set_modified(save)
                return True
            else:
                if not self.snmp_trap: self.snmp_trap = {}
                self.snmp_trap['set_status'] = val
                self.subscribe_snmp_traps()
                self.log_set('snmp_trap.set_status', val)
                self.set_modified(save)
                return True
        elif prop == 'snmp_trap.set_value' and self._snmp_traps_allowed:
            if val is None:
                if self.snmp_trap and 'set_value' in self.snmp_trap:
                    del self.snmp_trap['set_value']
                    if not self.snmp_trap: self.unsubscribe_snmp_traps()
                    self.log_set('snmp_trap.set_value', None)
                    self.set_modified(save)
                return True
            else:
                if not self.snmp_trap: self.snmp_trap = {}
                self.snmp_trap['set_value'] = val
                self.subscribe_snmp_traps()
                self.log_set('snmp_trap.set_value', val)
                self.set_modified(save)
                return True
        elif prop[:16] == 'snmp_trap.set_if' and self._snmp_traps_allowed:
            if val is None:
                if self.snmp_trap and 'set_if' in self.snmp_trap:
                    del self.snmp_trap['set_if']
                    self.log_set('snmp_trap.set_if', None)
                    self.set_modified(save)
                    if not self.snmp_trap: self.unsubscribe_snmp_traps()
                return True
            try:
                state, iv = val.split(':')
                s, va = state.split(',')
                ivars = {}
                for x in iv.split(','):
                    k, v = x.split('=')
                    ivars[k] = v
                if not self.snmp_trap: self.snmp_trap = {}
                if not 'set_if' in self.snmp_trap:
                    self.snmp_trap['set_if'] = []
                r = {'vars': ivars}
                if s != 'null' and s != '':
                    r['status'] = int(s)
                if va != 'null' and va != '':
                    r['value'] = va
                self.log_set('snmp_trap.set_if+', val)
                self.snmp_trap['set_if'].append(r)
            except:
                return False
            self.subscribe_snmp_traps()
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

    def register_modbus_status_updates(self):
        if self.modbus_status:
            import eva.uc.modbus
            eva.uc.modbus.register_handler(
                self.modbus_status[1:],
                self.modbus_update_status,
                register=self.modbus_status[0])

    def register_modbus_value_updates(self):
        if self.modbus_value:
            import eva.uc.modbus
            eva.uc.modbus.register_handler(
                self.modbus_value[1:],
                self.modbus_update_value,
                register=self.modbus_value[0])

    def unregister_modbus_status_updates(self):
        if self.modbus_status:
            import eva.uc.modbus
            eva.uc.modbus.unregister_handler(
                self.modbus_status[1:],
                self.modbus_update_status,
                register=self.modbus_status[0])

    def unregister_modbus_value_updates(self):
        if self.modbus_value:
            import eva.uc.modbus
            eva.uc.modbus.unregister_handler(
                self.modbus_value[1:],
                self.modbus_update_value,
                register=self.modbus_value[0])

    def start_processors(self):
        self.subscribe_mqtt_update()
        self.subscribe_snmp_traps()
        self.register_modbus_status_updates()
        self.register_modbus_value_updates()
        self.register_driver_updates()
        self.start_update_processor()
        self.start_update_scheduler()
        self.start_expiration_checker()
        super().start_processors()

    def stop_processors(self):
        self.unsubscribe_mqtt_update()
        self.unregister_driver_updates()
        self.unregister_modbus_value_updates()
        self.unregister_modbus_status_updates()
        self.unsubscribe_snmp_traps()
        self.stop_update_processor()
        self.stop_update_scheduler()
        self.stop_expiration_checker()
        super().stop_processors()

    def subscribe_snmp_traps(self):
        if self.snmp_trap and self._snmp_traps_allowed:
            eva.traphandler.subscribe(self)

    def register_driver_updates(self):
        if self._drivers_allowed and \
                self.update_exec and self.update_exec[0] == '|':
            import eva.uc.driverapi
            eva.uc.driverapi.register_item_update(self)

    def unsubscribe_snmp_traps(self):
        if self._snmp_traps_allowed:
            eva.traphandler.unsubscribe(self)

    def unregister_driver_updates(self):
        if self._drivers_allowed and \
                self.update_exec and self.update_exec[0] == '|':
            import eva.uc.driverapi
            eva.uc.driverapi.unregister_item_update(self)

    def subscribe_mqtt_update(self):
        if not self.mqtt_update or \
                not self._mqtt_updates_allowed:
            return False
        notifier = eva.notify.get_notifier(self.mqtt_update_notifier)
        if not notifier or notifier.notifier_type[:4] != 'mqtt': return False
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
        if not notifier or notifier.notifier_type[:4] != 'mqtt': return False
        try:
            notifier.update_item_remove(self)
        except:
            eva.core.log_traceback()
            return False
        return True

    def start_update_processor(self):
        self.update_processor_active = True
        if self.update_processor and self.update_processor.is_alive():
            return
        self.update_processor = threading.Thread(target = \
                self._t_update_processor,
                name = '_t_update_processor_' + self.oid)
        self.update_processor.start()

    def stop_update_processor(self):
        if self.update_processor_active:
            self.update_processor_active = False
            self.disable_updates()
            self.need_update.set()

    def start_update_scheduler(self):
        self.update_scheduler_active = True
        if self.update_scheduler and \
                self.update_scheduler.is_alive():
            return
        if not self.update_interval:
            self.update_scheduler_active = False
            return
        if eva.core.is_started() and self.updates_allowed():
            self.need_update.set()
        self.update_scheduler = threading.Thread(target = \
                self._t_update_scheduler,
                name = '_t_update_scheduler_' + self.oid)
        self.update_scheduler.start()

    def start_expiration_checker(self):
        self.expiration_checker_active = True
        if (self.expiration_checker and \
                self.expiration_checker.is_alive()):
            return
        if not self.expires:
            self.expiration_checker_active = False
            return
        self.expiration_checker = threading.Thread(target = \
                self._t_expiration_checker,
                name = '_t_expiration_checker_' + self.oid)
        self.expiration_checker.start()

    def stop_update_scheduler(self):
        if self.update_scheduler_active:
            self.update_scheduler_active = False
            self.update_scheduler.join()

    def stop_expiration_checker(self):
        if self.expiration_checker_active:
            self.expiration_checker_active = False
            self.expiration_checker.join()

    def updates_allowed(self):
        return self._updates_allowed

    def disable_updates(self):
        self._updates_allowed = False

    def enable_updates(self):
        self._updates_allowed = True

    def update_run_args(self):
        return ()

    def do_update(self):
        i = 0
        while i < self.update_delay and self.update_scheduler_active:
            time.sleep(eva.core.sleep_step)
            i += eva.core.sleep_step
        if self.update_scheduler_active:
            self.need_update.set()

    def _t_update_scheduler(self):
        logging.debug('%s update scheduler started' % self.oid)
        while self.update_scheduler_active and self.update_interval:
            i = 0
            while i < self.update_interval and self.update_scheduler_active:
                time.sleep(eva.core.sleep_step)
                i += eva.core.sleep_step
            if not self.update_scheduler_active or not self.update_interval:
                break
            if self.updates_allowed():
                if self.update_delay:
                    t  = threading.Thread(target = self.do_update,
                            name = 'do_update_%s_%f' % \
                                    (self.oid, time.time()))
                    t.start()
                else:
                    self.do_update()
        self.update_scheduler_active = False
        logging.debug('%s update scheduler stopped' % self.oid)

    def _t_update_processor(self):
        logging.debug('%s update processor started' % self.oid)
        while self.update_processor_active:
            self.need_update.wait()
            self.need_update.clear()
            if self.update_processor_active:
                self._perform_update()
        logging.debug('%s update processor stopped' % self.oid)

    def _t_expiration_checker(self):
        logging.debug('%s expiration checker started' % self.oid)
        while self.expiration_checker_active and self.expires:
            time.sleep(eva.core.config.polldelay)
            if self.status != -1 and \
                    (self.status != 0 or self._expire_on_any) and \
                    self.is_expired():
                logging.debug('%s expired, resetting status/value' % \
                        self.oid)
                self.set_expired()
                break
        self.expiration_checker_active = False
        logging.debug('%s expiration checker stopped' % self.oid)

    def is_expired(self):
        if not self.expires: return False
        return time.time() - self.set_time > self.expires

    def set_expired(self):
        if self.status == -1 and self.value == '': return False
        self.update_set_state(status=-1, value='', force_virtual=True)
        return True

    def update(self, driver_state_in=None):
        if self.updates_allowed() and not self.is_destroyed():
            self._perform_update(driver_state_in)

    def _perform_update(self, driver_state_in=None):
        try:
            self.update_log_run()
            self.update_before_run()
            xc = self.get_update_xc(driver_state_in)
            self.update_xc = xc
            xc.run()
            if xc.exitcode < 0:
                logging.error('update %s terminated' % self.oid)
            elif xc.exitcode > 0:
                logging.error('update %s failed, code %u' % \
                        (self.oid, xc.exitcode))
            else:
                if self.updates_allowed(): self.update_after_run(xc.out)
        except:
            logging.error('update %s failed' % self.oid)
            eva.core.log_traceback()

    def get_update_xc(self, driver_state_in=None):
        import eva.runner
        if self._drivers_allowed and not self.virtual and \
                self.update_exec and self.update_exec[0] == '|':
            return eva.runner.DriverCommand(
                item=self,
                update=True,
                timeout=self.update_timeout,
                state_in=driver_state_in)
        return eva.runner.ExternalProcess(
            fname=self.update_exec,
            item=self,
            env=self.update_env(),
            update=True,
            args=self.update_run_args(),
            timeout=self.update_timeout)

    def update_env(self):
        return {}

    def update_log_run(self):
        logging.debug('updating %s' % self.oid)

    def update_before_run(self):
        pass

    def update_expiration(self):
        self.set_time = time.time()
        self.start_expiration_checker()

    def update_after_run(self, update_out):
        if self._destroyed or update_out is False: return
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
                if value is None: value = ''
        except:
            logging.error('update %s returned bad data' % self.oid)
            eva.core.log_traceback()
            return False
        return self.update_set_state(status, value, force_virtual=True)

    def process_snmp_trap(self, host, data):
        if not self.snmp_trap: return
        try:
            if 'ident_vars' in self.snmp_trap:
                for i, v in self.snmp_trap['ident_vars'].items():
                    if not i in data or data[i] != v:
                        return
            _set = True
            if 'set_down' in self.snmp_trap:
                for i, v in self.snmp_trap['set_down'].items():
                    if not i in data or data[i] != v:
                        _set = False
                        break
            if _set:
                logging.debug('%s according to the trap has failed' % \
                        self.oid)
                self.update_set_state(status=-1)
                return
            if 'set_if' in self.snmp_trap:
                for cond in self.snmp_trap['set_if']:
                    if 'vars' in cond:
                        _set = True
                        for i, v in cond['vars'].items():
                            if not i in data or data[i] != v:
                                _set = False
                                break
                        if _set:
                            if 'status' in cond:
                                status = cond['status']
                            else:
                                status = None
                            if 'value' in cond:
                                value = cond['value']
                            else:
                                value = None
                            if status is not None or value is not None:
                                self.update_set_state(status, value)
            status = None
            value = None
            if 'set_status' in self.snmp_trap and \
                    self.snmp_trap['set_status'] in data:
                try:
                    status = \
                        int(data[self.snmp_trap['set_status']])
                except:
                    logging.error(
                        '%s bad status integer in snmp trap' % \
                                self.oid)
            if 'set_value' in self.snmp_trap and \
                    self.snmp_trap['set_value'] in data:
                value = data[self.snmp_trap['set_value']]
            if status is not None or value is not None:
                self.update_set_state(status, value)
        except:
            eva.core.log_traceback()

    def mqtt_set_state(self, topic, data):
        try:
            if topic.endswith('/status'):
                self.update_set_state(status=data)
            elif topic.endswith('/value'):
                self.update_set_state(value=data)
            elif topic == self.item_type + '/' + self.full_id:
                j = jsonpickle.decode(data)
                t = j['t']
                if t < self.mqtt_update_timestamp:
                    return None
                self.mqtt_update_timestamp = t
                if 'status' in j:
                    s = j['status']
                else:
                    s = None
                if 'value' in j:
                    v = j['value']
                else:
                    v = None
                if s is not None or v is not None:
                    self.update_set_state(status=s, value=v, from_mqtt=True)
                return j
        except:
            eva.core.log_traceback()

    def modbus_update_status(self, addr, values):
        v = values[0]
        if v is True: v = 1
        if v is False: v = 0
        self.update_set_state(status=v)

    def modbus_update_value(self, addr, values):
        v = values[0]
        if v is True: v = 1
        if v is False: v = 0
        self.update_set_state(value=v)

    def update_set_state(self,
                         status=None,
                         value=None,
                         from_mqtt=False,
                         force_virtual=False):
        if self.virtual and not force_virtual:
            logging.debug('%s skipping update - it\'s virtual' % \
                    self.oid)
            return
        self.update_expiration()
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
            need_notify = True
        if value is not None:
            if self.value != value:
                need_notify = True
                self.value = value
        if need_notify:
            self.notify(skip_subscribed_mqtt=from_mqtt)
        return True

    def serialize(self,
                  full=False,
                  config=False,
                  info=False,
                  props=False,
                  notify=False):
        d = {}
        if config or props:
            if self._snmp_traps_allowed:
                if self.snmp_trap:
                    d['snmp_trap'] = self.snmp_trap
                elif props:
                    d['snmp_trap'] = None
            if self._drivers_allowed:
                if self.update_driver_config:
                    d['update_driver_config'] = self.update_driver_config
                elif props:
                    d['update_driver_config'] = None
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
            if self._modbus_allowed:
                if self._modbus_status_allowed:
                    if not config or self.modbus_status:
                        d['modbus_status'] = self.modbus_status
                if not config or self.modbus_value:
                    d['modbus_value'] = self.modbus_value
        elif not info:
            d['status'] = self.status
            d['value'] = self.value
        if (full or config or props) and self._virtual_allowed:
            if not config or self.virtual:
                d['virtual'] = self.virtual
        d.update(super().serialize(
            full=full, config=config, info=info, props=props, notify=notify))
        return d

    def item_env(self, full=True):
        if self.value is not None: value = self.value
        else: value = ''
        e = {'EVA_ITEM_STATUS': str(self.status), 'EVA_ITEM_VALUE': str(value)}
        if full: e.update(super().item_env())
        return e

    def destroy(self):
        super().destroy()
        self.status = None
        self.value = None
        self.notify()


class ActiveItem(Item):

    def __init__(self, item_id, item_type):
        super().__init__(item_id, item_type)
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
        self.queue_lock = threading.Lock()
        self.action_processor = None
        self.action_processor_active = False
        self.current_action = None
        self.action_xc = None
        self.mqtt_control = None
        self.mqtt_control_notifier = None
        self.mqtt_control_qos = 1
        self._expire_on_any = True
        self._drivers_allowed = True
        self.action_driver_config = None

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
            self.queue.put(action)
            return True
        finally:
            self.queue_lock.release()

    def q_clean(self, lock=True):
        if lock:
            if not self.queue_lock.acquire(timeout=eva.core.config.timeout):
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
            if lock: self.queue_lock.release()

    def terminate(self, lock=True):
        if lock:
            if not self.queue_lock.acquire(timeout=eva.core.config.timeout):
                logging.critical('ActiveItem::terminate locking broken')
                eva.core.critical()
                return False
        try:
            if self.action_xc and not self.action_xc.is_finished():
                if not self.action_allow_termination:
                    logging.info('termination of %s denied by config' % \
                            self.oid)
                    return False
                self.action_xc.terminate()
                logging.info('requesting to terminate action %s' % \
                        self.current_action.uuid)
                return True
            return None
        finally:
            if lock: self.queue_lock.release()

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
        self.action_processor_active = True
        if self.action_processor and self.action_processor.is_alive():
            return
        self.action_processor = threading.Thread(target =\
                self._t_action_processor,
                name = '_t_action_processor_' + self.oid)
        self.action_processor.start()

    def stop_action_processor(self):
        if self.action_processor_active:
            self.action_processor_active = False
            a = ItemAction(None)
            self.q_put_task(a)

    def subscribe_mqtt_control(self):
        if not self.mqtt_control: return False
        notifier = eva.notify.get_notifier(self.mqtt_control_notifier)
        if not notifier or notifier.notifier_type[:4] != 'mqtt': return False
        try:
            notifier.control_item_append(self)
        except:
            eva.core.log_traceback()
            return False
        return True

    def unsubscribe_mqtt_control(self):
        if not self.mqtt_control: return False
        notifier = eva.notify.get_notifier(self.mqtt_control_notifier)
        if not notifier or notifier.notifier_type[:4] != 'mqtt': return False
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

    def action_run_args(self, action, n2n=True):
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

    def _t_action_processor(self):
        logging.debug('%s action processor started' % self.oid)
        while self.action_processor_active:
            try:
                self.current_action = None
                self.action_before_get_task()
                a = self.q_get_task()
                self.action_after_get_task(a)
                if not a or not a.item: continue
                if not self.queue_lock.acquire(timeout=eva.core.config.timeout):
                    logging.critical(
                        'ActiveItem::_t_action_processor locking broken')
                    eva.core.critical()
                    continue
                # dirty fix for action_queue == 0
                if not self.action_queue:
                    while self.q_is_task():
                        ar = self.q_get_task()
                        ar.set_refused()
                # dirty fix for action_queue == 2
                elif self.action_queue == 2:
                    while self.q_is_task():
                        a = self.q_get_task()
                        if self.q_is_task(): a.set_canceled()
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
                        self.action_before_run(a)
                        xc = self.get_action_xc(a)
                        self.action_xc = xc
                        self.queue_lock.release()
                        xc.run()
                        self.action_after_run(a, xc)
                        if xc.exitcode < 0:
                            a.set_terminated(
                                exitcode=xc.exitcode, out=xc.out, err=xc.err)
                            logging.error('action %s terminated' % a.uuid)
                        elif xc.exitcode == 0:
                            a.set_completed(
                                exitcode=xc.exitcode, out=xc.out, err=xc.err)
                            logging.debug('action %s completed' % a.uuid)
                        else:
                            a.set_failed(
                                exitcode=xc.exitcode, out=xc.out, err=xc.err)
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
                    'ActiveItem::_t_action_processor locking broken')
                eva.core.critical()
                continue
            self.current_action = None
            self.action_xc = None
            self.queue_lock.release()
        logging.debug('%s action processor stopped' % self.oid)

    def get_action_xc(self, a):
        import eva.runner
        if self._drivers_allowed and not self.virtual and \
                self.action_exec and self.action_exec[0] == '|':
            return eva.runner.DriverCommand(
                item=self,
                state=self.action_run_args(a, n2n=False),
                timeout=self.action_timeout,
                tki=self.term_kill_interval,
                _uuid=a.uuid)
        else:
            return eva.runner.ExternalProcess(
                fname=self.action_exec,
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
        if 'action_driver_config' in data:
            self.action_driver_config = data['action_driver_config']
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
                if val and val[0] == '|':
                    if self._drivers_allowed:
                        import eva.uc.driverapi
                        d = eva.uc.driverapi.get_driver(val[1:])
                        if not d:
                            logging.error(
                                'Can not set ' + \
                                    '%s.action_exec = %s, no such driver'
                                    % (self.oid, val))
                            return False
                    else:
                        return False
                self.action_exec = val
                self.log_set(prop, val)
                self.set_modified(save)
            return True
        elif prop == 'action_driver_config' and self._drivers_allowed:
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
            if not 0 <= v <= 2: return False
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
                    self.action_timeout = eva.core.config.timeout
                    self._action_timeout = None
                    self.log_set(prop, None)
                    self.set_modified(save)
            else:
                try:
                    action_timeout = float(val)
                except:
                    return False
                if action_timeout <= 0: return False
                if self._action_timeout != action_timeout:
                    self._action_timeout = action_timeout
                    self.action_timeout = action_timeout
                    self.log_set(prop, action_timeout)
                    self.set_modified(save)
            return True
        elif prop == 'term_kill_interval':
            if val is None:
                if self._term_kill_interval is not None:
                    self.term_kill_interval = eva.core.config.timeout
                    self._term_kill_interval = None
                    self.log_set(prop, None)
                    self.set_modified(save)
            else:
                try:
                    term_kill_interval = float(val)
                except:
                    return False
                if term_kill_interval <= 0: return False
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
            if self._drivers_allowed:
                if self.action_driver_config:
                    d['action_driver_config'] = self.action_driver_config
                elif props:
                    d['action_driver_config'] = None
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
        d.update(super().serialize(
            full=full, config=config, info=info, props=props, notify=notify))
        return d

    def disable_actions(self):
        if not self.action_enabled: return True
        self.update_config({'action_enabled': False})
        logging.info('%s actions disabled' % self.oid)
        self.notify()
        if eva.core.config.db_update == 1: self.save()
        return True

    def enable_actions(self):
        if self.action_enabled: return True
        self.update_config({'action_enabled': True})
        logging.info('%s actions enabled' % self.oid)
        self.notify()
        if eva.core.config.db_update == 1: self.save()
        return True

    def destroy(self):
        self.action_enabled = None
        self.notify()
        super().destroy()


ia_status_names = [
    'created', 'pending', 'queued', 'refused', 'dead', 'canceled', 'ignored',
    'running', 'failed', 'terminated', 'completed'
]

ia_default_priority = 100


class ItemAction(GenericAction):

    def __init__(self, item, priority=None, action_uuid=None):
        super().__init__()
        self.item_action_lock = threading.Lock()
        if not self.item_action_lock.acquire(timeout=eva.core.config.timeout):
            logging.critical('ItemAction::__init___ locking broken')
            eva.core.critical()
            return False
        if priority: self.priority = priority
        else: self.priority = ia_default_priority
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
            if eva.notify.is_action_subscribed():
                eva.notify.notify('action', (self, self.serialize()))
        self.item_action_lock.release()

    def __cmp__(self, other):
        return cmp(self.priority, other.priority) if \
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

    def set_status(self, status, exitcode=None, out=None, err=None, lock=True):
        if lock:
            if not self.item_action_lock.acquire(
                    timeout=eva.core.config.timeout):
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
            if eva.notify.is_action_subscribed():
                t = threading.Thread(
                    target=eva.notify.notify,
                    args=('action', (self, self.serialize())))
                t.setDaemon(True)
                t.start()
            return True
        finally:
            if lock: self.item_action_lock.release()

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
                if self.is_finished(): return None
                if self.is_status_running():
                    result = self.item.terminate(lock=False)
                else:
                    result = self.set_status(
                        eva.core.item.ia_status_canceled, lock=False)
                return result
            finally:
                self.item.queue_lock.release()
        finally:
            self.item_action_lock.release()

    def serialize(self):
        d = {}
        d['uuid'] = self.uuid
        d['status'] = ia_status_names[self.get_status()]
        d['priority'] = self.priority
        d['exitcode'] = self.exitcode
        d['out'] = self.out
        d['err'] = self.err
        d['item_id'] = self.item.item_id
        d['item_group'] = self.item.group
        d['item_type'] = self.item.item_type
        d['item_oid'] = self.item.oid
        d['time'] = {}
        for i, v in self.time.items():
            d['time'][ia_status_names[i]] = v
        return d


class MultiUpdate(UpdatableItem):

    def __init__(self, mu_id):
        super().__init__(mu_id, 'mu')
        self.items_to_update = []
        self._update_run_args = ()
        self.update_allow_check = True
        self.get_item_func = None
        self._drivers_allowed = False
        self._snmp_traps_allowed = False
        self._modbus_allowed = False
        self._mqtt_updates_allowed = False

    def updates_allowed(self):
        if not self.update_allow_check: return True
        for i in self.items_to_update:
            if not i.updates_allowed(): return False
        return True

    def register_driver_updates(self):
        return

    def unregister_driver_updates(self):
        return

    def update_after_run(self, update_out):
        if self._destroyed: return
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
        d = super().serialize(
            full=full, config=config, info=info, props=props, notify=notify)
        if 'mqtt_update' in d:
            del d['mqtt_update']
        if 'snmp_trap' in d:
            del d['snmp_trap']
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
                         force_virtual=False):
        if self._destroyed: return False
        if self.virtual and not force_virtual:
            logging.debug('%s skipping update - it\'s virtual' % \
                    self.oid)
            return False
        try:
            if status is not None: _status = int(status)
            else: _status = None
        except:
            logging.error('update %s returned bad data' % self.oid)
            eva.core.log_traceback()
            return False
        if not self.status and _status is None:
            logging.debug('%s skipping update - it\'s not active' % \
                    self.oid)
            return False
        self.update_expiration()
        need_notify = False
        if _status is not None:
            if self.status != _status: need_notify = True
            self.status = _status
        if value is not None and self.status:
            if self.value != value: need_notify = True
            self.value = value
            if self.status == -1 and _status is None and value != '':
                self.status = 1
                need_notify = True
        if need_notify:
            logging.debug(
                '%s status = %u, value = "%s"' % \
                        (self.oid, self.status, self.value))
            self.notify(skip_subscribed_mqtt=from_mqtt)
        return True

    def is_expired(self):
        if not self.status: return False
        return super().is_expired()

    # def serialize(self,
    # full=False,
    # config=False,
    # info=False,
    # props=False,
    # notify=False):
    # d = super().serialize(
    # full=full, config=config, info=info, props=props, notify=notify)
    # if notify and 'value' in d and \
    # self.status == -1 and \
    # self.value != '' and \
    # self.value is not None:
    # del d['value']
    # return d


def item_match(item, item_ids, groups=None):
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
                if rt != item.item_type: continue
            else:
                g = grp
            p = g.find('#')
            if p > -1 and g[:p] == item.group[:p]: return True
            if g.find('+') > -1:
                g1 = g.split('/')
                g2 = item.group.split('/')
                if len(g1) == len(g2):
                    match = True
                    for i in range(0, len(g1)):
                        if g1[i] != '+' and g1[i] != g2[i]:
                            match = False
                            break
                    if match: return True
    return False


def get_state_history(a=None,
                      oid=None,
                      t_start=None,
                      t_end=None,
                      limit=None,
                      prop=None,
                      time_format=None,
                      fill=None,
                      fmt=None):
    import dateutil
    import pytz
    import pandas as pd
    import math
    from datetime import datetime

    if oid is None: raise ResourceNotFound
    n = eva.notify.get_db_notifier(a)
    if not t_start and fill:
        raise InvalidParameter('start time is required when fill is used')
    if t_start and fill: tf = 'iso'
    else: tf = time_format
    if not n: raise ResourceNotFound('notifier')
    try:
        result = n.get_state(
            oid=oid,
            t_start=t_start,
            t_end=t_end,
            limit=limit,
            prop=prop,
            time_format=tf)
    except:
        raise FunctionFailed
    if t_start and fill and result:
        tz = pytz.timezone(time.tzname[0])
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
        if t_e > time.time(): t_e = time.time()
        try:
            df = pd.DataFrame(result)
            df = df.set_index('t')
            df.index = pd.to_datetime(df.index, utc=True)
            if fill.find(':') != -1:
                _fill, _pc = fill.split(':')
                _pc = pow(10, int(_pc))
            else:
                _fill = fill
                _pc = None
            sp1 = df.resample(_fill).mean()
            sp2 = df.resample(_fill).pad()
            sp = sp1.fillna(sp2).to_dict(orient='split')
            result = []
            for i in range(0, len(sp['index'])):
                t = sp['index'][i].timestamp()
                if time_format == 'iso':
                    t = datetime.fromtimestamp(t, tz).isoformat()
                r = {'t': t}
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
                if 'value' in r and isinstance(r['value'], float):
                    if math.isnan(r['value']):
                        r['value'] = None
                    elif _pc:
                        r['value'] = math.floor(r['value'] * _pc) / _pc
                result.append(r)
        except:
            eva.core.log_traceback()
            raise FunctionFailed
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
        return InvalidParameter('Invalid result format {}'.format(fmt))
    return result
