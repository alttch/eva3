__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"
__description__ = "Emulates virtual sensors"

__equipment__ = 'virtual'
__api__ = 9
__required__ = ['port_get', 'value']
__mods_required__ = []
__lpi_default__ = 'sensor'
__features__ = ['aao_get', 'push']
__config_help__ = [{
    'name': 'default_value',
    'help': 'sensors value on load (default: None)',
    'type': 'float',
    'required': False
}, {
    'name': 'auto_modify',
    'help': '"randomize" or "increment"',
    'type': 'str',
    'required': False
}]
__get_help__ = []
__set_help__ = []
__help__ = """
Simple virtual sensor controller, may be used for the various tests/debugging.
When loaded, simulates sensors with ports 1000..1015, which may be extended,
also any labels for the sensors (including strings) may be used. Virtual
sensors can be set to float values only.
"""

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import handle_phi_event
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import critical
from eva.uc.driverapi import phi_constructor

import eva.benchmark
import threading


class PHI(GenericPHI):

    @phi_constructor
    def __init__(self, **kwargs):
        self.auto_modify = self.phi_cfg.get('auto_modify')
        self.data_lock = threading.RLock()
        d = self.phi_cfg.get('default_value')
        if d is None:
            d = None
        else:
            try:
                d = float(d)
            except:
                d = None
        self.data = {}
        if self.auto_modify == 'increment' and d is None:
            d = 0
        for i in range(1000, 1016):
            self.data[str(i)] = d

    def get_ports(self):
        return self.generate_port_list(port_min=1000,
                                       port_max=1015,
                                       description='virtual sensor port #{}')

    def get(self, port=None, cfg=None, timeout=0):
        if not port:
            if self.auto_modify:
                if self.auto_modify == 'randomize':
                    import random
                    with self.data_lock:
                        for d in self.data:
                            self.data[d] = random.randint(1, 1000000000)
                elif self.auto_modify == 'increment':
                    with self.data_lock:
                        for d in self.data:
                            self.data[d] += 1
                            if self.data[d] > 1000000000:
                                self.data[d] = 0
            return self.data
        try:
            if self.auto_modify:
                if self.auto_modify == 'randomize':
                    import random
                    self.data[str(port)] = random.randint(1, 1000000000)
                elif self.auto_modify == 'increment':
                    k = str(port)
                    v = self.data[k] + 1
                    if v > 1000000000:
                        v = 0
                    self.data[k] = v
            return self.data[str(port)]
        except:
            return None

    def push_state(self, payload):
        if payload == 'test':
            return True
        else:
            for port, v in payload.items():
                try:
                    if port in self.data:
                        self.data[port] = v
                    else:
                        raise LookupError(f'Port {port} not found')
                except:
                    log_traceback()
                    return False
            return True

    def validate_config(self, config={}, config_type='config'):
        self.validate_config_whi(config=config,
                                 config_type=config_type,
                                 xparams=[{
                                     'name': 'event_on_test_set',
                                     'type': 'bool'
                                 }])
        if config.get('auto_modify') not in [None, 'randomize', 'increment']:
            raise ValueError('Invalid auto_modify value')

    def test(self, cmd=None):
        if cmd == 'self':
            return 'OK'
        if cmd == 'get':
            return self.get()
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
            self.log_debug('%s test completed, set port %s=%s' %
                           (self.phi_id, port, val))
            if self.phi_cfg.get('event_on_test_set'):
                handle_phi_event(self, port, self.data)
            return self.data
        except:
            return {
                'get': 'get sensors values',
                'X=S': 'set sensor port X to S'
            }
