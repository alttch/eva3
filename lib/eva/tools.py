__author__ = "Altertech Group, http://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "See http://www.eva-ics.com/"
__version__ = "3.0.2"

import json
import jsonpickle
import time
import socket
import struct

from collections import OrderedDict
from netaddr import IPNetwork, IPAddress

import eva.core


class MultiOrderedDict(OrderedDict):

    def __setitem__(self, key, value):
        if isinstance(value, list) and key in self:
            self[key].extend(value)
        else:
            super().__setitem__(key, value)


def config_error(fname, section, key, value):
    logging.error('%s error, unknown value %s = "%s" in section %s' % \
            (fname, key, value, section))


def format_json(obj, minimal=False):
    return json.dumps(json.loads(jsonpickle.encode(obj,
            unpicklable = False)), indent = 4, sort_keys = True) \
                if not minimal else jsonpickle.encode(obj, unpicklable = False)


def fname_remove_unsafe(fname):
    return fname.replace('/', '').replace('..', '')


def print_json(obj):
    print(format_json(obj))


def parse_host_port(hp):
    if hp.find(':') == -1: return (hp, None)
    try:
        host, port = hp.split(':')
        port = int(port)
    except:
        eva.core.log_traceback()
        return (None, None)
    return (host, port)


def netacl_match(host, acl):
    for a in acl:
        if IPAddress(host) in a: return True
    return False


def wait_for(func, wait_timeout, delay, wait_for_false=False):
    a = 0
    if wait_for_false:
        while func() and a < wait_timeout / delay:
            a += 1
            time.sleep(delay)
    else:
        while not func() and a < wait_timeout / delay:
            a += 1
            time.sleep(delay)
    return func()


def val_to_boolean(s):
    if s is None: return None
    val = str(s)
    if val.lower() in ['1', 'true', 'yes', 'on', 'y']: return True
    if val.lower() in ['0', 'false', 'no', 'off', 'n']: return False
    return None
