__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"

import eva.core
import eva.item
import eva.uc.controller
import logging
import time

from eva.uc.ucitem import UCItem


class Sensor(UCItem, eva.item.VariableItem, eva.item.PhysicalItem):

    fields = [
        'description',
        'expires',
        'location',
        'maintenance_duration',
        'modbus_value',
        'mqtt_update',
        'notify_events',
        'snmp_trap',
        'update_delay',
        'update_driver_config',
        'update_exec',
        'update_interval',
        'update_timeout',
        'value_condition',
        'value_in_range_max',
        'value_in_range_max_eq',
        'value_in_range_min',
        'value_in_range_min_eq',
    ]

    def __init__(self, sensor_id=None, create=False, **kwargs):
        super().__init__(sensor_id, 'sensor', **kwargs)
        self._modbus_status_allowed = False
        if create:
            self.set_defaults(self.fields)

    def set_expired(self):
        if super().set_expired():
            logging.error('%s status is -1 (failed)' % self.oid)

    def updates_allowed(self):
        return self.status != 0 and super().updates_allowed()

    def update_set_state(self,
                         status=None,
                         value=None,
                         from_mqtt=False,
                         force_notify=False,
                         timestamp=None):
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
        return super().update_set_state(status=status,
                                        value=value,
                                        from_mqtt=from_mqtt,
                                        force_notify=force_notify,
                                        update_expiration=ue,
                                        timestamp=timestamp)
