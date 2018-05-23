__author__ = "Altertech Group, http://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2017 Altertech Group"
__license__ = "See http://www.eva-ics.com/"
__version__ = "3.0.1"

import eva.core
import eva.item


class RemoteDMRule(object):

    def __init__(self, controller, rule_id):
        self.item_id = rule_id
        self.controller = controller
        self.group = 'dm_rules'
        self.full_id = self.group + '/' + rule_id


class RemoteUpdatableItem(eva.item.UpdatableItem):

    def __init__(self, item_type, controller, state):
        item_id = state['id']
        super().__init__(item_id, item_type)
        self.controller = controller
        self._virtual_allowed = False
        self._snmp_traps_allowed = False
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


class RemoteLVar(RemoteUpdatableItem):

    def __init__(self, remote_lm, state):
        super().__init__('lvar', remote_lm, state)
        self.mqtt_update_topics.append('expires')
        self.mqtt_update_topics.append('set_time')

    def mqtt_set_state(self, topic, data):
        super().mqtt_set_state(topic, data)
        try:
            if topic.endswith('/expires'):
                self.expires = float(data)
                self.notify()
            if topic.endswith('/set_time'):
                self.set_time = float(data)
                self.notify()
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


class RemoteSensor(RemoteUpdatableItem):

    def __init__(self, remote_uc, state):
        super().__init__('sensor', remote_uc, state)


class RemoteUnit(RemoteUpdatableItem):

    def __init__(self, remote_uc, state):
        super().__init__('unit', remote_uc, state)
        self.mqtt_update_topics.append('action_enabled')
        self.mqtt_update_topics.append('nstatus')
        self.mqtt_update_topics.append('nvalue')
        self.nstatus = self.status
        self.nvalue = self.value
        self.action_enabled = True

    def mqtt_set_state(self, topic, data):
        super().mqtt_set_state(topic, data)
        try:
            if topic.endswith('/nstatus'):
                self.nstatus = int(data)
                self.notify()
            elif topic.endswith('/nvalue'):
                self.nvalue = data
                self.notify()
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
        d.update(super().serialize(
            full=full, config=config, info=info, props=props, notify=notify))
        return d


class RemoteMacro(eva.item.Item):

    def __init__(self, macro_id, controller):
        super().__init__(macro_id, 'lmacro')
        self.controller = controller
