__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "AKCP MD00 motion sensor"

__id__ = 'akcp_md'
__equipment__ = ['AKCP MD00']
__api__ = 1
__required__ = ['port_get', 'value']
__mods_required__ = []
__lpi_default__ = 'ssp'
__features__ = ['events']
__config_help__ = [{
    'name': 'host',
    'help': 'AKCP controller IP',
    'type': 'str',
    'required': True
}, {
    'name':
    'sp',
    'help':
    'controller port where sensor is located (1..X), may be list',
    'type':
    'int|list:int',
    'required':
    True
}]
__get_help__ = []
__set_help__ = []

__help__ = """
PHI for AKCP MD00 motion sensor, uses SNMP traps to set sensor status. EVA
sensor should have "port" set to sp value in driver config or use ssp LPI.

If only one port is specified, LPI "ssp" is automatically assigned to the
default driver, otherwise LPI "sensor".

PHI doesn't provide any control/monitoring functions.
"""

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import get_timeout
from eva.uc.driverapi import handle_phi_event

from eva.tools import parse_host_port

import eva.uc.drivers.tools.snmp as snmp
import eva.traphandler


class PHI(GenericPHI):

    def __init__(self, phi_cfg=None, info_only=False):
        super().__init__(phi_cfg=phi_cfg, info_only=info_only)
        self.phi_mod_id = __id__
        self.__author = __author__
        self.__license = __license__
        self.__description = __description__
        self.__version = __version__
        self.__api_version = __api__
        self.__equipment = __equipment__
        self.__features = __features__
        self.__required = __required__
        self.__mods_required = __mods_required__
        self.__lpi_default = __lpi_default__
        self.__config_help = __config_help__
        self.__get_help = __get_help__
        self.__set_help = __set_help__
        self.__help = __help__
        if info_only: return
        self.snmp_host, self.snmp_port = parse_host_port(
            self.phi_cfg.get('host'), 161)
        self.sensor_port = self.phi_cfg.get('sp')
        if self.sensor_port and not isinstance(self.sensor_port, list):
            self.sensor_port = [self.sensor_port]
        try:
            for i in range(len(self.sensor_port)):
                self.sensor_port[i] = int(self.sensor_port[i]) - 1
                if self.sensor_port[i] < 0:
                    raise Exception('Sensor port can not be less than 1')
                self.sensor_port[i] = str(self.sensor_port[i])
        except:
            self.sensor_port = None
        if not self.snmp_host:
            self.log_error('no host specified')
            self.ready = False
        if not self.sensor_port:
            self.log_error('no sensor port specified')
            self.ready = False
        else:
            print(self.sensor_port)
            if len(self.sensor_port) > 1:
                self.__lpi_default = 'sensor'

    def start(self):
        eva.traphandler.subscribe(self)

    def stop(self):
        eva.traphandler.unsubscribe(self)

    def process_snmp_trap(self, host, data):
        if host != self.snmp_host: return
        if data.get('1.3.6.1.4.1.3854.1.7.4.0') not in self.sensor_port:
            return
        try:
            port = str(int(data.get('1.3.6.1.4.1.3854.1.7.4.0')) + 1)
        except:
            return
        d = data.get('1.3.6.1.4.1.3854.1.7.1.0')
        if d == '7':
            handle_phi_event(self, self.sensor_port, {port: False})
        elif d == '2':
            handle_phi_event(self, self.sensor_port, {port: 0})
        elif d == '4':
            handle_phi_event(self, self.sensor_port, {port: 1})
        return

    def test(self, cmd=None):
        if cmd == 'self':
            return 'OK'
        return {'-': 'self test only'}
