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
import eva.core
import eva.item

from netaddr import IPNetwork
from eva.tools import netacl_match
from eva.tools import val_to_boolean

masterkey = None
keys = {}
keys_by_id = {}
_keys_loaded_from_ini = {}

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
        self.rpvt_uris = []

    def serialize(self):
        result = copy.copy(self.__dict__)
        result['hosts_allow'] = [str(i) for i in self.hosts_allow]
        result['hosts_assign'] = [str(i.ip) for i in self.hosts_assign]
        return result

def load(fname=None):
    global keys, keys_by_id, masterkey
    _keys = {}
    _keys_by_id = {}
    _masterkey = None
    logging.info('Loading API keys')
    eva.core.append_save_func(_save)
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
        _keys_loaded_from_ini.update(_keys_by_id)
        _keys_from_db, _keys_from_db_by_id = _load_keys_from_db()
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


def add_api_key(name=None,
                s=False,
                i=None,
                g=None,
                a=None,
                hal=None,
                has=None,
                pvt=None,
                rpvt=None):
    if name is None or hal is None or name in keys_by_id:
        return False
    saved_args = {
        k: v
        for k, v in locals().items()
        if k in ('rpvt', 'pvt', 'has', 'hal', 'a', 'g', 'i', 's',
                 'name') and v is not None
    }
    key_hash = gen_random_hash()
    key = APIKey(key_hash, name)
    key.master = False
    key = parse_key_args(key, saved_args)
    if key:
        keys_by_id[key.key_id] = key
        keys[key.key] = key
        result = key.serialize()
        if eva.core.db_update == 1:
            return result if _save_key_to_db(key) else False
        return result
    return False


def modify_api_key(name=None,
                   s=None,
                   i=None,
                   g=None,
                   a=None,
                   hal=None,
                   has=None,
                   pvt=None,
                   rpvt=None):
    if name is None or hal is '' or name not in keys_by_id or \
        keys_by_id[name].master or name in _keys_loaded_from_ini:
        return False
    saved_args = {
        k: v
        for k, v in locals().items()
        if k in ('rpvt', 'pvt', 'has', 'hal', 'a', 'g', 'i', 's',
                 'name') and v is not None
    }

    temp_key = APIKey(None)
    try:
        temp_key = parse_key_args(temp_key, saved_args)
    except:
        logging.error('error while parsing arguments')
        eva.core.log_traceback()
        return False
    del saved_args['name']
    key = keys_by_id[name]
    args_table = {
        'i': 'item_ids',
        'g': 'groups',
        'a': 'allow',
        'pvt': 'pvt_files',
        'rpvt': 'rpvt_uris',
        'has': 'hosts_assign',
        'hal': 'hosts_allow',
        's': 'sysfunc'
    }
    if temp_key:
        for k in saved_args.keys():
            setattr(key, args_table[k], getattr(temp_key, args_table[k]))
        keys_by_id[name] = key
        keys[key.key] = key
        result = key.serialize()
        if eva.core.db_update == 1:
            return result if _update_key_in_db(key) else False
        return result
    return False


def delete_api_key(name):
    if name is None or name not in keys_by_id or keys_by_id[name].master \
            or name in _keys_loaded_from_ini:
        return False
    del keys[keys_by_id[name].key]
    del keys_by_id[name]
    if eva.core.db_update == 1:
        return _delete_key_from_db(name)
    return True

def regenerate_key(name):
    if name is None or name not in keys_by_id or keys_by_id[name].master \
    or name in _keys_loaded_from_ini:
        return False
    key = keys_by_id[name]
    old_key = key.key
    key.key = gen_random_hash()
    keys[key.key] = keys.pop(old_key)
    result = key.serialize()
    if eva.core.db_update == 1:
        return result if _update_key_in_db(key) else False
    return result

