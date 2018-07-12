__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "GPIO power"

__id__ = 'gpio_power'
__equipment__ = 'GPIO'
__api__ = 1
__required__ = []
__features__ = []
__config_help__ = [{
    'name': 'port',
    'help': 'gpio port(s) to turn power on',
    'type': 'list:int',
    'required': False
}]

__get_help__ = []
__set_help__ = []
__help__ = """Dummy PHI for turning on power for GPIO ports. Turns on power on
selected GPIO ports on controller start and turns it back off on controller
shutdown. Doesn't provide any control or monitoring functions.
"""

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback

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
        self.__config_help = __config_help__
        self.__get_help = __get_help__
        self.__set_help = __set_help__
        self.__help = __help__
        if info_only: return
        self.ports = self.phi_cfg.get('port')
        self.devices = []

    def start(self):
        try:
            gpiozero = importlib.import_module('gpiozero')
        except:
            self.log_error('gpiozero python module not found')
            return
        if self.ports:
            ports = self.ports
            if not isinstance(ports, list):
                ports = [ports]
            for p in ports:
                try:
                    d = gpiozero.DigitalOutputDevice(int(p))
                    d.on()
                    self.devices.append(d)
                except:
                    log_traceback()
                    self.log_error('can not power on gpio port %s' % p)

    def stop(self):
        for d in self.devices:
            try:
                d.off()
                d.close()
            except:
                log_traceback()
        self.devices = []

    def test(self, cmd=None):
        if cmd == 'self':
            try:
                if os.path.isdir('/sys/bus/gpio'):
                    try:
                        importlib.import_module('gpiozero')
                    except:
                        raise Exception('gpiozero python module not found')
                    return 'OK'
                else:
                    raise Exception('gpio bus not found')
            except:
                log_traceback()
                return 'FAILED'
        return {'-': 'only self test command available'}
