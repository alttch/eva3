__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.2"

import threading

import eva.core

locks = {}


def lock(bus):
    if bus not in locks:
        l = threading.Lock()
        locks[bus] = l
    if not locks[bus].acquire(timeout=eva.core.config.timeout):
        return False
    return True


def release(bus):
    if bus in locks:
        locks[bus].release()
    return True