def parse_key_args(key, saved_args):
    try:
        key.sysfunc = True if val_to_boolean(str(
            saved_args.get('s'))) else False
    except:
        logging.error('key %s bad sysfunc arg, skipping' % saved_args.get('s'))
        eva.core.log_traceback()
    if saved_args.get('hal'):
        try:
            _hosts_allow = list(
                filter(None, [x.strip() for x in saved_args['hal'].split(',')]))
            key.hosts_allow = \
                    [ IPNetwork(h) for h in _hosts_allow ]
        except:
            logging.error('key %s bad host acl!, skipping' % saved_args['hal'])
            eva.core.log_traceback()
            return False
    if saved_args.get('has'):
        try:
            _hosts_assign = list(
                filter(None, [x.strip() for x in saved_args['has'].split(',')]))
            key.hosts_assign = \
                    [ IPNetwork(h) for h in _hosts_assign ]
        except:
            logging.error('key %s bad hosts_assign' % saved_args['has'])
            eva.core.log_traceback()
            return False
    for k, v in {
            'item_ids': saved_args.get('i'),
            'groups': saved_args.get('g'),
            'allow': saved_args.get('a'),
            'pvt_files': saved_args.get('pvt'),
            'rpvt_uris': saved_args.get('rpvt')
    }.items():
        if v:
            try:
                parsed = list(filter(None, [x.strip() for x in v.split(',')]))
                setattr(key, k, parsed)
            except:
                logging.error('bad arguments')
                eva.core.log_traceback()
                return False
    if not all([i in allows for i in key.allow]):
        return False
    return key


def _delete_key_from_db(name=None, keys_list=None):
    if name is None and keys_list is None:
        return False
    try:
        db = eva.core.get_user_db()
        c = db.cursor()
        if keys_list:
            c.execute('delete from apikeys where k_id in (%s)'%','.join(['?'] *\
                       len(keys_list)), keys_list)
        else:
            c.execute('delete from apikeys where k_id = ?', (name,))
        db.commit()
        c.close()
        db.close()
        return True
    except:
        logging.critical('apikey db error')
        eva.core.log_traceback()


def _save_key_to_db(key=None, keys_list=None, create=True):
    if key is None and keys_list is None:
        return False
    try:
        db = eva.core.get_user_db()
        c = db.cursor()
        key = keys_by_id[keys_list[0]] if keys_list else key
        c.execute('select k from apikeys where k_id = ?', (key.key_id,))
        row = c.fetchone()
        db.commit()
        c.close()
        db.close()
        if row:
            logging.info('can not create key %s - already exist' % (key.key_id))
            return False
    except:
        if not create:
            logging.critical('db error')
            eva.core.log_traceback()
            return False
        else:
            logging.info('no apikeys table in db, creating new')
            _create_apikeys_table()
            _save_key_to_db(create=False)
    try:
        db = eva.core.get_user_db()
        c = db.cursor()
        if keys_list:
            keys = [keys_by_id[k_id] for k_id in keys_list]
            keys_to_insert = [
                (key.key_id, key.key, key.master, key.sysfunc, ','.join([
                    str(i) for i in key.item_ids
                ]), ','.join([str(i) for i in key.groups]), ','.join([
                    str(i) for i in key.allow
                ]), ','.join([str(i) for i in key.hosts_allow]),
                 ','.join([str(i) for i in key.hosts_assign]), ','.join([
                     str(i) for i in key.pvt_files
                 ]), ','.join([str(i) for i in key.rpvt_uris])) for key in keys
            ]
            c.executemany(
                'insert into apikeys (k_id, k, m, s, i, g, a, hal, \
                has, pvt, rpvt) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                keys_to_insert)
        else:
            c.execute(
                'insert into apikeys (k_id, k, m, s, i, g, a, hal, has, pvt,\
             rpvt) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (
                    key.key_id,
                    key.key,
                    key.master,
                    key.sysfunc,
                    ','.join([str(i) for i in key.item_ids]),
                    ','.join([str(i) for i in key.groups]),
                    ','.join([str(i) for i in key.allow]),
                    ','.join([str(i) for i in key.hosts_allow]),
                    ','.join([str(i) for i in key.hosts_assign]),
                    ','.join([str(i) for i in key.pvt_files]),
                    ','.join([str(i) for i in key.rpvt_uris]),
                ))
        db.commit()
        c.close()
        db.close()
        if keys_list:
            logging.info('multiple apikeys created')
            return True
        logging.info('apikey %s created' % (key.key_id))
        return True
    except:
        logging.critical('apikeys db error')
        eva.core.log_traceback()


