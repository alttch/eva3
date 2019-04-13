__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.1"

import eva.core
import eva.item
import eva.uc.controller


class UCItem(eva.item.Item):

    def do_notify(self, skip_subscribed_mqtt=False, for_destroy=False):
        super().notify(
            skip_subscribed_mqtt=skip_subscribed_mqtt,
            for_destroy=for_destroy)
        if eva.core.config.db_update == 1:
            eva.uc.controller.save_item_state(self)

    def notify(self, skip_subscribed_mqtt=False, for_destroy=False):
        self.do_notify(
            skip_subscribed_mqtt=skip_subscribed_mqtt,
            for_destroy=for_destroy)
        eva.uc.controller.handle_event(self)
