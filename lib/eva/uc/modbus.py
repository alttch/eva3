__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.1.2"

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


def get_port(port_id, timeout=None):
    """Get modbus port with the choosen ID

    Args:

      port_id: modbus port ID
      timeout: max allowed timeout for the operations

    Returns:
      None if port doesn't exist or the operations could require more time than
      timeout specified, 0 if port is busy, False if port connect error or
      modbus port object itself if success

    Don't forget to call port.release() after the work is over, otherwise the
    port stays locked!
    """
    port = ports.get(port_id)
    if timeout and timeout < port.timeout * port.tries:
        logging.warning(
            'unable to acquire modbus port {}, '.format(port_id) + \
                'commands execution time may exceed the limit')
        return None
    if not port: return None
    result = port.acquire()
    return port if result else result


# private functions


def serialize(config=False):
    result = []
    for k, p in ports.copy().items():
        result.append(p.serialize(config=config))
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
        retries: retry attempts for port read/write operations (default: 0)

    Returns:
        True if success, False if failed
    """
    p = ModbusPort(port_id, params, **kwargs)
    if not p.client:
        logging.error('Failed to create modbus port {}, params: {}'.format(
            port_id, params))
        return False
    else:
        if port_id in ports:
            ports[port_id].stop()
        ports[port_id] = p
        logging.info('modbus port {} : {}'.format(port_id, params))
        return True


def destroy_modbus_port(port_id):
    if port_id in ports:
        ports[port_id].stop()
        try:
            del ports[port_id]
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
            d = p.copy()
            del d['id']
            del d['params']
            create_modbus_port(p['id'], p['params'], **d)
    except:
        logging.error('unable to load uc_modbus.json')
        eva.core.log_traceback()
        return False
    return True


def save():
    try:
        open(eva.core.dir_runtime + '/uc_modbus.json', 'w').write(
            format_json(serialize(config=True)))
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
        self.lock = kwargs.get('lock', True)
        self.lock = True if self.lock else False
        try:
            self.timeout = float(kwargs.get('timeout'))
            self._timeout = self.timeout
        except:
            self.timeout = eva.core.timeout - 1
            self._timeout = None
            if self.timeout < 1: self.timeout = 1
        try:
            self.delay = float(kwargs.get('delay'))
        except:
            self.delay = default_delay
        try:
            self.retries = int(kwargs.get('retries'))
        except:
            self.retries = 0
        self.tries = self.retries + 1
        if self.tries < 0: self.tries = 1
        self.params = params
        self.client = None
        self.client_type = None
        self.locker = threading.Lock()
        self.last_action = 0
        if params:
            p = params.split(':')
            if p[0] in ['tcp', 'udp']:
                try:
                    host = p[1]
                    try:
                        port = int(p[2])
                    except:
                        port = 502
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
                    speed = int(p[2])
                    bits = int(p[3])
                    parity = p[4]
                    stopbits = int(p[5])
                    if bits < 5 or bits > 9:
                        raise Exception('bits not in range 5..9')
                    if parity not in ['N', 'E', 'O', 'M', 'S']:
                        raise Exception('parity should be: N, E, O, M or S')
                    if stopbits < 1 or stopbits > 2:
                        raise Exception('stopbits not in range 1..2')
                    self.client = ModbusSerialClient(
                        method=p[0],
                        port=port,
                        stopbits=stopbits,
                        parity=parity,
                        baudrate=speed)
                except:
                    eva.core.log_traceback()
            if self.client:
                self.client_type = p[0]

    def acquire(self):
        if not self.client: return False
        if self.lock and not self.locker.acquire(timeout=eva.core.timeout):
            return 0
        self.client.connect()
        if self.client.is_socket_open():
            return True
        else:
            if self.lock: self.locker.release()
            return False

    def release(self):
        if self.lock: self.locker.release()
        return True

    def read_coils(self, address, count=1, **kwargs):
        for i in range(self.tries):
            self.sleep()
            result = self.client.read_coils(address, count, **kwargs)
            if not result.isError(): break
        return result

    def read_discrete_inputs(self, address, count=1, **kwargs):
        for i in range(self.tries):
            self.sleep()
            result = self.client.read_discrete_inputs(address, count, **kwargs)
            if not result.isError(): break
        return result

    def write_coil(self, address, value, **kwargs):
        for i in range(self.tries):
            self.sleep()
            result = self.client.write_coil(address, value, **kwargs)
            if not result.isError(): break
        return result

    def write_coils(self, address, values, **kwargs):
        for i in range(self.tries):
            self.sleep()
            result = self.client.write_coils(address, values, **kwargs)
            if not result.isError(): break
        return result

    def write_register(self, address, value, **kwargs):
        for i in range(self.tries):
            self.sleep()
            result = self.client.write_register(address, value, **kwargs)
            if not result.isError(): break
        return result

    def write_registers(self, address, values, **kwargs):
        for i in range(self.tries):
            self.sleep()
            result = self.client.write_registers(address, values, **kwargs)
            if not result.isError(): break
        return result

    def read_holding_registers(self, address, count=1, **kwargs):
        for i in range(self.tries):
            self.sleep()
            result = self.client.read_holding_registers(address, count,
                                                        **kwargs)
            if not result.isError(): break
        return result

    def read_input_registers(self, address, count=1, **kwargs):
        for i in range(self.tries):
            self.sleep()
            result = self.client.read_input_registers(address, count, **kwargs)
            if not result.isError(): break
        return result

    def readwrite_registers(self, *args, **kwargs):
        for i in range(self.tries):
            self.sleep()
            result = self.client.readwrite_registers(*args, **kwargs)
            if not result.isError(): break
        return result

    def mask_write_register(self, *args, **kwargs):
        for i in range(self.tries):
            self.sleep()
            result = self.client.mask_write_register(*args, **kwargs)
            if not result.isError(): break
        return result

    def sleep(self):
        a = time.time()
        if a < self.last_action + self.delay:
            time.sleep(self.delay - a + self.last_action)
        self.last_action = time.time()

    def serialize(self, config=False):
        d = {
            'id': self.port_id,
            'params': self.params,
            'lock': self.lock,
            'delay': self.delay,
            'retries': self.retries
        }
        d['timeout'] = self._timeout if config else self.timeout
        return d

    def stop(self):
        try:
            if self.client: self.client.close()
        except:
            eva.core.log_traceback()
