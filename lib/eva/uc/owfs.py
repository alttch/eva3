__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.1.2"

import onewire
import eva.core
import logging
import jsonpickle
import threading

from eva.tools import format_json

owbus = {}

# public functions


# is onewire bus with the given ID exist
def is_bus(bus_id):
    return bus_id in owbus


def get_bus(bus_id):
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
    if not bus: return None
    result = bus.acquire()
    return bus if result else result


# private functions


def serialize(config=False):
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

    Returns:
        True if success, False if failed
    """
    bus = OWFSBus(bus_id, location, **kwargs)
    if not bus.ow:
        logging.error('Failed to create owfs bus {}, location: {}'.format(
            bus_id, location))
        return False
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
        return False


def load():
    try:
        data = jsonpickle.decode(
            open(eva.core.dir_runtime + '/uc_owfs.json').read())
        for p in data:
            d = p.copy()
            del d['id']
            del d['location']
            create_owfs_bus(p['id'], p['location'], **d)
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
        self.location = location
        self.locker = threading.Lock()
        try:
            self.ow = onewire.Onewire(('--' if location.find('=') != -1 and
                                       not location.startswith('--') else '') +
                                      location)
        except:
            self.ow = None

    def acquire(self):
        if not self.ow or not self.ow.initialized: return False
        return 0 if self.lock and \
                not self.locker.acquire(timeout=eva.core.timeout) else True

    def release(self):
        if self.lock: self.locker.release()
        return True

    def serialize(self, config=False):
        d = {
            'id': self.bus_id,
            'location': self.location,
            'lock': self.lock,
        }
        return d

    def stop(self):
        try:
            if self.ow: self.ow.finish()
        except:
            eva.core.log_traceback()
