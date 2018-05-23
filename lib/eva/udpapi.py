__author__ = "Altertech Group, http://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2017 Altertech Group"
__license__ = "See http://www.eva-ics.com/"
__version__ = "3.0.2"
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

import eva.core
import eva.uc.controller

from eva.tools import parse_host_port
from eva.tools import netacl_match

from netaddr import IPNetwork

host = None
port = None
hosts_allow = []

default_port = 8881

_t_dispatcher_active = False

server_socket = None


def update_config(cfg):
    global host, port, hosts_allow
    try:
        host, port = parse_host_port(cfg.get('udpapi', 'listen'))
        if not port:
            port = default_port
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
            logging.error('udpapi bad host acl!')
            host = None
            eva.core.log_traceback()
            return False
    if hosts_allow:
        logging.debug('udpapi.hosts_allow = %s' % \
                ', '.join([ str(h) for h in hosts_allow ]))
    else:
        logging.debug('udpapi.hosts_allow = 0.0.0.0/0')
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
            data = data.decode()
            logging.debug('UDP API cmd from %s' % address)
            if hosts_allow:
                if not netacl_match(address, hosts_allow):
                    logging.warning(
                        'UDP API from %s denied by server configuration' % \
                                address)
                    continue
            try:
                cmd = data.split(' ')
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
                logging.debug('udp cmd data item_id = %s' % item_id)
                logging.debug('udp cmd data update = %s' % update)
                logging.debug('udp cmd data status = %s' % status)
                logging.debug('udp cmd data value = "%s"' % value)
                logging.debug('udp cmd data priority = "%s"' % priority)
                item = None
                if status: status = int(status)
                if priority: priority = int(priority)
                item = eva.uc.controller.get_item(item_id)
                if not item:
                    logging.warning('UDP API item unknown %s' % item_id)
                    continue
                if not item.item_type in ['unit', 'sensor']:
                    logging.warning(
                            'UDP API: item %s must be unit or sensor' % \
                                    item_id)
                    continue
                if update:
                    item.update_set_state(status, value)
                else:
                    if item.item_type in ['unit']:
                        if status is None:
                            logging.warning('UDP API no status - no action')
                        else:
                            eva.uc.controller.exec_unit_action(
                                item_id, status, value, priority)
                    else:
                        logging.warning(
                                'UDP API no action for %s' % \
                                item.item_type)
            except:
                logging.warning('UDP API received bad cmd data from %s' % \
                        address)
                eva.core.log_traceback()
        except:
            logging.critical('UDP API dispatcher crashed, restarting')
            eva.core.log_traceback()
    logging.debug('UDP API dispatcher stopped')
