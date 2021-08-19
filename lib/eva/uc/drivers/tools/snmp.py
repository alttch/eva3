__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.1"

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
        snmp_ver=2,
        walk=False):
    """
    Args:
        oid: SNMP OID or MIB name
        host: target host
        port: target port (default: 161)
        community: SNMP community (default: public)
        timeout: max SNMP timeout
        retries: max retry count (default: 0)
        rf: return format: str, float, int or None
        snmp_ver: SNMP version (default: 2)
        walk: if True, SNMP walk will be performed

    Returns:
        If rf is set to None, raw pysnmp object is returned, otherwise parsed
        to float, int or str

        If walk is requested, list of pysnmp objects is returned
    """
    result = []
    snmpfunc = snmp_engine.nextCmd if walk else snmp_engine.getCmd
    try:
        for (err_i, err_st, err_idx, vals) in snmpfunc(
                snmp_engine.SnmpEngine(),
                snmp_engine.CommunityData(community, mpModel=snmp_ver - 1),
                snmp_engine.UdpTransportTarget(
                    (host, port), timeout=timeout, retries=retries),
                snmp_engine.ContextData(),
                snmp_engine.ObjectType(snmp_engine.ObjectIdentity(oid)),
                lexicographicMode=False):
            if err_i or err_st:
                logging.debug('snmp error: %s' % err_i)
                return
            else:
                for v in vals:
                    if walk:
                        result.append(v)
                    else:
                        if rf is None: return v
                        try:
                            _v = str(v[1])
                            try:
                                if rf is float: _v = float(_v)
                                if rf is int: _v = int(_v)
                            except:
                                _v = None
                            return _v
                        except:
                            return
        return result
    except:
        log_traceback()
        return


def set(oid,
        value,
        host,
        port=161,
        community='private',
        timeout=0,
        retries=0,
        snmp_ver=2):
    """
    Args:
        oid: SNMP OID or MIB name
        value: value to set
        host: target host
        port: target port (default: 161)
        community: SNMP community (default: public)
        timeout: max SNMP timeout
        retries: max retry count (default: 0)
        snmp_ver: SNMP version (default: 2)

    Returns:
        True if value is set, False if not
    """
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
