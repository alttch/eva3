__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "Generic macro extension, don't use"
__api__ = 1

__id__ = 'generic'

__config_help__ = []

__functions__ = {}

__help__ = """
This is generic extension for using as a base for all other LM PLC macro
extensions. For a list of the available functions look directly into
the extension code or to EVA ICS documentation.
"""

import logging

from eva.lm.extapi import critical


class LMExt(object):
    """
    Override everything. super() constructor may be useful to keep unparsed
    config
    """

    def __init__(self, cfg=None):
        if cfg:
            self.cfg = cfg
        else:
            self.cfg = {}
        self.mod_id = __id__
        self.__author = __author__
        self.__license = __license__
        self.__description = __description__
        self.__version = __version__
        self.__api_version = __api__
        self.__config_help = __config_help__
        self.__functions = __functions__
        self.__help = __help__
        self.ready = True
        self.ext_id = None  # set by extapi on load

    def start(self):
        return True

    def stop(self):
        return True

    def serialize(self, full=False, config=False, helpinfo=None):
        d = {}
        if helpinfo:
            if helpinfo == 'cfg':
                d = self.__config_help
            elif helpinfo == 'functions':
                d = self.__functions
            else:
                d = None
            return d
        if full:
            d['author'] = self.__author
            d['license'] = self.__license
            d['description'] = self.__description
            d['version'] = self.__version
            d['api'] = self.__api_version
            d['help'] = self.__help
        if config:
            d['cfg'] = self.cfg
        d['mod'] = self.mod_id
        d['id'] = self.ext_id
        return d

    def test(self, cmd=None):
        return None

    def log_debug(self, msg):
        logging.debug('Extension %s: %s' % (self.ext_id, msg))

    def log_info(self, msg):
        logging.info('Extension %s: %s' % (self.ext_id, msg))

    def log_warning(self, msg):
        logging.warning('Extension %s: %s' % (self.ext_id, msg))

    def log_error(self, msg):
        logging.error('Extension %s: %s' % (self.ext_id, msg))

    def log_error(self, msg):
        logging.error('Extension %s: %s' % (self.ext_id, msg))

    def log_critical(self, msg):
        self.critical(msg)

    def critical(self, msg):
        logging.critical('Extension %s: %s' % (self.ext_id, msg))
        critical()

    def get_functions(self):
        result = []
        for f, h in self.__functions.copy().items():
            result.append(f.split('(')[0].strip())
        return result
