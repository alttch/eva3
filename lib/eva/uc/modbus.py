__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"

default_delay = 0.02

import importlib
import threading
import time
import logging
import rapidjson
import re
import numpy as np

import eva.core
import eva.registry

from eva.exceptions import InvalidParameter
from eva.exceptions import FunctionFailed
from eva.exceptions import ResourceNotFound

from eva.tools import format_json
from eva.tools import parse_host_port
from eva.tools import safe_int

from eva.tools import SimpleNamespace

import threading

with_ports_lock = eva.core.RLocker('uc/modbus')

config = SimpleNamespace(slave={'tcp': [], 'udp': [], 'serial': []})

slave_regsz = 10000
slave_reg_max = slave_regsz - 1

slave_registers = {}

ports = {}

_d = SimpleNamespace(modified=set())

# public functions


def _parse_reg(reg):
    reg_type = reg[0]
    addr = safe_int(reg[1:])
    if reg_type not in ['c', 'd', 'i', 'h']:
        raise ValueError(f'Invalid register type: {reg_type}')
    return reg_type, addr


def set_data(addr, values, register='h'):
    """
    set data to modbus slave context

    Args:
        addr: addr to set to
        values: values to set

    Optional:
        register: h (default, 16 bit) - holding, i (16 bit) - input,
                  c (1 bit) - coil, d (1 bit) - discrete input)
    """
    if register not in slave_registers:
        raise FunctionFailed(
            'Slave register {} not initialized'.format(register))
    slave_registers[register].setValues(addr, values)


def get_data(addr, register='h', count=1):
    """
    get data from modbus slave context

    Args:
        addr: addr to get from

    Optional:
        register: h (default, 16 bit) - holding, i (16 bit) - input,
                  c (1 bit) - coil, d (1 bit) - discrete input)
        count: amount of data to get (default: 1 value)
    """
    if register not in slave_registers:
        raise FunctionFailed(
            'Slave register {} not initialized'.format(register))
    return slave_registers[register].getValues(addr, count)


def get_bool(reg, count=1):
    reg_type, addr = _parse_reg(reg)
    if reg_type in ['c', 'd']:
        return get_data(addr, reg_type, count)
    else:
        raise ValueError(f'Method not supported for register type {reg_type}')


def get_u16(reg, count=1):
    reg_type, addr = _parse_reg(reg)
    if reg_type in ['i', 'h']:
        return get_data(addr, reg_type, count)
    else:
        raise ValueError(f'Method not supported for register type {reg_type}')


def get_i16(reg, count=1):
    reg_type, addr = _parse_reg(reg)
    if reg_type in ['i', 'h']:
        return [
            x if x < 32768 else x - 65536
            for x in get_data(addr, reg_type, count)
        ]
    else:
        raise ValueError(f'Method not supported for register type {reg_type}')


def get_u32(reg, count=1):
    reg_type, addr = _parse_reg(reg)
    if reg_type in ['i', 'h']:
        result = get_data(addr, reg_type, count=count * 2)
    else:
        raise ValueError(f'Method not supported for register type {reg_type}')
    data = []
    for i in range(0, len(result), 2):
        data.append((result[i] << 16) + result[i + 1])
    return data


def get_i32(reg, count=1):
    reg_type, addr = _parse_reg(reg)
    if reg_type in ['i', 'h']:
        result = get_data(addr, reg_type, count=count * 2)
    else:
        raise ValueError(f'Method not supported for register type {reg_type}')
    data = []
    for i in range(0, len(result), 2):
        x = (result[i] << 16) + result[i + 1]
        data.append(x if x < 2147483648 else x - 4294967296)
    return data


def get_u64(reg, count=1):
    reg_type, addr = _parse_reg(reg)
    if reg_type in ['i', 'h']:
        result = get_data(addr, reg_type, count=count * 4)
    else:
        raise ValueError(f'Method not supported for register type {reg_type}')
    data = []
    for i in range(0, len(result), 4):
        data.append((result[i] << 48) + (result[i + 1] << 32) +
                    (result[i + 2] << 16) + result[i + 3])
    return data


def get_i64(reg, count=1):
    reg_type, addr = _parse_reg(reg)
    if reg_type in ['i', 'h']:
        result = get_data(addr, reg_type, count=count * 4)
    else:
        raise ValueError(f'Method not supported for register type {reg_type}')
    data = []
    for i in range(0, len(result), 4):
        x = ((result[i] << 48) + (result[i + 1] << 32) + (result[i + 2] << 16) +
             result[i + 3])
        data.append(x if x < 9223372036854775808 else x - 18446744073709551616)
    return data


