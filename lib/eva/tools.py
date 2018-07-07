__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "3.1.0"

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


def format_json(obj, minimal=False, unpicklable=False):
    return json.dumps(json.loads(jsonpickle.encode(obj,
            unpicklable = unpicklable)), indent=4, sort_keys=True) \
                if not minimal else jsonpickle.encode(obj, unpicklable = False)


def fname_remove_unsafe(fname):
    return fname.replace('/', '').replace('..', '')


def print_json(obj):
    print(format_json(obj))


def parse_host_port(hp, default_port=None):
    if hp is None: return (None, default_port)
    if hp.find(':') == -1: return (hp, default_port)
    try:
        host, port = hp.split(':')
        port = int(port)
    except:
        eva.core.log_traceback()
        return (None, default_port)
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


def is_oid(oid):
    if oid is None: return False
    return oid.find(':') != -1

def parse_oid(oid):
    if oid is None: return None, None
    try:
        tp, i = oid.split(':')
    except:
        return None, None
    return tp, i

def oid_to_id(oid, required=None):
    if not is_oid(oid): return oid
    tp, i = parse_oid(oid)
    if tp is None or i is None: return None
    if required and tp != required: return None
    return i

