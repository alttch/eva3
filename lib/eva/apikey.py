__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.5"

import hashlib
import os
import uuid
import logging
import configparser
import copy
import base64
import hashlib
import sqlalchemy as sa
from sqlalchemy import text as sql
from cryptography.fernet import Fernet
from netaddr import IPNetwork

import eva.core
import eva.item

from eva.core import userdb

from eva.tools import netacl_match
from eva.tools import val_to_boolean
from eva.tools import gen_random_str

from eva.exceptions import ResourceAlreadyExists
from eva.exceptions import ResourceNotFound
from eva.exceptions import FunctionFailed

from functools import partial
from types import SimpleNamespace

config = SimpleNamespace(masterkey=None)

keys = {}
keys_by_id = {}

allows = []
all_allows = ['cmd', 'lock', 'device']

keys_to_delete = set()


class APIKey(object):

    def __init__(self, k, key_id=''):
        self.key_id = key_id
        self.master = False
        self.sysfunc = False
        self.item_ids = []
        self.groups = []
        self.item_ids_ro = []
        self.groups_ro = []
        self.allow = []
        self.hosts_allow = []
        self.hosts_assign = []
        self.pvt_files = []
        self.rpvt_uris = []
        self.config_changed = False
        self.in_db = False
        self.dynamic = False
        self.set_key(k)

    def serialize(self):
        result = {
            'id': self.key_id,
            'master': self.master,
            'key': self.key,
            'sysfunc': self.sysfunc,
            'items': self.item_ids,
            'groups': self.groups,
            'items_ro': self.item_ids_ro,
            'groups_ro': self.groups_ro,
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
        _k = base64.b64encode(hashlib.sha256(str(k).encode()).digest())
        self.ce = Fernet(_k)

    def set_prop(self, prop, value=None, save=False):
        if not self.dynamic or self.master:
            raise FunctionFailed('Master and static keys can not be changed')
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
        elif prop == 'sysfunc':
            val = val_to_boolean(value)
            if val is None: return False
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
        raise ResourceNotFound('property ' + prop)

    def set_modified(self, save):
        if save:
            self.save()
        else:
            self.config_changed = True

    def save(self):
        if not self.dynamic:
            return False
        data = self.serialize()
        for d in [
                'items', 'groups', 'items_ro', 'groups_ro', 'allow',
                'hosts_allow', 'hosts_assign', 'pvt', 'rpvt'
        ]:
            data[d] = ','.join(data[d])
        dbconn = userdb()
        try:
            if not self.in_db:
                # if save on exit is set, deleted key with the same name could
                # still be present in the database
                dbconn.execute(
                    sql('delete from apikeys where k_id=:k_id'),
                    k_id=data['id'])
                dbconn.execute(
                    sql('insert into apikeys(k_id, k, m, s, i,' +
                        ' g, i_ro, g_ro, a,hal, has, pvt, rpvt) values ' +
                        '(:k_id, :k, :m, :s, :i, :g, :i_ro, :g_ro, :a, ' +
                        ':hal, :has, :pvt, :rpvt)'),
                    k_id=data['id'],
                    k=data['key'],
                    m=1 if data['master'] else 0,
                    s=1 if data['sysfunc'] else 0,
                    i=data['items'],
                    g=data['groups'],
                    i_ro=data['items_ro'],
                    g_ro=data['groups_ro'],
                    a=data['allow'],
                    hal=data['hosts_allow'],
                    has=data['hosts_assign'],
                    pvt=data['pvt'],
                    rpvt=data['rpvt'])
            else:
                dbconn.execute(
                    sql('update apikeys set k=:k, s=:s, i=:i, g=:g, ' +
                        'i_ro=:i_ro, g_ro=:g_ro, a=:a, ' +
                        'hal=:hal, has=:has, pvt=:pvt, rpvt=:rpvt where ' +
                        'k_id=:k_id'),
                    k=self.key,
                    s=1 if data['sysfunc'] else 0,
                    i=data['items'],
                    g=data['groups'],
                    i_ro=data['items_ro'],
                    g_ro=data['groups_ro'],
                    a=data['allow'],
                    hal=data['hosts_allow'],
                    has=data['hosts_assign'],
                    pvt=data['pvt'],
                    rpvt=data['rpvt'],
                    k_id=data['id'])
        except:
            eva.core.report_userdb_error()
        self.in_db = True
        return True


def load(fname=None, load_from_db=True):
    keys.clear()
    keys_by_id.clear()
    config.masterkey = None
    logging.info('Loading API keys')
    fname_full = eva.core.format_cfg_fname(fname, 'apikeys')
    if not fname_full:
        logging.warning('No file or product specified ' + \
                                'skipping loading custom variables')
        return False
    try:
        cfg = configparser.ConfigParser(inline_comment_prefixes=';')
        cfg.read(fname_full)
        for ks in cfg.sections():
            try:
                k = cfg.get(ks, 'key')
                if k in keys.keys():
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
                            x.strip() for x in cfg.get(ks, 'allow').split(',')
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
            logging.warning('no masterkey in this configuration')
        return True
    except:
        logging.error('Unable to load API keys')
        eva.core.log_traceback()
        return False


def key_by_id(key_id):
    return None if not key_id or not key_id in keys_by_id else \
        keys_by_id[key_id].key


def key_ce(key_id):
    return None if not key_id or not key_id in keys_by_id else \
        keys_by_id[key_id].ce


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
          rpvt_uri=None,
          ip=None,
          master=False,
          sysfunc=False,
          ro_op=False):
    if eva.core.is_setup_mode():
        return True
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
        if not eva.item.item_match(item, _k.item_ids, _k.groups):
            if ro_op:
                if not eva.item.item_match(item, _k.item_ids_ro, _k.groups_ro):
                    return False
            else:
                return False
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
    if rpvt_uri:
        if rpvt_uri.find('//') != -1 and rpvt_uri[:3] not in ['uc/', 'lm/']:
            r = rpvt_uri.split('//', 1)[1]
        else:
            r = rpvt_uri
        if '#' in _k.rpvt_uris or r in _k.rpvt_uris: return True
        for d in _k.rpvt_uris:
            p = d.find('#')
            if p > -1 and d[:p] == r[:p]: return True
            if d.find('+') > -1:
                g1 = d.split('/')
                g2 = r.split('/')
                if len(g1) == len(g2):
                    match = True
                    for i in range(0, len(g1)):
                        if g1[i] != '+' and g1[i] != g2[i]:
                            match = False
                            break
                    if match: return True
        return False
    return True


