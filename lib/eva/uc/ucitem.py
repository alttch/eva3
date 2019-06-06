__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.3"

import eva.core
import eva.runner
import eva.item
import eva.uc.modbus
import eva.uc.controller
import eva.uc.driverapi
import eva.traphandler

from eva.tools import safe_int
from eva.tools import dict_from_str
from eva.tools import format_modbus_value


class UCItem(eva.item.Item):

    def __init__(self, item_id, item_type):
        self.update_driver_config = None
        self.modbus_value = None
        self.modbus_value_reg = None
        self.modbus_value_addr = None
        self.modbus_value_multiplier = 1
        self.modbus_value_signed = False
        self.snmp_trap = None
        super().__init__(item_id, item_type)

    def update_config(self, data):
        if 'update_driver_config' in data:
            self.update_driver_config = data['update_driver_config']
        if 'snmp_trap' in data:
            self.snmp_trap = data['snmp_trap']
        if 'modbus_value' in data:
            self.modbus_value = data['modbus_value']
            self.modbus_value_reg, self.modbus_value_addr, \
                    self.modbus_value_multiplier, \
                    self.modbus_value_signed = format_modbus_value(
                self.modbus_value)
        super().update_config(data)

    def update(self, **kwargs):
        if self.updates_allowed() and not self.is_destroyed():
            self._perform_update(**kwargs)

    def register_modbus_value_updates(self):
        if self.modbus_value:
            try:
                eva.uc.modbus.register_handler(
                    self.modbus_value_addr,
                    self.modbus_update_value,
                    register=self.modbus_value_reg)
            except:
                eva.core.log_traceback()

    def unregister_modbus_value_updates(self):
        if self.modbus_value:
            try:
                eva.uc.modbus.unregister_handler(
                    self.modbus_value_addr,
                    self.modbus_update_value,
                    register=self.modbus_value_reg)
            except:
                eva.core.log_traceback()

    def do_notify(self, skip_subscribed_mqtt=False, for_destroy=False):
        super().notify(
            skip_subscribed_mqtt=skip_subscribed_mqtt, for_destroy=for_destroy)
        if eva.core.config.db_update == 1:
            eva.uc.controller.save_item_state(self)

    def notify(self, skip_subscribed_mqtt=False, for_destroy=False):
        self.do_notify(
            skip_subscribed_mqtt=skip_subscribed_mqtt, for_destroy=for_destroy)
        eva.uc.controller.handle_event(self)

    def set_prop(self, prop, val=None, save=False):
        if prop == 'update_exec':
            if self.update_exec != val:
                if val and val[0] == '|':
                    d = eva.uc.driverapi.get_driver(val[1:])
                    if not d:
                        logging.error(
                            'Can not set ' + \
                                '%s.update_exec = %s, no such driver'
                                % (self.oid, val))
                        return False
                if not val:
                    self.unregister_driver_updates()
                self.update_exec = val
                self.log_set(prop, val)
                self.set_modified(save)
                self.register_driver_updates()
            return True
        elif prop == 'update_driver_config':
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
        elif prop == 'modbus_value':
            if self.modbus_value == val: return True
            if val is None:
                self.unregister_modbus_value_updates()
                self.modbus_value = None
            else:
                reg, addr, multiplier, signed = format_modbus_value(val)
                if reg is None or addr is None or multiplier is None:
                    return False
                self.unregister_modbus_value_updates()
                self.modbus_value = val
                self.modbus_value_reg = reg
                self.modbus_value_addr = addr
                self.modbus_value_multiplier = multiplier
                self.modbus_value_signed = signed
                self.modbus_update_value(addr, eva.uc.modbus.get_data(
                    addr, reg))
                self.register_modbus_value_updates()
            self.log_set('modbus_value', val)
            self.set_modified(save)
            return True
        elif prop == 'snmp_trap':
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
        elif prop == 'snmp_trap.ident_vars':
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
        elif prop == 'snmp_trap.set_down':
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
        elif prop == 'snmp_trap.set_status':
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
        elif prop == 'snmp_trap.set_value':
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
        elif prop[:16] == 'snmp_trap.set_if':
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
        else:
            return super().set_prop(prop, val, save)

    def start_processors(self):
        self.register_driver_updates()
        self.register_modbus_value_updates()
        self.subscribe_snmp_traps()
        super().start_processors()

    def stop_processors(self):
        self.unsubscribe_snmp_traps()
        self.unregister_modbus_value_updates()
        self.unregister_driver_updates()
        super().stop_processors()

    def modbus_update_value(self, addr, values):
        v = values[0]
        if v is True: v = 1
        elif v is False: v = 0
        if self.modbus_value_signed and v > 32767:
            v = v - 65536
        self.update_set_state(value=v * self.modbus_value_multiplier)

    def register_driver_updates(self):
        if self.update_exec and self.update_exec[0] == '|':
            eva.uc.driverapi.register_item_update(self)

    def unregister_driver_updates(self):
        if self.update_exec and self.update_exec[0] == '|':
            eva.uc.driverapi.unregister_item_update(self)

    def subscribe_snmp_traps(self):
        if self.snmp_trap:
            eva.traphandler.subscribe(self)

    def unsubscribe_snmp_traps(self):
        eva.traphandler.unsubscribe(self)

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

    def get_update_xc(self, **kwargs):
        if self.update_exec and self.update_exec[0] == '|':
            return eva.runner.DriverCommand(
                item=self,
                update=True,
                timeout=self.update_timeout,
                state_in=kwargs.get('driver_state_in'))
        else:
            return super().get_update_xc(**kwargs)

    def serialize(self,
                  full=False,
                  config=False,
                  info=False,
                  props=False,
                  notify=False):
        d = super().serialize(
            full=full, config=config, info=info, props=props, notify=notify)
        if config or props:
            if self.update_driver_config:
                d['update_driver_config'] = self.update_driver_config
            elif props:
                d['update_driver_config'] = None
            if self.snmp_trap:
                d['snmp_trap'] = self.snmp_trap
            elif props:
                d['snmp_trap'] = None
            if not config or self.modbus_value:
                d['modbus_value'] = self.modbus_value
        return d
