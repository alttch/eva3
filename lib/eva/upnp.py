__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.6"
"""
UPnP services

Controllers listen on ports:

UC: 1911
LM: 1912

Request example:

M-SEARCH * HTTP/1.1
Host: ......
Man: "ssdp:discover"
St: altertech_evaics[:uc|lm]

Response:

HTTP/1.1 200 OK
Ext:
Host: <hostname>
Location: http(s)://IP:PORT
EVA-version: 3.2.6
EVA-build: xxxxxxxx
EVA-controller: <uc|lm>
EVA-host: <system name>
St: altertech_evaics:<uc|lm>
Usn: uuid:UNIQUE_INSTALLATION_ID
Cache-control: max-age: 60
"""

import logging
import threading
import socket
import math
import time
import random
import textwrap
import netaddr
import netifaces
import platform

import eva.core
import eva.uc.controller

from eva.tools import parse_host_port

from types import SimpleNamespace

config = SimpleNamespace(host=None)
port = 1900

# TODO: installation USN
response_msg = 'HTTP/1.1 200 OK\r\n' + '\r\n'.join([
    '{}: {}'.format(x[0], x[1]) for x in
    [('Ext', ''), ('Host', socket.getfqdn()), ('Location', '{location}'),
     ('EVA-version', '{version}'), ('EVA-build', '{build}'),
     ('EVA-controller', '{product}'), ('EVA-host', '{system_name}'),
     ('ST', 'altertech_evaics:{product}'), ('Cache-control', 'max-age: 60')]
]) + '\r\n'

_flags = SimpleNamespace(dispatcher_active=False)


def update_config(cfg):
    try:
        config.host = cfg.get('upnp', 'listen')
        logging.debug(f'upnp.listen = {config.host}')
        return True
    except:
        return False


def start():
    if not config.host: return False
    logging.info('Starting UPnP response server, listening at %s:%u' %
                 (config.host, port))
    eva.core.stop.append(stop)
    _t = threading.Thread(target=_t_dispatcher,
                          name='upnp_t_dispatcher',
                          args=(config.host, port))
    _flags.dispatcher_active = True
    _t.setDaemon(True)
    _t.start()
    return True


def stop():
    _flags.dispatcher_active = False


def find_api_location_for(host):

    import eva.api

    host_addr = netaddr.IPAddress(host)

    api_host = eva.api.config.ssl_host
    if api_host:
        proto = 'https'
        port = eva.api.config.ssl_port
    else:
        api_host = eva.api.config.host
        proto = 'http'
        port = eva.api.config.port
    api_addr = netaddr.IPAddress(api_host)

    for iface in netifaces.interfaces():
        try:
            for a in netifaces.ifaddresses(iface)[netifaces.AF_INET]:
                network = netaddr.IPNetwork(a['addr'] + '/' + a['netmask'])
                if host_addr in network and (api_host == '0.0.0.0' or
                                             api_addr in network):
                    return '{}://{}:{}'.format(proto, a['addr'], port)
        except:
            pass
    return None


def send_response(addr, mx=0):
    try:
        location = find_api_location_for(addr[0])
        if location:
            if mx > 0:
                time.sleep(random.uniform(0, min(5, mx)))
            logging.debug(f'sending UPnP reply to {addr[0]}')
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(
                response_msg.format(
                    system_name=eva.core.config.system_name,
                    location=location,
                    version=eva.core.version,
                    build=eva.core.product.build,
                    product=eva.core.product.code).encode('utf-8'), addr)
        else:
            logging.debug('skipping UPnP reply to ' +
                          f'{addr[0]}, no suitable API address found')
    except:
        eva.core.log_traceback()


def _t_dispatcher(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM,
                                  socket.IPPROTO_UDP)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST,
                             math.ceil(eva.core.config.timeout))
    server_socket.bind((host, port))
    logging.debug('UPnP dispatcher started')
    while _flags.dispatcher_active:
        try:
            data, addr = server_socket.recvfrom(4096)
            if not _flags.dispatcher_active: return
            if not data: continue
            address = addr[0]
            logging.debug('UPnP packet from %s' % address)
            data = data.decode('utf-8').strip().replace('\r', '').split('\n')
            if not data[0].lower().startswith('m-search * http/1'): continue
            headers = {}
            for d in data[1:]:
                try:
                    k, v = d.split(': ', 1)
                    headers[k.lower()] = v.lower().replace('"', '')
                except:
                    pass
            if headers.get('man') == 'ssdp:discover' and \
                    headers.get('st') in \
                        [ 'upnp:rootdevice', 'altertech_evaics',
                                'altertech_evaics:' + eva.core.product.code]:
                try:
                    mx = int(headers.get('mx'))
                except:
                    mx = 0
                eva.core.spawn(send_response, addr, mx)
        except:
            logging.critical('UPnP dispatcher crashed, restarting')
            eva.core.log_traceback()
    logging.debug('UPnP dispatcher stopped')
