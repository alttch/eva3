__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "AKCP THSXX temperature and humidity sensor"

__id__ = 'akcp_ths'
__equipment__ = ['AKCP THS00', 'AKCP THS01']
__api__ = 1
__required__ = ['port_get', 'value']
__mods_required__ = []
__features__ = ['port_get', 'events']
__config_help__ = [{
    'name': 'host',
    'help': 'AKCP controller ip[:port]',
    'type': 'str',
    'required': True
}, {
    'name': 'sp',
    'help': 'controller port where sensor is located (1..X)',
    'type': 'int',
    'required': True
}, {
    'name': 'community',
    'help': 'snmp community (default: public)',
    'type': 'str',
    'required': False
}, {
    'name': 'retries',
    'help': 'snmp retry attemps (default: 0)',
    'type': 'int',
    'required': False
}]
__get_help__ = []
__set_help__ = []

__help__ = """
PHI for AKCP THS00/THS01 temperature and humidity sensors, uses SNMP API to
monitor the equipment. SNMP on controller should be enabled and configured to
allow packets from UC.

Sensor port should be specified 't' for temperature or 'h' for humidity.

Some pysnmp versions have a bug which throws ValueConstraintError exception
when sensor data is processed despite the data is good. Quick and dirty fix is
to turn on debug, perform PHI self test, get an exception trace and disable the
value testing in pysnmp or pyasn1.
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
        self.__config_help = __config_help__
        self.__get_help = __get_help__
        self.__set_help = __set_help__
        self.__help = __help__
        if info_only: return
        self.community = self.phi_cfg.get('community') if self.phi_cfg.get(
            'community') else 'public'
        try:
            self.snmp_tries = int(self.phi_get('retries')) + 1
        except:
            self.snmp_tries = 1
        self.snmp_host, self.snmp_port = parse_host_port(
            self.phi_cfg.get('host'), 161)
        try:
            self.sensor_port = int(self.phi_cfg.get('sp'))
            if self.sensor_port < 1: self.sensor_port = None
        except:
            self.sensor_port = None
        if not self.snmp_host:
            self.log_error('no host specified')
            self.ready = False
        if not self.sensor_port:
            self.log_error('no sensor port specified')
            self.ready = False

    def get(self, port=None, cfg=None, timeout=0):
        work_oids = {'t': 16, 'h': 17}
        wo = work_oids.get(port)
        if wo is None: return None
        snmp_oid = '.1.3.6.1.4.1.3854.1.2.2.1.%u.1.3.%u' % (
            wo, self.sensor_port - 1)
        _timeout = (timeout - 1) / self.snmp_tries
        return snmp.get(
            snmp_oid,
            self.snmp_host,
            self.snmp_port,
            self.community,
            _timeout,
            self.snmp_tries - 1,
            rf=int,
            snmp_ver=1)

    def start(self):
        eva.traphandler.subscribe(self)

    def stop(self):
        eva.traphandler.unsubscribe(self)

    def process_snmp_trap(self, host, data):
        if host != self.snmp_host: return
        if data.get('1.3.6.1.4.1.3854.1.7.4.0') != str(self.sensor_port - 1):
            return
        d = data.get('1.3.6.1.4.1.3854.1.7.1.0')
        if d == '7':
            handle_phi_event(self, ['t', 'h'], {'t': False, 'h': False})
        elif d == '2':
            t = self.get('t', timeout=get_timeout())
            h = self.get('h', timeout=get_timeout())
            handle_phi_event(self, ['t', 'h'], {'t': t, 'h': h})
        return

    def test(self, cmd=None):
        if cmd == 'info':
            name = snmp.get(
                '.1.3.6.1.4.1.3854.1.1.8.0',
                self.snmp_host,
                self.snmp_port,
                self.community,
                timeout=get_timeout() - 0.5,
                snmp_ver=1)
            if not name: return 'FAILED'
            vendor = snmp.get(
                '.1.3.6.1.4.1.3854.1.1.6.0',
                self.snmp_host,
                self.snmp_port,
                self.community,
                timeout=get_timeout() - 0.5,
                snmp_ver=1)
            if not vendor: return 'FAILED'
            return '%s %s' % (vendor.strip(), name.strip())
        if cmd == 'self':
            t = self.get('t')
            h = self.get('h')
            return 'OK' if t and h else 'FAILED'
        return {'info': 'returns relay ip module name and version'}
