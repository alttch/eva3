__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.6"

import eva.core
import threading
import logging
import importlib

from eva.tools import parse_host_port
from eva.tools import netacl_match

from netaddr import IPNetwork
from types import SimpleNamespace
from pyaltt import background_worker

subscribed_items = set()

config = SimpleNamespace(host=None, port=None, community=None, hosts_allow=[])
entities = SimpleNamespace(snmpEngine=None)

default_port = 162
default_community = 'eva'


def update_config(cfg):
    try:
        config.host, config.port = parse_host_port(
            cfg.get('snmptrap', 'listen'), default_port)
        logging.debug('snmptrap.listen = %s:%u' % (config.host, config.port))
    except:
        return False
    try:
        config.community = cfg.get('snmptrap', 'community')
    except:
        config.community = default_community
    logging.debug('snmptrap.community = %s' % config.community)
    try:
        _ha = cfg.get('snmptrap', 'hosts_allow')
    except:
        _ha = None
    if _ha:
        try:
            _hosts_allow = list(
                filter(None, [x.strip() for x in _ha.split(',')]))
            config.hosts_allow = [IPNetwork(h) for h in _hosts_allow]
        except:
            logging.error('snmptrap bad host acl!')
            config.host = None
            eva.core.log_traceback()
            return False
    if config.hosts_allow:
        logging.debug('snmptrap.hosts_allow = %s' % \
                ', '.join([ str(h) for h in config.hosts_allow ]))
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
    if config.hosts_allow:
        if not netacl_match(host, config.hosts_allow):
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
    if not config.host: return False
    _port = config.port if config.port else default_port
    _community = config.community if config.community else default_community
    try:
        engine = importlib.import_module('pysnmp.entity.engine')
        snmp_config = importlib.import_module('pysnmp.entity.config')
        udp = importlib.import_module('pysnmp.carrier.asyncore.dgram.udp')
        ntfrcv = importlib.import_module('pysnmp.entity.rfc3413.ntfrcv')
    except:
        logging.error(
            'Unable to import pysnmp module')
        eva.core.log_traceback()
        return False
    try:
        entities.snmpEngine = engine.SnmpEngine()
        snmp_config.addTransport(
            entities.snmpEngine, udp.domainName + (1,),
            udp.UdpTransport().openServerMode((config.host, _port)))
    except:
        logging.error(
            'Can not bind SNMP handler to %s:%s' % (config.host, _port))
        eva.core.log_traceback()
        return False
    logging.info('Starting SNMP trap handler, listening at %s:%u' % \
            (config.host, _port))
    try:
        snmp_config.addV1System(entities.snmpEngine, eva.core.product.code,
                                _community)
        ntfrcv.NotificationReceiver(entities.snmpEngine, __cbFun)
        entities.snmpEngine.transportDispatcher.jobStarted(1)
        eva.core.stop.append(stop)
        dispatcher.start(entities.snmpEngine)
    except:
        logging.error(
            'Failed to start SNMP trap handler. Try updating pysnmp library')
        eva.core.log_traceback()
    return True


def stop():
    try:
        entities.snmpEngine.transportDispatcher.jobFinished(1)
        entities.snmpEngine.transportDispatcher.closeDispatcher()
    except:
        pass
    dispatcher.stop()


@background_worker(name='snmp_trap_dispatcher')
def dispatcher(snmpEngine, **kwargs):
    try:
        snmpEngine.transportDispatcher.runDispatcher()
    except:
        snmpEngine.transportDispatcher.closeDispatcher()
        logging.error('SNMP trap dispatcher crashed, restarting')
        eva.core.log_traceback()
