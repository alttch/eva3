"""
Modbus helper module

For all functions included:

Args:
    port: modbus virtual port
    reg: starting register
    kwargs: additional kwargs for pymodbus functions ("unit" is usually
            required)

Raises:
    ValueError: failed to parse register
    RuntimeError: Modbus port I/O error

Register format: tX, where:

    t = register type (c = coil, d = discrete, i = input reg, h = holding reg)
    X = register number (hex or decimal)
"""

__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2020 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.3.2"

from eva.tools import safe_int
from eva.tools import val_to_boolean
from eva.uc.modbus import get_port
from eva.uc.modbus import is_port

import struct


def _parse_reg(reg):
    reg_type = reg[0]
    addr = safe_int(reg[1:])
    if reg_type not in ['c', 'd', 'i', 'h']:
        raise ValueError(f'Invalid register type: {reg_type}')
    return reg_type, addr


def read_bool(port, reg, count=1, **kwargs):
    """
    Read boolean values

    Returns:
        list of booleans
    """
    reg_type, addr = _parse_reg(reg)
    if reg_type == 'c':
        result = port.read_coils(addr, count=count, **kwargs)
    elif reg_type == 'd':
        result = port.read_discrete_inputs(addr, count=count, **kwargs)
    else:
        raise ValueError(f'Method not supported for register type {reg_type}')
    if result.isError():
        raise RuntimeError('Modbus I/O error')
    else:
        return result.bits[:count]


def write_bool(port, reg, values, **kwargs):
    """
    Write boolean values

    Args:
        values: a single boolean, list of boolean, list of strings or list of
                integers
    """
    reg_type, addr = _parse_reg(reg)
    if not isinstance(values, list) and not isinstance(values, tuple):
        values = [values]
    values = [val_to_boolean(x) for x in values]
    if reg_type == 'c':
        result = port.write_coils(addr, values, **kwargs)
    else:
        raise ValueError(f'Method not supported for register type {reg_type}')
    if result.isError():
        raise RuntimeError('Modbus I/O error')
    else:
        return True


def read_u16(port, reg, count=1, **kwargs):
    """
    Read u16 values

    Returns:
        list of u16
    """
    reg_type, addr = _parse_reg(reg)
    if reg_type == 'i':
        result = port.read_input_registers(addr, count=count, **kwargs)
    elif reg_type == 'h':
        result = port.read_holding_registers(addr, count=count, **kwargs)
    else:
        raise ValueError(f'Method not supported for register type {reg_type}')
    if result.isError():
        raise RuntimeError('Modbus I/O error')
    else:
        return result.registers


def write_u16(port, reg, values, **kwargs):
    """
    Write boolean values
    """
    reg_type, addr = _parse_reg(reg)
    if not isinstance(values, list) and not isinstance(values, tuple):
        values = [values]
    if reg_type == 'h':
        result = port.write_registers(addr, values, **kwargs)
    else:
        raise ValueError(f'Method not supported for register type {reg_type}')
    if result.isError():
        raise RuntimeError('Modbus I/O error')
    else:
        return True


def read_i16(port, reg, count=1, **kwargs):
    """
    Read i16 values

    Returns:
        list of i16
    """
    reg_type, addr = _parse_reg(reg)
    if reg_type == 'i':
        result = port.read_input_registers(addr, count=count, **kwargs)
    elif reg_type == 'h':
        result = port.read_holding_registers(addr, count=count, **kwargs)
    else:
        raise ValueError(f'Method not supported for register type {reg_type}')
    if result.isError():
        raise RuntimeError('Modbus I/O error')
    else:
        return [x if x < 32768 else x - 65536 for x in result.registers]


def write_i16(port, reg, values, **kwargs):
    """
    Write i16 values
    """
    reg_type, addr = _parse_reg(reg)
    if not isinstance(values, list) and not isinstance(values, tuple):
        values = [values]
    values = [x if x >= 0 else 65536 + x for x in values]
    if reg_type == 'h':
        result = port.write_registers(addr, values, **kwargs)
    else:
        raise ValueError(f'Method not supported for register type {reg_type}')
    if result.isError():
        raise RuntimeError('Modbus I/O error')
    else:
        return True


def read_u32(port, reg, count=1, **kwargs):
    """
    Read u32 values

    Returns:
        list of u32
    """
    reg_type, addr = _parse_reg(reg)
    if reg_type == 'i':
        result = port.read_input_registers(addr, count=count * 2, **kwargs)
    elif reg_type == 'h':
        result = port.read_holding_registers(addr, count=count * 2, **kwargs)
    else:
        raise ValueError(f'Method not supported for register type {reg_type}')
    if result.isError():
        raise RuntimeError('Modbus I/O error')
    else:
        data = []
        for i in range(0, len(result.registers), 2):
            data.append((result.registers[i] << 16) + result.registers[i + 1])
        return data


def write_u32(port, reg, values, **kwargs):
    """
    Write u32 values
    """
    reg_type, addr = _parse_reg(reg)
    if not isinstance(values, list) and not isinstance(values, tuple):
        values = [values]
    data = []
    for v in values:
        data.append(v >> 16)
        data.append(v & 0xffff)
    if reg_type == 'h':
        result = port.write_registers(addr, data, **kwargs)
    else:
        raise ValueError(f'Method not supported for register type {reg_type}')
    if result.isError():
        raise RuntimeError('Modbus I/O error')
    else:
        return True


