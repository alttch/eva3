__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"
__description__ = "Generic LPI, don't use"
__api__ = 9

__logic__ = 'abstract'

__features__ = []

__config_help__ = []

__action_help__ = []

__state_help__ = []

__help__ = """
Generic extension for using as a base for all other UC LPI modules. For a list
of the available functions look directly into the extension code or to EVA ICS
documentation.
"""

import threading
import logging
import time
import uuid
import sys
import timeouter

from eva.uc.driverapi import get_polldelay
from eva.uc.driverapi import get_timeout
from eva.uc.driverapi import critical
from eva.uc.driverapi import get_phi
from eva.uc.driverapi import get_timeout

from eva.x import GenericX


class LPI(GenericX):

    connections = {'port': 'primary'}
    """
    Functions required to be overriden
    """
    """
    Returns item state tuple (status, value)
    Override this function with your own
    """

    def do_state(self, _uuid, cfg, timeout, tki, state_in):
        self.log_error('state function not implemented')
        return self.state_result_error(_uuid)

    """
    Performs item action
    Override this function with your own
    """

    def do_action(self, _uuid, status, value, cfg, timeout, tki):
        self.log_error('action function not implemented')
        return self.action_result_error(_uuid,
                                        msg='action function not implemented')

    """
    Starts LPI threads
    """

    def start(self):
        return True

    """
    Stops LPI threads
    """

    def stop(self):
        return True

    """
    Get item connection map
    """

    def get_item_cmap(self, cfg):
        port = cfg.get(self.io_label)
        if not isinstance(port, list):
            port = [port]
        return {'port': port}

    def serialize(self, full=False, config=False, helpinfo=None):
        d = {}
        if helpinfo:
            if helpinfo == 'cfg':
                d = self._config_help.copy()
                return d
            elif helpinfo == 'action':
                d = self._action_help.copy()
            elif helpinfo == 'update':
                d = self._state_help.copy()
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
            d['logic'] = self.__logic
            d['help'] = self.__help
            d['connections'] = self.connections
            if self.phi:
                d['phi'] = self.phi.serialize(full=True, config=True)
        if config:
            d['cfg'] = self.lpi_cfg
        d['lpi_id'] = self.lpi_id
        d['id'] = self.driver_id
        d['mod'] = self.lpi_mod_id
        d['phi_id'] = self.phi_id
        if not config:
            d['features'] = self.__features
        return d

    """
    Functions allowed to use in LPI
    """
    """
    Checks if the port state need to be inverted

    Args:
        port - port number (string, in case of integer state should not be
        inverted)

    Returns (port, True) if port state need to be inverted, (port, False) if not
    """

    def need_invert(self, port):
        if not isinstance(port, str) or port[:2] != 'i:':
            return port, False
        return port[2:], True

    """
    Checks for the terminate call

    Args:
        _uuid - action uuid

    Returns True if the controller requested action termination
    """

    def need_terminate(self, _uuid):
        e = self.__terminate.get(_uuid)
        if not e:
            self.critical('termination engine broken')
        return e.is_set()

    """
    Performs a delay in action execution. If the controller requested action
    termination, immediately returns False

    Args:
        _uuid - action uuid
        sec - seconds to sleep (float or int)

    Returns False if the controller requested action termination during the
    pause
    """

    def delay(self, _uuid, sec):
        t_end = time.perf_counter() + sec
        while time.perf_counter() < t_end:
            if self.need_terminate(_uuid):
                return False
            time.sleep(get_polldelay())
        return not self.need_terminate(_uuid)

    def action_result_terminated(self, _uuid):
        return self.action_result(_uuid, -15, '', '')

    def action_result_error(self, _uuid, code=1, msg=''):
        return self.action_result(_uuid, code, '', msg)

    def action_result_ok(self, _uuid, msg=''):
        return self.action_result(_uuid, 0, msg, '')

    def action_result(self, _uuid, code=0, out='', err=''):
        self._remove_terminate(_uuid)
        result = {'exitcode': code, 'out': out, 'err': err}
        self.set_result(_uuid, result)
        return result

    def state_result_error(self, _uuid):
        self.set_result(_uuid, (-1, None))
        return False

    def state_result_skip(self, _uuid):
        self.set_result(_uuid, False)
        return False

    def set_result(self, _uuid, result=None):
        if not self.__results_lock.acquire(timeout=get_timeout()):
            self.critical('GenericLPI::set_result locking broken')
            return None
        self.__results[_uuid] = result
        self.__results_lock.release()
        return True

    def log_debug(self, msg):
        logging.debug('driver %s: %s' % (self.driver_id, msg))

    def log_info(self, msg):
        logging.info('driver %s: %s' % (self.driver_id, msg))

    def log_warning(self, msg):
        logging.warning('driver %s: %s' % (self.driver_id, msg))

    def log_error(self, msg):
        logging.error('driver %s: %s' % (self.driver_id, msg))

    def log_error(self, msg):
        logging.error('driver %s: %s' % (self.driver_id, msg))

    def log_critical(self, msg):
        self.critical(msg)

    def critical(self, msg):
        logging.critical('driver %s: %s' % (self.driver_id, msg))
        critical()

    """
    Constructor should be overriden to set lpi id plus i.e. to parse config,
    just don't forget to call super().__init__ before your code
    """

    def __init__(self, **kwargs):
        self.phi_id = kwargs.get('phi_id')
        lpi_cfg = kwargs.get('lpi_cfg')
        self.lpi_id = None  # set by driverapi on load
        self.driver_id = None  # set by driverapi on load
        self.phi = None  # set by driverapi on each call
        self.oid = None
        if lpi_cfg:
            self.lpi_cfg = lpi_cfg
        else:
            self.lpi_cfg = {}
        self.default_tki_diff = 2
        self.__terminate = {}
        self.__results = {}
        self.__terminate_lock = threading.Lock()
        self.__results_lock = threading.Lock()

        mod = kwargs.get('_xmod')
        self.__xmod__ = mod
        self.lpi_mod_id = mod.__name__.rsplit('.', 1)[-1]
        self.__author = mod.__author__
        self.__license = mod.__license__
        self.__description = mod.__description__
        self.__version = mod.__version__
        self.__api_version = mod.__api__
        self.__logic = mod.__logic__
        self.__features = mod.__features__
        self._config_help = mod.__config_help__
        self._action_help = mod.__action_help__
        self._state_help = mod.__state_help__
        self.__help = mod.__help__
        self.io_label = self.lpi_cfg.get('io_label') if self.lpi_cfg.get(
            'io_label') else 'port'
        if self.io_label != 'port':
            for l in self._action_help, self._state_help:
                for v in l:
                    if v['name'] == 'port':
                        v['name'] = self.io_label
        if kwargs.get('info_only'):
            return
        if not kwargs.get('config_validated'):
            self.validate_config(self.lpi_cfg,
                                 config_type='config',
                                 xparams=[{
                                     'name': 'io_label',
                                     'type': 'str'
                                 }])
        self.ready = True

    """
    DO NOT OVERRIDE THE FUNCTIONS BELOW
    """

    def state(self, _uuid, cfg=None, timeout=None, tki=None, state_in=None):
        if timeout:
            _timeout = timeout
        else:
            _timeout = get_timeout()
        timeouter.init(_timeout)
        if tki:
            _tki = tki
        else:
            _tki = get_timeout() - self.default_tki_diff
            if _tki < 0:
                _tki = 0
        if not self.phi:
            self.log_error('no PHI assigned')
            return None
        return self.do_state(_uuid, cfg, timeout, _tki, state_in)

    def action(self,
               _uuid,
               status=None,
               value=None,
               cfg=None,
               timeout=None,
               tki=None):
        if timeout:
            _timeout = timeout
        else:
            _timeout = get_timeout()
        timeouter.init(_timeout)
        if tki:
            _tki = tki
        else:
            _tki = get_timeout() - self.default_tki_diff
            if _tki < 0:
                _tki = 0
        if not self.phi:
            self.log_error('no PHI assigned')
            return None
        self.prepare_action(_uuid)
        return self.do_action(_uuid, status, value, cfg, timeout, tki)

    def prepare_action(self, _uuid):
        self._append_terminate(_uuid)
        self.set_result(_uuid)

    def terminate(self, _uuid):
        if not self.__terminate_lock.acquire(timeout=get_timeout()):
            self.critical('GenericLPI::terminate locking broken')
            return None
        t = self.__terminate.get(_uuid)
        if not t:
            self.__terminate_lock.release()
            return False
        t.set()
        self.__terminate_lock.release()
        return True

    def _append_terminate(self, _uuid):
        if not self.__terminate_lock.acquire(timeout=get_timeout()):
            self.critical('GenericLPI::_append_terminate locking broken')
            return None
        self.__terminate[_uuid] = threading.Event()
        self.__terminate_lock.release()
        return True

    def _remove_terminate(self, _uuid):
        if not self.__terminate_lock.acquire(timeout=get_timeout()):
            self.critical('GenericLPI::_remove_terminate locking broken')
            return None
        try:
            del (self.__terminate[_uuid])
        except:
            self.__terminate_lock.release()
            return False
        self.__terminate_lock.release()
        return True

    def clear_result(self, _uuid):
        if not self.__results_lock.acquire(timeout=get_timeout()):
            self.critical('GenericLPI::clear_result locking broken')
            return None
        try:
            del (self.__results[_uuid])
        except:
            self.__results_lock.release()
            return False
        self.__results_lock.release()
        return True

    def get_result(self, _uuid):
        if not self.__results_lock.acquire(timeout=get_timeout()):
            self.critical('GenericLPI::get_result locking broken')
            return None
        result = self.__results.get(_uuid)
        self.__results_lock.release()
        return result

    def prepare_phi_cfg(self, cfg):
        phi_cfg = {}
        if isinstance(cfg, dict):
            for k, v in cfg.copy().items():
                if k[0] == '_':
                    phi_cfg[k[1:]] = v
        return phi_cfg

    def gen_uuid(self):
        return str(uuid.uuid4())

    def _start(self):
        return self.start()

    def _stop(self):
        return self.stop()