def _update_key_in_db(key=None, keys_list=None):
    try:
        db = eva.core.get_user_db()
        c = db.cursor()
        if keys_list:
            keys = [keys_by_id[k_id] for k_id in keys_list]
            keys_to_update = [(
                key.sysfunc,
                key.key,
                ','.join([str(i) for i in key.item_ids]),
                ','.join([str(i) for i in key.groups]),
                ','.join([str(i) for i in key.allow]),
                ','.join([str(i) for i in key.hosts_allow]),
                ','.join([str(i) for i in key.hosts_assign]),
                ','.join([str(i) for i in key.pvt_files]),
                ','.join([str(i) for i in key.rpvt_uris]),
                key.key_id,
            ) for key in keys]
            c.executemany(
                'update apikeys set s=?, k=?, i=?, g=?, a=?, hal=?, has=?,\
             pvt=?, rpvt=? where k_id=?', keys_to_update)
        else:
            c.execute(
                'update apikeys set s=?, k=?, i=?, g=?, a=?, hal=?, has=?, pvt=?,\
             rpvt=? where k_id=?', (
                    key.sysfunc,
                    key.key,
                    ','.join([str(i) for i in key.item_ids]),
                    ','.join([str(i) for i in key.groups]),
                    ','.join([str(i) for i in key.allow]),
                    ','.join([str(i) for i in key.hosts_allow]),
                    ','.join([str(i) for i in key.hosts_assign]),
                    ','.join([str(i) for i in key.pvt_files]),
                    ','.join([str(i) for i in key.rpvt_uris]),
                    key.key_id,
                ))
        db.commit()
        c.close()
        db.close()
        if keys_list:
            logging.info('multiple apikeys updated')
            return True
        logging.info('apikey %s updated' % (key.key_id))
        return True
    except:
        logging.critical('apikeys update db error')
        eva.core.log_traceback()


def _load_keys_from_db():
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
            _keys[key.key] = key
            _keys_by_id[key.key_id] = key
    except:
        logging.warning('unable to load API keys from db')
        eva.core.log_traceback()
    return _keys, _keys_by_id


def _create_apikeys_table():
    try:
        db = eva.core.get_user_db()
        c = db.cursor()
        c.execute('create table apikeys (k_id primary key, k, m, s, i, g, a,\
                   hal, has, pvt, rpvt)')
        db.commit()
        c.close()
    except:
        logging.critical('unable to create apikeys table in db')


def _save():
    try:
        db = eva.core.get_user_db()
        c = db.cursor()
        rows_in_mem = list(filter(lambda x: x != "masterkey" and \
            x not in _keys_loaded_from_ini, keys_by_id.keys()))
        c.execute('select k_id from apikeys')
        db.commit()
        rows_in_db = [i[0] for i in c.fetchall()]
        c.close()
        db.close()
        rows_to_add = list(set(rows_in_mem) - set(rows_in_db))
        rows_to_delete = list(set(rows_in_db) - set(rows_in_mem))
        rows_to_update = list(set(rows_in_db) & set(rows_in_mem))
        if rows_to_add:
            _save_key_to_db(keys_list=rows_to_add)
        if rows_to_update:
            _update_key_in_db(keys_list=rows_to_update)
        if rows_to_delete:
            _delete_key_from_db(keys_list=rows_to_delete)
        return True
    except Exception as e:
        if 'no such table: apikeys' in e.args:
            _save_key_to_db(keys_list=rows_in_mem)
            return True
        else:
            logging.critical('apikeys db error')
            eva.core.log_traceback()


def gen_random_hash():
    s = hashlib.sha256()
    s.update(os.urandom(1024))
    s.update(str(uuid.uuid4()).encode())
    s.update(os.urandom(1024))
    return s.hexdigest()
