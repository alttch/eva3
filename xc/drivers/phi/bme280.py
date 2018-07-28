__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "BME280 temperature/humidity/pressure sensors (I2C/SMBus)"

__id__ = 'bme280'
__equipment__ = ['BME280']
__api__ = 1
__required__ = ['aao_get', 'value']
__mods_required__ = []
__lpi_default__ = 'sensor'
__features__ = ['aao_get']
__config_help__ = [{
    'name': 'bus',
    'help': 'I2C bus to use',
    'type': 'int',
    'required': True
}, {
    'name': 'addr',
    'help': 'Device address on bus, hexdecimal (default: 0x76)',
    'type': 'hex',
    'required': True
}]
__get_help__ = []
__set_help__ = []

bus_delay = 0.5

__help__ = """
PHI for BME280 sensors (and compatible) connected via local I2C bus. Returns
port 'h' for humidity, 't' for temperature, 'p' for pressure.
"""

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import get_timeout

import eva.uc.smbus as smbus

import os
import importlib
import time
from ctypes import c_short
from ctypes import c_byte
from ctypes import c_ubyte


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
        self.aao_get = True
        if info_only: return
        try:
            self.bus = int(self.phi_cfg.get('bus'))
        except:
            self.log_error('I2C bus not specified')
            self.ready = False
            return
        try:
            self.addr = int(self.phi_cfg.get('addr', '0x76'), 16)
        except:
            self.log_error('Invalid address: %s ' % self.phi_cfg.get('addr'))
            self.ready = False

    def get(self, port=None, cfg=None, timeout=0):
        try:
            b = smbus.get(self.bus)
            if not b:
                raise Exception('Unable to acquire I2C bus %s ' % self.bus)
            time_start = time.time()
            rd = False
            while time_start + timeout >= time.time():
                try:
                    t, p, h = self.readBME280All(bus=b, addr=self.addr)
                    if t is not None and p is not None and h is not None:
                        rd = True
                        break
                except:
                    pass
                time.sleep(bus_delay)
            smbus.release(self.bus)
            if not rd: raise Exception('data read error')
            return {
                't': int(t * 100) / 100.0,
                'p': int(p * 100) / 100.0,
                'h': int(h * 100) / 100.0
            }
        except:
            log_traceback()
            return None

    def test(self, cmd=None):
        if cmd == 'self' or cmd == 'info':
            try:
                b = smbus.get(self.bus)
                if not b:
                    raise Exception('Unable to acquire I2C bus %s ' % self.bus)
                try:
                    i, v = self.readBME280ID(bus=b, addr=self.addr)
                except:
                    smbus.release(self.bus)
                    raise
                smbus.release(self.bus)
                if i is None or v is None: raise Exception('data read error')
            except:
                log_traceback()
                return 'FAILED'
            return {'id': i, 'version': v} if cmd != 'self' else 'OK'
        elif cmd == 'get':
            return self.get(timeout=get_timeout())
        else:
            return {
                'info': 'Get chip ID and version',
                'get': 'Get data from chip'
            }

    # the code below is based on bme280.py tool
    # Author : Matt Hawkins
    # Date   : 25/07/2016
    #
    # http://www.raspberrypi-spy.co.uk/
    #
    #--------------------------------------
    def readBME280ID(self, bus, addr):
        # Chip ID Register Address
        REG_ID = 0xD0
        (chip_id, chip_version) = bus.read_i2c_block_data(addr, REG_ID, 2)
        return (chip_id, chip_version)

    def readBME280All(self, bus, addr):
        # Register Addresses
        REG_DATA = 0xF7
        REG_CONTROL = 0xF4
        REG_CONFIG = 0xF5

        REG_CONTROL_HUM = 0xF2
        REG_HUM_MSB = 0xFD
        REG_HUM_LSB = 0xFE

        # Oversample setting - page 27
        OVERSAMPLE_TEMP = 2
        OVERSAMPLE_PRES = 2
        MODE = 1

        # Oversample setting for humidity register - page 26
        OVERSAMPLE_HUM = 2
        bus.write_byte_data(addr, REG_CONTROL_HUM, OVERSAMPLE_HUM)

        control = OVERSAMPLE_TEMP << 5 | OVERSAMPLE_PRES << 2 | MODE
        bus.write_byte_data(addr, REG_CONTROL, control)

        # Read blocks of calibration data from EEPROM
        # See Page 22 data sheet
        cal1 = bus.read_i2c_block_data(addr, 0x88, 24)
        cal2 = bus.read_i2c_block_data(addr, 0xA1, 1)
        cal3 = bus.read_i2c_block_data(addr, 0xE1, 7)

        # Convert byte data to word values
        dig_T1 = getUShort(cal1, 0)
        dig_T2 = getShort(cal1, 2)
        dig_T3 = getShort(cal1, 4)

        dig_P1 = getUShort(cal1, 6)
        dig_P2 = getShort(cal1, 8)
        dig_P3 = getShort(cal1, 10)
        dig_P4 = getShort(cal1, 12)
        dig_P5 = getShort(cal1, 14)
        dig_P6 = getShort(cal1, 16)
        dig_P7 = getShort(cal1, 18)
        dig_P8 = getShort(cal1, 20)
        dig_P9 = getShort(cal1, 22)

        dig_H1 = getUChar(cal2, 0)
        dig_H2 = getShort(cal3, 0)
        dig_H3 = getUChar(cal3, 2)

        dig_H4 = getChar(cal3, 3)
        dig_H4 = (dig_H4 << 24) >> 20
        dig_H4 = dig_H4 | (getChar(cal3, 4) & 0x0F)

        dig_H5 = getChar(cal3, 5)
        dig_H5 = (dig_H5 << 24) >> 20
        dig_H5 = dig_H5 | (getUChar(cal3, 4) >> 4 & 0x0F)

        dig_H6 = getChar(cal3, 6)

        # Wait in ms (Datasheet Appendix B: Measurement time and current
        # calculation)
        wait_time = 1.25 + (2.3 * OVERSAMPLE_TEMP) + (
            (2.3 * OVERSAMPLE_PRES) + 0.575) + ((2.3 * OVERSAMPLE_HUM) + 0.575)
        time.sleep(wait_time / 1000)  # Wait the required time

        # Read temperature/pressure/humidity
        data = bus.read_i2c_block_data(addr, REG_DATA, 8)
        pres_raw = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
        temp_raw = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
        hum_raw = (data[6] << 8) | data[7]

        #Refine temperature
        var1 = ((((temp_raw >> 3) - (dig_T1 << 1))) * (dig_T2)) >> 11
        var2 = (((((temp_raw >> 4) - (dig_T1)) * (
            (temp_raw >> 4) - (dig_T1))) >> 12) * (dig_T3)) >> 14
        t_fine = var1 + var2
        temperature = float(((t_fine * 5) + 128) >> 8)

        # Refine pressure and adjust for temperature
        var1 = t_fine / 2.0 - 64000.0
        var2 = var1 * var1 * dig_P6 / 32768.0
        var2 = var2 + var1 * dig_P5 * 2.0
        var2 = var2 / 4.0 + dig_P4 * 65536.0
        var1 = (dig_P3 * var1 * var1 / 524288.0 + dig_P2 * var1) / 524288.0
        var1 = (1.0 + var1 / 32768.0) * dig_P1
        if var1 == 0:
            pressure = 0
        else:
            pressure = 1048576.0 - pres_raw
            pressure = ((pressure - var2 / 4096.0) * 6250.0) / var1
            var1 = dig_P9 * pressure * pressure / 2147483648.0
            var2 = pressure * dig_P8 / 32768.0
            pressure = pressure + (var1 + var2 + dig_P7) / 16.0

        # Refine humidity
        humidity = t_fine - 76800.0
        humidity = (hum_raw - (dig_H4 * 64.0 + dig_H5 / 16384.0 * humidity)) * (
            dig_H2 / 65536.0 * (1.0 + dig_H6 / 67108864.0 * humidity *
                                (1.0 + dig_H3 / 67108864.0 * humidity)))
        humidity = humidity * (1.0 - dig_H1 * humidity / 524288.0)
        if humidity > 100:
            humidity = 100
        elif humidity < 0:
            humidity = 0

        return temperature / 100.0, pressure / 100.0, humidity


def getShort(data, index):
    # return two bytes from data as a signed 16-bit value
    return c_short((data[index + 1] << 8) + data[index]).value


def getUShort(data, index):
    # return two bytes from data as an unsigned 16-bit value
    return (data[index + 1] << 8) + data[index]


def getChar(data, index):
    # return one byte from data as a signed char
    result = data[index]
    if result > 127:
        result -= 256
    return result


def getUChar(data, index):
    # return one byte from data as an unsigned char
    result = data[index] & 0xFF
    return result
