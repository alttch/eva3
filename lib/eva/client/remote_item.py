__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.3"

import eva.core
import eva.item
import eva.tools


class RemoteUpdatableItem(eva.item.UpdatableItem):

    def __init__(self, item_type, controller, state):
        item_id = state['id']
        super().__init__(item_id, item_type)
        self.controller = controller
        cfg = {}
        if controller.mqtt_update:
            cfg['mqtt_update'] = controller.mqtt_update
        cfg.update(state)
        self.update_config(cfg)
        self.status = state['status']
        self.value = state.get('value')
        self.mqtt_update_topics = ['']
        self.allow_mqtt_updates_from_controllers = True

    def notify(self, retain=None, skip_subscribed_mqtt=False,
               for_destroy=False):
        super().notify(skip_subscribed_mqtt=True, for_destroy=for_destroy)

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
        self.expires = state.get('expires')
        self.set_time = state.get('set_time')

    def set_state_from_serialized(self, data, from_mqtt=False):
        need_notify = False
        try:
            if 'expires' in data:
                try:
                    expires = float(data['expires'])
                    if self.expires != expires:
                        self.expires = expires
                        need_notify = True
                    need_notify = True
                except:
                    pass
            if 'set_time' in data:
                try:
                    set_time = float(data['set_time'])
                    if self.set_time != set_time:
                        self.set_time = set_time
                        need_notify = True
                except:
                    pass
            super().set_state_from_serialized(
                data, from_mqtt=from_mqtt, force_notify=need_notify)
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
        self.nstatus = state['nstatus']
        self.nvalue = state.get('nvalue', '')
        self.action_enabled = eva.tools.val_to_boolean(
            state.get('action_enabled', False))
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
            if nvalue == '': nv = ''
            else: nv = nvalue
            if self.nvalue != nv:
                self.nvalue = nv
                need_notify = True
        if need_notify:
            self.notify()
        return True

    def mqtt_set_state(self, topic, data):
        j = super().mqtt_set_state(topic, data)
        if j:
            try:
                if 'nstatus' in j:
                    s = j['nstatus']
                else:
                    s = None
                if 'nvalue' in j:
                    v = j['nvalue']
                else:
                    v = None
                if s is not None or v is not None:
                    self.update_nstate(nstatus=s, nvalue=v)
                if 'action_enabled' in j:
                    self.action_enabled = eva.tools.val_to_boolean(
                        j['action_enabled'])
                    self.notify()
            except:
                eva.core.log_traceback()

    def serialize(self,
                  full=False,
                  config=False,
                  info=False,
                  props=False,
                  notify=False):
        d = {
            'nstatus': self.nstatus,
            'nvalue': self.nvalue,
            'action_enabled': self.action_enabled
        }
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
        self.allow_mqtt_updates_from_controllers = True

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


class RemoteCycle(RemoteUpdatableItem):

    def __init__(self, remote_lm, state):
        super().__init__('lcycle', remote_lm, state)
        self.allow_mqtt_updates_from_controllers = True

    def update_config(self, cfg):
        super().update_config(cfg)
        if 'interval' in cfg:
            try:
                self.interval = float(cfg['interval'])
            except:
                eva.core.log_traceback()
        if 'iterations' in cfg:
            try:
                self.iterations = int(cfg['iterations'])
            except:
                eva.core.log_traceback()
        if 'avg' in cfg:
            try:
                self.avg = int(cfg['avg'])
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
        d['controller_id'] = self.controller.full_id
        d['interval'] = self.interval
        d['iterations'] = self.iterations
        d['avg'] = self.avg
        return d

    def notify(self, retain=None, skip_subscribed_mqtt=False):
        super().notify(skip_subscribed_mqtt=True)

    def mqtt_set_state(self, topic, data):
        j = super().mqtt_set_state(topic, data)
        if j:
            need_notify = False
            if 'interval' in j:
                try:
                    d = float(j['interval'])
                    if self.interval != d:
                        self.interval = d
                        need_notify = True
                except:
                    eva.core.log_traceback()
            if 'iterations' in j:
                try:
                    d = int(j['iterations'])
                    if self.iterations != d:
                        self.iterations = d
                        need_notify = True
                except:
                    eva.core.log_traceback()
            if 'avg' in j:
                try:
                    d = float(j['avg'])
                    if self.avg != d:
                        self.avg = d
                        need_notify = True
                except:
                    eva.core.log_traceback()
            if need_notify:
                self.notify()
