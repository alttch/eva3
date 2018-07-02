__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "Generic LPI, don't use"
__api__ = 1

import threading
import logging
import time

from eva.uc.driverapi import get_polldelay
from eva.uc.driverapi import get_timeout
from eva.uc.driverapi import critical
from eva.uc.driverapi import get_phi


class LPI(object):
    """
    Functions required to be overriden
    """
    """
    Returns item state tuple (status, value)
    Override this function with your own
    """

    def do_state(self, cfg, multi, timeout, state_in):
        logging.error('driver lpi %s state function not implemented' %
                      self.lpi_id.split('.')[-1])
        return -1, None

    """
    Performs item action
    Override this function with your own
    """

    def do_action(self, _uuid, status, value, cfg, timeout):
        logging.error('driver lpi %s action function not implemented' %
                      self.lpi_id.split('.')[-1])
        return self.result_error(_uuid, msg='action function not implemented')

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
        if not isinstance(port, str) or port[:2] != 'i:': return port, False
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
            logging.critical('Driver %s termination engine broken' %
                             self.lpi_id.split('.')[-1])
            critical()
        return e.isSet()

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
        i = 0
        while i < sec:
            if self.need_terminate(_uuid): return False
            time.sleep(get_polldelay())
            i += get_polldelay()
        return not self.need_terminate(_uuid)

    def result_terminated(self, _uuid):
        return self.result(_uuid, -15, '', '')

    def result_error(self, _uuid, code=1, msg=''):
        return self.result(_uuid, code, '', msg)

    def result_ok(self, _uuid, msg=''):
        return self.result(_uuid, 0, msg, '')

    def result(self, _uuid, code=0, out='', err=''):
        self._remove_terminate(_uuid)
        result = {'exitcode': code, 'out': out, 'err': err}
        self._set_result(_uuid, result)
        return result

    """
    Constructor should be overriden to set lpi id plus i.e. to parse config,
    just don't forget to call super().__init__ before your code
    """

    def __init__(self, lpi_cfg=None, phi_id=None):
        self.phi = get_phi(phi_id)
        if lpi_cfg:
            self.lpi_cfg = lpi_cfg
        else:
            self.lpi_cfg = {}
        self.__terminate = {}
        self.__action_results = {}
        self.__terminate_lock = threading.Lock()
        self.__action_results_lock = threading.Lock()
        self.lpi_id = 'generic'
        self.io_label = lpi.cfg.get('io_label') if lpi_cfg.get(
            'io_label') else 'port'

    """
    DO NOT OVERRIDE THE FUNCTIONS BELOW
    """

    def state(self, cfg=None, multi=False, timeout=None, state_in=None):
        if not self.phi:
            logging.error(
                'lpi %s has no phi assigned' % self.lpi_id.split('.')[-1])
            return None
        return self.do_state(cfg, multi, timeout, state_in)

    def action(self, _uuid, status=None, value=None, cfg=None, timeout=None):
        if not self.phi:
            logging.error(
                'lpi %s has no phi assigned' % self.lpi_id.split('.')[-1])
            return None
        self._append_terminate(_uuid)
        self._set_result(_uuid)
        return self.do_action(_uuid, status, value, cfg, timeout)

    def terminate(self, _uuid):
        if not self.__terminate_lock.acquire(timeout=get_timeout()):
            logging.critical('GenericLPI::terminate locking broken')
            critical()
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
            logging.critical('GenericLPI::_append_terminate locking broken')
            critical()
            return None
        self.__terminate[_uuid] = threading.Event()
        self.__terminate_lock.release()
        return True

    def _remove_terminate(self, _uuid):
        if not self.__terminate_lock.acquire(timeout=get_timeout()):
            logging.critical('GenericLPI::_remove_terminate locking broken')
            critical()
            return None
        try:
            del (self.__terminate[_uuid])
        except:
            self.__terminate_lock.release()
            return False
        self.__terminate_lock.release()
        return True

    def _set_result(self, _uuid, result=None):
        if not self.__action_results_lock.acquire(timeout=get_timeout()):
            logging.critical('GenericLPI::_set_result locking broken')
            critical()
            return None
        self.__action_results[_uuid] = result
        self.__action_results_lock.release()
        return True

    def clear_result(self, _uuid):
        if not self.__action_results_lock.acquire(timeout=get_timeout()):
            logging.critical('GenericLPI::clear_result locking broken')
            critical()
            return None
        try:
            del (self.__action_results[_uuid])
        except:
            self.__action_results_lock.release()
            return False
        self.__action_results_lock.release()
        return True

    def get_result(self, _uuid):
        if not self.__action_results_lock.acquire(timeout=get_timeout()):
            logging.critical('GenericLPI::get_result locking broken')
            critical()
            return None
        result = self.__action_results.get(_uuid)
        self.__action_results_lock.release()
        return result
