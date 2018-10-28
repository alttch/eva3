__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "3.1.1"

import hashlib
import os
import uuid
import logging
import configparser
import copy
import base64
import hashlib
from cryptography.fernet import Fernet
from netaddr import IPNetwork

import eva.core
import eva.item

from eva.tools import netacl_match
from eva.tools import val_to_boolean

masterkey = None
keys = {}
keys_by_id = {}

allows = []
all_allows = ['cmd', 'lock', 'device', 'dm_rule_props', 'dm_rules_list']

keys_to_delete = set()


class APIKey(object):

    def __init__(self, k, key_id=''):
        self.key_id = key_id
        self.master = False
        self.sysfunc = False
        self.item_ids = []
        self.groups = []
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
        if not self.dynamic: return False
        if prop == 'key':
            if value is None or value == '': return False
            if self.key != value:
                regenerate_key(self.key_id, k=value, save=False)
                self.set_modified(save)
            return True
        elif prop == 'sysfunc':
            val = val_to_boolean(value)
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
        return False

    def set_modified(self, save):
        if save:
            self.save()
        else:
            self.config_changed = True

    def save(self, create=True):
        if not self.dynamic:
            return False
        db = eva.core.get_user_db()
        c = db.cursor()
        data = self.serialize()
        for d in [
                'items', 'groups', 'allow', 'hosts_allow', 'hosts_assign',
                'pvt', 'rpvt'
        ]:
            data[d] = ','.join(data[d])
        try:
            if not self.in_db:
                c.execute('insert into apikeys(k_id, k, m, s, i, g, a,' + \
                        ' hal, has, pvt, rpvt) values ' + \
                        '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                        (
                            data['id'],
                            data['key'],
                            data['master'],
                            data['sysfunc'],
                            data['items'],
                            data['groups'],
                            data['allow'],
                            data['hosts_allow'],
                            data['hosts_assign'],
                            data['pvt'],
                            data['rpvt'])
                        )
            else:
                c.execute(
                    'update apikeys set k=?, s=?, i=?, g=?, a=?,' + \
                            ' hal=?, has=?, pvt=?, rpvt=? where k_id=?',
                    (self.key, data['sysfunc'], data['items'], data['groups'],
                     data['allow'], data['hosts_allow'], data['hosts_assign'],
                     data['pvt'], data['rpvt'], data['id']))
        except:
            if not create:
                logging.critical('apikeys db error')
                eva.core.log_traceback()
                return False
            else:
                logging.info('no apikeys table in db, creating new')
                create_apikeys_table()
                self.save(create=False)
        db.commit()
        c.close()
        db.close()
        self.in_db = True
        return True


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
        cfg.read(fname_full)
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
                _keys[k] = key
                _keys_by_id[ks] = key
                if key.master and not masterkey:
                    _masterkey = k
                    logging.info('+ masterkey loaded')
            except:
                pass
        _keys_from_db, _keys_from_db_by_id = load_keys_from_db()
        keys = _keys
        keys.update(_keys_from_db)
        keys_by_id = _keys_by_id
        keys_by_id.update(_keys_from_db_by_id)
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
          sysfunc=False):
    if eva.core.setup_mode:
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
    if rpvt_uri:
        if rpvt_uri.find('//') != -1:
            r = rpvt_uri.split('//')[1]
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


def serialized_acl(k):
    if not k or not k in keys: return None
    _k = keys[k]
    r = {'key_id': _k.key_id, 'master': _k.master or eva.core.setup_mode}
    if _k.master or eva.core.setup_mode: return r
    r['sysfunc'] = _k.sysfunc
    r['items'] = _k.item_ids
    r['groups'] = _k.groups
    if _k.pvt_files: r['pvt'] = _k.pvt_files
    if _k.rpvt_uris: r['rpvt'] = _k.rpvt_uris
    r['allow'] = {}
    for a in allows:
        r['allow'][a] = True if a in _k.allow else False
    return r


def add_api_key(key_id=None, save=False):
    if key_id is None or key_id in keys_by_id:
        return False
    key_hash = gen_random_hash()
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
    if key_id is None or key_id not in keys_by_id or keys_by_id[key_id].master \
        or not keys_by_id[key_id].dynamic:
        return False
    del keys[keys_by_id[key_id].key]
    del keys_by_id[key_id]
    if eva.core.db_update == 1:
        db = eva.core.get_user_db()
        c = db.cursor()
        try:
            c.execute('delete from apikeys where k_id=?', (key_id,))
            db.commit()
        except:
            logging.critical('apikeys db error')
            eva.core.log_traceback()
            return False
        c.close()
        db.close()
    else:
        keys_to_delete.add(key_id)
    return True


def regenerate_key(key_id, k=None, save=False):
    if key_id is None or key_id not in keys_by_id or keys_by_id[key_id].master \
            or not keys_by_id[key_id].dynamic:
        return False
    key = keys_by_id[key_id]
    old_key = key.key
    key.set_key(gen_random_hash() if k is None else k)
    keys[key.key] = keys.pop(old_key)
    key.set_modified(save)
    return key.key


def load_keys_from_db(create=True):
    _keys = {}
    _keys_by_id = {}
    try:
        db = eva.core.get_user_db()
        c = db.cursor()
        c.execute('select * from apikeys')
        rows = c.fetchall()
        db.commit()
        c.close()
        db.close()
        for i in rows:
            key = APIKey(i[1], i[0])
            key.sysfunc = True if val_to_boolean(str(i[3])) else False
            for k, v in {
                    4: 'item_ids',
                    5: 'groups',
                    6: 'allow',
                    9: 'pvt_files',
                    10: 'rpvt_uris'
            }.items():
                setattr(
                    key, v,
                    list(filter(None, [j.strip() for j in i[k].split(',')])))

            _hosts_allow = list(
                filter(None, [j.strip() for j in i[7].split(',')]))
            key.hosts_allow = [IPNetwork(h) for h in _hosts_allow]

            _hosts_assign = list(
                filter(None, [x.strip() for x in i[8].split(',')]))
            key.hosts_assign = \
                    [ IPNetwork(h) for h in _hosts_assign ]
            key.dynamic = True
            key.in_db = True
            _keys[key.key] = key
            _keys_by_id[key.key_id] = key
    except:
        if create:
            create_apikeys_table()
            load_keys_from_db(create=False)
        else:
            logging.warning('unable to load API keys from db')
            eva.core.log_traceback()
    return _keys, _keys_by_id


def create_apikeys_table():
    try:
        db = eva.core.get_user_db()
        c = db.cursor()
        c.execute('create table apikeys (k_id primary key, k, m, s, i, g, a,\
                   hal, has, pvt, rpvt)')
        db.commit()
        c.close()
    except:
        logging.critical('unable to create apikeys table in db')


def save():
    for i, k in keys_by_id.copy().items():
        if k.config_changed and not k.save():
            return False
    db = eva.core.get_user_db()
    c = db.cursor()
    try:
        for k in keys_to_delete:
            c.execute('delete from apikeys where k_id=?', (k,))
        db.commit()
        c.close()
    except:
        logging.critical('apikeys db error')
        eva.core.log_traceback()
        c.close()
        db.close()
        return False
    db.close()
    return True


def init():
    eva.core.append_save_func(save)


def gen_random_hash():
    s = hashlib.sha256()
    s.update(os.urandom(1024))
    s.update(str(uuid.uuid4()).encode())
    s.update(os.urandom(1024))
    return s.hexdigest()
