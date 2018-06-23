__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "3.0.3"

import logging
import configparser
import eva.core
import eva.item

from netaddr import IPNetwork

from eva.tools import netacl_match

masterkey = None
keys = {}
keys_by_id = {}

allows = []


class APIKey(object):

    def __init__(self, k, key_id=''):
        self.key = k
        self.key_id = key_id
        self.master = False
        self.sysfunc = False
        self.item_ids = []
        self.groups = []
        self.allow = []
        self.hosts_allow = []
        self.hosts_assign = []
        self.pvt_files = []


def load(fname=None):
    global keys, keys_by_id, masterkey
    _keys = {}
    _keys_by_id = {}
    _masterkey = None
    logging.info('Loading API keys')
    fname_full = eva.core.format_cfg_fname(fname, 'apikeys')
    if not fname_full:
        logging.warning('No file or product specified ' + \
                                'skipping loading custom variables')
        return False
    try:
        cfg = configparser.ConfigParser(inline_comment_prefixes=';')
        cfg.readfp(open(fname_full))
        for ks in cfg.sections():
            try:
                k = cfg.get(ks, 'key')
                if k in _keys.keys():
                    logging.warning(
                            'duplicate key %s, problems might occur' % \
                                    k)
                key = APIKey(k, ks)
                try:
                    key.master = (cfg.get(ks, 'master') == 'yes')
                except:
                    pass
                try:
                    key.sysfunc = (cfg.get(ks, 'sysfunc') == 'yes')
                except:
                    pass
                try:
                    _ha = cfg.get(ks, 'hosts_allow')
                except:
                    _ha = None
                if _ha:
                    try:
                        _hosts_allow = list(
                            filter(None, [x.strip() for x in _ha.split(',')]))
                        key.hosts_allow = \
                                [ IPNetwork(h) for h in _hosts_allow ]
                    except:
                        logging.error('key %s bad host acl!, skipping' % ks)
                        eva.core.log_traceback()
                        continue
                try:
                    _ha = cfg.get(ks, 'hosts_assign')
                except:
                    _ha = None
                if _ha:
                    try:
                        _hosts_assign = list(
                            filter(None, [x.strip() for x in _ha.split(',')]))
                        key.hosts_assign = \
                                [ IPNetwork(h) for h in _hosts_assign ]
                    except:
                        logging.warning('key %s bad hosts_assign' % ks)
                        eva.core.log_traceback()
                try:
                    key.item_ids = list(
                        filter(None, [
                            x.strip() for x in cfg.get(ks, 'items').split(',')
                        ]))
                except:
                    pass
                try:
                    key.groups = list(
                        filter(None, [
                            x.strip() for x in cfg.get(ks, 'groups').split(',')
                        ]))
                except:
                    pass
                try:
                    key.pvt_files = list(filter(None,
                        [x.strip() for x in \
                                cfg.get(ks, 'pvt').split(',')]))
                except:
                    pass
                try:
                    key.allow = list(
                        filter(None, [
                            x.strip() for x in cfg.get(ks, 'allow').split(',')
                        ]))
                except:
                    pass
                _keys[k] = key
                _keys_by_id[ks] = key
                if key.master and not _masterkey:
                    _masterkey = k
                    logging.info('+ masterkey loaded')
            except:
                pass
        keys = _keys
        keys_by_id = _keys_by_id
        masterkey = _masterkey
        if not _masterkey:
            logging.warning('no masterkey in this configuration')
        return True
    except Exception as e:
        logging.error('Failed to read API keys from %s' % (fname))
        eva.core.log_traceback()
        return False


def key_by_id(key_id):
    return None if not key_id or not key_id in keys_by_id else \
                                                keys_by_id[key_id].key


def key_id(k):
    return 'unknown' if not k or not k in keys else keys[k].key_id


def key_by_ip_address(ip=None):
    if not ip: return None
    for k, key in keys.copy().items():
        if netacl_match(ip, key.hosts_assign):
            return k


def format_key(k):
    if not k: return None
    return key_by_id(k[1:]) if k[0] == '$' else k


def check(k,
          item=None,
          allow=[],
          pvt_file=None,
          ip=None,
          master=False,
          sysfunc=False):
    if not k or not k in keys or (master and not keys[k].master): return False
    _k = keys[k]
    if ip and not netacl_match(ip, _k.hosts_allow):
        return False
    if _k.master: return True
    if sysfunc and not _k.sysfunc: return False
    if item:
        try:
            grp = item.group
        except:
            grp = 'nogroup'
        if not eva.item.item_match(item, _k.item_ids, _k.groups): return False
    if allow:
        for a in allow:
            if not a in _k.allow: return False
    if pvt_file:
        if '#' in _k.pvt_files or pvt_file in _k.pvt_files: return True
        for d in _k.pvt_files:
            p = d.find('#')
            if p > -1 and d[:p] == pvt_file[:p]: return True
            if d.find('+') > -1:
                g1 = d.split('/')
                g2 = pvt_file.split('/')
                if len(g1) == len(g2):
                    match = True
                    for i in range(0, len(g1)):
                        if g1[i] != '+' and g1[i] != g2[i]:
                            match = False
                            break
                    if match: return True
        return False
    return True


def serialized_acl(k):
    if not k or not k in keys: return None
    _k = keys[k]
    r = {'key_id': _k.key_id, 'master': _k.master}
    if _k.master: return r
    r['sysfunc'] = _k.sysfunc
    r['items'] = _k.item_ids
    r['groups'] = _k.groups
    if _k.pvt_files: r['pvt'] = _k.pvt_files
    r['allow'] = {}
    for a in allows:
        r['allow'][a] = True if a in _k.allow else False
    return r