def get_f32(reg, count=1):
    reg_type, addr = _parse_reg(reg)
    if reg_type in ['i', 'h']:
        result = get_data(addr, reg_type, count=count * 2)
    else:
        raise ValueError(f'Method not supported for register type {reg_type}')
    data = []
    for i in range(0, len(result), 2):
        data.append(
            np.array([
                x for x in result[i].to_bytes(2, byteorder='little') +
                result[i + 1].to_bytes(2, byteorder='little')
            ],
                     dtype=np.uint8).view(dtype=np.float32)[0])
    return data


def register_handler(addr, f, register='h'):
    """
    register modbus slave event handler

    the handler will be called in format f(addr, values) when slave context is
    changed

    Args:
        addr: addr to watch
        f: handler function

    Optional:
        register: h (default, 16 bit) - holding, i (16 bit) - input,
                  c (1 bit) - coil, d (1 bit) - discrete input)
    """
    if register not in slave_registers:
        raise FunctionFailed(
            'Slave register {} not initialized'.format(register))
    slave_registers[register].registerEventHandler(addr, f)
    logging.debug(
        'registered Modbus slave handler: {}, addr: {}, registers: {}'.format(
            f, addr, register))


def unregister_handler(addr, f, register='h'):
    """
    unregister modbus slave event handler

    Args:
        addr: addr to watch
        f: handler function

    Optional:
        register: h (default, 16 bit) - holding, i (16 bit) - input,
                  c (1 bit) - coil, d (1 bit) - discrete input)
    """
    if register not in slave_registers:
        raise FunctionFailed(
            'Slave register {} not initialized'.format(register))
    slave_registers[register].unregisterEventHandler(addr, f)
    logging.debug(
        'unregistered Modbus slave handler: {}, addr: {}, registers: {}'.format(
            f, addr, register))


# is modbus port with the given ID exist
@with_ports_lock
def is_port(port_id):
    return port_id in ports


@with_ports_lock
def _get_port(port_id):
    return ports.get(port_id)


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
    port = _get_port(port_id)
    if timeout and timeout < port.timeout * port.tries:
        logging.warning(
            'unable to acquire modbus port {}, '.format(port_id) + \
                'commands execution time may exceed the limit')
        return None
    if not port:
        return None
    result = port.acquire()
    return port if result else result


# private functions


@with_ports_lock
def serialize(port_id=None, config=False):
    if port_id:
        if port_id in ports:
            return ports[port_id].serialize(config=config)
        else:
            raise ResourceNotFound
    result = []
    for k, p in ports.copy().items():
        result.append(p.serialize(config=config))
    return result


@eva.core.dump
@eva.core.minidump
def dump():
    result = {'ports': serialize(), 'slave': config.slave}
    return result


@with_ports_lock
def create_modbus_port(port_id, params, **kwargs):
    """Create new modbus port

    Args:
        port_id: port ID
        params: port params (i.e. tcp:localhost:502, rtu:/dev/ttyS0:9600:8:N:1)
        lock: should the port be locked, True/False (default: True)
        timeout: port timeout (default: EVA timeout)
        delay: delay between operations (default: 0.02 sec)
        retries: retry attempts for port read/write operations (default: 0)
    """
    try:
        if not port_id or not re.match(eva.core.ID_ALLOWED_SYMBOLS, port_id):
            raise InvalidParameter('port id')
        p = ModbusPort(port_id, params, **kwargs)
        if not p.client:
            raise FunctionFailed
    except InvalidParameter:
        raise
    except:
        raise FunctionFailed(
            'Failed to create modbus port {}, params: {}'.format(
                port_id, params))
    else:
        if port_id in ports:
            ports[port_id].stop()
        ports[port_id] = p
        set_modified(port_id)
        logging.info('created modbus port {} : {}'.format(port_id, params))
        return True


@with_ports_lock
def destroy_modbus_port(port_id):
    if port_id in ports:
        ports[port_id].stop()
        try:
            del ports[port_id]
            set_modified(port_id)
        except:
            pass
        return True
    else:
        raise ResourceNotFound


