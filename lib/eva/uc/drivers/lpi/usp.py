__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.2"
__description__ = "Single port unit LPI"
__api__ = 9

__logic__ = 'single port, basic status on/off'

__features__ = [
    'status', 'port_get', 'port_set', 'events', 'usp', 'value', 'action'
]

__config_help__ = []

__action_help__ = []

__state_help__ = []

__state_help__ += __config_help__

__help__ = """
LPI to work with unit PHIs which provide/manage state for single unit only
(port=1), doesn't process unit status in any way, returning it to controller
as-is. For unit actions port is not required, however LPI sets it to 1 when
transmitting to PHIs.
"""

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
            status = _state_in.get(list(_state_in)[0])
        else:
            status = self.phi.get(1, cfg=phi_cfg, timeout=timeouter.get())
        if isinstance(status, dict):
            status = status.get(list(status)[0])
        if isinstance(status, tuple):
            status, value = status
        else:
            value = None
        if status is None and evh:
            return self.state_result_skip(_uuid)
        if status is None or status is False:
            return self.state_result_error(_uuid)
        self.set_result(_uuid, (status, value))
        return

    def do_action(self, _uuid, status, value, cfg, timeout, tki):
        phi_cfg = self.prepare_phi_cfg(cfg)
        if status is None:
            return self.action_result_error(_uuid, 1, 'no status provided')
        try:
            status = int(status)
        except:
            return self.action_result_error(_uuid, msg='status is not integer')
        # if status not in [0, 1]:
        # return self.action_result_error(
        # _uuid, msg='status is not in range 0..1')
        _port = 1
        if self.phi._is_required.value:
            state = status, value
        else:
            state = status
        set_result = self.phi.set(_port,
                                  state,
                                  phi_cfg,
                                  timeout=timeouter.get())
        if set_result is False or set_result is None:
            return self.action_result_error(_uuid,
                                            msg='port %s set error' % _port)
        return self.action_result_ok(_uuid)

    def validate_config(self, config={}, config_type='config', **kwargs):
        self.validate_config_whi(config=config,
                                 config_type=config_type,
                                 ignore_private=True,
                                 **kwargs)
