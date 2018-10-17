__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "3.1.1"

import eva.core
import eva.item
import eva.uc.controller
import logging
import time

from eva.uc.ucitem import UCItem


class Sensor(eva.item.VariableItem, eva.item.PhysicalItem, UCItem):

    def __init__(self, sensor_id):
        super().__init__(sensor_id, 'sensor')

    def set_expired(self):
        if super().set_expired():
            logging.error('%s status is -1 (failed)' % self.oid)
