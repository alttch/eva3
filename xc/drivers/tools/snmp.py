__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "3.1.0"

import pysnmp.hlapi as snmp_engine

def get(oid, host, port=161, community='public', timeout=0, retries=0,
        rf=str):
    result = []
    try:
        for (err_i, err_st, err_idx, vals) in snmp_engine.getCmd(
                snmp_engine.SnmpEngine(), snmp_engine.CommunityData(community),
                snmp_engine.UdpTransportTarget(
                    (host, port), timeout=timeout, retries=retries),
                snmp_engine.ContextData(),
                snmp_engine.ObjectType(snmp_engine.ObjectIdentity(oid))):
            if err_i or err_st:
                logging.debug('snmp error %s' (err_st))
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
        return None


def set(oid, value, host, port=161, community='private', timeout=0, retries=0):
    try:
        for (err_i, err_st, err_idx, vals) in snmp_engine.setCmd(
                snmp_engine.SnmpEngine(), snmp_engine.CommunityData(community),
                snmp_engine.UdpTransportTarget(
                    (host, port), timeout=timeout, retries=retries),
                snmp_engine.ContextData(),
                snmp_engine.ObjectType(snmp_engine.ObjectIdentity(oid),
                                        value)):
            if err_i or err_st:
                logging.debug('snmp error %s' (err_st))
                return None
            else:
                return True
    except:
        return False
