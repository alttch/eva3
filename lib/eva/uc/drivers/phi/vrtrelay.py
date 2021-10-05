__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.2"
__description__ = "Emulates 16-port relay"

__equipment__ = 'virtual'
__api__ = 9
__required__ = ['port_get', 'port_set', 'action']
__mods_required__ = []
__lpi_default__ = 'basic'
__features__ = ['aao_set', 'aao_get', 'push']
__config_help__ = [{
    'name': 'default_status',
    'help': 'ports status on load (default: 0)',
    'type': 'int',
    'required': False
}, {
    'name': 'state_full',
    'help': 'full state (status/value)',
    'type': 'bool',
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

import time


class PHI(GenericPHI):

    @phi_constructor
    def __init__(self, **kwargs):
        d = self.phi_cfg.get('default_status')
        if self.phi_cfg.get('state_full'):
            self._has_feature.value = True
            self._is_required.value = True
        if d is None:
            d = 0
        else:
            try:
                d = int(d)
            except:
                d = -1
        self.data = {}
        for i in range(1, 17):
            self.data[str(i)] = (d, '') if self._is_required.value else d
        self.simulate_timeout = float(self.phi_cfg.get('simulate_timeout', 0))

    def get_ports(self):
        return self.generate_port_list(port_max=16,
                                       description='virtual relay port #{}')

    def get(self, port=None, cfg=None, timeout=0):
        if not port:
            return self.data.copy()
        try:
            # if self.simulate_timeout:
            # self._make_timeout()
            return self.data.get(str(port))
        except:
            return None

    def _make_timeout(self):
        self.log_debug('simulating timeout for {} seconds'.format(
            self.simulate_timeout))
        time.sleep(self.simulate_timeout)

    def set(self, port=None, data=None, cfg=None, timeout=0):
        if self.simulate_timeout and (not cfg or not cfg.get('skip_timeout')):
            self._make_timeout()
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
            if self._is_required.value:
                d, value = d
            try:
                _data = int(d)
            except:
                return False
            if not _port in self.data:
                return False
            self.data[_port] = (_data,
                                value) if self._is_required.value else _data
            eva.benchmark.report('ACTION', _data, end=True)

        if self.phi_cfg.get('event_on_set'):
            handle_phi_event(self, port, self.data)
        return True

    def push_state(self, payload):
        if payload == 'test':
            return True
        else:
            for port, v in payload.items():
                try:
                    val = int(v)
                    if val < -1 or val > 1:
                        raise ValueError(f'Invalid port value {port} = {val}')
                    if port in self.data:
                        self.data[port] = val
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
                                     'name': 'simulate_timeout',
                                     'type': 'ufloat'
                                 }, {
                                     'name': 'event_on_set',
                                     'type': 'bool'
                                 }, {
                                     'name': 'event_on_test_set',
                                     'type': 'bool'
                                 }])

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
            if self._is_required.value:
                if val.find(',') != -1:
                    val, value = val.split(',', 1)
                else:
                    value = ''
            val = int(val)
            if self._is_required.value:
                state = val, value
            else:
                state = val
            if port < 1 or port > 16 or val < -1 or val > 1:
                return None
            self.set(port=str(port), data=state, cfg={'skip_timeout': True})
            self.log_debug('test set port %s=%s' % (port, state))
            if self.phi_cfg.get('event_on_test_set'):
                handle_phi_event(self, port, self.data)
            return self.data
        except:
            return {'get': 'get relay ports status', 'X=S': 'set port X to S'}
