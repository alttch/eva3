__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.2"
__description__ = "Generic macro extension, don't use"
__api__ = 7
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
import threading
import sys

from eva.lm.extapi import critical
from eva.lm.extapi import load_data
from eva.lm.extapi import save_data
from eva.lm.extapi import log_traceback

from eva.x import GenericX


class LMExt(GenericX):
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
        mod = kwargs.get('_xmod')
        self.__xmod__ = mod
        self.mod_id = mod.__name__.rsplit('.', 1)[-1]
        self.__author = mod.__author__
        self.__license = mod.__license__
        self.__description = mod.__description__
        self.__version = mod.__version__
        self.__mods_required = mod.__mods_required__
        self.__api_version = mod.__api__
        self._config_help = mod.__config_help__
        self.__functions = mod.__functions__
        self.__help = mod.__help__
        try:
            self.__iec_functions = mod.__iec_functions__
        except:
            self.__iec_functions = {}
        self.ext_id = None  # set by extapi on load
        if kwargs.get('info_only'):
            return
        if not kwargs.get('config_validated'):
            self.validate_config(self.cfg, config_type='config')
        self.data = {}
        self.data_lock = threading.RLock()
        self.data_modified = True
        self.ready = True

    def start(self):
        return True

    def stop(self):
        return True

    def load(self):
        try:
            load_data(self)
        except FileNotFoundError:
            self.log_debug('no ext data file')
        except:
            self.log_error('unable to load ext data')
            log_traceback()

    def save(self):
        if self.data_modified:
            try:
                save_data(self)
                self.data_modified = False
            except:
                self.log_error('unable to save ext data')
                log_traceback()

    def serialize(self, full=False, config=False, helpinfo=None):
        d = {}
        if helpinfo:
            if helpinfo == 'cfg':
                d = self._config_help
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

    def get_iec_functions(self):
        return self.__iec_functions.copy()
