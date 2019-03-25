__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.1.0"
__description__ = "Emulates 16-port relay"

__equipment__ = 'virtual'
__api__ = 4
__required__ = ['port_get', 'port_set']
__mods_required__ = []
__lpi_default__ = 'basic'
__features__ = ['port_get', 'port_set', 'aao_set', 'aao_get']
__config_help__ = [{
    'name': 'default_status',
    'help': 'ports status on load (default: -1)',
    'type': 'int',
    'required': False
}]
__get_help__ = []
__set_help__ = []
__help__ = """
Simple 16-port virtual relay, may be used for the various tests/debugging.
"""

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import handle_phi_event
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import phi_constructor

import eva.benchmark
from eva.uc.controller import register_benchmark_handler
from eva.uc.controller import unregister_benchmark_handler

class PHI(GenericPHI):

    @phi_constructor
    def __init__(self, **kwargs):
        d = self.phi_cfg.get('default_status')
        if d is None: d = -1
        else:
            try:
                d = int(d)
            except:
                d = -1
        self.data = {}
        for i in range(1, 17):
            self.data[str(i)] = d

    def get(self, port=None, cfg=None, timeout=0):
        # if self.aao_get: return self.data
        if not port: return self.data
        try:
            return self.data.get(str(port))
        except:
            return None

    def set(self, port=None, data=None, cfg=None, timeout=0):
        if isinstance(port, list):
            ports = port
            multi = True
        else:
            ports = [port]
            multi = False
        for i in range(0, len(ports)):
            p = ports[i]
            _port = str(p)
            if multi:
                d = data[i]
            else:
                d = data
            try:
                _data = int(d)
            except:
                return False
            if not _port in self.data:
                return False
            self.data[_port] = _data
            eva.benchmark.report('ACTION', _data, end=True)

        if self.phi_cfg.get('event_on_set'):
            handle_phi_event(self.phi_id, port, self.data)
        return True

    def test(self, cmd=None):
        if cmd == 'self':
            return 'OK'
        if cmd == 'get':
            return self.data
        if cmd == 'critical':
            self.log_critical('test')
            return True
        if cmd == 'start_benchmark':
            eva.benchmark.enabled = True
            register_benchmark_handler()
            eva.benchmark.reset()
            return 'OK'
        if cmd == 'stop_benchmark':
            eva.benchmark.enabled = False
            unregister_benchmark_handler()
            return 'OK'
        try:
            port, val = cmd.split('=')
            port = int(port)
            val = int(val)
            if port < 1 or port > 16 or val < -1 or val > 1: return None
            self.data[str(port)] = val
            self.log_debug('test set port %s=%s' % (port, val))
            if self.phi_cfg.get('event_on_test_set'):
                handle_phi_event(self, port, self.data)
            return self.data
        except:
            return {'get': 'get relay ports status', 'X=S': 'set port X to S'}
