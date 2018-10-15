__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "Generic CPLC, don't use"

__id__ = 'generic'
__api__ = 1
__mods_required__ = []
__config_help__ = []

__help__ = """
Generic Core PLC logic module
"""

import logging
import threading

import eva.core

from eva.uc.coreplc import critical
from eva.uc.coreplc import log_traceback

from time import time
from time import sleep


class CPLC(object):
    """
    Override everything. super() constructor may be useful to keep unparsed
    config
    """

    def __init__(self, cfg=None, info_only=False):
        if cfg:
            self.cfg = cfg
        else:
            self.cfg = {}
        self.mod_id = __id__
        self.cplc_id = None
        self.oid = None
        #'cplc:uc/%s/%s' % (eva.core.system_name, __id__)
        self.__author = __author__
        self.__license = __license__
        self.__description = __description__
        self.__version = __version__
        self.__api_version = __api__
        self.__mods_required = __mods_required__
        self.__config_help = __config_help__
        self.__help = __help__
        if info_only: return
        self._loops = set()
        self._event_handlers = set()
        self._loop_processors = []
        self.loops_active = False

    def start(self):
        return True

    def stop(self):
        return True

    def serialize(self, full=False, config=False, helpinfo=None):
        d = {}
        if helpinfo:
            if helpinfo == 'cfg':
                d = self.__config_help.copy()
            else:
                d = None
            return d
        if full:
            d['author'] = self.__author
            d['license'] = self.__license
            d['description'] = self.__description
            d['version'] = self.__version
            d['api'] = self.__api_version
            d['oid'] = self.oid
            d['mods_required'] = self.__mods_required if \
                    isinstance(self.__mods_required, list) else \
                    [self.__mods_required]
            d['help'] = self.__help
        if config:
            d['cfg'] = self.cfg
        d['mod'] = self.mod_id
        d['id'] = self.cplc_id
        return d

    def test(self, cmd=None):
        return 'FAILED'

    # don't override the methods below

    def register_loop(self, target, interval=None, delay=None):
        self._loops.add({
            'target': target,
            'interval': interval,
            'delay': delay
        })

    def register_event_handler(self, item_id, func):
        result = register_event_handler(item_id, func)
        if result:
            self._event_handlers.add({
                'id': item_id,
                'func': func,
            })

    def log_debug(self, msg):
        i = self.cplc_id if self.cplc_id is not None else self.mod_id
        logging.debug('CORE PLC %s: %s' % (i, msg))

    def log_info(self, msg):
        i = self.cplc_id if self.cplc_id is not None else self.mod_id
        logging.info('CORE PLC %s: %s' % (i, msg))

    def log_warning(self, msg):
        i = self.cplc_id if self.cplc_id is not None else self.mod_id
        logging.warning('CORE PLC %s: %s' % (i, msg))

    def log_error(self, msg):
        i = self.cplc_id if self.cplc_id is not None else self.mod_id
        logging.error('CORE PLC %s: %s' % (i, msg))

    def log_error(self, msg):
        i = self.cplc_id if self.cplc_id is not None else self.mod_id
        logging.error('CORE PLC %s: %s' % (i, msg))

    def log_critical(self, msg):
        self.critical(msg)

    def critical(self, msg):
        i = self.cplc_id if self.cplc_id is not None else self.mod_id
        logging.critical('CORE PLC %s: %s' % (i, msg))
        critical()

    def _start(self):
        self.start()
        self.loops_active = True
        for l in self._loops:
            t = threading.Thread(
                target=self._t_loop,
                args=(l.get('target'), l.get('interval'), l.get('delay')))
            self._loop_processors.append(t)
            t.start()

    def _stop(self):
        self.loops_active = False
        for h in self._event_handlers:
            unregister_event_handler(h.get('id'), h.get('func'))
        self._event_handlers = []
        for l in self._loop_processors:
            if l.isActive():
                l.join()
        self._loop_processors = []
        self.stop()

    def _t_loop(self, target, interval=None, delay=None):
        polldelay = get_polldelay()
        try:
            logging.info('%s loop %s started' % self.oid, target.__name__)
            while self.loops_active:
                t_start = time()
                try:
                    target()
                except:
                    logging.error(
                        '%s loop %s target error' % (self.oid, target.__name__))
                    log_traceback()
                xtime = time() - t_start
                if interval:
                    sleep_time = intrval - xtime
                    if sleep_time < 0:
                        logging.critical(
                            '%s loop %s' % (self.oid, target.__name__) + \
                                    'target exec time exceeded interval set')
                        critical()
                else:
                    sleep_time = delay
                if sleep_time:
                    if sleep_time > 1:
                        i = 0
                        while i < sleep_time and self.loops_active:
                            sleep(polldelay)
                    else:
                        sleep(sleep_time)
            logging.info('%s loop %s stopped' % (self.oid, target.__name__))
        except:
            logging.error('%s loop %s error' % (self.oid, target.__name__))
            log_traceback()
            return
