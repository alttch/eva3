__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "DHT11, DHT22, AM3202 temperature/humidity sensors"

__id__ = 'am2302'
__equipment__ = ['DHT11', 'DHT22', 'AM2302']
__api__ = 1
__required__ = ['aao_get', 'value']
__mods_required__ = 'Adafruit_DHT'
__lpi_default__ = 'sensor'
__features__ = ['aao_get']
__config_help__ = [{
    'name': 'port',
    'help': 'GPIO port to use',
    'type': 'int',
    'required': True
}, {
    'name': 'type',
    'help': 'Sensor type (dht11, dht22, or am2302)',
    'type': 'enum:str:dht11,dht22,am2302',
    'required': True
}]
__get_help__ = []
__set_help__ = []

bus_delay = 0.5

__help__ = """
PHI for DT11, DT22, AMR2302 temperature sensors (and compatible). Returns port
'h' for humidity and 't' for temperature.

PHI automatically calculates retries by formula (timeout - 2) / 0.5. To
increase amount of retries retries increase EVA sensor update timeout. The
delay between retries is 0.5 sec.
"""

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import get_timeout

import os
import importlib


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
        self.aao_get = True
        if info_only: return
        try:
            importlib.import_module('Adafruit_DHT')
        except:
            self.log_error('Adafruit_DHT python module not found')
            return
        port = self.phi_cfg.get('port')
        try:
            port = int(port)
        except:
            port = None
        tp = self.phi_cfg.get('type')
        if not port:
            self.log_error('port not specified')
            self.ready = False
        elif tp not in ['dht11', 'dht22', 'am2302']:
            self.log_error('type not specified')
            self.ready = False
        elif not os.path.isdir('/sys/bus/gpio'):
            self.log_error('gpio bus not ready')
            self.ready = False
        else:
            self.port = port
            self.type = tp

    def get(self, port=None, cfg=None, timeout=0):
        retries = int((timeout - 2) / bus_delay)
        try:
            dht = importlib.import_module('Adafruit_DHT')
        except:
            self.log_error('Adafruit_DHT python module not found')
            return None
        try:
            if self.type == 'dht11':
                sensor = dht.DHT11
            elif self.type == 'dht22':
                sensor = dht.DHT22
            else:
                sensor = dht.AM2302
            h, t = dht.read_retry(
                sensor,
                int(self.port),
                retries=retries,
                delay_seconds=bus_delay)
            if h is not None: h = int(h * 1000) / 1000.0
            if t is not None: t = int(t * 1000) / 1000.0
            return { 'h': h, 't': t }
        except:
            log_traceback()
            return None

    def test(self, cmd=None):
        if cmd == 'self':
            try:
                if os.path.isdir('/sys/bus/gpio'):
                    return 'OK'
                else:
                    raise Exception('gpio bus not found')
            except:
                log_traceback()
                return 'FAILED'
        elif cmd == 'get':
            return self.get(timeout=get_timeout())
        else:
            return {'get', 'Return current sensor state'}
