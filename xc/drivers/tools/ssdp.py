__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.3"

import socket
import logging
import netifaces

from eva.uc.driverapi import get_timeout
from eva.uc.driverapi import log_traceback


def discover(st,
             ip='239.255.255.250',
             port=1900,
             mx=True,
             interface=None,
             trailing_crlf=True,
             parse_data=True,
             discard_headers=['CACHE-CONTROL', 'HOST'],
             timeout=None):
    """
    Args:
        st: service type
        ip: multicast ip
        port: multicast port
        mx: use MX header (=timeout)
        interface: network interface (None - scan all)
        trailing_crlf: put trainling CRLF at the end of msg
        parse_data: if False, raw data will be returned
        discard_headers: headers to discard (if parse_data is True)
        timeout: socket timeout (for a single interface)

    Returns:
        dict, where key=equipment IP addr, value=dict of variables (or raw)
        note that dict of variables has all keys converted to lowercase and
        capitalized
    """
    t = timeout if timeout else get_timeout()
    req = [
        'M-SEARCH * HTTP/1.1', 'HOST: {}:{}'.format(ip, port),
        'MAN: "ssdp:discover"', 'ST: ' + st
    ]
    if mx:
        req += ['MX: {}'.format(t)]
    msg = ('\r\n'.join(req) + '\r\n' if trailing_crlf else '').encode('utf-8')
    if interface:
        its = interface
    else:
        its = netifaces.interfaces()
    result = {}
    for iface in its:
        try:
            inet = netifaces.ifaddresses(iface)[netifaces.AF_INET]
            addr, broadcast = inet[0]['addr'], inet[0]['broadcast']
        except:
            logging.debug(
                'ssdp scan: skipping interface {}, no ip addr or broadcast'.
                format(iface))
            continue
        logging.debug('ssdp scan {}:{}'.format(iface, addr))
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, t)
        s.bind((addr, 0))
        s.settimeout(t)
        s.sendto(msg, (ip, port))
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
                        log_traceback()
        except socket.timeout:
            pass
        except:
            log_traceback()
            logging.error('ssdp scan error ({}:{}:{}/{})'.format(
                iface, addr, port, st))
    return result


# import json
# print(json.dumps(discover('ssdp:all', timeout=10), indent=2, sort_keys=True))
# print(discover('upnp:rootdevice', timeout=2))
