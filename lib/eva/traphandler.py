__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.1.1"

import eva.core
import threading
import logging
import importlib

from eva.tools import parse_host_port
from eva.tools import netacl_match

from netaddr import IPNetwork

subscribed_items = set()

host = None
port = None
community = None
hosts_allow = []

default_port = 162
default_community = 'eva'

_t_dispatcher_active = False

_t_dispatcher = None


def update_config(cfg):
    global host, port, community, hosts_allow
    try:
        host, port = parse_host_port(
            cfg.get('snmptrap', 'listen'), default_port)
        logging.debug('snmptrap.listen = %s:%u' % (host, port))
    except:
        return False
    try:
        community = cfg.get('snmptrap', 'community')
    except:
        community = default_community
    logging.debug('snmptrap.community = %s' % community)
    try:
        _ha = cfg.get('snmptrap', 'hosts_allow')
    except:
        _ha = None
    if _ha:
        try:
            _hosts_allow = list(
                filter(None, [x.strip() for x in _ha.split(',')]))
            hosts_allow = [IPNetwork(h) for h in _hosts_allow]
        except:
            logging.error('snmptrap bad host acl!')
            host = None
            eva.core.log_traceback()
            return False
    if hosts_allow:
        logging.debug('snmptrap.hosts_allow = %s' % \
                ', '.join([ str(h) for h in hosts_allow ]))
    else:
        logging.debug('snmptrap.hosts_allow = 0.0.0.0/0')
    return True


def subscribe(item):
    subscribed_items.add(item)
    logging.debug('%s subscribed to snmp traps' % item.oid)
    return True


def unsubscribe(item):
    try:
        subscribed_items.remove(item)
        logging.debug('%s unsubscribed from snmp traps' % item.oid)
    except:
        return False
    return True


def __cbFun(snmpEngine, stateReference, contextEngineId, contextName, varBinds,
            cbCtx):
    transportDomain, transportAddress = \
            snmpEngine.msgAndPduDsp.getTransportInfo(stateReference)
    host = transportAddress[0]
    logging.debug('snmp trap from %s' % host)
    if hosts_allow:
        if not netacl_match(host, hosts_allow):
            logging.warning(
                'snmp trap from %s denied by server configuration' % host)
            return
    data = {}
    for name, val in varBinds:
        logging.debug('snmp trap host: %s, data %s = %s' % \
                (host, name.prettyPrint(), val.prettyPrint()))
        data[name.prettyPrint()] = val.prettyPrint()
    for i in subscribed_items:
        t = threading.Thread(target=i.process_snmp_trap, args=(host, data))
        t.start()


def start():
    global _t_dispatcher
    global _t_dispatcher_active
    global snmpEngine
    if not host: return False
    if not port: _port = default_port
    else: _port = port
    if not community: _community = default_community
    else: _community = community
    try:
        engine = importlib.import_module('pysnmp.entity.engine')
        config = importlib.import_module('pysnmp.entity.config')
        udp = importlib.import_module('pysnmp.carrier.asyncore.dgram.udp')
        ntfrcv = importlib.import_module('pysnmp.entity.rfc3413.ntfrcv')
    except:
        logging.error(
            'Failed to import SNMP modules. Try updating pysnmp library')
        eva.core.log_traceback()
        return False
    try:
        snmpEngine = engine.SnmpEngine()
        config.addTransport(snmpEngine, udp.domainName + (1,),
                            udp.UdpTransport().openServerMode((host, _port)))
    except:
        logging.error('Can not bind SNMP handler to %s:%s' % (host, _port))
        eva.core.log_traceback()
        return False
    logging.info('Starting SNMP trap handler, listening at %s:%u' % \
            (host, _port))
    try:
        config.addV1System(snmpEngine, eva.core.product_code, _community)
        ntfrcv.NotificationReceiver(snmpEngine, __cbFun)
        snmpEngine.transportDispatcher.jobStarted(1)
        eva.core.append_stop_func(stop)
        _t_dispatcher = threading.Thread(
            target=_t_dispatcher,
            name='traphandler_t_dispatcher',
            args=(snmpEngine,))
        _t_dispatcher_active = True
        _t_dispatcher.start()
    except:
        logging.error(
            'Failed to start SNMP trap handler. Try updating pysnmp library')
        eva.core.log_traceback()
    return True


def stop():
    global _t_dispatcher_active
    if _t_dispatcher_active:
        _t_dispatcher_active = False
        try:
            snmpEngine.transportDispatcher.jobFinished(1)
            snmpEngine.transportDispatcher.closeDispatcher()
        except:
            pass
        _t_dispatcher.join()


def _t_dispatcher(snmpEngine):
    logging.debug('SNMP trap dispatcher started')
    while _t_dispatcher_active:
        try:
            snmpEngine.transportDispatcher.runDispatcher()
        except:
            snmpEngine.transportDispatcher.closeDispatcher()
            logging.error('SNMP trap dispatcher crashed, restarting')
            eva.core.log_traceback()
    logging.debug('SNMP trap dispatcher stopped')
