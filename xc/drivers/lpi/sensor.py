__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "Basic sensor LPI"
__api__ = 1

__id__ = 'sensor'
__logic__ = 'single polling'

__features__ = ['value', 'mu_value', 'port_get', 'aao_get', 'cfg', 'events']

__config_help__ = []

__action_help__ = []

__state_help__ = [{
    'name': 'port',
    'help': 'port(s) to use',
    'type': 'str',
    'required': True
}]

__state_help__ += __config_help__

__help__ = """
Basic LPI to work with sensors, doesn't process sensor value in any way,
returning it to controller as-is. """

from time import time

from eva.uc.drivers.lpi.generic_lpi import LPI as GenericLPI

from eva.tools import val_to_boolean


class LPI(GenericLPI):

    def __init__(self, lpi_cfg=None, phi_id=None, info_only=False):
        super().__init__(lpi_cfg, phi_id, info_only)
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
        # if info_only: return

    def do_state(self, _uuid, cfg, timeout, tki, state_in):
        time_start = time()
        _state_in = state_in
        if _state_in: evh = True
        else: evh = False
        if cfg is None or cfg.get(self.io_label) is None:
            return self.state_result_error(_uuid)
        phi_cfg = self.prepare_phi_cfg(cfg)
        if self.phi.aao_get and not _state_in:
            _state_in = self.phi.get(cfg=phi_cfg, timeout=timeout)
            if not _state_in: return self.state_result_error(_uuid)
        port = cfg.get(self.io_label)
        if not isinstance(port, list):
            _port = [port]
            multi = False
        else:
            _port = port
            multi = True
        st = []
        for p in _port:
            if _state_in:
                value = _state_in.get(str(p))
            else:
                value = self.phi.get(
                    str(p), phi_cfg, timeout + time_start - time())
            if value is None and evh:
                if multi:
                    st.append(False)
                    continue
                else:
                    return self.state_result_skip(_uuid)
            if value is None:
                if multi:
                    st.append((-1, None))
                    continue
                else:
                    return self.state_result_error(_uuid)
            if multi:
                st.append((1, value))
            else:
                st = value
        if multi:
            self.set_result(_uuid, st)
        else:
            self.set_result(_uuid, (1, st))
        return
