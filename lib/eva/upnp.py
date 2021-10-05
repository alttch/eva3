__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.2"
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
EVA-version: 3.3.0
EVA-build: xxxxxxxx
EVA-product: <uc|lm>
EVA-controller-id: <uc|lm>/<system name>
EVA-host: <system name>
ST: altertech_evaics:<uc|lm>
USN: uuid:UNIQUE_INSTALLATION_ID
Cache-Control: max-age: 60
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

from eva.tools import parse_host_port

from eva.tools import SimpleNamespace

from neotasker import background_worker

config = SimpleNamespace(host=None,
                         broadcast='239.255.255.250',
                         discover=False,
                         discovery_interfaces=None)
port = 1900

_data = SimpleNamespace(discover_ports=())

response_msg = 'HTTP/1.1 200 OK\r\n' + '\r\n'.join([
    '{}: {}'.format(x[0], x[1])
    for x in [('Ext', ''), ('Host', socket.getfqdn()),
              ('Location', '{location}'), ('EVA-version', '{version}'),
              ('EVA-build', '{build}'), ('EVA-product', '{product}'),
              ('EVA-controller-id',
               '{product}/{system_name}'), ('EVA-host', '{system_name}'),
              ('ST', 'altertech_evaics:{product}'), ('USN', 'uuid:{usn}'),
              ('Cache-Control', 'max-age: 60')]
]) + '\r\n'

_flags = SimpleNamespace(dispatcher_active=False)


def update_config(cfg):
    try:
        config.host = cfg.get('upnp/listen')
    except LookupError:
        pass
    logging.debug(f'upnp.listen = {config.host}')
    # for tests only, undocumented
    try:
        config.broadcast = cfg.get('upnp/broadcast-ip')
    except LookupError:
        pass
    logging.debug(f'upnp.broadcast_ip = {config.broadcast}')
    try:
        interfaces = cfg.get('upnp/discover-on')
        if not isinstance(interfaces, list):
            interfaces = [interfaces]
        config.interfaces = interfaces
        config.discover = True
    except LookupError:
        pass
    logging.debug('upnp.discover_controllers = ' +
                  ('enabled' if config.discover else 'disabled'))
    if config.discover:
        logging.debug('upnp.discover_on = ' +
                      (', '.join(config.discovery_interfaces) if config.
                       discovery_interfaces else 'all'))
    return True


