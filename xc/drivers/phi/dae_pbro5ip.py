__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "Emulates 16-port relay"
__api__ = 1

__id__ = 'dae_pbro5ip'
__equipment__ = 'DAE-PB-RO5-DAEnetIP4'

__features__ = ['port_get', 'port_set']

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback

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
        host = self.phi_cfg.get('host')
        self.port_shift = 7
        self.port_max = 5
        if host:
            try:
                self.snmp_host, port = host.split(':')
                self.snmp_port = int(port)
            except:
                self.snmp_host = host
                self.snmp_port = 161
        else:
            self.ready = False

    def get(self, port=None, cfg=None, timeout=0):
        try:
            port = int(port)
        except:
            return None
        if port > self.port_max: return None
        _timeout = (timeout - 1) / self.snmp_tries
        return snmp.get(
            '.1.3.6.1.4.1.42505.1.2.3.1.11.%u' % (port + self.port_shift),
            self.snmp_host,
            self.snmp_port,
            self.snmp_read_community,
            _timeout,
            self.snmp_tries - 1,
            rf=int)

    def set(self, port, data, cfg=None, timeout=0):
        try:
            port = int(port)
            val = int(data)
        except:
            return None
        if port > self.port_max or val < 0 or val > 1: return None
        _timeout = (timeout - 1) / self.snmp_tries
        return snmp.set(
            '.1.3.6.1.4.1.42505.1.2.3.1.11.%u' % (port + self.port_shift),
            rfc1902.Integer(val), self.snmp_host, self.snmp_port,
            self.snmp_write_community, _timeout, self.snmp_tries - 1)

    def serialize(self, full=False, config=False):
        d = super().serialize(full=full, config=config)
        return d

    def test(self, cmd=None):
        if cmd == 'info':
            name = snmp.get(
                '.1.3.6.1.4.1.42505.1.1.1.0',
                self.snmp_host,
                self.snmp_port,
                self.snmp_read_community,
                timeout=5)
            if not name: return 'QUERY FAILED'
            version = snmp.get(
                '.1.3.6.1.4.1.42505.1.1.2.0',
                self.snmp_host,
                self.snmp_port,
                self.snmp_read_community,
                timeout=5)
            if not version: return 'QUERY FAILED'
            return '%s %s' % (name.strip(), version.strip())
        return [{
            'command': 'info',
            'help': 'returns relay ip module name and version'
        }]
