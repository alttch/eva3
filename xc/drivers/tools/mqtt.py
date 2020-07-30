__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2020 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.3.1"

import eva.notify


class MQTT(object):

    def __init__(self, notifier_id):
        self.notifier = eva.notify.get_notifier(notifier_id)
        self.ready = self.notifier is not None

    def register(self, topic, func, qos=1):
        if not self.notifier: return False
        self.notifier.handler_append(topic, func, qos=qos)
        return True

    def unregister(self, topic, func):
        if not self.notifier: return False
        self.notifier.handler_remove(topic, func)
        return True

    def send(self, topic, data, retain=None, qos=1):
        if not self.notifier: return False
        self.notifier.send_message(topic, data, retain=retain, qos=qos)
