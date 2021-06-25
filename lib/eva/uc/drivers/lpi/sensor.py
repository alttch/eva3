__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"
__description__ = "Basic sensor LPI"
__api__ = 9

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
import timeouter

from eva.uc.drivers.lpi.generic_lpi import LPI as GenericLPI

from eva.tools import val_to_boolean


class LPI(GenericLPI):

    def do_state(self, _uuid, cfg, timeout, tki, state_in):
        _state_in = state_in
        # for events - skip update if PHI not provided any value
        if _state_in:
            evh = True
        else:
            evh = False
        if cfg is None or cfg.get(self.io_label) is None:
            return self.state_result_error(_uuid)
        phi_cfg = self.prepare_phi_cfg(cfg)
        if self.phi._is_required.aao_get and not _state_in:
            _state_in = self.phi.get(cfg=phi_cfg, timeout=timeout)
            if not _state_in:
                return self.state_result_error(_uuid)
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
                value = self.phi.get(str(p), phi_cfg, timeouter.get())
            if value is None and evh:
                if multi:
                    st.append(False)
                    continue
                else:
                    return self.state_result_skip(_uuid)
            if value is None or value is False:
                if multi:
                    st.append((-1, None))
                    continue
                else:
                    return self.state_result_error(_uuid)
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