def check_master(k):
    return check(k, master=True)


def get_masterkey():
    return config.masterkey


def serialized_acl(k):
    r = {'key_id': None, 'master': True}
    setup_on = eva.core.is_setup_mode()
    if not k or not k in keys:
        return r if setup_on else None
    _k = keys[k]
    r['key_id'] = _k.key_id
    r['master'] = _k.master or setup_on
    if _k.master or setup_on: return r
    r['sysfunc'] = _k.sysfunc
    r['items'] = _k.item_ids
    r['groups'] = _k.groups
    r['items_ro'] = _k.item_ids_ro
    r['groups_ro'] = _k.groups_ro
    if _k.pvt_files: r['pvt'] = _k.pvt_files
    if _k.rpvt_uris: r['rpvt'] = _k.rpvt_uris
    r['allow'] = {}
    for a in allows:
        r['allow'][a] = True if a in _k.allow else False
    return r


def add_api_key(key_id=None, save=False):
    if key_id is None: raise FunctionFailed
    if key_id in keys_by_id: raise ResourceAlreadyExists
    key_hash = gen_random_str()
    key = APIKey(key_hash, key_id)
    key.master = False
    key.dynamic = True
    key.set_prop('hosts_allow', '0.0.0.0/0', save)
    keys_by_id[key.key_id] = key
    keys[key.key] = key
    result = key.serialize()
    if key_id in keys_to_delete:
        keys_to_delete.remove(key_id)
    return result


def delete_api_key(key_id):
    if key_id is None or key_id not in keys_by_id:
        raise ResourceNotFound
    if keys_by_id[key_id].master or not keys_by_id[key_id].dynamic:
        raise FunctionFailed('Master and static keys can not be deleted')
    del keys[keys_by_id[key_id].key]
    del keys_by_id[key_id]
    if eva.core.config.db_update == 1:
        dbconn = userdb()
        try:
            dbconn.execute(
                sql('delete from apikeys where k_id=:key_id'), key_id=key_id)
        except:
            eva.core.report_userdb_error()
    else:
        keys_to_delete.add(key_id)
    return True


def regenerate_key(key_id, k=None, save=False):
    if key_id is None or key_id not in keys_by_id:
        raise ResourceNotFound
    if keys_by_id[key_id].master or not keys_by_id[key_id].dynamic:
        raise FunctionFailed('Master and static keys can not be changed')
    key = keys_by_id[key_id]
    old_key = key.key
    key.set_key(gen_random_str() if k is None else k)
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
                         sa.Column('i', sa.String(1024)),
                         sa.Column('g', sa.String(1024)),
                         sa.Column('i_ro', sa.String(1024)),
                         sa.Column('g_ro', sa.String(1024)),
                         sa.Column('a', sa.String(256)),
                         sa.Column('hal', sa.String(1024)),
                         sa.Column('has', sa.String(1024)),
                         sa.Column('pvt', sa.String(1024)),
                         sa.Column('rpvt', sa.String(1024)))
    try:
        meta.create_all(dbconn)
    except:
        logging.critical('unable to create apikeys table in db')
        return _keys, _keys_by_id
    try:
        result = dbconn.execute(sql('select * from apikeys'))
        while True:
            r = result.fetchone()
            if not r: break
            key = APIKey(r.k, r.k_id)
            key.sysfunc = True if val_to_boolean(r.s) else False
            for i, v in {
                    'item_ids': 'i',
                    'groups': 'g',
                    'item_ids_ro': 'i_ro',
                    'groups_ro': 'g_ro',
                    'allow': 'a',
                    'pvt_files': 'pvt',
                    'rpvt_uris': 'rpvt'
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
    except:
        eva.core.report_userdb_error(raise_exeption=False)
    return _keys, _keys_by_id


@eva.core.stop
def stop():
    save()


@eva.core.save
def save():
    for i, k in keys_by_id.copy().items():
        if k.config_changed and not k.save():
            return False
    dbconn = userdb()
    try:
        for k in keys_to_delete:
            dbconn.execute(sql('delete from apikeys where k_id=:k_id'), k_id=k)
        return True
    except:
        eva.core.report_db_error(raise_exeption=False)


def init():
    pass