# use threading until asyncio have all required features
def discover(st,
             ip='239.255.255.250',
             port=1900,
             mx=True,
             interface=None,
             trailing_crlf=True,
             parse_data=True,
             discard_headers=['Cache-control', 'Host'],
             timeout=None):
    """
    discover uPnP equipment

    Args:
        st: service type
        ip: multicast ip
        port: multicast port
        mx: use MX header (=timeout)
        interface: network interface (None - scan all)
        trailing_crlf: put trailing CRLF at the end of msg
        parse_data: if False, raw data will be returned
        discard_headers: headers to discard (if parse_data is True)
        timeout: socket timeout (for a single interface)

    Returns:
        if data is parsed: list of dicts, where IP=equipment IP, otherwise
        dict, where key=equipment IP addr, value=raw ssdp reply. Note: if data
        is parsed, all variables are converted to lowercase and capitalized.
    """

    def _t_discover_on_interface(iface, addr, msg, timeout):
        logging.debug('ssdp scan {}:{}'.format(iface, addr))
        result = {}
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST,
                         math.ceil(timeout))
            s.bind((addr, 0))
            s.settimeout(timeout)
            s.sendto(msg, (ip, port))
        except:
            logging.info('ssdp unable to scan ({}:{}:{}/{})'.format(
                iface, addr, port, st))
            return
        try:
            while True:
                data, addr = s.recvfrom(65507)
                if addr[0] not in result:
                    try:
                        data = data.decode('utf-8')
                        if parse_data:
                            data = data.split('\r\n')
                            if not data[0].endswith(' 200 OK'):
                                raise Exception(
                                    'Invalid header data from {}: {}'.format(
                                        addr[0], data[0]))
                            result[addr[0]] = {}
                            for d in data[1:]:
                                if d:
                                    k, v = d.split(':', 1)
                                    k = k.lower().capitalize()
                                    if k not in discard_headers:
                                        result[addr[0]][k] = v.lstrip()
                        else:
                            result[addr[0]] = data
                    except:
                        eva.core.log_traceback()
        except socket.timeout:
            pass
        except:
            eva.core.log_traceback()
            logging.error('ssdp scan error ({}:{}:{}/{})'.format(
                iface, addr, port, st))
        return result

    _timeout = timeout if timeout else eva.core.config.timeout
    req = [
        'M-SEARCH * HTTP/1.1', 'HOST: {}:{}'.format(ip, port),
        'MAN: "ssdp:discover"', 'ST: ' + st
    ]
    if mx:
        req += ['MX: {}'.format(_timeout)]
    msg = ('\r\n'.join(req) + '\r\n' if trailing_crlf else '').encode('utf-8')
    if interface:
        its = interface if isinstance(interface, list) else [interface]
    else:
        its = netifaces.interfaces()
    futures = []
    for iface in its:
        try:
            inet = netifaces.ifaddresses(iface)[netifaces.AF_INET]
            addr, broadcast = inet[0]['addr'], inet[0]['broadcast']
        except:
            logging.debug(
                'ssdp scan: skipping interface {}, no ip addr or broadcast'.
                format(iface))
            continue
        futures.append(
            eva.core.spawn(_t_discover_on_interface, iface, addr, msg,
                           _timeout))
    result = {}
    for f in futures:
        try:
            data = f.result()
            if data:
                result.update(data)
        except:
            eva.core.log_traceback()
    if parse_data:
        r = []
        for i, v in result.items():
            d = {'IP': i}
            d.update(v)
            r.append(d)
        return r
    else:
        return result


def start():
    if config.host:
        logging.info('Starting UPnP response server, listening at %s:%u' %
                     (config.host, port))
        eva.core.stop.append(stop)
        _t = threading.Thread(target=_t_dispatcher,
                              name='upnp_t_dispatcher',
                              args=(config.host, port))
        _flags.dispatcher_active = True
        _t.setDaemon(True)
        _t.start()
    if config.discover:
        discovery_worker.start()
    return True


@eva.core.stop
def stop():
    if config.discover:
        discovery_worker.stop()
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
                response_msg.format(system_name=eva.core.config.system_name,
                                    location=location,
                                    version=eva.core.version,
                                    build=eva.core.product.build,
                                    product=eva.core.product.code,
                                    usn=eva.core.product.usn).encode('utf-8'),
                addr)
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
            if not _flags.dispatcher_active:
                return
            if not data:
                continue
            address = addr[0]
            logging.debug('UPnP packet from %s' % address)
            data = data.decode('utf-8').strip().replace('\r', '').split('\n')
            if not data[0].lower().startswith('m-search * http/1'):
                continue
            headers = {}
            for d in data[1:]:
                try:
                    k, v = d.split(': ', 1)
                    headers[k.lower()] = v.lower().replace('"', '')
                except:
                    pass
            if headers.get('man') == 'ssdp:discover' and \
                    headers.get('st') in \
                    [ 'upnp:rootdevice', 'altertech_evaics', 'upnp:all',
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


@background_worker(interval=120, on_error=eva.core.log_traceback)
def discovery_worker(**kwargs):
    import eva.api
    from eva.core import spawn, log_traceback, is_shutdown_requested
    futures = []
    for p in _data.discover_ports:
        logging.debug(f'Starting UPnP discovery, port {p}')
        futures.append(
            spawn(discover,
                  'altertech_evaics',
                  ip=config.broadcast,
                  port=p,
                  mx=False,
                  interface=config.discovery_interfaces))
    for f in futures:
        try:
            result = f.result()
            if is_shutdown_requested():
                break
            for data in result:
                controller_id = data.get('Eva-controller-id')
                location = data.get('Location')
                if controller_id and location:
                    spawn(eva.api.controller_discovery_handler, 'UPnP',
                          controller_id, location)
        except:
            log_traceback()
