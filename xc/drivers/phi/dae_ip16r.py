__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "Denkovi relay smartDEN-IP-16R"

__id__ = 'dae_ip16r'
__equipment__ = 'smartDEN-IP-16R'
__api__ = 1
__required__ = ['port_get', 'port_set', 'status', 'action']
__features__ = ['port_get', 'port_set', 'universal']
__config_help__ = {
    'host': 'relay host/ip[:port]',
    'community': 'snmp community (default: private)',
    'read_community': 'snmp read community',
    'write_community': 'snmp write community',
    'retries': 'snmp retry attemps (default: 0)'
}

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import get_timeout

from eva.tools import parse_host_port

import eva.uc.drivers.tools.snmp as snmp

import pysnmp.proto.rfc1902 as rfc1902


class PHI(GenericPHI):

    def __init__(self, phi_cfg=None):
        super().__init__(phi_cfg=phi_cfg)
        self.phi_mod_id = __id__
        self.__author = __author__
        self.__license = __license__
        self.__description = __description__
        self.__version = __version__
        self.__api_version = __api__
        self.__equipment = __equipment__
        self.__features = __features__
        self.__required = __required__
        self.__config_help = __config_help__
        c = self.phi_cfg.get('community') if self.phi_cfg.get(
            'community') else 'private'
        self.snmp_read_community = c
        self.snmp_write_community = c
        if 'read_community' in self.phi_cfg:
            self.snmp_read_community = self.phi_cfg.get('read_community')
        if 'write_community' in self.phi_cfg:
            self.snmp_read_community = self.phi_cfg.get('write_community')
        try:
            self.snmp_tries = int(self.phi_get('retries')) + 1
        except:
            self.snmp_tries = 1
        self.port_shift = -1
        self.port_max = 16
        self.snmp_host, self.snmp_port = parse_host_port(
            self.phi_cfg.get('host'), 161)
        self.oid_name = '.1.3.6.1.4.1.42505.6.1.1.0'
        self.oid_version = '.1.3.6.1.4.1.42505.6.1.2.0'
        self.oid_work = '.1.3.6.1.4.1.42505.6.2.3.1.3'

    def get(self, port=None, cfg=None, timeout=0):
        try:
            port = int(port)
        except:
            return None
        if cfg:
            host, snmp_port = parse_host_port(cfg.get('host'), 161)
            community = cfg.get('community')
            tries = cfg.get('retries')
            try:
                tries = int(tries)
            except:
                tries = None
        else:
            host = None
            community = None
            tries = None
        if not host:
            host = self.snmp_host
            snmp_port = self.snmp_port
        if not community:
            community = self.snmp_read_community
        if tries is None: tries = self.snmp_tries
        if port < 1 or port > self.port_max: return None
        _timeout = (timeout - 1) / tries
        return snmp.get(
            '%s.%u' % (self.oid_work, port + self.port_shift),
            host,
            snmp_port,
            community,
            _timeout,
            tries - 1,
            rf=int)

    def set(self, port=None, data=None, cfg=None, timeout=0):
        try:
            port = int(port)
            val = int(data)
        except:
            return None
        if cfg:
            host, snmp_port = parse_host_port(cfg.get('host'), 161)
            community = cfg.get('community')
            tries = cfg.get('retries')
            try:
                tries = int(tries)
            except:
                tries = None
        else:
            host = None
            community = None
            tries = None
        if not host:
            host = self.snmp_host
            snmp_port = self.snmp_port
        if not community:
            community = self.snmp_write_community
        if tries is None: tries = self.snmp_tries
        if port < 1 or port > self.port_max or val < 0 or val > 1: return None
        _timeout = (timeout - 1) / self.snmp_tries
        return snmp.set('%s.%u' % (self.oid_work, port + self.port_shift),
                        rfc1902.Integer(val), host, snmp_port, community,
                        _timeout, tries - 1)

    def test(self, cmd=None):
        if cmd == 'info' or cmd == 'self':
            name = snmp.get(
                self.oid_name,
                self.snmp_host,
                self.snmp_port,
                self.snmp_read_community,
                timeout=get_timeout() - 0.5)
            if not name: return 'FAILED'
            if name and cmd == 'self': return 'OK'
            version = snmp.get(
                self.oid_version,
                self.snmp_host,
                self.snmp_port,
                self.snmp_read_community,
                timeout=get_timeout() - 0.5)
            if not version: return 'FAILED'
            return '%s %s' % (name.strip(), version.strip())
        return {'info': 'returns relay ip module name and version'}
