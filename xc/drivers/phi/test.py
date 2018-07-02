__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "Emulates 16-port relay"
__api__ = 1
__id__ = 'test'

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import handle_phi_event
from eva.uc.driverapi import log_traceback

import logging

class PHI(GenericPHI):

    def __init__(self, phi_cfg):
        super().__init__(phi_cfg=phi_cfg)
        d = self.phi_cfg.get('default_state')
        if d is None: d = -1
        else:
            try:
                d = int(d)
            except:
                d = -1
        self.data = {}
        for i in range(1,32):
            self.data[str(i)] = d
        self.phi_mod_id = __id__
        self.author = __author__
        self.license = __license__
        self.description = __description__
        self.version = __version__
        self.api_version = __api__

    def get(self, port, timeout):
        try:
            return self.data.get(str(port))
        except:
            return None

    def set(self, port, data, timeout):
        _port = str(port)
        try:
            _data = int(data)
        except:
            return False
        if not _port in self.data:
            return False
        self.data[_port] = _data
        if self.phi_cfg.get('event_on_set'):
            handle_phi_event(self.phi_id, port, self.data)
        return True

    def serialize(self, full=False, config=False):
        d = super().serialize(full=full, config=config)
        return d

    def test(self, cmd=None):
        if cmd == 'get':
            return self.data
        try:
            port, val = cmd.split('=')
            port = int(port)
            val = int(val)
            if port < 1 or port > 16 or val < -1 or val > 1: return None
            self.data[port] = val
            logging.debug(
                '%s test completed, set port %s=%s' % (self.phi_id, port, val))
            handle_phi_event(self, port, self.data)
            return self.data
        except:
            log_traceback()
            return None
