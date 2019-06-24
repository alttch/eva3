__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.3"

import eva.core
import eva.item
import eva.uc.controller
import logging
import time

from eva.uc.ucitem import UCItem


class Sensor(UCItem, eva.item.VariableItem, eva.item.PhysicalItem):

    def __init__(self, sensor_id):
        super().__init__(sensor_id, 'sensor')
        self._modbus_status_allowed = False

    def set_expired(self):
        if super().set_expired():
            logging.error('%s status is -1 (failed)' % self.oid)

    def update_set_state(self,
                         status=None,
                         value=None,
                         from_mqtt=False,
                         force_notify=False):
        if self.is_maintenance_mode():
            logging.info('Ignoring {} update in maintenance mode'.format(
                self.oid))
            return False
        if not self.is_value_valid(value):
            logging.error('Sensor {} got invalid value {}'.format(
                self.oid, value))
            status = -1
            value = None
            ue = False
        else:
            ue = True
        return super().update_set_state(
            status=status,
            value=value,
            from_mqtt=from_mqtt,
            force_notify=force_notify,
            update_expiration=ue)
