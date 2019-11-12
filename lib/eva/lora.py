__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.5"
"""
LoRa server implementation
"""

import logging
import threading
import socket
import base64

import eva.core
import eva.uc.controller
import rapidjson

from eva.tools import parse_host_port
from eva.tools import netacl_match
from eva import apikey

from netaddr import IPNetwork
from types import SimpleNamespace

config = SimpleNamespace(host=None, port=None, hosts_allow=[])

custom_handlers = {}

default_port = 1700

_flags = SimpleNamespace(dispatcher_active=False)


def subscribe(handler_id, func):
    custom_handlers.setdefault(handler_id, set()).add(func)
    logging.debug('LoRa: added custom handler %s, function %s' %
                  (handler_id, func))
    return True


def unsubscribe(handler_id, func):
    try:
        custom_handlers[handler_id].remove(func)
        logging.debug('LoRa: removed custom handler %s, function %s' %
                      (handler_id, func))
        if not custom_handlers.get(handler_id):
            del custom_handlers[handler_id]
            logging.debug(
                'LoRa: removing custom handler id %s, last handler left' %
                handler_id)
    except:
        return False
    return True


def exec_custom_handler(func, pk, payload, address):
    try:
        func(pk, payload, address)
    except:
        logging.error('LoRa: failed to exec custom handler %s' % func)
        eva.core.log_traceback()


def update_config(cfg):
    try:
        config.host, config.port = parse_host_port(cfg.get('lorawan', 'listen'),
                                                   default_port)
        logging.debug('lorawan.listen = %s:%u' % (config.host, config.port))
    except:
        return False
    try:
        _ha = cfg.get('lorawan', 'hosts_allow')
    except:
        _ha = None
    if _ha:
        try:
            _hosts_allow = list(
                filter(None, [x.strip() for x in _ha.split(',')]))
            config.hosts_allow = [IPNetwork(h) for h in _hosts_allow]
        except:
            logging.error('LoRa: invalid hosts allow acl!')
            config.host = None
            eva.core.log_traceback()
            return False
    if config.hosts_allow:
        logging.debug('lorawan.hosts_allow = %s' % \
                ', '.join([ str(h) for h in config.hosts_allow ]))
    else:
        logging.debug('LoRa.hosts_allow = none')
    return True


def start():
    if not config.host: return False
    _port = config.port if config.port else default_port
    logging.info('Starting LoRa Server, listening at %s:%u' %
                 (config.host, _port))
    eva.core.stop.append(stop)
    _t = threading.Thread(target=_t_dispatcher,
                          name='lora_t_dispatcher',
                          args=(config.host, _port))
    _flags.dispatcher_active = True
    _t.setDaemon(True)
    _t.start()
    return True


def stop():
    _flags.dispatcher_active = False


def check_access(address, data=None):
    return config.hosts_allow and netacl_match(address, config.hosts_allow)


def _t_dispatcher(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((host, port))
    logging.debug('LoRa dispatcher started')
    while _flags.dispatcher_active:
        try:
            data, addr = server_socket.recvfrom(16384)
            if not _flags.dispatcher_active: return
            if not data: continue
            address = addr[0]
            logging.debug('LoRa server packet from %s' % address)
            if not check_access(address, data):
                logging.warning(
                    'LoRa packet' +
                    ' from %s denied by server configuration' % \
                            address)
                continue
            if len(data) < 13:
                logging.warning('LoRa invalid packet from {}'.format(address))
            if data[0] != 2:
                logging.warning(
                    'LoRa packet from {}, protocol {} is not supported'.format(
                        address, data[0]))
            if data[3] != 0:
                logging.debug(
                    'LoRa packet from {}: packets of type {} are not supported'.
                    format(addres, data[3]))
                continue
            try:
                rxpk = rapidjson.loads(data[12:].decode())['rxpk']
            except:
                logging.warning('LoRa invalid JSON from {}'.format(address))
                continue
            server_socket.sendto(b'\x02' + data[1:3] + b'\x01', addr)
            for pk in rxpk:
                try:
                    payload = base64.b64decode(pk['data'])
                except:
                    logging.warning('LoRa invalid pk from {}'.format(address))
                    continue
                for i, hs in custom_handlers.items():
                    for h in hs:
                        try:
                            t = threading.Thread(target=exec_custom_handler,
                                                 args=(h, pk, payload, address))
                            t.start()
                        except:
                            eva.core.log_traceback()
        except:
            logging.critical('LoRa dispatcher crashed, restarting')
            eva.core.log_traceback()
    logging.debug('LoRa dispatcher stopped')