def read_i32(port, reg, count=1, **kwargs):
    """
    Read i32 values

    Returns:
        list of i32
    """
    reg_type, addr = _parse_reg(reg)
    if reg_type == 'i':
        result = port.read_input_registers(addr, count=count * 2, **kwargs)
    elif reg_type == 'h':
        result = port.read_holding_registers(addr, count=count * 2, **kwargs)
    else:
        raise ValueError(f'Method not supported for register type {reg_type}')
    if result.isError():
        raise RuntimeError('Modbus I/O error')
    else:
        data = []
        for i in range(0, len(result.registers), 2):
            x = (result.registers[i] << 16) + result.registers[i + 1]
            data.append(x if x < 2147483648 else x - 4294967296)
        return data


def write_i32(port, reg, values, **kwargs):
    """
    Write i32 values
    """
    reg_type, addr = _parse_reg(reg)
    if not isinstance(values, list) and not isinstance(values, tuple):
        values = [values]
    values = [x if x >= 0 else 4294967296 + x for x in values]
    data = []
    for v in values:
        data.append(v >> 16)
        data.append(v & 0xffff)
    if reg_type == 'h':
        result = port.write_registers(addr, data, **kwargs)
    else:
        raise ValueError(f'Method not supported for register type {reg_type}')
    if result.isError():
        raise RuntimeError('Modbus I/O error')
    else:
        return True


def read_u64(port, reg, count=1, **kwargs):
    """
    Read u64 values

    Returns:
        list of u64
    """
    reg_type, addr = _parse_reg(reg)
    if reg_type == 'i':
        result = port.read_input_registers(addr, count=count * 4, **kwargs)
    elif reg_type == 'h':
        result = port.read_holding_registers(addr, count=count * 4, **kwargs)
    else:
        raise ValueError(f'Method not supported for register type {reg_type}')
    if result.isError():
        raise RuntimeError('Modbus I/O error')
    else:
        data = []
        for i in range(0, len(result.registers), 4):
            data.append((result.registers[i] << 48) +
                        (result.registers[i + 1] << 32) +
                        (result.registers[i + 2] << 16) +
                        result.registers[i + 3])
        return data


def write_u64(port, reg, values, **kwargs):
    """
    Write u32 values
    """
    reg_type, addr = _parse_reg(reg)
    if not isinstance(values, list) and not isinstance(values, tuple):
        values = [values]
    data = []
    for v in values:
        data.append(v >> 48)
        data.append(v >> 32 & 0xffff)
        data.append(v >> 16 & 0xffff)
        data.append(v & 0xffff)
    if reg_type == 'h':
        result = port.write_registers(addr, data, **kwargs)
    else:
        raise ValueError(f'Method not supported for register type {reg_type}')
    if result.isError():
        raise RuntimeError('Modbus I/O error')
    else:
        return True


def read_i64(port, reg, count=1, **kwargs):
    """
    Read i64 values

    Returns:
        list of i64
    """
    reg_type, addr = _parse_reg(reg)
    if reg_type == 'i':
        result = port.read_input_registers(addr, count=count * 4, **kwargs)
    elif reg_type == 'h':
        result = port.read_holding_registers(addr, count=count * 4, **kwargs)
    else:
        raise ValueError(f'Method not supported for register type {reg_type}')
    if result.isError():
        raise RuntimeError('Modbus I/O error')
    else:
        data = []
        for i in range(0, len(result.registers), 4):
            x = ((result.registers[i] << 48) + (result.registers[i + 1] << 32) +
                 (result.registers[i + 2] << 16) + result.registers[i + 3])
            data.append(x if x < 9223372036854775808 else x -
                        18446744073709551616)
        return data


def write_i64(port, reg, values, **kwargs):
    """
    Write i64 values
    """
    reg_type, addr = _parse_reg(reg)
    if not isinstance(values, list) and not isinstance(values, tuple):
        values = [values]
    values = [x if x >= 0 else 18446744073709551616 + x for x in values]
    data = []
    for v in values:
        data.append(v >> 48)
        data.append(v >> 32 & 0xffff)
        data.append(v >> 16 & 0xffff)
        data.append(v & 0xffff)
    if reg_type == 'h':
        result = port.write_registers(addr, data, **kwargs)
    else:
        raise ValueError(f'Method not supported for register type {reg_type}')
    if result.isError():
        raise RuntimeError('Modbus I/O error')
    else:
        return True


def read_f32(port, reg, count=1, **kwargs):
    """
    Read IEEE 754 f32 values

    Returns:
        list of f32
    """
    reg_type, addr = _parse_reg(reg)
    if reg_type == 'i':
        result = port.read_input_registers(addr, count=count * 2, **kwargs)
    elif reg_type == 'h':
        result = port.read_holding_registers(addr, count=count * 2, **kwargs)
    else:
        raise ValueError(f'Method not supported for register type {reg_type}')
    if result.isError():
        raise RuntimeError('Modbus I/O error')
    else:
        data = []
        for i in range(0, len(result.registers), 2):
            data.append(
                struct.unpack(
                    'f',
                    struct.pack('H', result.registers[i]) +
                    struct.pack('H', result.registers[i + 1]))[0])
        return data


def write_f32(port, reg, values, **kwargs):
    """
    Write f32 values
    """
    reg_type, addr = _parse_reg(reg)
    if not isinstance(values, list) and not isinstance(values, tuple):
        values = [values]
    data = []
    for v in values:
        x = struct.pack('f', float(v))
        data.append(struct.unpack('H', x[:2])[0])
        data.append(struct.unpack('H', x[2:])[0])
    if reg_type == 'h':
        result = port.write_registers(addr, data, **kwargs)
    else:
        raise ValueError(f'Method not supported for register type {reg_type}')
    if result.isError():
        raise RuntimeError('Modbus I/O error')
    else:
        return True
