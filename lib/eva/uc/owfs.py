__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.1"

default_delay = 0.05

import onewire
import eva.core
import logging
import jsonpickle
import threading
import time

from eva.tools import format_json

from eva.exceptions import FunctionFailed
from eva.exceptions import InvalidParameter
from eva.exceptions import ResourceNotFound

owbus = {}

# public functions


# is onewire bus with the given ID exist
def is_bus(bus_id):
    return bus_id in owbus


def get_bus(bus_id, timeout=None):
    """Get OWFS bus with the choosen ID

    Args:

      bus_id: owfs bus ID

    Returns:
      None if bus doesn't exist, 0 if bus is busy, False if bus connect error
      or bus object itself if success

    Don't forget to call bus.release() after the work is over, otherwise the
    port stays locked!
    """
    bus = owbus.get(bus_id)
    if timeout and timeout < bus.timeout * bus.tries:
        logging.warning(
            'unable to acquire owfs bus {}, '.format(bus_id) + \
                'commands execution time may exceed the limit')
        return None
    if not bus: return None
    result = bus.acquire()
    return bus if result else result


# private functions


def serialize(bus_id=None, config=False):
    if bus_id:
        if bus_id in owbus:
            return owbus[bus_id].serialize(config=config)
        else:
            raise ResourceNotFound
    result = []
    for k, p in owbus.copy().items():
        result.append(p.serialize(config=config))
    return result


@eva.core.dump
def dump():
    return serialize()


def create_owfs_bus(bus_id, location, **kwargs):
    """Create new owfs bus

    Args:
        bus_id: bus ID
        location: bus location (e.g. --i2c=/dev/i2c-1:ALL or localhost:4302 for
        owfs server)
        lock: should bus be locked, True/False (default: True)
        timeout: bus timeout (default: EVA timeout)
        delay: delay between operations (default: 0.02 sec)
        retries: retry attempts for bus read/write operations (default: 0)
    """
    try:
        bus = OWFSBus(bus_id, location, **kwargs)
        if not bus._ow:
            raise FunctionFailed
    except InvalidParameter:
        raise
    except:
        raise FunctionFailed(
            'Failed to create owfs bus {}, location: {}'.format(
                bus_id, location))
    else:
        if bus_id in owbus:
            owbus[bus_id].stop()
        owbus[bus_id] = bus
        logging.info('owfs bus {} : {}'.format(bus_id, location))
        return True


def destroy_owfs_bus(bus_id):
    if bus_id in owbus:
        owbus[bus_id].stop()
        try:
            del owbus[bus_id]
        except:
            pass
        return True
    else:
        raise ResourceNotFound


def load():
    try:
        data = jsonpickle.decode(
            open(eva.core.dir_runtime + '/uc_owfs.json').read())
        for p in data:
            d = p.copy()
            del d['id']
            del d['location']
            try:
                create_owfs_bus(p['id'], p['location'], **d)
            except Exception as e:
                logging.error(e)
    except:
        logging.error('unable to load uc_owfs.json')
        eva.core.log_traceback()
        return False
    return True


@eva.core.save
def save():
    try:
        open(eva.core.dir_runtime + '/uc_owfs.json', 'w').write(
            format_json(serialize(config=True)))
    except:
        logging.error('unable to save owfs bus config')
        eva.core.log_traceback()
        return False
    return True


def start():
    pass


def stop():
    for k, p in owbus.copy().items():
        p.stop()


class OWFSBus(object):

    def __init__(self, bus_id, location, **kwargs):
        self.bus_id = bus_id
        self.lock = kwargs.get('lock', True)
        self.lock = True if self.lock else False
        try:
            self.timeout = float(kwargs.get('timeout'))
            self._timeout = self.timeout
        except:
            self.timeout = eva.core.config.timeout - 1
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
        self.location = location
        self.locker = threading.Lock()
        self.last_action = 0
        self._ow = onewire.Onewire(('--' if location.find('=') != -1 and
                                    not location.startswith('--') else '') +
                                   location)

    def acquire(self):
        if not self._ow or not self._ow.initialized: return False
        return 0 if self.lock and \
                not self.locker.acquire(
                        timeout=eva.core.config.timeout) else True

    def release(self):
        if self.lock: self.locker.release()
        return True

    def read(self, path, attr):
        for i in range(self.tries):
            self.sleep()
            try:
                result = self._ow.get(path + '/' + attr)
                if result is not None: return result
            except:
                pass
        return None

    def write(self, path, attr, value):
        for i in range(self.tries):
            self.sleep()
            try:
                val = str(value)
                result = self._ow.set(path + '/' + attr, val)
                if result == len(val): return True
            except:
                pass
        return False

    def sleep(self):
        a = time.time()
        if a < self.last_action + self.delay:
            time.sleep(self.delay - a + self.last_action)
        self.last_action = time.time()

    def serialize(self, config=False):
        d = {
            'id': self.bus_id,
            'location': self.location,
            'lock': self.lock,
            'delay': self.delay,
            'retries': self.retries
        }
        d['timeout'] = self._timeout if config else self.timeout
        return d

    def stop(self):
        try:
            if self._ow: self._ow.finish()
        except:
            eva.core.log_traceback()
