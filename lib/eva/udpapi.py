__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "3.1.1"
"""
Simple UDP API for controlling and updating

Useful for communicating with UC from simple controllers
like Arduino, connected with Ethernet - doesn't require any
libraries and very simple to code

Just send UDP packet and that's it

Cons: simple
Pros: doesn't give any warranty the packet was delivered

Recommended usage:

monitoring sensor activity for sensors like PIR,
when the controller is coded to send a lot of the same data

UDP packet format:

<item_id> [u] <status> [value] [priority]

u for update status, otherwise exec action

status - new status
value - new value

to keep existing, use null as status/value

to set value to "", just send double space at the end of packet
"""

import logging
import threading
import socket
import base64
import hashlib

import eva.core
import eva.uc.controller

from eva.tools import parse_host_port
from eva.tools import netacl_match
from eva import apikey

from netaddr import IPNetwork
from cryptography.fernet import Fernet

host = None
port = None
hosts_allow = []
hosts_allow_encrypted = []
custom_handlers = {}

default_port = 8881

_t_dispatcher_active = False

server_socket = None


def subscribe(handler_id, func):
    custom_handlers.setdefault(handler_id, set()).add(func)
    logging.debug(
        'UDP API: added custom handler %s, function %s' % (handler_id, func))
    return True


def unsubscribe(handler_id, func):
    try:
        custom_handlers[handler_id].remove(func)
        logging.debug('UDP API: removed custom handler %s, function %s' %
                      (handler_id, func))
        if not custom_handlers.get(handler_id):
            del custom_handlers[handler_id]
            logging.debug(
                'UDP API: removing custom handler id %s, last handler left' %
                handler_id)
    except:
        return False
    return True


def update_config(cfg):
    global host, port, hosts_allow, hosts_allow_encrypted
    try:
        host, port = parse_host_port(cfg.get('udpapi', 'listen'), default_port)
        logging.debug('udpapi.listen = %s:%u' % (host, port))
    except:
        return False
    try:
        _ha = cfg.get('udpapi', 'hosts_allow')
    except:
        _ha = None
    if _ha:
        try:
            _hosts_allow = list(
                filter(None, [x.strip() for x in _ha.split(',')]))
            hosts_allow = [IPNetwork(h) for h in _hosts_allow]
        except:
            logging.error('udpapi: invalid hosts allow acl!')
            host = None
            eva.core.log_traceback()
            return False
    if hosts_allow:
        logging.debug('udpapi.hosts_allow = %s' % \
                ', '.join([ str(h) for h in hosts_allow ]))
    else:
        logging.debug('udpapi.hosts_allow = none')
    try:
        _ha = cfg.get('udpapi', 'hosts_allow_encrypted')
    except:
        _ha = None
    if _ha:
        try:
            _hosts_allow = list(
                filter(None, [x.strip() for x in _ha.split(',')]))
            hosts_allow_encrypted = [IPNetwork(h) for h in _hosts_allow]
        except:
            logging.error('udpapi: invalid encrypted hosts allow acl!')
            host = None
            eva.core.log_traceback()
            return False
    if hosts_allow_encrypted:
        logging.debug('udpapi.hosts_allow_encrypted = %s' % \
                ', '.join([ str(h) for h in hosts_allow_encrypted ]))
    else:
        logging.debug('udpapi.hosts_allow_encrypted = none')
    return True


def start():
    global _t_dispatcher_active
    if not host: return False
    if not port: _port = default_port
    else: _port = port

    logging.info('Starting UDP API, listening at %s:%u' % (host, _port))
    eva.core.append_stop_func(stop)
    _t = threading.Thread(
        target=_t_dispatcher, name='udpapi_t_dispatcher', args=(host, _port))
    _t_dispatcher_active = True
    _t.setDaemon(True)
    _t.start()
    return True


def stop():
    global _t_dispatcher_active
    _t_dispatcher_active = False


def check_access(address, data):
    if data[0] == '|':
        return hosts_allow_encrypted and netacl_match(address,
                                                      hosts_allow_encrypted)
    else:
        return hosts_allow and netacl_match(address, hosts_allow)


