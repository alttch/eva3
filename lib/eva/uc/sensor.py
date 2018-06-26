__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "3.1.0"

import eva.core
import eva.item
import eva.uc.controller
import logging
import time


class Sensor(eva.item.VariableItem):

    def __init__(self, sensor_id):
        super().__init__(sensor_id, 'sensor')

    def notify(self, skip_subscribed_mqtt=False):
        super().notify(skip_subscribed_mqtt=skip_subscribed_mqtt)
        if eva.core.db_update == 1: eva.uc.controller.save_item_state(self)

    def set_expired(self):
        if super().set_expired():
            logging.error('%s status is -1 (failed)', self.full_id)
