__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.1.1"

import eva.core
import eva.item


class RemoteDMRule(object):

    def __init__(self, controller, rule_id):
        self.item_id = rule_id
        self.controller = controller
        self.group = 'dm_rules'
        self.full_id = self.group + '/' + rule_id
        self._destroyed = False

    def start_processors(self):
        return True

    def stop_processors(self):
        return True

    def destroy(self):
        self._destroyed = True

    def is_destroyed(self):
        return self._destroyed


class RemoteUpdatableItem(eva.item.UpdatableItem):

    def __init__(self, item_type, controller, state):
        item_id = state['id']
        super().__init__(item_id, item_type)
        self.controller = controller
        self._virtual_allowed = False
        self._snmp_traps_allowed = False
        self._drivers_allowed = False
        cfg = {}
        if controller.mqtt_update:
            cfg['mqtt_update'] = controller.mqtt_update
        cfg.update(state)
        self.update_config(cfg)
        self.status = state['status']
        self.value = state['value']

    def notify(self, retain=None, skip_subscribed_mqtt=False):
        super().notify(skip_subscribed_mqtt=True)

    def start_expiration_checker(self):
        pass

    def start_update_processor(self):
        pass

    def update_expiration(self):
        pass

    def destroy(self):
        self._destroyed = True
        self.stop_processors()

    def serialize(self,
                  full=False,
                  config=False,
                  info=False,
                  props=False,
                  notify=False):
        d = super().serialize(
            full=full, config=config, info=info, props=props, notify=notify)
        d['controller_id'] = self.controller.full_id
        try:
            del d['config_changed']
        except:
            pass
        return d


class RemoteLVar(RemoteUpdatableItem):

    def __init__(self, remote_lm, state):
        super().__init__('lvar', remote_lm, state)
        self.mqtt_update_topics.append('expires')
        self.mqtt_update_topics.append('set_time')

    def mqtt_set_state(self, topic, data):
        super().mqtt_set_state(topic, data)
        try:
            if topic.endswith('/expires'):
                try:
                    self.expires = float(data)
                    self.notify()
                except:
                    pass
            if topic.endswith('/set_time'):
                try:
                    self.set_time = float(data)
                    self.notify()
                except:
                    pass
        except:
            eva.core.log_traceback()

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


class RemoteSensor(RemoteUpdatableItem, eva.item.PhysicalItem):

    def __init__(self, remote_uc, state):
        super().__init__('sensor', remote_uc, state)


class RemoteUnit(RemoteUpdatableItem, eva.item.PhysicalItem):

    def __init__(self, remote_uc, state):
        super().__init__('unit', remote_uc, state)
        self.mqtt_update_topics.append('action_enabled')
        self.mqtt_update_topics.append('nstatus')
        self.mqtt_update_topics.append('nvalue')
        self.nstatus = self.status
        self.nvalue = self.value
        self.action_enabled = True
        self.status_labels = state.get('status_labels')

    def update_nstate(self, nstatus=None, nvalue=None):
        need_notify = False
        if nstatus is not None:
            try:
                _s = int(nstatus)
                if self.nstatus != _s:
                    self.nstatus = _s
                    need_notify = True
            except:
                logging.info('%s nstatus "%s" is not number, can not set' % \
                        (self.full_id, nstatus))
                eva.core.log_traceback()
                return False
        if nvalue is not None:
            if nvalue == '': nv = 'null'
            else: nv = nvalue
            if self.nvalue != nv:
                self.nvalue = nv
                need_notify = True
        if need_notify:
            self.notify()
        return True

    def mqtt_set_state(self, topic, data):
        super().mqtt_set_state(topic, data)
        try:
            if topic.endswith('/nstatus'):
                self.update_nstate(nstatus=data)
            elif topic.endswith('/nvalue'):
                self.update_nstate(nvalue=data)
            elif topic.endswith('/action_enabled'):
                self.action_enabled = eva.tools.val_to_boolean(data)
                self.notify()
        except:
            eva.core.log_traceback()

    def serialize(self,
                  full=False,
                  config=False,
                  info=False,
                  props=False,
                  notify=False):
        d = {'nstatus': self.nstatus, 'nvalue': self.nvalue}
        if full and self.status_labels:
            d['status_labels'] = self.status_labels
        d.update(super().serialize(
            full=full, config=config, info=info, props=props, notify=notify))
        return d


class RemoteMacro(eva.item.Item):

    def __init__(self, macro_id, controller):
        super().__init__(macro_id, 'lmacro')
        self.controller = controller
        self.action_enabled = False

    def update_config(self, cfg):
        super().update_config(cfg)
        if 'action_enabled' in cfg:
            self.action_enabled = cfg['action_enabled']

    def serialize(self,
                  full=False,
                  config=False,
                  info=False,
                  props=False,
                  notify=False):
        d = super().serialize(
            full=full, config=config, info=info, props=props, notify=notify)
        d['controller_id'] = self.controller.full_id
        d['action_enabled'] = self.action_enabled
        return d
