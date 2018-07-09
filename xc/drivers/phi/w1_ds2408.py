__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "1-Wire DS2408 8-port relay"

__id__ = 'w1_ds2408'
__equipment__ = 'DS2408'
__api__ = 1
__required__ = ['aao_get', 'aao_set', 'status', 'action']
__features__ = ['aao_get', 'aao_set', 'universal']
__config_help__ = [{
    'name': 'addr',
    'help': 'relay address on 1-Wire bus',
    'type': 'str',
    'required': False
}, {
    'name': 'retries',
    'help': '1-Wire set retry attempts (default: 3)',
    'type': 'int',
    'required': False
}]
__get_help__ = __config_help__
__set_help__ = __config_help__

w1_delay = 0.05

__help__ = """
PHI for Maxim Integrated 1-Wire DS2408, uses Linux w1 module and /sys/bus/w1
bus to access the equipment. The Linux module should be always loaded before
PHI. The equipment returns and sets ports state all at once only, LPI should
support this method.

This is universal PHI which means one PHI can control either one or multiple
relays of the same type if relay config (addr) is provided in unit driver
configuration.

Property 'addr' should be specified either in driver primary configuration or
in each unit configuration which uses the driver with this PHI.
"""

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import lock
from eva.uc.driverapi import unlock

import os

from time import time
from time import sleep


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
        self.__get_help = __get_help__
        self.__set_help = __set_help__
        self.__help = __help__
        self.addr = self.phi_cfg.get('addr')
        self.w1 = '/sys/bus/w1/devices'
        self.aao_get = True
        self.aao_set = True
        retries = self.phi_cfg.get('retries')
        try:
            retries = int(retries)
        except:
            retries = None
        self.retries = retries if retries is not None else 3
        if not os.path.isdir(self.w1):
            self.log_error('1-Wire bus not ready')
            self.ready = False

    def safe_read(self, addr):
        for i in range(self.retries + 1):
            result = []
            for ins in range(2):
                for i in range(self.retries + 1):
                    try:
                        r = ord(
                            open('%s/%s/state' % (self.w1, addr), 'rb').read(1))
                        break
                    except:
                        r = None
                result.append(r)
                if not ins: sleep(w1_delay)
            if result[0] == result[1]:
                return result[0]
        return None

    def get(self, port=None, cfg=None, timeout=0):
        if cfg:
            addr = cfg.get('addr')
            if addr is None: addr = self.addr
        else: addr = self.addr
        if addr is None: return None
        if not lock('w1:' + addr):
            self.log_error('can not acquire lock')
            return False
        try:
            r = self.safe_read(addr)
            if r is None:
                raise Exception('1-Wire get error')
            sleep(w1_delay)
            data = {}
            for i in range(8):
                data[str(i + 1)] = 0 if 1 << i & r else 1
        except:
            unlock('w1:' + addr)
            log_traceback()
            return None
        unlock('w1:' + addr)
        return data

    def set(self, port=None, data=None, cfg=None, timeout=0):
        time_start = time()
        if cfg:
            addr = cfg.get('addr')
            if addr is None: addr = self.addr
        else: addr = self.addr
        if addr is None:
            self.log_error('1-Wire addr not specified')
            return False
        if not lock('w1:' + addr):
            self.log_error('can not acquire lock')
            return False
        try:
            if isinstance(port, list):
                _port = port
                _data = data
            else:
                _port = [port]
                _data = [data]
            r = self.safe_read(addr)
            if r is None:
                raise Exception('1-Wire get error')
            for i in range(0, len(_port)):
                _p = int(_port[i])
                _d = int(_data[i])
                if _p < 1 or _p > 8:
                    raise Exception('port is not in range 1..8')
                if _d < 0 or _d > 1:
                    raise Exception('data is not in range 0..1')
                if _d: r = 1 << (_p - 1) ^ 0xFF & r
                else: r = r | 1 << (_p - 1)
            if time_start + timeout <= time():
                raise Exception('1-Wire timeout')
            for i in range(self.retries + 1):
                try:
                    open('%s/%s/output' % (self.w1, addr), 'wb').write(
                        bytes([r]))
                    sleep(w1_delay)
                    rn = self.safe_read(addr)
                except:
                    rn = None
                if r == rn: break
                if i == self.retries: raise Exception('1-Wire set error')
                if time_start + timeout <= time():
                    raise Exception('1-Wire timeout')
            unlock('w1:' + addr)
            return True
        except:
            unlock('w1:' + addr)
            log_traceback()
            return False

    def test(self, cmd=None):
        if cmd == 'self':
            if self.addr is None:
                return 'OK' if os.path.isdir(self.w1) else 'FAILED'
            else:
                return 'OK' if self.get() else 'FAILED'
        elif cmd == 'get':
            return self.get()
        else:
            return {'get': 'get current relay ports state'}