@with_ports_lock
def load():
    try:
        for i, v in eva.registry.key_get_recursive('config/uc/buses/modbus'):
            if i != v['id']:
                raise ValueError(f'port {i} id mismatch')
            p = v['params']
            del v['id']
            del v['params']
            try:
                create_modbus_port(i, p, **v)
            except Exception as e:
                logging.error(f'Error loading modbus port: {e}')
                eva.core.log_traceback()
        _d.modified.clear()
        return True
    except Exception as e:
        logging.error(f'Error loading modbus ports: {e}')
        eva.core.log_traceback()
        return False


@eva.core.save
@with_ports_lock
def save():
    try:
        for i in _d.modified:
            kn = f'config/uc/buses/modbus/{i}'
            try:
                eva.registry.key_set(kn, ports[i].serialize(config=True))
            except KeyError:
                eva.registry.key_delete(kn)
        _d.modified.clear()
        return True
    except Exception as e:
        logging.error(f'Error saving modbus ports config: {e}')
        eva.core.log_traceback()
        return False


def modbus_slave_block(size):
    from pymodbus.datastore import ModbusSequentialDataBlock

    class WatchBlock(ModbusSequentialDataBlock):

        def __init__(self, *args, **kwargs):
            self.event_handlers = {}
            self.event_handlers_lock = threading.RLock()
            super().__init__(*args, **kwargs)

        def setValues(self, addr, values):
            super().setValues(addr, values)
            if not self.event_handlers_lock.acquire(
                    timeout=eva.core.config.timeout):
                logging.critical('WatchBlock::setValues locking broken')
                eva.core.critical()
                return False
            try:
                if addr not in self.event_handlers:
                    return
                for f in self.event_handlers[addr]:
                    eva.core.spawn(f, addr, values)
            finally:
                self.event_handlers_lock.release()

        def registerEventHandler(self, addr, f):
            if not self.event_handlers_lock.acquire(
                    timeout=eva.core.config.timeout):
                logging.critical(
                    'WatchBlock::registerEventHandler locking broken')
                eva.core.critical()
                return False
            try:
                self.event_handlers.setdefault(safe_int(addr), set()).add(f)
            except:
                logging.error(
                    'Unable to register modbus handler for address {}'.format(
                        addr))
                eva.core.log_traceback()
            finally:
                self.event_handlers_lock.release()

        def unregisterEventHandler(self, addr, f):
            if not self.event_handlers_lock.acquire(
                    timeout=eva.core.config.timeout):
                logging.critical(
                    'WatchBlock::unregisterEventHandler locking broken')
                eva.core.critical()
                return False
            try:
                a = safe_int(addr)
                if a in self.event_handlers:
                    try:
                        self.event_handlers[a].remove(f)
                    except KeyError:
                        pass
                    except:
                        logging.error(
                            'Unable to register modbus handler for address {}'.
                            format(addr))
                        eva.core.log_traceback()
            finally:
                self.event_handlers_lock.release()

    return WatchBlock(0, [0] * size)


