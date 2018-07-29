__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "3.1.0"

import threading

import eva.core

locks = {}


def lock(bus):
    if bus not in locks:
        l = threading.Lock()
        locks[bus] = l
    if not locks[bus].acquire(timeout=eva.core.timeout):
        return False
    return True


def release(bus):
    if bus in locks:
        locks[bus].release()
    return True
