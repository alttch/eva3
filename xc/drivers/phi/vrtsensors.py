__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "Emulates virtual sensors"
__api__ = 1

__id__ = 'vrtsensors'
__equipment__ = 'virtual sensors'

__features__ = [ 'port_get' ]

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import handle_phi_event
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import critical

class PHI(GenericPHI):

    def __init__(self, phi_cfg=None):
        super().__init__(phi_cfg=phi_cfg)
        d = self.phi_cfg.get('default_value')
        if d is None: d = None
        else:
            try:
                d = float(d)
            except:
                d = None
        self.data = {}
        for i in range(1000, 1010):
            self.data[str(i)] = d
        self.phi_mod_id = __id__
        self.__author = __author__
        self.__license = __license__
        self.__description = __description__
        self.__version = __version__
        self.__api_version = __api__
        self.__equipment = __equipment__
        self.__features = __features__

    def get(self, port=None, cfg=None, timeout=0):
        try:
            return self.data.get(str(port))
        except:
            return None

    def serialize(self, full=False, config=False):
        d = super().serialize(full=full, config=config)
        return d

    def test(self, cmd=None):
        if cmd == 'get':
            return self.data
        if cmd == 'critical':
            self.log_critical('test')
            return True
        try:
            port, val = cmd.split('=')
            try:
                val = float(val)
                self.data[port] = val
            except:
                self.data[port] = None
            self.log_debug(
                '%s test completed, set port %s=%s' % (self.phi_id, port, val))
            if self.phi_cfg.get('event_on_test_set'):
                handle_phi_event(self, port, self.data)
            return self.data
        except:
            log_traceback()
            return None
