__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "Basic LPI for simple devices"
__api__ = 1

__id__ = 'basic'

import threading
from eva.uc.drivers.lpi.generic_lpi import LPI as GenericLPI


class LPI(GenericLPI):

    def __init__(self, lpi_cfg=None, phi_id=None):
        super().__init__(lpi_cfg, phi_id)
        self.lpi_mod_id = __id__
        self.author = __author__
        self.license = __license__
        self.description = __description__
        self.version = __version__
        self.api_version = __api__
        self.lpi_mod_id = __id__

    def do_state(self, _uuid, cfg, multi, timeout, tki, state_in):
        if cfg is None or cfg.get(self.io_label) is None:
            return self.state_result_error(_uuid)
        port = cfg.get(self.io_label)
        if not isinstance(port, list):
            _port = [port]
        else:
            _port = port
        if multi:
            st = []
        else:
            st = None
        for p in _port:
            _p, invert = self.need_invert(p)
            if state_in and _p in state_in:
                status = state_in.get(_p)
            else:
                print(_p, invert)
                status = self.phi.get(_p, timeout=timeout)
                print(status)
            if status is None or status not in [0, 1]:
                if multi:
                    st.append((-1, None))
                    continue
                else:
                    self.set_result(_uuid, (-1, None))
                    return
            if invert:
                _status = 1 - status
            else:
                _status = status
            if multi:
                st.append((_status, None))
            else:
                if st is None:
                    st = _status
                else:
                    if st != _status:
                        self.set_result(_uuid, (-1, None))
                        return
        if multi:
            self.set_result(_uuid, st)
        else:
            self.set_result(_uuid, (st, None))
        return

    def do_action(self, _uuid, status, value, cfg, timeout, tki):
        if cfg is None:
            return self.action_result_error(_uuid, 1, 'no config specified')
        if status is None:
            return self.action_result_error(_uuid, 1, 'no status specified')
        port = cfg.get(self.io_label)
        if port is None:
            return self.action_result_error(
                _uuid, 1, 'no ' + self.io_label + ' in config')
        try:
            status = int(status)
        except:
            return self.action_result_error(_uuid, msg='status is not integer')
        if status not in [0, 1]:
            return self.action_result_error(
                _uuid, msg='status is not in range 0..1')
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
                return self.action_result_error(
                    _uuid, msg='port %s set error' % _port)
        return self.action_result_ok(_uuid)
