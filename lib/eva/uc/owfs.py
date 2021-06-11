__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"

default_delay = 0.05

import importlib
import logging
import rapidjson
import threading
import time
import re

import eva.core
import eva.registry

from eva.tools import format_json

from eva.exceptions import FunctionFailed
from eva.exceptions import InvalidParameter
from eva.exceptions import ResourceNotFound

from eva.tools import SimpleNamespace

with_ports_lock = eva.core.RLocker('uc/owfs')

owbus = {}

_d = SimpleNamespace(modified=set())

# public functions


# is onewire bus with the given ID exist
@with_ports_lock
def is_bus(bus_id):
    return bus_id in owbus


@with_ports_lock
def _get_bus(bus_id):
    return owbus.get(bus_id)


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
    bus = _get_bus(bus_id)
    if timeout and timeout < bus.timeout * bus.tries:
        logging.warning(
            'unable to acquire owfs bus {}, '.format(bus_id) + \
                'commands execution time may exceed the limit')
        return None
    if not bus:
        return None
    result = bus.acquire()
    return bus if result else result


# private functions


@with_ports_lock
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


@with_ports_lock
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
        if not bus_id or not re.match(eva.core.ID_ALLOWED_SYMBOLS, bus_id):
            raise InvalidParameter('bus id')
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
        set_modified(bus_id)
        logging.info('owfs bus {} : {}'.format(bus_id, location))
        return True


@with_ports_lock
def destroy_owfs_bus(bus_id):
    if bus_id in owbus:
        owbus[bus_id].stop()
        try:
            del owbus[bus_id]
            set_modified(bus_id)
        except:
            pass
        return True
    else:
        raise ResourceNotFound


@with_ports_lock
def load():
    try:
        for i, v in eva.registry.key_get_recursive('config/uc/buses/owfs'):
            if i != v['id']:
                raise ValueError(f'bus {i} id mismatch')
            p = v['location']
            del v['id']
            del v['location']
            try:
                create_owfs_bus(i, p, **v)
            except Exception as e:
                logging.error(f'Error loading owfs bus: {e}')
                eva.core.log_traceback()
        _d.modified.clear()
        return True
    except Exception as e:
        logging.error(f'Error loading OWFS buses: {e}')
        eva.core.log_traceback()
        return False


@eva.core.save
@with_ports_lock
def save():
    try:
        for i in _d.modified:
            kn = f'config/uc/buses/owfs/{i}'
            try:
                eva.registry.key_set(kn, owbus[i].serialize(config=True))
            except KeyError:
                eva.registry.key_delete(kn)
        _d.modified.clear()
        return True
    except Exception as e:
        logging.error(f'Error saving owfs bus config: {e}')
        eva.core.log_traceback()
        return False


def start():
    pass


def stop():
    for k, p in owbus.copy().items():
        p.stop()
    if eva.core.config.db_update != 0 and _d.modified:
        save()


class OWFSBus(object):

    def __init__(self, bus_id, location, **kwargs):
        self.bus_id = bus_id
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
        self.location = location
        self.locker = threading.Lock()
        self.last_action = 0
        try:
            onewire = importlib.import_module('onewire')
        except:
            logging.error('Unable to import onewire module')
            raise
        self._ow = onewire.Onewire(('--' if location.find('=') != -1 and
                                    not location.startswith('--') else '') +
                                   location)

    def acquire(self):
        if not self._ow or not self._ow.initialized:
            return False
        return 0 if self.lock and \
                not self.locker.acquire(
                        timeout=eva.core.config.timeout) else True

    def release(self):
        if self.lock:
            self.locker.release()
        return True

    def read(self, path, attr):
        for i in range(self.tries):
            self.sleep()
            try:
                result = self._ow.get(path + '/' + attr)
                if result is not None:
                    return result
            except:
                pass
        return None

    def write(self, path, attr, value):
        for i in range(self.tries):
            self.sleep()
            try:
                val = str(value)
                result = self._ow.set(path + '/' + attr, val)
                if result == len(val):
                    return True
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
        if config:
            if self._timeout is not None:
                d['timeout'] = self._timeout
        else:
            d['timeout'] = self.timeout
        return d

    def stop(self):
        try:
            if self._ow:
                self._ow.finish()
        except:
            eva.core.log_traceback()


def set_modified(bus_id):
    _d.modified.add(bus_id)