def start():

    if not config.slave['tcp'] and \
            not config.slave['udp'] and \
            not config.slave['serial']:
        return
    try:
        modbus_server = importlib.import_module('pymodbus.server.asynchronous')
        modbus_device = importlib.import_module('pymodbus.device')
        modbus_transactions = importlib.import_module('pymodbus.transaction')
        modbus_datastore = importlib.import_module('pymodbus.datastore')

        # monkey-patch for pymodbus/server/asynchronous 2.2.0: udp server fix
        def datagramReceived_pymodbus_2_2_0_mp(self, data, addr):
            _logger = modbus_server._logger
            hexlify_packets = modbus_server.hexlify_packets
            _logger.debug("Client Connected [%s]" % addr[0])
            if _logger.isEnabledFor(logging.DEBUG):
                _logger.debug("Datagram Received: " + hexlify_packets(data))
            if not self.control.ListenOnly:
                continuation = lambda request: self._execute(request, addr)
                units = self.store.slaves()
                single = self.store.single
                self.framer.processIncomingPacket(data,
                                                  continuation,
                                                  single=single,
                                                  unit=units)

        modbus_server.ModbusUdpProtocol.datagramReceived = \
                datagramReceived_pymodbus_2_2_0_mp
        # end monkey-patch
    except:
        logging.error('Unable to import pymodbus module')
        eva.core.log_traceback()
        return

    slave_identity = modbus_device.ModbusDeviceIdentification()
    slave_identity.VendorName = 'Altertech'
    slave_identity.ProductCode = 'EVA'
    slave_identity.VendorUrl = 'https://www.eva-ics.com/'
    slave_identity.ProductName = 'EVA ICS'
    slave_identity.ModelName = eva.core.product.name
    slave_identity.MajorMinorRevision = '.'.join(
        eva.core.version.split('.')[:2])

    slave_framer = {
        'rtu': modbus_transactions.ModbusRtuFramer,
        'ascii': modbus_transactions.ModbusAsciiFramer,
        'binary': modbus_transactions.ModbusBinaryFramer
    }

    slave_di = modbus_slave_block(slave_regsz)
    slave_co = modbus_slave_block(slave_regsz)
    slave_hr = modbus_slave_block(slave_regsz)
    slave_ir = modbus_slave_block(slave_regsz)

    slave_registers.update({
        'h': slave_hr,
        'i': slave_ir,
        'c': slave_co,
        'd': slave_di
    })

    slave_store = modbus_datastore.ModbusSlaveContext(di=slave_di,
                                                      co=slave_co,
                                                      hr=slave_hr,
                                                      ir=slave_ir,
                                                      zero_mode=True)

    for v in config.slave['tcp']:
        try:
            modbus_server.StartTcpServer(modbus_datastore.ModbusServerContext(
                slaves={v['a']: slave_store}, single=False),
                                         identity=slave_identity,
                                         address=(v['h'], v['p']),
                                         defer_reactor_run=True)
        except:
            logging.error('Unable to start Modbus slave tcp:{}:{}'.format(
                v['h'], v['p']))
            eva.core.log_traceback()
    for v in config.slave['udp']:
        try:
            modbus_server.StartUdpServer(modbus_datastore.ModbusServerContext(
                slaves={v['a']: slave_store}, single=False),
                                         identity=slave_identity,
                                         address=(v['h'], v['p']),
                                         defer_reactor_run=True)
        except:
            logging.error('Unable to start Modbus slave udp:{}:{}'.format(
                v['h'], v['p']))
            eva.core.log_traceback()
    for v in config.slave['serial']:
        try:
            modbus_server.StartSerialServer(
                modbus_datastore.ModbusServerContext(
                    slaves={v['a']: slave_store}, single=False),
                identity=slave_identity,
                port=v['p'],
                baudrate=v['b'],
                bytesize=v['bs'],
                parity=v['pt'],
                stopbits=v['s'],
                framer=slave_framer[v['f']],
                defer_reactor_run=True)
        except:
            logging.error('Unable to start Modbus slave, port {}'.format(
                v['p']))
            eva.core.log_traceback()


# started by uc controller
@with_ports_lock
def stop():
    for k, p in ports.copy().items():
        p.stop()
    if eva.core.config.db_update != 0 and _d.modified:
        save()


