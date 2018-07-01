__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "Emulates 4-port relay"
__api__ = 1

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI

class PHI(GenericPHI):

    def __init__(self, cfg):
        self.data = {
                '1': -1,
                '2': -1,
                '3': -1,
                '4': -1
                }
        super().__init__(cfg=cfg)

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
