__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.1"
__description__ = "Enhanced sensor LPI"
__api__ = 9

__logic__ = 'single and group polling'

__features__ = [
    'value', 'value_mp', 'mu_value', 'mu_value_mp', 'port_get', 'aao_get',
    'cfg', 'events'
]

__config_help__ = [{
    'name': 'skip_err',
    'help': 'skips failed sensor in a group',
    'type': 'bool',
    'required': False
}, {
    'name': 'gpf',
    'help': 'avg, max, min, first - group function',
    'type': 'enum:str:avg,max,min,first',
    'required': False
}, {
    'name': 'max_diff',
    'help': 'maximum value diff until marked as failed',
    'type': 'float',
    'required': False,
}]

__action_help__ = []

__state_help__ = [{
    'name': 'port',
    'help': 'port(s) to use',
    'type': 'str',
    'required': True
}]

__state_help__ += __config_help__

__help__ = """
Enhanced LPI to work with groups of sensors, supports various typical
functions: working with a sensor groups, returning the average, max or min
group value etc. Can use 'max_diff' param to control the maximum difference of
the sensor value in a group and automatically remove possible broken sensors
from the result (if the number of good sensors in a group is more than broken).

For multiupdates all ports specified in mu should be lists.

This LPI is dedicated to work with a groups of sensors and doesn't support
single sensor event processing.
"""

from time import time
import timeouter

from eva.uc.drivers.lpi.generic_lpi import LPI as GenericLPI

from eva.tools import val_to_boolean

from eva.uc.driverapi import lpi_constructor


class LPI(GenericLPI):

    @lpi_constructor
    def __init__(self, **kwargs):
        # skip - skip sensor errors (log error and continue)
        # otherwise if one sensor in a group failed, stop polling others
        #
        # may be overriden with skip_errors param in a state request cfg
        self.skip_err = val_to_boolean(self.lpi_cfg.get('skip_err'))
        # when polling a sensor group
        # avg - return avg sensor value
        # max - return max sensor value
        # min - return min sensor value
        # first - return first sensor value unless it's failed
        #
        # may be overriden with gpf param in a state request cfg
        self.gpf = self.lpi_cfg.get('gpf') if \
                self.lpi_cfg.get('gpf') is not None else 'avg'
        # when polling a sensor group, mark sensor as broken if its value is
        # different from avg on max_diff. Setting variable to 'skip' disables
        # this feature
        try:
            self.max_diff = float(self.lpi_cfg.get('max_diff'))
        except:
            self.max_diff = None

    def do_state(self, _uuid, cfg, timeout, tki, state_in):
        # we don't handle events
        if state_in:
            return self.state_result_error(_uuid)
        if cfg is None or cfg.get(self.io_label) is None:
            return self.state_result_error(_uuid)
        phi_cfg = self.prepare_phi_cfg(cfg)
        if self.phi._is_required.aao_get:
            _state_in = self.phi.get(cfg=phi_cfg, timeout=timeouter.get())
            if not _state_in:
                return self.state_result_error(_uuid)
        else:
            _state_in = {}
        skip_err = val_to_boolean(cfg.get('skip_err')) if \
                cfg.get('skip_err') is not None else self.skip_err
        gpf = cfg.get('gpf') if \
                cfg.get('gpf') is not None else self.gpf
        max_diff = cfg.get('max_diff') if \
                cfg.get('max_diff') is not None else self.max_diff
        try:
            max_diff = float(max_diff)
        except:
            max_diff = self.max_diff
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
        else:
            _port = [_port]
        if multi:
            st = []
        else:
            st = None
        for pi in _port:
            if isinstance(pi, list):
                pp = pi
            else:
                pp = [pi]
            st_arr = []
            st_ports = []
            _status = 1
            for p in pp:
                if _state_in and str(p) in _state_in:
                    value = _state_in.get(str(p))
                else:
                    value = self.phi.get(str(p),
                                         phi_cfg,
                                         timeout=timeouter.get())
                try:
                    value = float(value)
                except:
                    value = None
                if value is None:
                    if not skip_err:
                        _status = -1
                        break
                    else:
                        self.log_error('%s %s failed to get value' %
                                       (self.io_label, p))
                else:
                    st_arr.append(value)
                    st_ports.append(str(p))
            if max_diff and _status != -1 and len(st_arr) > 1:
                _st_ports = st_ports.copy()
                while True:
                    diver = False
                    for i in range(0, len(st_arr)):
                        _s = st_arr.copy()
                        del _s[i]
                        _avg = sum(_s) / float(len(_s))
                        if abs(st_arr[i] - _avg) > max_diff:
                            if len(st_arr) == 2:
                                self.log_error(
                                'one %s of %s failed' %
                                (self.io_label, ', '.join(_st_ports)) + \
                                '  - value is too different')
                                if multi:
                                    _status = -1
                                    break
                                else:
                                    return self.state_result_error(_uuid)
                            else:
                                diver = True
                                break
                    if diver and _status != -1:
                        diffs = []
                        for i in range(0, len(st_arr)):
                            diff = 0
                            for i2 in range(0, len(st_arr)):
                                if i != i2:
                                    diff += abs(st_arr[i2] - st_arr[i])
                            diffs.append(diff)
                        bi = diffs.index(max(diffs))
                        self.log_error('%s %s seems to be failed' %
                                       (self.io_label, st_ports[bi]) +
                                       ' - value is too different')
                        del st_arr[bi]
                        del st_ports[bi]
                    else:
                        break
            if _status == -1 or not st_arr:
                if multi:
                    st.append((-1, None))
                    continue
                else:
                    return self.state_result_error(_uuid)
            if gpf == 'first':
                value = st_arr[0]
            elif gpf == 'max':
                value = max(st_arr)
            elif gpf == 'min':
                value = min(st_arr)
            else:
                value = sum(st_arr) / float(len(st_arr))
            if multi:
                st.append((1, str(value)))
            else:
                st = str(value)
        if multi:
            self.set_result(_uuid, st)
        else:
            self.set_result(_uuid, (1, st))
        return

    def validate_config(self, config={}, config_type='config', **kwargs):
        self.validate_config_whi(config=config,
                                 config_type=config_type,
                                 ignore_private=True,
                                 **kwargs)
