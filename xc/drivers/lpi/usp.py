__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "Single port unit LPI"
__api__ = 1

__id__ = 'usp'
__logic__ = 'single port, basic status on/off'

__features__ = ['status', 'port_get', 'port_set', 'events', 'usp']

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

    def do_state(self, _uuid, cfg, timeout, tki, state_in):
        time_start = time()
        _state_in = state_in
        if _state_in: evh = True
        else: evh = False
        phi_cfg = self.prepare_phi_cfg(cfg)
        if _state_in:
            status = _state_in.get(list(_state_in)[0])
        else:
            status = self.phi.get(1,
                cfg=phi_cfg, timeout=timeout + time_start - time())
            if isinstance(status, dict):
                status = status.get(list(status)[0])
        if status is None and evh:
            return self.state_result_skip(_uuid)
        if status is None or status is False:
            return self.state_result_error(_uuid)
        self.set_result(_uuid, (status, None))
        return

    def do_action(self, _uuid, status, value, cfg, timeout, tki):
        time_start = time()
        phi_cfg = self.prepare_phi_cfg(cfg)
        if status is None:
            return self.action_result_error(_uuid, 1, 'no status provided')
        try:
            status = int(status)
        except:
            return self.action_result_error(_uuid, msg='status is not integer')
        if status not in [0, 1]:
            return self.action_result_error(
                _uuid, msg='status is not in range 0..1')
        _port = 1
        set_result = self.phi.set(
            _port,
            status,
            phi_cfg,
            timeout=(timeout + time_start - time()))
        if set_result is False or set_result is None:
            return self.action_result_error(
                _uuid, msg='port %s set error' % _port)
        return self.action_result_ok(_uuid)