def _t_dispatcher(host, port):
    global server_socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((host, port))
    logging.debug('UDP API dispatcher started')
    while _t_dispatcher_active:
        try:
            data, address = server_socket.recvfrom(256)
            if not _t_dispatcher_active: return
            address = address[0]
            logging.debug('UDP API cmd from %s' % address)
            if not check_access(address, data):
                logging.warning(
                    'UDP API from %s denied by server configuration' % \
                            address)
                continue
            if data[0] == 1:
                try:
                    p, handler, dt = data.split(b'\x01', 2)
                    handler = handler.decode()
                except:
                    logging.warning(
                        'UDP API: invalid custom packet from %s' % address)
                    continue
                if not handler in custom_handlers or \
                        not custom_handlers.get(handler):
                    logging.warning('UDP API: no handlers for %s from %s' %
                                    (handler, address))
                    continue
                for h in custom_handlers.get(handler):
                    try:
                        h(dt, address)
                    except:
                        eva.core.log_traceback()
                continue
            data = data.decode()
            if data[0] == '|':
                try:
                    x, api_key_id, data = data.split('|', 2)
                    api_key = apikey.key_by_id(api_key_id)
                    if api_key is None:
                        logging.warning('UDP API: invalid api key id in' + \
                                ' encrypted packet from %s' % address)
                        continue
                    _k = base64.b64encode(
                        hashlib.sha256(api_key.encode()).digest())
                    try:
                        data = Fernet(_k).decrypt(data.encode()).decode()
                    except:
                        logging.warning('UDP API: invalid api key in' + \
                                ' encrypted packet from %s' % address)
                        continue
                except:
                    logging.warning('UDP API: received invalid encrypted' + \
                                ' packet from %s' % address)
                    eva.core.log_traceback()
                    continue
            else:
                api_key_id = None
                api_key = None
            for _data in data.split('\n'):
                try:
                    if not _data: continue
                    cmd = _data.split(' ')
                    item_id = cmd[0]
                    status = None
                    value = None
                    update = False
                    priority = None
                    if cmd[1] == 'u':
                        update = True
                        status = cmd[2]
                        if len(cmd) > 3:
                            value = cmd[3]
                    else:
                        status = cmd[1]
                        if len(cmd) > 2:
                            value = cmd[2]
                        if len(cmd) > 3:
                            priority = cmd[3]
                    if status == 'None': status = None
                    if value == 'None': value = None
                    if api_key is not None:
                        logging.debug('udp cmd data api_key = %s' % api_key_id)
                    logging.debug('udp cmd data item_id = %s' % item_id)
                    logging.debug('udp cmd data update = %s' % update)
                    logging.debug('udp cmd data status = %s' % status)
                    logging.debug('udp cmd data value = "%s"' % value)
                    logging.debug('udp cmd data priority = "%s"' % priority)
                    item = None
                    if status: status = int(status)
                    if priority: priority = int(priority)
                    item = eva.uc.controller.get_item(item_id)
                    if not item or \
                            (api_key is not None and \
                            not apikey.check(api_key, item)):
                        logging.warning('UDP API item unknown %s' % item_id)
                        continue
                    if not item.item_type in ['unit', 'sensor']:
                        logging.warning(
                            'UDP API: item ' + \
                            '%s must be either unit or sensor from %s' % \
                            item_id, address)
                        continue
                    if update:
                        item.update_set_state(status, value)
                    else:
                        if item.item_type in ['unit']:
                            if status is None:
                                logging.warning(
                                    'UDP API no status - no action from %s' %
                                    address)
                            else:
                                eva.uc.controller.exec_unit_action(
                                    item_id, status, value, priority)
                        else:
                            logging.warning(
                                    'UDP API no action for %s' % \
                                    item.item_type)
                except:
                    logging.warning('UDP API: received invalid cmd data' + \
                            ' from %s' % address)
                    eva.core.log_traceback()
        except:
            logging.critical('UDP API dispatcher crashed, restarting')
            eva.core.log_traceback()
    logging.debug('UDP API dispatcher stopped')
