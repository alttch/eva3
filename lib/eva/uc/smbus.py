__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "3.1.0"

import smbus2
import threading

import eva.core

locks = {}


def get(bus):
    if bus not in locks:
        l = threading.Lock()
        locks[bus] = l
    if not locks[bus].acquire(timeout=eva.core.timeout):
        return None
    return smbus2.SMBus(bus)


def release(bus):
    if bus in locks:
        bus.locks[bus].release()
    return True
