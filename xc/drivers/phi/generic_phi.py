__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "Generic PHI, don't use"
__api__ = 1

__id__ = 'generic'
__equipment__ = 'abstract'

class PHI(object):
    """
    Override everything. super() constructor may be useful to keep unparsed
    config
    """
    def __init__(self, phi_cfg):
        if phi_cfg:
            self.phi_cfg = phi_cfg
        else:
            self.phi_cfg = {}
        self.phi_mod_id = __id__
        self.__author = __author__
        self.__license = __license__
        self.__description = __description__
        self.__version = __version__
        self.__api_version = __api__
        self.__equipment = __equipment__
        # set all_at_once = True if the equipment can query/modify only all
        # ports at once and can not work with a single ports
        self.all_at_once = False 
        self.ready = True
        self.phi_id = None # set by driverapi on load

    def get(self, port, timeout):
        return None

    def set(self, port, data, timeout):
        return False

    def handle_event(self):
        pass

    def start(self):
        return True

    def stop(self):
        return True

    def serialize(self, full=False, config=False):
        d = {}
        if full:
            d['author'] = self.__author
            d['license'] = self.__license
            d['description'] = self.__description
            d['version'] = self.__version
            d['api'] = self.__api_version
            d['equipment'] = self.__equipment
        if config:
            d['cfg'] = self.phi_cfg
        d['mod'] = self.phi_mod_id
        d['id'] = self.phi_id
        return d

    def test(self, cmd=None):
        return False
