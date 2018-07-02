__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "Generic PHI, don't use"
__api__ = 1

__id__ = 'generic'


class PHI(object):
    """
    Override everything. super() constructor may be useful to keep unparsed
    config
    """
    def __init__(self, cfg):
        if cfg:
            self.cfg = cfg
        else:
            self.cfg = {}
        self.phi_id = __id__
        self.author = __author__
        self.license = __license__
        self.description = __description__
        self.version = __version__
        self.api_version = __api__

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
            d['author'] = self.author
            d['license'] = self.license
            d['description'] = self.description
            d['version'] = self.version
            d['api'] = self.api_version
        if config:
            d['cfg'] = self.cfg
        d['id'] = self.phi_id
        return d
