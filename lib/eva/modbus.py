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


class ModbusPort(object):

    def __init__(self, port_id, params, **kwargs):
        self.port_id = port_id
        self.timeout = kwargs.get('timeout', eva.core.timeout)
        self.lock = kwargs.get('lock', True)
        self.delay = kwargs.get('delay', default_delay)
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
            return None
        self.client.connect()
        return self.client.is_socket_open()

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
