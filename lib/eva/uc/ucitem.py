__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.1.2"

import eva.core
import eva.item
import eva.uc.controller
import threading


class UCItem(eva.item.Item):

    def do_notify(self, skip_subscribed_mqtt=False):
        super().notify(skip_subscribed_mqtt=skip_subscribed_mqtt)
        if eva.core.db_update == 1: eva.uc.controller.save_item_state(self)

    def notify(self, skip_subscribed_mqtt=False):
        self.do_notify(skip_subscribed_mqtt=skip_subscribed_mqtt)
        eva.uc.controller.handle_event(self)
