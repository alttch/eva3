__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "Basic LPI for simple devices"
__api__ = 1

__id__ = 'basic'
__logic__ = 'basic status on/off'

__features__ = [
    'status', 'status_mp', 'mu_status', 'mu_status_mp', 'port_get', 'aao_get',
    'action', 'action_mp', 'port_set', 'aao_set'
]

__config_help__ = []

__action_help__ = [{
    'name': 'port',
    'help': 'port(s) to use',
    'type': 'str',
    'required': True
}]

__state_help__ = [{
    'name': 'port',
    'help': 'port(s) to use',
    'type': 'str',
    'required': True
}]

__help__ = """
Basic LPI for simple unit status control (on/off) and monitoring. Support
status 0 and 1. Unit driver config fields should have property 'port' with a
port label/number for PHI. 'io_label' prop allows to rename 'port' i.e. to
'socket' for a more fancy unit configuration. Each port may be specified as a
single value or contain an array of values, in this case multiple ports are
used simultaneously.
"""

from time import time

from eva.uc.drivers.lpi.generic_lpi import LPI as GenericLPI


class LPI(GenericLPI):

    def __init__(self, lpi_cfg=None, phi_id=None):
        super().__init__(lpi_cfg, phi_id)
        self.lpi_mod_id = __id__
        self.__author = __author__
        self.__license = __license__
        self.__description = __description__
        self.__version = __version__
        self.__api_version = __api__
        self.__lpi_mod_id = __id__
        self.__logic = __logic__
        self.__features = __features__
        self.__config_help = __config_help__
        self.__action_help = __action_help__
        self.__state_help = __state_help__
        self.__help = __help__

    def do_state(self, _uuid, cfg, timeout, tki, state_in):
        time_start = time()
        _state_in = state_in
        if cfg is None or cfg.get(self.io_label) is None:
            return self.state_result_error(_uuid)
        phi_cfg = self.prepare_phi_cfg(cfg)
        if self.phi.aao_get and not _state_in:
            _state_in = self.phi.get(timeout=(timeout + time_start - time()))
        port = cfg.get(self.io_label)
        if not isinstance(port, list):
            _port = [port]
        else:
            _port = port
        multi = False
        for p in _port:
            if isinstance(p, list):
                multi = True
                break
        if multi:
            st = []
        else:
            st = None
        for pi in _port:
            if isinstance(pi, list):
                pp = pi
            else:
                pp = [pi]
            st_prev = None
            for p in pp:
                _p, invert = self.need_invert(p)
                if _state_in and _p in _state_in:
                    status = _state_in.get(_p)
                else:
                    status = self.phi.get(_p, phi_cfg,
                                          timeout + time_start - time())
                if status is None or status not in [0, 1]:
                    if multi:
                        st_prev = -1
                        break
                    else:
                        self.set_result(_uuid, (-1, None))
                        return
                if invert:
                    _status = 1 - status
                else:
                    _status = status
                if multi:
                    if st_prev is None:
                        st_prev = _status
                    elif st_prev != _status:
                        st_prev = -1
                        break
                else:
                    if st is None:
                        st = _status
                    elif st != _status:
                        self.set_result(_uuid, (-1, None))
                        return
            if multi:
                st.append((st_prev, None))
        if multi:
            self.set_result(_uuid, st)
        else:
            self.set_result(_uuid, (st, None))
        return

    def do_action(self, _uuid, status, value, cfg, timeout, tki):
        time_start = time()
        if cfg is None:
            return self.action_result_error(_uuid, 1, 'no config provided')
        phi_cfg = self.prepare_phi_cfg(cfg)
        if status is None:
            return self.action_result_error(_uuid, 1, 'no status provided')
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
        if self.phi.aao_set:
            ports_to_set = []
            data_to_set = []
        for p in _port:
            _port, invert = self.need_invert(p)
            if invert:
                _status = 1 - status
            else:
                _status = status
            if self.phi.aao_set:
                ports_to_set.append(_port)
                data_to_set.append(_status)
            else:
                if not self.phi.set(
                        _port,
                        _status,
                        phi_cfg,
                        timeout=(timeout + time_start - time())):
                    return self.action_result_error(
                        _uuid, msg='port %s set error' % _port)
        if self.phi.aao_set:
            if not self.phi.set(ports_to_set, data_to_set, timeout=timeout):
                return self.action_result_error(_uuid, msg='ports set error')
        return self.action_result_ok(_uuid)
