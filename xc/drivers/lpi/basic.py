__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.3.0"
__description__ = "Basic LPI for simple devices"
__api__ = 9

__logic__ = 'basic status on/off'

__features__ = [
    'status', 'status_mp', 'mu_status', 'mu_status_mp', 'port_get', 'aao_get',
    'action', 'action_mp', 'port_set', 'aao_set', 'events', 'value'
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
port label/number for PHI. 'io_label' prop allows to rename 'port' e.g. to
'socket' for a more fancy unit configuration. Each port may be specified as a
single value or contain an array of values, in this case multiple ports are
used simultaneously.

You may set i: before the port label/number, e.g. i:2, to return/use inverted
port state.
"""

from time import time

from eva.uc.drivers.lpi.generic_lpi import LPI as GenericLPI

import eva.benchmark
import timeouter


class LPI(GenericLPI):

    def do_state(self, _uuid, cfg, timeout, tki, state_in):
        _state_in = state_in
        if _state_in:
            evh = True
        else:
            evh = False
        if cfg is None or cfg.get(self.io_label) is None:
            return self.state_result_error(_uuid)
        phi_cfg = self.prepare_phi_cfg(cfg)
        if self.phi._is_required.aao_get and not _state_in:
            _state_in = self.phi.get(cfg=phi_cfg, timeout=timeouter.get())
            if not _state_in:
                return self.state_result_error(_uuid)
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
            val_prev = None
            for p in pp:
                _p, invert = self.need_invert(p)
                if _state_in:
                    status = _state_in.get(str(_p))
                else:
                    status = self.phi.get(str(_p),
                                          phi_cfg,
                                          timeout=timeouter.get())
                if isinstance(status, tuple):
                    status, value = status
                else:
                    value = None
                try:
                    status = int(status)
                except:
                    status = None
                if status is None and evh:
                    if multi:
                        st_prev = False
                        break
                    else:
                        return self.state_result_skip(_uuid)
                if status is None or (invert and status not in [0, 1]):
                    if multi:
                        st_prev = -1
                        break
                    else:
                        return self.state_result_error(_uuid)
                if invert:
                    _status = 1 - status
                else:
                    _status = status
                if multi:
                    if st_prev is None:
                        st_prev = _status
                        val_prev = value
                    elif st_prev != _status or val_prev != value:
                        st_prev = -1
                        break
                else:
                    if st is None:
                        st = (_status, value)
                    elif st[0] != _status or st[1] != value:
                        self.set_result(_uuid, (-1, None))
                        return
            if multi:
                if st_prev is False:
                    st.append(False)
                else:
                    st.append((st_prev, val_prev))
        self.set_result(_uuid, st)
        return

    def do_action(self, _uuid, status, value, cfg, timeout, tki):
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
        # if status not in [0, 1] and not eva.benchmark.enabled:
        # return self.action_result_error(
        # _uuid, msg='status is not in range 0..1')
        if not isinstance(port, list):
            _port = [port]
        else:
            _port = port
        if self.phi._has_feature.aao_set:
            ports_to_set = []
            data_to_set = []
        for p in _port:
            _port, invert = self.need_invert(p)
            if invert:
                _status = 1 - status
            else:
                _status = status
            state = (_status, value) if self.phi._is_required.value else _status
            if self.phi._has_feature.aao_set:
                ports_to_set.append(_port)
                data_to_set.append(state)
            else:
                set_result = self.phi.set(_port,
                                          state,
                                          phi_cfg,
                                          timeout=timeouter.get())
                if set_result is False or set_result is None:
                    return self.action_result_error(_uuid,
                                                    msg='port %s set error' %
                                                    _port)
        if self.phi._has_feature.aao_set:
            set_result = self.phi.set(ports_to_set,
                                      data_to_set,
                                      timeout=timeouter.get())
            if set_result is False or set_result is None:
                return self.action_result_error(_uuid, msg='ports set error')
        return self.action_result_ok(_uuid)

    def validate_config(self, config={}, config_type='config', **kwargs):
        self.validate_config_whi(config=config,
                                 config_type=config_type,
                                 ignore_private=True,
                                 **kwargs)
