__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.0"
__description__ = "Generic macro extension, don't use"
__api__ = 4
__mods_required__ = []

__id__ = 'generic'

__config_help__ = []

__functions__ = {}

__help__ = """
This is generic extension for using as a base for all other LM PLC macro
extensions. For a list of the available functions look directly into
the extension code or to EVA ICS documentation.
"""

import logging
import sys

from eva.lm.extapi import critical


class LMExt(object):
    """
    Override everything. super() constructor may be useful to keep unparsed
    config
    """

    def __init__(self, **kwargs):
        cfg = kwargs.get('cfg')
        if cfg:
            self.cfg = cfg
        else:
            self.cfg = {}
        mod = sys.modules[self.__module__]
        self.mod_id = mod.__name__.split('.')[-1]
        self.__author = mod.__author__
        self.__license = mod.__license__
        self.__description = mod.__description__
        self.__version = mod.__version__
        self.__mods_required = mod.__mods_required__
        self.__api_version = mod.__api__
        self.__config_help = mod.__config_help__
        self.__functions = mod.__functions__
        self.__help = mod.__help__
        self.ext_id = None  # set by extapi on load
        if kwargs.get('info_only'): return
        self.ready = True

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
            d['mods_required'] = self.__mods_required if \
                    isinstance(self.__mods_required, list) else \
                    [self.__mods_required]
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
