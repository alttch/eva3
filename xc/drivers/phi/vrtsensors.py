__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.2.0"
__description__ = "Emulates virtual sensors"

__equipment__ = 'virtual'
__api__ = 4
__required__ = ['port_get', 'value']
__mods_required__ = []
__lpi_default__ = 'sensor'
__features__ = ['aao_get']
__config_help__ = [{
    'name': 'default_value',
    'help': 'sensors value on load (default: None)',
    'type': 'float',
    'required': False
}]
__get_help__ = []
__set_help__ = []
__help__ = """
Simple virtual sensor controller, may be used for the various tests/debugging.
When loaded, simulates sensors with ports 1000..1010, which may be extended,
also any labels for the sensors (including strings) may be used. Virtual
sensors can be set to float values only.
"""

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import handle_phi_event
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import critical
from eva.uc.driverapi import phi_constructor

import eva.benchmark


class PHI(GenericPHI):

    @phi_constructor
    def __init__(self, **kwargs):
        d = self.phi_cfg.get('default_value')
        if d is None: d = None
        else:
            try:
                d = float(d)
            except:
                d = None
        self.data = {}
        for i in range(1000, 1011):
            self.data[str(i)] = d

    def get_ports(self):
        return self.generate_port_list(
            port_min=1000, port_max=1010, description='virtual sensor port #{}')

    def get(self, port=None, cfg=None, timeout=0):
        if not port: return self.data
        try:
            return self.data.get(str(port))
        except:
            return None

    def test(self, cmd=None):
        if cmd == 'self':
            return 'OK'
        if cmd == 'get':
            return self.data
        if cmd == 'critical':
            self.log_critical('test')
            return True
        try:
            port, val = cmd.split('=')
            try:
                val = float(val)
                eva.benchmark.report('UPDATE', val)
                self.data[port] = val
            except:
                self.data[port] = val
            self.log_debug(
                '%s test completed, set port %s=%s' % (self.phi_id, port, val))
            if self.phi_cfg.get('event_on_test_set'):
                handle_phi_event(self, port, self.data)
            return self.data
        except:
            return {
                'get': 'get sensors values',
                'X=S': 'set sensor port X to S'
            }
