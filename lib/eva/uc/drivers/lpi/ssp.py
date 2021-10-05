__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.2"
__description__ = "Single port sensor LPI"
__api__ = 9

__logic__ = 'single port'

__features__ = ['value', 'port_get', 'events', 'ssp']

__config_help__ = []

__action_help__ = []

__state_help__ = []

__state_help__ += __config_help__

__help__ = """
LPI to work with sensor PHIs which provide state for single sensor only
(port=1), doesn't process sensor value in any way, returning it to controller
as-is. """

from time import time
import timeouter

from eva.uc.drivers.lpi.generic_lpi import LPI as GenericLPI

from eva.tools import val_to_boolean


class LPI(GenericLPI):

    def do_state(self, _uuid, cfg, timeout, tki, state_in):
        _state_in = state_in
        if _state_in:
            evh = True
        else:
            evh = False
        phi_cfg = self.prepare_phi_cfg(cfg)
        if _state_in:
            value = _state_in.get(list(_state_in)[0])
        else:
            value = self.phi.get(cfg=phi_cfg, timeout=timeouter.get())
            if isinstance(value, dict):
                value = value.get(list(value)[0])
        if value is None and evh:
            return self.state_result_skip(_uuid)
        if value is None or value is False:
            return self.state_result_error(_uuid)
        self.set_result(_uuid, (1, str(value)))
        return

    def validate_config(self, config={}, config_type='config', **kwargs):
        self.validate_config_whi(config=config,
                                 config_type=config_type,
                                 ignore_private=True,
                                 **kwargs)