class ModbusPort(object):

    def __init__(self, port_id, params, **kwargs):
        self.port_id = port_id
        self.lock = kwargs.get('lock', True)
        self.lock = True if self.lock else False
        try:
            self.timeout = float(kwargs.get('timeout'))
            self._timeout = self.timeout
        except:
            self.timeout = 1
            self._timeout = None
        try:
            self.delay = float(kwargs.get('delay'))
        except:
            self.delay = default_delay
        try:
            self.retries = int(kwargs.get('retries'))
        except:
            self.retries = 0
        self.tries = self.retries + 1
        if self.tries < 0:
            self.tries = 1
        self.params = params
        self.client = None
        self.client_type = None
        self.locker = threading.Lock()
        self.last_action = 0
        try:
            modbus_client = importlib.import_module('pymodbus.client.sync')
        except:
            logging.error('Unable to import pymodbus module')
            raise
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
                        self.client = modbus_client.ModbusTcpClient(host, port)
                    else:
                        self.client = modbus_client.ModbusUdpClient(host, port)
                    self.client.timeout = self.timeout
                except:
                    eva.core.log_traceback()
            elif p[0] in ['rtu', 'ascii', 'binary']:
                port = p[1]
                speed = int(p[2])
                bits = int(p[3])
                parity = p[4]
                stopbits = int(p[5])
                if bits < 5 or bits > 9:
                    raise InvalidParameter('bits not in range 5..9')
                if parity not in ['N', 'E', 'O', 'M', 'S']:
                    raise InvalidParameter('parity should be: N, E, O, M or S')
                if stopbits < 1 or stopbits > 2:
                    raise InvalidParameter('stopbits not in range 1..2')
                self.client = modbus_client.ModbusSerialClient(
                    method=p[0],
                    port=port,
                    bytesize=bits,
                    stopbits=stopbits,
                    parity=parity,
                    baudrate=speed)
            if self.client:
                self.client_type = p[0]

    def acquire(self):
        if not self.client:
            return False
        if self.lock and not self.locker.acquire(
                timeout=eva.core.config.timeout):
            return 0
        self.client.connect()
        if self.client.is_socket_open():
            return True
        else:
            if self.lock:
                self.locker.release()
            return False

    def release(self):
        if self.lock:
            self.locker.release()
        return True

    def read_coils(self, address, count=1, **kwargs):
        for i in range(self.tries):
            self.sleep()
            result = self.client.read_coils(address, count, **kwargs)
            if not result.isError():
                break
        return result

    def read_discrete_inputs(self, address, count=1, **kwargs):
        for i in range(self.tries):
            self.sleep()
            result = self.client.read_discrete_inputs(address, count, **kwargs)
            if not result.isError():
                break
        return result

    def write_coil(self, address, value, **kwargs):
        for i in range(self.tries):
            self.sleep()
            result = self.client.write_coil(address, value, **kwargs)
            if not result.isError():
                break
        return result

    def write_coils(self, address, values, **kwargs):
        for i in range(self.tries):
            self.sleep()
            result = self.client.write_coils(address, values, **kwargs)
            if not result.isError():
                break
        return result

    def write_register(self, address, value, **kwargs):
        for i in range(self.tries):
            self.sleep()
            result = self.client.write_register(address, value, **kwargs)
            if not result.isError():
                break
        return result

    def write_registers(self, address, values, **kwargs):
        for i in range(self.tries):
            self.sleep()
            result = self.client.write_registers(address, values, **kwargs)
            if not result.isError():
                break
        return result

    def read_holding_registers(self, address, count=1, **kwargs):
        for i in range(self.tries):
            self.sleep()
            result = self.client.read_holding_registers(address, count,
                                                        **kwargs)
            if not result.isError():
                break
        return result

    def read_input_registers(self, address, count=1, **kwargs):
        for i in range(self.tries):
            self.sleep()
            result = self.client.read_input_registers(address, count, **kwargs)
            if not result.isError():
                break
        return result

    def readwrite_registers(self, *args, **kwargs):
        for i in range(self.tries):
            self.sleep()
            result = self.client.readwrite_registers(*args, **kwargs)
            if not result.isError():
                break
        return result

    def mask_write_register(self, *args, **kwargs):
        for i in range(self.tries):
            self.sleep()
            result = self.client.mask_write_register(*args, **kwargs)
            if not result.isError():
                break
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
        if config:
            if self._timeout is not None:
                d['timeout'] = self._timeout
        else:
            d['timeout'] = self.timeout
        return d

    def stop(self):
        try:
            if self.client:
                self.client.close()
        except:
            eva.core.log_traceback()


def append_ip_slave(proto, unit, listen):
    try:
        host, port = parse_host_port(listen, 502)
        a = safe_int(unit)
        if not host:
            raise Exception
        config.slave[proto].append({'a': a, 'h': host, 'p': port})
        logging.debug('modbus.slave.{} = {}.{}:{}'.format(
            proto, hex(a), host, port))
    except:
        eva.core.log_traceback()


def append_serial_slave(proto, unit, listen):
    try:
        try:
            port, baudrate, bytesize, parity, stopbits = listen.split(':')
        except:
            port = listen
            baudrate = 9600
            bytesize = 8
            parity = 'N'
            stopbits = 1
        a = safe_int(unit)
        baudrate = int(baudrate)
        bytesize = int(bytesize)
        stopbits = int(stopbits)
        try:
            port = int(port)
        except:
            pass
        if proto not in ['rtu', 'ascii', 'binary']:
            raise Exception(f'Invalid Modbus slave framer: {proto}')
        config.slave['serial'].append({
            'a': a,
            'p': port,
            'f': proto,
            'b': baudrate,
            'bs': bytesize,
            'pt': parity,
            's': stopbits
        })
        logging.debug('modbus.slave.serial = {}.{}:{}:{}:{}:{}:{}'.format(
            hex(a), proto, port, baudrate, bytesize, parity, stopbits))
    except:
        eva.core.log_traceback()


def update_config(cfg):
    try:
        for c in cfg.get('modbus-slave', default=[]):
            proto = c['proto']
            unit = c['unit']
            listen = c['listen']
            if proto in ['tcp', 'udp']:
                append_ip_slave(proto, unit, listen)
            else:
                append_serial_slave(proto, unit, listen)
    except:
        eva.core.log_traceback()


def set_modified(port_id):
    _d.modified.add(port_id)
