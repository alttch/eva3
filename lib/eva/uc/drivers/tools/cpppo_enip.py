__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "GNU GPL v3"
__version__ = "3.4.1"
"""
Helper module for cpppo.server.enip.client

Requires cpppo (https://github.com/pjkundert/cpppo/) module

The helper module contains parts of cpppo code and licensed under GNU General
Public License v3.
"""

import threading
import logging
import timeouter as to

from eva.core import log_traceback, config as core_config

if not core_config.development:
    for x in ['enip', 'cpppo']:
        logging.getLogger(x).setLevel(logging.WARNING)

try:
    from cpppo.server.enip.client import (connector, parse_operations, recycle,
                                          device)
    from cpppo.server.enip.get_attribute import proxy
except:
    logging.error('unable to import cpppo module')
    log_traceback()

from types import GeneratorType


class SafeProxy(proxy):
    """
    Helper class for cpppo client proxy

    Keeps the connection stable (self.op_retries = attempts)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._proxy_lock = threading.RLock()
        self.op_retries = 1

    def operate(self, fn, *args, **kwargs):
        """
        call proxy function

        e.g. operate('read', *args, **kwargs)
        """
        for x in range(self.op_retries + 1):
            if not to.has(self.timeout):
                raise TimeoutError
            try:
                result = getattr(self, fn)(*args, **kwargs)
                if isinstance(result, GeneratorType):
                    result = list(result)
                if not result:
                    raise Exception
                return result
            except:
                if not to.has(self.timeout):
                    raise TimeoutError
                if not self._proxy_lock.acquire(timeout=to.get(check=True)):
                    raise TimeoutError('lock timeout')
                try:
                    if not to.has(self.timeout):
                        raise TimeoutError
                    try:
                        self.close_gateway()
                    except:
                        log_traceback()
                    if not to.has(self.timeout):
                        raise TimeoutError
                    try:
                        self.open_gateway()
                    except:
                        log_traceback()
                finally:
                    self._proxy_lock.release()
        else:
            raise RuntimeError(
                f'Unable to communicate with EnIP ({self.host}:{self.port})')


def operate(host='localhost',
            port=44818,
            tags=[],
            udp=False,
            broadcast=False,
            timeout=5,
            repeat=1,
            depth=1,
            fragment=False,
            route_path=None,
            send_path='',
            simple=False,
            multiple=False,
            priority_time_tick=5,
            timeout_ticks=157):
    """
    Read/write specified EthernetIP tags

    Function arguments are similar to cpppo.server.enip.client command line
    arguments.

    Args:
        host: host to connect (default: localhost)
        port: port to connect (44818)
        tags: list of tag operations, e.g. TAG1, TAG2[0-2], TAG3[5]=5,
            TAG4=77.99 (refer to client CLI for more help)
        udp: use UDP/IP (default: False)
        broadcast: allow multiple peers, and use of broadcast address (default:
            False)
        timeout: EIP timeout (default: 5s)
        repeat: times to repeat request (default: 1)
        depth: pipeline requests to this depth (default: 1)
        fragment: always use read/write tag fragmented requests (default: False)
        route_path: <port>/<link> or JSON (default: '[{"port": 1, "link":
            0}]'); 0/false to specify no/empty route_path
        send_path: send Path to UCMM (default: @6/1); specify an empty string
            '' for no send path
        simple: access a simple (non-routing) EIP CIP device (eg. MicroLogix,
            default: False)
        multiple: use multiple service packet request targeting ~500 bytes
            (default: False)
        priority_time_tick: timeout tick length N range (0,15) (default: 5 ==
            32), where each tick is 2**N ms. Eg. 0 ==> 1ms., 5 ==> 32ms., 15 ==>
            32768ms
        timeout_ticks: timeout duration ticks in range (1,255) (default: 157 ==
            5024ms)
    Returns:
        tuple (result, failures) where result is a list of operation results
        (lists for get, True for set) and failures is a number of failed
        operations
    Raises:
        socket exceptions if connection has been failed
    """
    addr = (host, port)
    multiple = 500 if multiple else 0
    # route_path may be None/0/False/'[]', send_path may be None/''/'@2/1'.
    # simple designates '[]', '' respectively, appropriate for non-routing CIP
    # devices, eg. MicroLogix, PowerFlex, ...
    route_path   = device.parse_route_path( route_path ) if route_path \
                                      else [] if simple else None
    send_path   = send_path                if send_path \
                                      else '' if simple else None
    failures = 0
    transactions = []
    with connector(host=addr[0],
                   port=addr[1],
                   timeout=timeout,
                   udp=udp,
                   broadcast=broadcast) as connection:
        if tags:
            operations = parse_operations(recycle(tags, times=repeat),
                                          route_path=route_path,
                                          send_path=send_path,
                                          timeout_ticks=timeout_ticks,
                                          priority_time_tick=priority_time_tick)
            failed, transactions = connection.process(operations=operations,
                                                      depth=depth,
                                                      multiple=multiple,
                                                      fragment=fragment,
                                                      printing=False,
                                                      timeout=timeout)
            failures += failed
    return transactions, failures
