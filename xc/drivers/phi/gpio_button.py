__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "GPIO buttons"

__id__ = 'gpio_button'
__equipment__ = 'GPIO buttons'
__api__ = 1
__required__ = []
__features__ = []
__mods_required__ = 'gpiozero'
__lpi_default__ = 'sensor'
__config_help__ = [{
    'name': 'port',
    'help': 'gpio port(s) with buttons',
    'type': 'list:str',
    'required': False
}, {
    'name': 'no_pullup',
    'help': 'Skip internal pull up resistors activation',
    'type': 'bool',
    'required': False
}]

__get_help__ = []
__set_help__ = []
__help__ = """ Handling pressed events from GPIO buttons.

PHI doesn't provide any control/monitoring functions, each button can be
configured as unit (via basic LPI) or sensor (via esensor) and contain its port
in update_driver_config, update_interval should be set to 0.
"""

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import handle_phi_event
from eva.tools import val_to_boolean

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
        if info_only: return
        self.ports = self.phi_cfg.get('port')
        self.no_pullup = val_to_boolean(self.phi_cfg.get('no_pullup'))
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
                    _p = int(p)
                    pf = lambda a=str(_p): \
                        handle_phi_event(self, a, {str(a): '1'})
                    rf = lambda a=str(_p):  \
                        handle_phi_event(self, a, {str(a): '0'})
                    d = gpiozero.Button(_p, pull_up=not self.no_pullup)
                    d.when_pressed = pf
                    d.when_released = rf
                    self.devices.append(d)
                except:
                    log_traceback()
                    self.log_error('can not assign button to gpio port %s' % p)

    def stop(self):
        for d in self.devices:
            try:
                d.close()
            except:
                log_traceback()

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
