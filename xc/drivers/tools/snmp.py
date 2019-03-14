__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.0"

# SNMP get/set module. Supports SNMPv1 and 2

import pysnmp.hlapi as snmp_engine
import logging
from eva.uc.driverapi import log_traceback


def get(oid,
        host,
        port=161,
        community='public',
        timeout=0,
        retries=0,
        rf=str,
        snmp_ver=2):
    result = []
    try:
        for (err_i, err_st, err_idx, vals) in snmp_engine.getCmd(
                snmp_engine.SnmpEngine(),
                snmp_engine.CommunityData(community, mpModel=snmp_ver - 1),
                snmp_engine.UdpTransportTarget(
                    (host, port), timeout=timeout, retries=retries),
                snmp_engine.ContextData(),
                snmp_engine.ObjectType(snmp_engine.ObjectIdentity(oid))):
            if err_i or err_st:
                logging.debug('snmp error: %s' % err_i)
                return None
            else:
                for v in vals:
                    _v = str(v[1])
                    try:
                        if rf is float: _v = float(_v)
                        if rf is int: _v = int(_v)
                    except:
                        _v = None
                    return _v
    except:
        log_traceback()
        return None


def set(oid,
        value,
        host,
        port=161,
        community='private',
        timeout=0,
        retries=0,
        snmp_ver=2):
    try:
        for (err_i, err_st, err_idx, vals) in snmp_engine.setCmd(
                snmp_engine.SnmpEngine(),
                snmp_engine.CommunityData(community, mpModel=snmp_ver - 1),
                snmp_engine.UdpTransportTarget(
                    (host, port), timeout=timeout, retries=retries),
                snmp_engine.ContextData(),
                snmp_engine.ObjectType(snmp_engine.ObjectIdentity(oid), value)):
            if err_i or err_st:
                logging.debug('snmp error: %s' % err_i)
                return None
            else:
                return True
    except:
        log_traceback()
        return False
