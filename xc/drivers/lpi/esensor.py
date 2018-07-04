__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "Enhanced sensor LPI"
__api__ = 1

__id__ = 'basic'
__logic__ = 'basic status on/off'

from time import time

import logging

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
        # 1 - skip sensor errors (log error and continue)
        # 0 - if one sensor in a group failed, stop polling others
        #
        # may be overriden with skip_errors param in a state request cfg
        self.on_err = self.lpi_cfg.get('on_err') if \
                self.lpi_cfg.get('on_err') is not None else 'skip'
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
        # different from avg on maxdiff. Setting variable to 'skip' disables
        # this feature
        try:
            self.maxdiff = float(self.lpi_cfg.get('maxdiff'))
        except:
            self.maxdiff = 'skip'

    def do_state(self, _uuid, cfg, timeout, tki, state_in):
        time_start = time()
        _state_in = state_in
        if cfg is None or cfg.get(self.io_label) is None:
            return self.state_result_error(_uuid)
        if self.phi.all_at_once and not _state_in:
            _state_in = self.phi.get(timeout=timeout)
        on_err = cfg.get('on_err') if \
                cfg.get('on_err') is not None else self.on_err
        gpf = cfg.get('gpf') if \
                cfg.get('gpf') is not None else self.gpf
        maxdiff = cfg.get('maxdiff') if \
                cfg.get('maxdiff') is not None else self.maxdiff
        try:
            maxdiff = float(maxdiff)
        except:
            maxdiff = self.maxdiff
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
            st_arr = []
            st_ports = []
            _status = 0
            for p in pp:
                if _state_in and p in _state_in:
                    value = _state_in.get(p)
                else:
                    value = self.phi.get(
                        p, timeout=(timeout + time_start - time()))
                try:
                    value = float(value)
                except:
                    value = None
                if value is None:
                    if on_error != 'skip':
                        _status = -1
                        break
                    else:
                        logging.error(
                            '%s %s failed to get value' % (self.io_label, p))
                else:
                    st_arr.append(value)
                    st_ports.append(p)
            if _status == -1:
                if multi:
                    st.append(-1, None)
                else:
                    self.set_result(_uuid, (-1, None))
                    return
            else:
                avg = sum(st_arr) / float(len(st_arr))
                _st = st_arr.copy()
                if maxdiff != 'skip':
                    for i in range(0, len(st_arr)):
                        if abs(st_arr[i] - avg) > maxdiff:
                            logging.error(
                                '%s %s may be failed, value is too different' % (self.io_label, st_ports[i]))
                            del st_arr[i]
                if gpf == 'first':
                    value = _st[0]
                elif gpf == 'max':
                    value = max(_st)
                elif gpf == 'min':
                    value = min(_st)
                else:
                    value = sum(_st) / float(len(_st))
                if multi:
                    st.append(1, value)
                else:
                    st = value
        if multi:
            self.set_result(_uuid, st)
        else:
            self.set_result(_uuid, (1, st))
        return

    def do_action(self, _uuid, status, value, cfg, timeout, tki):
        time_start = time()
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
        if self.phi.all_at_once:
            ports_to_set = []
            data_to_set = []
        for p in _port:
            _port, invert = self.need_invert(p)
            if invert:
                _status = 1 - status
            else:
                _status = status
            if self.phi.all_at_once:
                ports_to_set.append(_port)
                data_to_set.append(_status)
            else:
                if not self.phi.set(
                        _port, _status,
                        timeout=(timeout + time_start - time())):
                    return self.action_result_error(
                        _uuid, msg='port %s set error' % _port)
        if self.phi.all_at_once:
            if not self.phi.set(ports_to_set, data_to_set, timeout=timeout):
                return self.action_result_error(_uuid, msg='ports set error')
        return self.action_result_ok(_uuid)
