__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.1"

import eva.notify


class MQTT(object):
    """
    MQTT helper class
    """

    def __init__(self, notifier_id):
        """
        Args:
            notifier_id: MQTT notifier to use (default: eva_1)
        """
        self.notifier = eva.notify.get_notifier(notifier_id)
        self.ready = self.notifier is not None

    def register(self, topic, func, qos=1):
        """
        Register MQTT topic handler
        """
        if not self.notifier:
            return False
        self.notifier.handler_append(topic, func, qos=qos)
        return True

    def unregister(self, topic, func):
        """
        Unregister MQTT topic handler
        """
        if not self.notifier:
            return False
        self.notifier.handler_remove(topic, func)
        return True

    def send(self, topic, data, retain=None, qos=1):
        """
        Send MQTT message
        """
        if not self.notifier:
            return False
        self.notifier.send_message(topic, data, retain=retain, qos=qos)
