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
        # skip - skip sensor errors (log error and continue)
        # otherwise if one sensor in a group failed, stop polling others
        #
        # may be overriden with skip_errors param in a state request cfg
        self.on_err = self.lpi_cfg.get('on_err') if \
                self.lpi_cfg.get('on_err') is not None else ''
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
            self.max_diff = 'skip'

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
                    if on_err != 'skip':
                        _status = -1
                        break
                    else:
                        logging.error(
                            '%s %s failed to get value' % (self.io_label, p))
                else:
                    st_arr.append(value)
                    st_ports.append(p)
            if _status == -1 or not st_arr:
                if multi:
                    st.append((-1, None))
                else:
                    self.set_result(_uuid, (-1, None))
                    return
            else:
                broken = False
                if max_diff != 'skip' and len(st_arr) > 1:
                    for i in range(0, len(st_arr)):
                        _s = st_arr.copy()
                        del _s[i]
                        _avg = sum(_s) / float(len(_s))
                        if abs(st_arr[i] - _avg) > max_diff:
                            if len(st_arr) == 2:
                                logging.error(
                                'one %s of %s failed' %
                                (self.io_label, ', '.join(st_ports)) + \
                                '  - value is too different')
                                if multi:
                                    _status = -1
                                    break
                                else:
                                    self.set_result(_uuid, (-1, None))
                                    return
                            else:
                                broken = True
                if broken:
                    diffs = []
                    for i in range(0, len(st_arr)):
                        diff = 0
                        for i2 in range(0, len(st_arr)):
                            if i != i2: diff += abs(st_arr[i2] - st_arr[i])
                        diffs.append(diff)
                    bi = diffs.index(max(diffs))
                    logging.error('%s %s seems to be failed' %
                    (self.io_label, st_ports[bi]) + ' - value is too different')
                    del st_arr[bi]
                if _status == -1 or not st_arr:
                    if multi:
                        st.append((-1, None))
                        continue
                    else:
                        self.set_result(_uuid, (-1, None))
                        return
                if gpf == 'first':
                    value = st_arr[0]
                elif gpf == 'max':
                    value = max(st_arr)
                elif gpf == 'min':
                    value = min(st_arr)
                else:
                    value = sum(st_arr) / float(len(st_arr))
                if multi:
                    st.append((1, value))
                else:
                    st = value
        if multi:
            self.set_result(_uuid, st)
        else:
            self.set_result(_uuid, (1, st))
        return
