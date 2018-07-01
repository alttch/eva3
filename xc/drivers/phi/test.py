__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "Emulates 4-port relay"
__api__ = 1

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI

class PHI(GenericPHI):

    def __init__(self, cfg):
        super().__init__(cfg=cfg)
        d = self.cfg.get('default_state')
        if d is None: d = -1
        self.data = {
                '1': d,
                '2': d,
                '3': d,
                '4': d 
                }

    def get(self, port, timeout):
        try:
            return self.data.get(str(port))
        except:
            return None

    def set(self, port, data, timeout):
        _port = str(port)
        try:
            data = int(data)
        except:
            return False
        if not _port in self.data:
            return False
        self.data[_port] = data
        return True
