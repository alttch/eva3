__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "1-Wire DS18N20 temperature sensors"

__id__ = 'w1_ds18n20'
__equipment__ = ['DS18S20', 'DS18B20']
__api__ = 1
__required__ = ['port_get', 'value']
__mods_required__ = []
__lpi_default__ = 'sensor'
__features__ = ['port_get', 'universal']
__config_help__ = [{
    'name': 'retries',
    'help': '1-Wire retry attempts (default: 3)',
    'type': 'int',
    'required': False
}]
__get_help__ = __config_help__
__set_help__ = __config_help__

w1_delay = 0.5

__help__ = """
PHI for Maxim Integrated 1-Wire DS18N20 temperature sensors (DS18S20, DS18B20
and comiatible), uses Linux w1 module and /sys/bus/w1 bus to access the
equipment. The Linux module should be always loaded before PHI.

This is universal PHI and no additional config params are required. PHI should
be loaded once and can query any compatible sensor on the local bus, sensor
1-Wire address should be specified in 'port' variable.
"""

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback
from time import sleep

import os


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
        self.w1 = '/sys/bus/w1/devices'
        retries = self.phi_cfg.get('retries')
        try:
            retries = int(retries)
        except:
            retries = None
        self.retries = retries if retries is not None else 3
        if not os.path.isdir(self.w1):
            self.log_error('1-Wire bus not ready')
            self.ready = False

    def get(self, port=None, cfg=None, timeout=0):
        if port is None: return None
        for i in range(self.retries + 1):
            try:
                r = open('%s/%s/w1_slave' % (self.w1, port)).readlines()
                if r[0].strip()[-3:] != 'YES': return None
                d, val = r[1].strip().split('=')
                val = float(val) / 1000
                return val
            except:
                if i == self.retries:
                    log_traceback()
                else:
                    sleep(w1_delay)
        return None

    def test(self, cmd=None):
        if cmd == 'self':
            return 'OK' if os.path.isdir(self.w1) else 'FAILED'
        else:
            return {'-': 'this PHI has no test functions except "self"'}
