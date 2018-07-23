__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "Denkovi ModBus relay DAE-RO16"

__id__ = 'dae_ro16_modbus'
__equipment__ = 'DAE-RO16-MODBUS'
__api__ = 1
__required__ = ['aao_get', 'port_set', 'status', 'action']
__mods_required__ = []
__lpi_default__ = 'basic'
__features__ = ['aao_get', 'port_set']
__config_help__ = [{
    'name': 'port',
    'help': 'ModBus port ID',
    'tyoe': 'str',
    'required': True
}, {
    'name': 'unit',
    'help': 'modbus unit ID',
    'type': 'int',
    'required': True
}]
__get_help__ = []
__set_help__ = []

__help__ = """
PHI for Denkovi DAE-RO16-MODBUS relay. ModBus port should be created in UC
before loading. Uses coils for the relay state control/monitoring.
"""

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import get_timeout

import eva.uc.modbus as modbus


class PHI(GenericPHI):

    def __init__(self, phi_cfg=None, info_only=False):
        super().__init__(phi_cfg=phi_cfg, info_only=info_only)
        self.phi_mod_id = __id__
        self.__author = __author__
        self.__license = __license__
        self.__description = __description__
        self.__version = __version__
        self.__api_version = __api__
        self.__equipment = __equipment__
        self.__features = __features__
        self.__required = __required__
        self.__mods_required = __mods_required__
        self.__lpi_default = __lpi_default__
        self.__config_help = __config_help__
        self.__get_help = __get_help__
        self.__set_help = __set_help__
        self.__help = __help__
        if info_only: return
        self.aao_get = True
        self.port_max = 16
        self.modbus_port = self.phi_cfg.get('port')
        if not modbus.is_port(self.modbus_port):
            self.log_error('modbus port ID not specified or invalid')
            self.ready = False
            return
        try:
            self.unit_id = int(self.phi_cfg.get('unit'))
        except:
            self.log_error('modbus unit ID not specified or invalid')
            self.ready = False
            return

    def get(self, port=None, cfg=None, timeout=0):
        mb = modbus.get_port(self.modbus_port, timeout)
        if not mb: return None
        rr = mb.read_coils(0, 16, unit=self.unit_id)
        mb.release()
        if rr.isError(): return None
        result = {}
        try:
            for i in range(16):
                result[str(i + 1)] = 1 if rr.bits[i] else 0
        except:
            result = None
        mb.release()
        return result

    def set(self, port=None, data=None, cfg=None, timeout=0):
        try:
            port = int(port)
            val = int(data)
        except:
            return False
        if port < 1 or port > self.port_max or val < 0 or val > 1: return False
        mb = modbus.get_port(self.modbus_port, timeout)
        if not mb: return None
        result = mb.write_coil(
            port - 1, True if val else False, unit=self.unit_id)
        mb.release()
        return not result.isError()

    def test(self, cmd=None):
        if cmd == 'self':
            mb = modbus.get_port(self.modbus_port)
            if not mb: return 'FAILED'
            mb.release()
            return 'OK'
        if cmd == 'info':
            mb = modbus.get_port(self.modbus_port)
            if not mb: return 'FAILED'
            if mb.client_type in ['tcp', 'udp']:
                reg = 22
            else:
                reg = 21
            rr = mb.read_holding_registers(reg, 1, unit=self.unit_id)
            mb.release()
            if rr.isError(): return 'FAILED'
            try:
                return '{:.2f}'.format(float(rr.registers[0]) / 100.0)
            except:
                log_traceback()
                return 'FAILED'
        if cmd == 'get': return self.get(timeout=get_timeout() * 10)
        return {
            'info': 'returns relay firmware version',
            'get': 'get current relay state'
        }
