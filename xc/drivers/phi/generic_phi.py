__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "Generic PHI, don't use"
__api__ = 1


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
