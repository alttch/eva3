__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "Basic LPI for simple devices"
__api__ = 1

import threading
from eva.uc.drivers.lpi.generic_lpi import LPI as GenericLPI


class LPI(GenericLPI):

    def do_state(self, cfg=None, timeout=None):
        if cfg is None: return None, None
        port = cfg.get('port')
        if port is None: return None, None
        if not isinstance(port, list):
            _port = [port]
        else:
            _port = port
        st = None
        for p in _port:
            _p, invert = self.need_invert(p)
            status = self.phi.get(_p, timeout=timeout)
            if status is None or status not in [0, 1]: return -1, None
            if invert:
                _status = 1 - status
            else:
                _status = status
            if st is None:
                st = _status
            else:
                if st != _status:
                    return -1, None
        return st, None

    def do_action(self, _uuid, status, value, cfg, timeout):
        if cfg is None or status is None:
            return self.result_error(_uuid, 1, 'no config specified')
        port = cfg.get('port')
        if port is None:
            return self.result_error(_uuid, 1, 'no ports in config')
        try:
            status = int(status)
        except:
            return self.result_error(_uuid, msg='status is not integer')
        if status not in [0, 1]:
            return self.result_error(_uuid, msg='status is not integer')
        if not isinstance(port, list):
            _port = [port]
        else:
            _port = port
        for p in _port:
            _port, invert = self.need_invert(p)
            if invert:
                _status = 1 - status
            else:
                _status = status
            if not self.phi.set(_port, _status, timeout=timeout):
                return self.result_error(_uuid, msg='port %s set error' % _port)
        return self.result_ok(_uuid)
