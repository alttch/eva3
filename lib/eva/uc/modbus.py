__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "3.1.0"

default_delay = 0.02

from pymodbus.client.sync import ModbusTcpClient
from pymodbus.client.sync import ModbusUdpClient
from pymodbus.client.sync import ModbusSerialClient

import eva.core
import threading
import time
import logging
import jsonpickle

from eva.tools import format_json

ports = {}

# public functions


# is modbus port with the given ID exist
def is_port(port_id):
    return port_id in ports


def get_port(port_id):
    """Get modbus port with the choosen ID

    Returns:
      None if port doesn't exist, 0 if port is busy, False if port connect
      error or modbus port object itself if success

    Don't forget to call port.release() after the work is over, otherwise the
    port stays locked!
    """
    port = ports.get(port_id)
    return port.acquire if port else None


# private functions


def serialize():
    result = []
    for k, p in ports.copy().items():
        result.append(p.serialize())
    return result


def dump():
    return serialize()


def create_modbus_port(port_id, params, **kwargs):
    """Create new modbus port

    Args:
        port_id: port ID
        params: port params (i.e. tcp:localhost:502, rtu:/dev/ttyS0:9600:8:N:1)
        lock: should the port be locked, True/False (default: True)
        timeout: port timeout (default: EVA timeout)
        delay: delay between operations (default: 0.02 sec)

    Returns:
        True if success, False if failed
    """
    p = ModbusPort(port_id, params, **kwargs)
    if not p.client:
        logging.error('Failed to create modbus port {}, params: {}'.format(
            port_id, params))
        return False
    else:
        if port_id in self.ports:
            self.ports[port_id].stop()
        self.ports[port_id] = p
        logging.info('modbus port {} : {}'.format(port_id, params))
        return True


def destroy_modbus_port(port_id):
    if port_id in self.ports:
        self.ports[port_id].stop()
        try:
            del self.ports[port_id]
        except:
            pass
        return True
    else:
        return False


def load():
    try:
        data = jsonpickle.decode(
            open(eva.core.dir_runtime + '/uc_modbus.json').read())
        for p in data:
            create_modbus_port(p['id'], p['params'], p)
    except:
        logging.error('unable to load uc_modbus.json')
        eva.core.log_traceback()
        return False
    return True


def save():
    try:
        open(eva.core.dir_runtime + '/uc_modbus.json', 'w').write(
            format_json(serialize()))
    except:
        logging.error('unable to save modbus ports config')
        eva.core.log_traceback()
        return False
    return True


def start():
    eva.core.append_dump_func('uc.modbus', dump)
    eva.core.append_save_func(save)


def stop():
    for k, p in ports.copy().items():
        p.stop()


class ModbusPort(object):

    def __init__(self, port_id, params, **kwargs):
        self.port_id = port_id
        self.timeout = kwargs.get('timeout', eva.core.timeout)
        self.lock = kwargs.get('lock', True)
        self._lock = kwargs.get('lock')
        self.delay = kwargs.get('delay', default_delay)
        self._delay = kwargs.get('delay')
        self.params = params
        self.client = None
        self.locker = threading.Lock()
        self.last_action = 0
        if params:
            p = params.split(':')
            if p[0] in ['tcp', 'udp']:
                try:
                    host = p[1]
                    try:
                        port = p[2]
                    except:
                        port = 503
                    if p[0] == 'tcp':
                        self.client = ModbusTcpClient(host, port)
                    else:
                        self.client = ModbusUdpClient(host, port)
                    self.client.timeout = self.timeout
                except:
                    eva.core.log_traceback()
            elif p[0] in ['rtu', 'ascii', 'binary']:
                try:
                    port = p[1]
                    speed = p[2]
                    bits = p[3]
                    parity = p[4]
                    stopbits = p[5]
                    if bits < 1 or bits > 8:
                        raise Exception('bits not in range 1..8')
                    if parity not in ['N', 'E']:
                        raise Exception('parity should be either E or N')
                    if stopbits < 1 or stopbits > 8:
                        raise Exception('stopbits not in range 1..8')
                    self.client = ModbusSerialClient(
                        method=p[0],
                        port=port,
                        stopbits=stopbits,
                        parity=parity,
                        baudrate=speed)
                except:
                    eva.core.log_traceback()

    def acquire(self):
        if not self.client: return False
        if self.lock and not self.locker.acquire(timeout=eva.core.timeout):
            return 0
        self.client.connect()
        return self if self.client.is_socket_open() else False

    def release(self):
        if self.lock: self.locker.release()
        return True

    def read_coils(self, address, count=1, **kwargs):
        self.sleep()
        return self.client.read_coils(address, count=1, **kwargs)

    def read_discrete_inputs(self, address, count=1, **kwargs):
        self.sleep()
        return self.client.read_discrete_inputs(
            self, address, count=1, **kwargs)

    def write_coil(self, address, value, **kwargs):
        self.sleep()
        return self.client.write_coil(self, address, value, **kwargs)

    def write_coils(self, address, values, **kwargs):
        self.sleep()
        return self.client.write_coils(self, address, values, **kwargs)

    def write_register(self, address, value, **kwargs):
        self.sleep()
        return self.client.write_register(self, address, value, **kwargs)

    def write_registers(self, address, values, **kwargs):
        self.sleep()
        return self.client.write_registers(self, address, values, **kwargs)

    def read_holding_registers(self, address, count=1, **kwargs):
        self.sleep()
        return self.client.read_holding_registers(
            self, address, count=1, **kwargs)

    def read_input_registers(self, address, count=1, **kwargs):
        self.sleep()
        return self.client.read_input_registers(
            self, address, count=1, **kwargs)

    def readwrite_registers(self, *args, **kwargs):
        self.sleep()
        return self.client.readwrite_registers(self, *args, **kwargs)

    def mask_write_register(self, *args, **kwargs):
        self.sleep()
        return self.client.mask_write_register(self, *args, **kwargs)

    def sleep(self):
        a = time.time()
        if a < self.last_action + self.delay:
            time.sleep(self.delay - a + self.last_action)
        self.last_action = time.time()

    def serialize(self):
        d = {'id': self.port_id, 'params': self.params}
        if self._lock is not None: d['lock'] = self._lock
        if self._delay is not None: d['delay'] = self._delay
        return d

    def stop(self):
        try:
            if self.client: self.client.close()
        except:
            eva.core.log_traceback()
