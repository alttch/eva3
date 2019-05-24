import socket
import logging

from eva.uc.driverapi import get_timeout
from eva.uc.driverapi import log_traceback


def discover(st,
             ip='239.255.255.250',
             port=1900,
             mx=True,
             trailing_crlf=True,
             parse_data=True,
             timeout=None):
    """
    Args:
        st: service type
        ip: multicast ip
        port: multicast port
        mx: use MX header (=timeout)
        trailing_crlf: put trainling CRLF at the end of msg
        parse_data: if False, raw data will be returned
        timeout: socket timeout

    Returns:
        dict, where key=equipment IP addr, value=dict of variables (or raw)
    """
    t = timeout if timeout else get_timeout()
    req = [
        'M-SEARCH * HTTP/1.1', 'HOST: {}:{}'.format(ip, port),
        'MAN: "ssdp:discover"', 'ST: ' + st
    ]
    if mx:
        req += ['MX: {}'.format(t)]
    msg = ('\r\n'.join(req) + '\r\n' if trailing_crlf else '').encode('utf-8')
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, t)
    s.settimeout(t)
    s.sendto(msg, (ip, port))
    result = {}
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
                                result[addr[0]][k] = v.lstrip()
                    else:
                        result[addr[0]] = data
                except:
                    log_traceback()
    except socket.timeout:
        pass
    except:
        log_traceback()
        logging.error('ssdp scan error ({}:{}/{})'.format(ip, port, st))
    return result
