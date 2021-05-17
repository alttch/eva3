__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.3.3"

import hashlib
import os
import uuid
import logging
import configparser
import copy
import base64
import hashlib
import sqlalchemy as sa
import threading
from sqlalchemy import text as sql
from cryptography.fernet import Fernet
from netaddr import IPNetwork

import eva.core
import eva.item

from eva.core import userdb

from eva.tools import netacl_match
from eva.tools import val_to_boolean
from eva.tools import gen_random_str
from eva.tools import SimpleNamespace

from eva.exceptions import ResourceAlreadyExists
from eva.exceptions import ResourceNotFound
from eva.exceptions import FunctionFailed

from functools import partial

config = SimpleNamespace(masterkey=None)

key_lock = threading.RLock()

keys = {}
keys_by_id = {}

allows = []
all_allows = ['cmd', 'lock', 'device', 'supervisor']

keys_to_delete = set()

combined_keys_cache = {}


class APIKey(object):

    def __init__(self, k, key_id=''):
        self.key_id = key_id
        self.master = False
        self.sysfunc = False
        self.cdata = []
        self.item_ids = []
        self.groups = []
        self.item_ids_ro = []
        self.groups_ro = []
        self.item_ids_deny = []
        self.groups_deny = []
        self.allow = []
        self.hosts_allow = []
        self.hosts_assign = []
        self.pvt_files = []
        self.rpvt_uris = []
        self.config_changed = False
        self.in_db = False
        self.dynamic = False
        self.temporary = False
        self.combined_from = []
        self.set_key(k)

    def serialize(self):
        with key_lock:
            if self.combined_from:
                _recombine_acl(self)
            result = {
                'id': self.key_id,
                'master': self.master,
                'key': self.key,
                'sysfunc': self.sysfunc,
                'cdata': self.cdata,
                'items': self.item_ids,
                'groups': self.groups,
                'items_ro': self.item_ids_ro,
                'groups_ro': self.groups_ro,
                'items_deny': self.item_ids_deny,
                'groups_deny': self.groups_deny,
                'allow': self.allow,
                'pvt': self.pvt_files,
                'rpvt': self.rpvt_uris
            }
            result['hosts_allow'] = [str(i) for i in self.hosts_allow]
            result['hosts_assign'] = [str(i) for i in self.hosts_assign]
            result['dynamic'] = self.dynamic
            return result

    def set_key(self, k):
        self.key = k
        self.private_key = hashlib.sha256(str(k).encode()).digest()
        self.private_key512 = hashlib.sha512(str(k).encode()).digest()
        self.ce = Fernet(base64.b64encode(self.private_key))

    def set_prop(self, prop, value=None, save=False):
        with key_lock:
            if not self.dynamic or self.master:
                raise FunctionFailed(
                    'Master and static keys can not be changed')
            if prop == 'key':
                if value is None or value == '' or value.find(
                        ':') != -1 or value.find('|') != -1:
                    return False
                if self.key != value:
                    if value in keys:
                        raise ResourceAlreadyExists('API key')
                    regenerate_key(self.key_id, k=value, save=False)
                    self.set_modified(save)
                return True
            elif prop == 'dynamic':
                return False
            elif prop == 'sysfunc':
                val = val_to_boolean(value)
                if val is None:
                    return False
                if self.sysfunc != val:
                    self.sysfunc = val
                    self.set_modified(save)
                return True
            elif prop == 'items':
                if isinstance(value, list):
                    val = value
                else:
                    if value:
                        val = value.split(',')
                    else:
                        val = []
                if self.item_ids != val:
                    self.item_ids = val
                    self.set_modified(save)
                return True
            elif prop == 'groups':
                if isinstance(value, list):
                    val = value
                else:
                    if value:
                        val = value.split(',')
                    else:
                        val = []
                if self.groups != val:
                    self.groups = val
                    self.set_modified(save)
                return True
            elif prop == 'items_ro':
                if isinstance(value, list):
                    val = value
                else:
                    if value:
                        val = value.split(',')
                    else:
                        val = []
                if self.item_ids_ro != val:
                    self.item_ids_ro = val
                    self.set_modified(save)
                return True
            elif prop == 'groups_ro':
                if isinstance(value, list):
                    val = value
                else:
                    if value:
                        val = value.split(',')
                    else:
                        val = []
                if self.groups_ro != val:
                    self.groups_ro = val
                    self.set_modified(save)
                return True
            elif prop == 'items_deny':
                if isinstance(value, list):
                    val = value
                else:
                    if value:
                        val = value.split(',')
                    else:
                        val = []
                if self.item_ids_deny != val:
                    self.item_ids_deny = val
                    self.set_modified(save)
                return True
            elif prop == 'groups_deny':
                if isinstance(value, list):
                    val = value
                else:
                    if value:
                        val = value.split(',')
                    else:
                        val = []
                if self.groups_deny != val:
                    self.groups_deny = val
                    self.set_modified(save)
                return True
            elif prop == 'allow':
                if isinstance(value, list):
                    val = value
                else:
                    if value:
                        val = value.split(',')
                    else:
                        val = []
                for v in val:
                    if v not in all_allows:
                        return False
                if self.allow != val:
                    self.allow = val
                    self.set_modified(save)
                return True
            elif prop == 'hosts_allow':
                if isinstance(value, list):
                    val = value
                else:
                    if value:
                        val = value.split(',')
                    else:
                        val = ['0.0.0.0/0']
                val = [IPNetwork(h) for h in val]
                if self.hosts_allow != val:
                    self.hosts_allow = val
                    self.set_modified(save)
                return True
            elif prop == 'hosts_assign':
                if isinstance(value, list):
                    val = value
                else:
                    if value:
                        val = value.split(',')
                    else:
                        val = []
                val = [IPNetwork(h) for h in val]
                if self.hosts_assign != val:
                    self.hosts_assign = val
                    self.set_modified(save)
                return True
            elif prop == 'pvt':
                if isinstance(value, list):
                    val = value
                else:
                    if value:
                        val = value.split(',')
                    else:
                        val = []
                if self.pvt_files != val:
                    self.pvt_files = val
                    self.set_modified(save)
                return True
            elif prop == 'rpvt':
                if isinstance(value, list):
                    val = value
                else:
                    if value:
                        val = value.split(',')
                    else:
                        val = []
                if self.rpvt_uris != val:
                    self.rpvt_uris = val
                    self.set_modified(save)
                return True
            elif prop == 'cdata':
                val = [] if value is None else value
                if isinstance(val, str):
                    val = val.split(',')
                res = []
                for v in val:
                    if v not in res:
                        res.append(str(v))
                if self.cdata != res:
                    self.cdata = res
                    self.set_modified(save)
                return True
            raise ResourceNotFound('property ' + prop)

    def set_modified(self, save):
        if save:
            self.save()
        else:
            self.config_changed = True

    def save(self):
        if not self.dynamic or self.temporary:
            return False
        data = self.serialize()
        for d in [
                'items', 'groups', 'items_ro', 'groups_ro', 'items_deny',
                'groups_deny', 'allow', 'hosts_allow', 'hosts_assign', 'pvt',
                'rpvt', 'cdata'
        ]:
            data[d] = ','.join(data[d])
        dbconn = userdb()
        try:
            if not self.in_db:
                # if save on exit is set, deleted key with the same name could
                # still be present in the database
                dbconn.execute(sql('delete from apikeys where k_id=:k_id'),
                               k_id=data['id'])
                dbconn.execute(sql(
                    'insert into apikeys(k_id, k, m, s, i,'
                    ' g, i_ro, g_ro, i_deny, g_deny, a, hal, has, pvt, rpvt, '
                    'cdata) values '
                    '(:k_id, :k, :m, :s, :i, :g, :i_ro, :g_ro, '
                    ':i_deny, :g_deny,'
                    ' :a, :hal, :has, :pvt, :rpvt, :cdata)'),
                               k_id=data['id'],
                               k=data['key'],
                               m=1 if data['master'] else 0,
                               s=1 if data['sysfunc'] else 0,
                               i=data['items'],
                               g=data['groups'],
                               i_ro=data['items_ro'],
                               g_ro=data['groups_ro'],
                               i_deny=data['items_deny'],
                               g_deny=data['groups_deny'],
                               a=data['allow'],
                               hal=data['hosts_allow'],
                               has=data['hosts_assign'],
                               pvt=data['pvt'],
                               rpvt=data['rpvt'],
                               cdata=data['cdata'])
            else:
                dbconn.execute(sql(
                    'update apikeys set k=:k, s=:s, i=:i, g=:g, '
                    'i_ro=:i_ro, g_ro=:g_ro, i_deny=:i_deny, g_deny=:g_deny, '
                    'a=:a, hal=:hal, has=:has, pvt=:pvt, rpvt=:rpvt, '
                    'cdata=:cdata where k_id=:k_id'),
                               k=self.key,
                               s=1 if data['sysfunc'] else 0,
                               i=data['items'],
                               g=data['groups'],
                               i_ro=data['items_ro'],
                               g_ro=data['groups_ro'],
                               i_deny=data['items_deny'],
                               g_deny=data['groups_deny'],
                               a=data['allow'],
                               hal=data['hosts_allow'],
                               has=data['hosts_assign'],
                               pvt=data['pvt'],
                               rpvt=data['rpvt'],
                               cdata=data['cdata'],
                               k_id=data['id'])
        except:
            eva.core.report_userdb_error()
        self.in_db = True
        return True


