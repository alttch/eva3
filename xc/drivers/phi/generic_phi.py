__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "Generic PHI, don't use"

__id__ = 'generic'
__equipment__ = 'abstract'
__api__ = 1
__required__ = []
__features__ = []
__config_help__ = []
__get_help__ = []
__set_help__ = []

__help__ = """
Generic PHI for using as a base for all other UC PHI modules. For a list of the
available functions look directly into the extension code or to EVA ICS
documentation.
"""

import logging

from eva.uc.driverapi import critical

from time import time

class PHI(object):
    """
    Override everything. super() constructor may be useful to keep unparsed
    config
    """

    def __init__(self, phi_cfg=None):
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
        self.__features = __features__
        self.__required = __required__
        self.__config_help = __config_help__
        self.__get_help = __get_help__
        self.__set_help = __set_help__
        self.__help = __help__
        # True if the equipment can query/modify only all
        # ports at once and can not work with a single ports
        self.aao_get = False
        self.aao_set = False
        self.ready = True
        self.phi_id = None  # set by driverapi on load
        # cache time, useful for aao_get devices
        self.cache_set = 0
        try:
            self.cache = float(self.phi_cfg.get('cache'))
        except:
            self.cache = 0
        self.cache_data = None

    def get_cached_state(self):
        if not self.cache or not self.cache_data:
            return None
        return self.cache_data if \
                time() - self.cache_set < self.cache else None

    def set_cached_state(self, data):
        if not self.cache:
            return False
        self.cache_data = data
        self.cache_set = time()

    def clear_cache(self):
        self.cache_set = 0
        self.cache_data = None

    def get(self, port=None, cfg=None, timeout=0):
        return None

    def set(self, port=None, data=None, cfg=None, timeout=0):
        return False

    def handle_event(self):
        pass

    def start(self):
        return True

    def stop(self):
        return True

    def serialize(self, full=False, config=False, helpinfo=None):
        d = {}
        if helpinfo:
            if helpinfo == 'cfg':
                d = self.__config_help
                if 'cache' in self.__features:
                    d.append({
                        'name': 'cache',
                        'help': 'caches state for N sec',
                        'type': 'float',
                        'required': False
                        })
            elif helpinfo == 'get':
                d = self.__get_help
            elif helpinfo == 'set':
                d = self.__set_help
            else:
                d = None
            return d
        if full:
            d['author'] = self.__author
            d['license'] = self.__license
            d['description'] = self.__description
            d['version'] = self.__version
            d['api'] = self.__api_version
            d['equipment'] = self.__equipment if \
                    isinstance(self.__equipment, list) else [self.__equipment]
            d['features'] = self.__features
            d['required'] = self.__required
            d['help'] = self.__help
        if config:
            d['cfg'] = self.phi_cfg
        d['mod'] = self.phi_mod_id
        d['id'] = self.phi_id
        return d

    def test(self, cmd=None):
        return 'FAILED'

    def log_debug(self, msg):
        logging.debug('PHI %s: %s' % (self.phi_id, msg))

    def log_info(self, msg):
        logging.info('PHI %s: %s' % (self.phi_id, msg))

    def log_warning(self, msg):
        logging.warning('PHI %s: %s' % (self.phi_id, msg))

    def log_error(self, msg):
        logging.error('PHI %s: %s' % (self.phi_id, msg))

    def log_error(self, msg):
        logging.error('PHI %s: %s' % (self.phi_id, msg))

    def log_critical(self, msg):
        self.critical(msg)

    def critical(self, msg):
        logging.critical('PHI %s: %s' % (self.phi_id, msg))
        critical()
