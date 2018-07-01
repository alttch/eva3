__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "Generic LPI, don't use"
__api__ = 1

import threading
import eva.core
import time


class LPI(object):
    """
    Functions required to be overriden
    """
    """
    Returns item state tuple (status, value)
    Override this function with your own
    """

    def do_state(self, cfg, timeout):
        return -1, None

    """
    Performs item action
    Override this function with your own
    """

    def do_action(self, _uuid, status, value, cfg, timeout):
        return self.result_error(_uuid, msg='do not use this lpi!')

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
        if not isinstance(port, str) or port[0] != 'i': return port, False
        return port[1:], True

    """
    Checks for the terminate call

    Args:
        _uuid - action uuid

    Returns True if the controller requested action termination
    """

    def need_terminate(self, _uuid):
        e = self.__terminate.get(_uuid)
        if not e:
            logging.critical('Driver %s termination engine broken' % __name__)
            eva.core.critical()
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
            time.sleep(eva.core.polldelay)
            i += eva.core.polldelay
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
    Constructor may be overriden i.e. to parse config, just don't forget to
    call super().__init__
    """

    def __init__(self, cfg=None, phi=None):
        self.phi = phi(cfg)
        if cfg:
            self.cfg = cfg.get('pli')
        else:
            self.cfg = {}
        self.__terminate = {}
        self.__action_results = {}

    """
    DO NOT OVERRIDE THE FUNCTIONS BELOW
    """

    def state(self, cfg=None, timeout=None):
        return self.do_state(cfg, timeout)

    def action(self, _uuid, status=None, value=None, cfg=None, timeout=None):
        self._append_terminate(_uuid)
        self._set_result(_uuid)
        return self.do_action(_uuid, status, value, cfg, timeout)

    def terminate(self, _uuid):
        # TODO locking
        t = self.__terminate.get(_uuid)
        if not t: return False
        t.set()
        return True

    def _set_result(self, _uuid, result=None):
        # TODO locking
        self.__action_results[_uuid] = result

    def clear_result(self, _uuid):
        # TODO locking
        try:
            del (self.__action_results[_uuid])
        except:
            return False
        return True

    def get_result(self, _uuid):
        # TODO locking
        result = self.__action_results.get(_uuid)
        return result

    def _append_terminate(self, _uuid):
        # TODO locking
        self.__terminate[_uuid] = threading.Event()

    def _remove_terminate(self, _uuid):
        # TODO locking
        try:
            del (self.__terminate[_uuid])
        except:
            pass