def load(fname=None, load_from_db=True):
    with key_lock:
        keys.clear()
        keys_by_id.clear()
        config.masterkey = None
        logging.info('Loading API keys')
        fname_full = eva.core.format_cfg_fname(fname, 'apikeys')
        if not fname_full:
            logging.warning('No file or product specified '
                            'skipping loading API keys')
            return False
        try:
            cfg = configparser.ConfigParser(inline_comment_prefixes=';')
            cfg.read(fname_full)
            for ks in cfg.sections():
                try:
                    k = cfg.get(ks, 'key')
                    if k in keys.keys():
                        logging.warning(
                            f'duplicate key {k}, problems might occur')
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
                                filter(None,
                                       [x.strip() for x in _ha.split(',')]))
                            key.hosts_allow = \
                                    [ IPNetwork(h) for h in _hosts_allow ]
                        except:
                            logging.error(
                                f'key {ks} invalid host acl!, skipping')
                            eva.core.log_traceback()
                            continue
                    try:
                        _ha = cfg.get(ks, 'hosts_assign')
                    except:
                        _ha = None
                    if _ha:
                        try:
                            _hosts_assign = list(
                                filter(None,
                                       [x.strip() for x in _ha.split(',')]))
                            key.hosts_assign = \
                                    [ IPNetwork(h) for h in _hosts_assign ]
                        except:
                            logging.warning(f'key {ks} invalid hosts_assign')
                            eva.core.log_traceback()
                    try:
                        key.item_ids = list(
                            filter(None, [
                                x.strip()
                                for x in cfg.get(ks, 'items').split(',')
                            ]))
                    except:
                        pass
                    try:
                        key.groups = list(
                            filter(None, [
                                x.strip()
                                for x in cfg.get(ks, 'groups').split(',')
                            ]))
                    except:
                        pass
                    try:
                        key.item_ids_ro = list(
                            filter(None, [
                                x.strip()
                                for x in cfg.get(ks, 'items_ro').split(',')
                            ]))
                    except:
                        pass
                    try:
                        key.groups_ro = list(
                            filter(None, [
                                x.strip()
                                for x in cfg.get(ks, 'groups_ro').split(',')
                            ]))
                    except:
                        pass
                    try:
                        key.item_ids_deny = list(
                            filter(None, [
                                x.strip()
                                for x in cfg.get(ks, 'items_deny').split(',')
                            ]))
                    except:
                        pass
                    try:
                        key.groups_deny = list(
                            filter(None, [
                                x.strip()
                                for x in cfg.get(ks, 'groups_deny').split(',')
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
                        key.rpvt_uris = list(filter(None,
                            [x.strip() for x in \
                                    cfg.get(ks, 'rpvt').split(',')]))
                    except:
                        pass
                    try:
                        key.allow = list(
                            filter(None, [
                                x.strip()
                                for x in cfg.get(ks, 'allow').split(',')
                            ]))
                    except:
                        pass
                    try:
                        key.allow = list(
                            filter(None, [
                                x.strip()
                                for x in cfg.get(ks, 'cdata').split(',')
                            ]))
                    except:
                        pass
                    keys[k] = key
                    keys_by_id[ks] = key
                    if key.master and not config.masterkey:
                        config.masterkey = k
                        logging.info('+ masterkey loaded')
                except:
                    pass
            if load_from_db:
                _keys_from_db, _keys_from_db_by_id = load_keys_from_db()
                keys.update(_keys_from_db)
                keys_by_id.update(_keys_from_db_by_id)
            if not config.masterkey:
                logging.warning('no masterkey specified')
            eva.core.update_corescript_globals({'masterkey': config.masterkey})
            return True
        except:
            logging.error('Unable to load API keys')
            eva.core.log_traceback()
            return False


def key_by_id(key_id):
    """
    get API key by API key ID

    Returns:
        API key
    """
    with key_lock:
        return None if not key_id or not key_id in keys_by_id else \
            keys_by_id[key_id].key


def key_ce(key_id):
    with key_lock:
        return None if not key_id or not key_id in keys_by_id else \
            keys_by_id[key_id].ce


def key_private(key_id):
    with key_lock:
        return None if not key_id or not key_id in keys_by_id else \
            keys_by_id[key_id].private_key


def key_private512(key_id):
    with key_lock:
        return None if not key_id or not key_id in keys_by_id else \
            keys_by_id[key_id].private_key512


def key_id(k):
    """
    get key ID by API key

    Returns:
        API key ID
    """
    with key_lock:
        return 'unknown' if not k or not k in keys else keys[k].key_id


def key_by_ip_address(ip=None):
    if not ip:
        return None
    with key_lock:
        for k, key in keys.items():
            if netacl_match(ip, key.hosts_assign):
                return k


def format_key(k):
    if not k:
        return None
    with key_lock:
        return key_by_id(k[1:]) if k[0] == '$' else k


def check(k,
          item=None,
          oid=None,
          allow=[],
          pvt_file=None,
          rpvt_uri=None,
          ip=None,
          master=False,
          sysfunc=False,
          ro_op=False):
    if eva.core.is_setup_mode():
        return True
    with key_lock:
        if not k or not k in keys or (master and not keys[k].master):
            return False
        _k = keys[k]
        if _k.combined_from:
            _recombine_acl(_k)
        if ip and not netacl_match(ip, _k.hosts_allow):
            return False
        if _k.master:
            return True
        if sysfunc and not _k.sysfunc:
            return False
        if item:
            # check access to PHI
            try:
                if ('#' not in _k.item_ids and item.phi_id
                        not in _k.item_ids) or ('#' not in _k.groups and
                                                'phi' not in _k.groups):
                    return False
            except:
                # check access to regular item
                try:
                    grp = item.group
                except:
                    grp = 'nogroup'
                if not ro_op and eva.item.item_match(item, _k.item_ids_deny,
                                                     _k.groups_deny):
                    return False
                if not eva.item.item_match(item, _k.item_ids, _k.groups):
                    if ro_op:
                        if not eva.item.item_match(item, _k.item_ids_ro,
                                                   _k.groups_ro):
                            return False
                    else:
                        return False
        if oid:
            if not eva.item.oid_match(oid, _k.item_ids, _k.groups):
                if ro_op:
                    if not eva.item.oid_match(oid, _k.item_ids_ro,
                                              _k.groups_ro):
                        return False
                else:
                    return False
        if allow:
            for a in allow:
                if not a in _k.allow:
                    return False
        if pvt_file:
            if '#' in _k.pvt_files or pvt_file in _k.pvt_files:
                return True
            for d in _k.pvt_files:
                p = d.find('#')
                if p > -1 and d[:p] == pvt_file[:p]:
                    return True
                if d.find('+') > -1:
                    g1 = d.split('/')
                    g2 = pvt_file.split('/')
                    if len(g1) == len(g2):
                        match = True
                        for i in range(0, len(g1)):
                            if g1[i] != '+' and g1[i] != g2[i]:
                                match = False
                                break
                        if match:
                            return True
            return False
        if rpvt_uri:
            if rpvt_uri.find('//') != -1 and rpvt_uri[:3] not in ['uc/', 'lm/']:
                r = rpvt_uri.split('//', 1)[1]
            else:
                r = rpvt_uri
            if '#' in _k.rpvt_uris or r in _k.rpvt_uris:
                return True
            for d in _k.rpvt_uris:
                p = d.find('#')
                if p > -1 and d[:p] == r[:p]:
                    return True
                if d.find('+') > -1:
                    g1 = d.split('/')
                    g2 = r.split('/')
                    if len(g1) == len(g2):
                        match = True
                        for i in range(0, len(g1)):
                            if g1[i] != '+' and g1[i] != g2[i]:
                                match = False
                                break
                        if match:
                            return True
            return False
        return True


def check_master(k):
    """
    check is given key a masterkey
    """
    return check(k, master=True)


def get_masterkey():
    """
    get master API key

    Returns:
        master API key
    """
    return config.masterkey


def serialized_acl(k):
    with key_lock:
        r = {'key_id': None, 'master': True}
        setup_on = eva.core.is_setup_mode()
        if not k or not k in keys:
            return r if setup_on else None
        _k = keys[k]
        if _k.combined_from:
            _recombine_acl(_k)
        r['key_id'] = _k.key_id
        r['master'] = _k.master or setup_on
        r['cdata'] = _k.cdata
        if _k.master or setup_on:
            return r
        r['sysfunc'] = _k.sysfunc
        r['items'] = _k.item_ids
        r['groups'] = _k.groups
        r['items_ro'] = _k.item_ids_ro
        r['groups_ro'] = _k.groups_ro
        r['items_deny'] = _k.item_ids_deny
        r['groups_deny'] = _k.groups_deny
        if _k.pvt_files:
            r['pvt'] = _k.pvt_files
        if _k.rpvt_uris:
            r['rpvt'] = _k.rpvt_uris
        r['allow'] = {}
        r['dynamic'] = _k.dynamic
        if _k.combined_from:
            r['combined_from'] = _k.combined_from
        for a in allows:
            r['allow'][a] = True if a in _k.allow else False
        return r


def add_api_key(key_id=None, save=False):
    with key_lock:
        if key_id is None:
            raise FunctionFailed
        if key_id in keys_by_id:
            raise ResourceAlreadyExists
        key_value = gen_random_str(length=64)
        key = APIKey(key_value, key_id)
        key.master = False
        key.dynamic = True
        key.set_prop('hosts_allow', '0.0.0.0/0', save)
        keys_by_id[key.key_id] = key
        keys[key.key] = key
        result = key.serialize()
        if key_id in keys_to_delete:
            keys_to_delete.remove(key_id)
        return result


def _recombine_acl(combined_key):
    with key_lock:
        combined_key.master = False
        combined_key.sysfunc = False
        for prop in [
                'item_ids', 'groups', 'item_ids_ro', 'groups_ro',
                'item_ids_deny', 'groups_deny', 'allow', 'pvt_files',
                'rpvt_uris', 'cdata', 'hosts_allow', 'hosts_assign'
        ]:
            setattr(combined_key, prop, [])
        for k_id in combined_key.combined_from:
            try:
                key = keys_by_id[k_id]
            except KeyError:
                continue
            if key.master:
                combined_key.master = True
            if key.sysfunc:
                combined_key.sysfunc = True
            for prop in [
                    'item_ids', 'groups', 'item_ids_ro', 'groups_ro',
                    'item_ids_deny', 'groups_deny', 'allow', 'pvt_files',
                    'rpvt_uris', 'hosts_allow', 'hosts_assign', 'cdata'
            ]:
                for i in getattr(key, prop):
                    a = getattr(combined_key, prop)
                    if i not in a:
                        a.append(i)


def create_combined_key(key_ids=[]):
    with key_lock:
        _key_ids = [k for k in sorted(key_ids) if k in keys_by_id]
        if not _key_ids:
            raise ValueError(f'no such API keys: {key_ids}')
        _combined_id = ','.join(_key_ids)
        try:
            return combined_keys_cache[_combined_id]
        except KeyError:
            # setup combined key
            ckey_value = gen_random_str(length=64)
            ckey_id = f'comb:{"+".join(_key_ids)}'
            combined_key = APIKey(ckey_value, ckey_id)
            combined_key.master = False
            combined_key.dynamic = True
            combined_key.temporary = True
            combined_key.combined_from = _key_ids
            # register
            keys_by_id[ckey_id] = combined_key
            keys[ckey_value] = combined_key
            combined_keys_cache[_combined_id] = ckey_id
    return ckey_id


def delete_api_key(key_id):
    with key_lock:
        if key_id is None or key_id not in keys_by_id:
            raise ResourceNotFound
        if keys_by_id[key_id].master or not keys_by_id[key_id].dynamic:
            raise FunctionFailed('Master and static keys can not be deleted')
        del keys[keys_by_id[key_id].key]
        del keys_by_id[key_id]
        if eva.core.config.db_update == 1:
            dbconn = userdb()
            try:
                dbconn.execute(sql('delete from apikeys where k_id=:key_id'),
                               key_id=key_id)
            except:
                eva.core.report_userdb_error()
        else:
            keys_to_delete.add(key_id)
        return True


def regenerate_key(key_id, k=None, save=False):
    with key_lock:
        if key_id is None or key_id not in keys_by_id:
            raise ResourceNotFound
        if keys_by_id[key_id].master or not keys_by_id[key_id].dynamic:
            raise FunctionFailed('Master and static keys can not be changed')
        key = keys_by_id[key_id]
        old_key = key.key
        key.set_key(gen_random_str(length=64) if k is None else k)
        keys[key.key] = keys.pop(old_key)
        key.set_modified(save)
        return key.key


def load_keys_from_db():
    _keys = {}
    _keys_by_id = {}
    dbconn = userdb()
    meta = sa.MetaData()
    t_apikeys = sa.Table('apikeys', meta,
                         sa.Column('k_id', sa.String(64), primary_key=True),
                         sa.Column('k', sa.String(64)),
                         sa.Column('m', sa.Integer), sa.Column('s', sa.Integer),
                         sa.Column('i', sa.String(8192)),
                         sa.Column('g', sa.String(8192)),
                         sa.Column('i_ro', sa.String(8192)),
                         sa.Column('g_ro', sa.String(8192)),
                         sa.Column('i_deny', sa.String(8192)),
                         sa.Column('g_deny', sa.String(8192)),
                         sa.Column('a', sa.String(256)),
                         sa.Column('hal', sa.String(8192)),
                         sa.Column('has', sa.String(8192)),
                         sa.Column('pvt', sa.String(8192)),
                         sa.Column('rpvt', sa.String(8192)),
                         sa.Column('cdata', sa.String(16384)))
    try:
        meta.create_all(dbconn)
    except:
        logging.critical('unable to create apikeys table in db')
        return _keys, _keys_by_id
    try:
        result = dbconn.execute(sql('select * from apikeys'))
        while True:
            r = result.fetchone()
            if not r:
                break
            key = APIKey(r.k, r.k_id)
            key.sysfunc = True if val_to_boolean(r.s) else False
            for i, v in {
                    'item_ids': 'i',
                    'groups': 'g',
                    'item_ids_ro': 'i_ro',
                    'groups_ro': 'g_ro',
                    'item_ids_deny': 'i_deny',
                    'groups_deny': 'g_deny',
                    'allow': 'a',
                    'pvt_files': 'pvt',
                    'rpvt_uris': 'rpvt',
                    'cdata': 'cdata'
            }.items():
                setattr(
                    key, i,
                    list(filter(None, [j.strip() for j in r[v].split(',')])))
            _hosts_allow = list(
                filter(None, [j.strip() for j in r.hal.split(',')]))
            key.hosts_allow = [IPNetwork(h) for h in _hosts_allow]
            _hosts_assign = list(
                filter(None, [x.strip() for x in r.has.split(',')]))
            key.hosts_assign = \
                    [ IPNetwork(h) for h in _hosts_assign ]
            key.dynamic = True
            key.in_db = True
            _keys[key.key] = key
            _keys_by_id[key.key_id] = key
        dbconn.close()
    except:
        eva.core.report_userdb_error(raise_exeption=False)
    return _keys, _keys_by_id


@eva.core.stop
def stop():
    save()


@eva.core.save
def save():
    with key_lock:
        for i, k in keys_by_id.items():
            if not k.temporary:
                if k.config_changed and not k.save():
                    return False
        dbconn = userdb()
        try:
            for k in keys_to_delete:
                dbconn.execute(sql('delete from apikeys where k_id=:k_id'),
                               k_id=k)
            return True
        except:
            eva.core.report_db_error(raise_exeption=False)


def init():
    pass
