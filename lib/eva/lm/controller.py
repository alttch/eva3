__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.0"

import glob
import os
import re
import logging
import threading
import time
import sqlalchemy as sa

from sqlalchemy import text as sql

import eva.core
import eva.api
import eva.apikey
import eva.item
import eva.lm.lvar
import eva.client.remote_controller
import eva.client.coreapiclient
import eva.lm.plc
import eva.lm.lremote
import eva.lm.lmqueue
import eva.lm.dmatrix
import eva.lm.extapi
import eva.lm.macro_api

from eva.exceptions import FunctionFailed
from eva.exceptions import ResourceNotFound
from eva.exceptions import ResourceAlreadyExists

from eva.exceptions import InvalidParameter

from eva.tools import is_oid
from eva.tools import oid_to_id
from eva.tools import oid_type
from eva.tools import parse_oid

from eva.core import db

from functools import wraps
from pyaltt import background_job

lvars_by_id = {}
lvars_by_group = {}
lvars_by_full_id = {}

macros_by_id = {}
macros_by_full_id = {}

cycles_by_id = {}
cycles_by_full_id = {}

dm_rules = {}

items_by_id = {}
items_by_group = {}
items_by_full_id = {}

remote_ucs = {}

configs_to_remove = set()

uc_pool = None

plc = None

Q = None

DM = None

with_item_lock = eva.core.RLocker('lm/controller')


def format_rule_id(r_id):
    if is_oid(r_id):
        r_id = oid_to_id(r_id, required='dmatrix_rule')
    if not isinstance(r_id, str): return None
    if r_id.find('/') != -1:
        g, r_id = r_id.split('/')
        if g != 'dm_rules': return None
    return r_id


@with_item_lock
def get_item(item_id):
    if not item_id: return None
    if is_oid(item_id):
        tp, i = parse_oid(item_id)
    else:
        i = item_id
    if tp == 'lmacro':
        return self.get_macro(i)
    elif tp == 'lcycle':
        return self.get_cycle(i)
    elif tp == 'dmatrix_rule':
        return self.get_dm_rule(i)
    item = None
    if i.find('/') > -1:
        if i in items_by_full_id: item = items_by_full_id[i]
    elif not eva.core.enterprise_layout and i in items_by_id:
        item = items_by_id[i]
    return None if item and is_oid(item_id) and item.item_type != tp else item


def get_controller(controller_id):
    _controller_id = oid_to_id(controller_id, 'remote_uc')
    if not _controller_id: return None
    if _controller_id.find('/') > -1:
        i = _controller_id.split('/')
        if len(i) > 2 or i[0] != 'uc': return None
        if i[1] in remote_ucs: return remote_ucs[i[1]]
    else:
        if _controller_id in remote_ucs: return remote_ucs[_controller_id]
    return None


@with_item_lock
def get_macro(macro_id):
    _macro_id = oid_to_id(macro_id, 'lmacro')
    if not _macro_id: return None
    if _macro_id.find('/') > -1:
        if _macro_id in macros_by_full_id: return macros_by_full_id[_macro_id]
    else:
        if _macro_id in macros_by_id: return macros_by_id[_macro_id]
    return None


@with_item_lock
def get_cycle(cycle_id):
    _cycle_id = oid_to_id(cycle_id, 'lcycle')
    if not _cycle_id: return None
    if _cycle_id.find('/') > -1:
        if _cycle_id in cycles_by_full_id: return cycles_by_full_id[_cycle_id]
    else:
        if _cycle_id in cycles_by_id: return cycles_by_id[_cycle_id]
    return None


@with_item_lock
def get_dm_rule(r_id):
    r_id = format_rule_id(r_id)
    if not r_id: return None
    if r_id in dm_rules: return dm_rules[r_id]
    return None


@with_item_lock
def get_lvar(lvar_id):
    if not lvar_id: return None
    if is_oid(lvar_id) and oid_type(lvar_id) != 'lvar': return None
    i = oid_to_id(lvar_id)
    if i.find('/') > -1:
        if i in lvars_by_full_id: return lvars_by_full_id[i]
    elif not eva.core.enterprise_layout and i in lvars_by_id:
        return lvars_by_id[i]
    return None


@with_item_lock
def append_item(item, start=False, load=True):
    try:
        if load and not item.load(): return False
    except:
        eva.core.log_traceback()
        return False
    if item.item_type == 'lvar':
        if not eva.core.enterprise_layout:
            lvars_by_id[item.item_id] = item
        lvars_by_group.setdefault(item.group, {})[item.item_id] = item
        lvars_by_full_id[item.full_id] = item
    if not eva.core.enterprise_layout:
        items_by_id[item.item_id] = item
    items_by_group.setdefault(item.group, {})[item.item_id] = item
    items_by_full_id[item.full_id] = item
    if start: item.start_processors()
    logging.debug('+ %s' % (item.oid))
    return True


@eva.core.save
@with_item_lock
def save():
    for i, v in lvars_by_full_id.items():
        if not save_lvar_state(v):
            return False
        if v.config_changed:
            if not v.save():
                return False
        try:
            configs_to_remove.remove(v.get_fname())
        except:
            pass
    for i, v in remote_ucs.items():
        if v.config_changed:
            if not v.save():
                return False
        try:
            if i.static:
                configs_to_remove.remove(v.get_fname())
        except:
            pass
    for i, v in macros_by_id.items():
        if v.config_changed:
            if not v.save():
                return False
        try:
            configs_to_remove.remove(v.get_fname())
        except:
            pass
    for i, v in cycles_by_id.items():
        if v.config_changed:
            if not v.save():
                return False
        try:
            configs_to_remove.remove(v.get_fname())
        except:
            pass
    for i, v in dm_rules.items():
        if v.config_changed:
            if not v.save():
                return False
        try:
            configs_to_remove.remove(v.get_fname())
        except:
            pass
    for f in configs_to_remove:
        try:
            os.unlink(f)
            logging.info('Removed unused config %s' % f)
        except:
            logging.error('Can not remove %s' % f)
            eva.core.log_traceback()
    return True


@with_item_lock
def save_lvar_state(item):
    dbconn = eva.core.db()
    try:
        _id = item.full_id if eva.core.enterprise_layout else item.item_id
        if dbconn.execute(
                sql('update lvar_state set set_time=:t,' +
                    ' status=:status, value=:value where id=:id'),
                t=item.set_time,
                status=item.status,
                value=item.value,
                id=_id).rowcount:
            logging.debug('%s state updated in db' % item.oid)
        else:
            dbconn.execute(
                sql('insert into lvar_state (id, set_time, status, value) ' +
                    'values(:id, :t, :status, :value)'),
                id=_id,
                t=item.set_time,
                status=item.status,
                value=item.value)
            logging.debug('{} state inserted into db'.format(item.oid))
        return True
    except:
        logging.critical('db error')
        eva.core.critical()
        return False


def load_extensions():
    eva.lm.extapi.load()


@with_item_lock
def load_lvar_db_state(items, clean=False):
    _db_loaded_ids = []
    _db_to_clean_ids = []
    try:
        dbconn = eva.core.db()
        if not dbconn:
            logging.critical('unable to get db')
            eva.core.critical()
            return
        meta = sa.MetaData()
        t_state_history = sa.Table(
            'lvar_state', meta, sa.Column(
                'id', sa.String(256), primary_key=True),
            sa.Column('set_time', sa.Numeric(20, 8)),
            sa.Column('status', sa.Integer), sa.Column('value', sa.String(256)))
        try:
            meta.create_all(dbconn)
        except:
            logging.critical('Failed to create lvar_state table')
            eva.core.critical()
            return False
        r = dbconn.execute(
            sql('select id, set_time, status, value from lvar_state'))
        while True:
            d = r.fetchone()
            if not d: break
            if d.id in items.keys():
                try:
                    items[d.id].set_time = float(d.set_time)
                except:
                    eva.core.log_traceback()
                    items[d.id].set_time = None
                try:
                    items[d.id].status = int(d.status)
                except:
                    eva.core.log_traceback()
                    items[d.id].status = 0
                items[d.id].value = d.value
                _db_loaded_ids.append(d.id)
                logging.debug(
                    '{} state loaded, set_time={}, status={}, value="{}"'.
                    format(d.id, d.set_time, d.status, d.value))
            else:
                _db_to_clean_ids.append(d.id)
        for i, v in items.items():
            if i not in _db_loaded_ids:
                dbconn.execute(
                    sql('insert into lvar_state (id, set_time, status, value) '
                        + 'values (:id, :t, :status, :value)'),
                    id=v.item_id,
                    t=v.set_time,
                    status=v.status,
                    value=v.value)
                logging.debug('{} state inserted into db'.format(v.oid))
        if clean:
            for i in _db_to_clean_ids:
                dbconn.execute(sql('delete from lvar_state where id=:id'), id=i)
                logging.debug('{} state removed from db'.format(i))
    except:
        logging.critical('db error')
        eva.core.critical()


@with_item_lock
def load_lvars(start=False):
    _loaded = {}
    logging.info('Loading lvars')
    try:
        fnames = eva.core.format_cfg_fname(eva.core.product_code + \
                '_lvar.d/*.json', runtime = True)
        for ucfg in glob.glob(fnames):
            lvar_id = os.path.splitext(os.path.basename(ucfg))[0]
            if eva.core.enterprise_layout:
                _id = lvar_id.split('___')[-1]
                lvar_id = lvar_id.replace('___', '/')
            else:
                _id = lvar_id
            u = eva.lm.lvar.LVar(_id)
            if eva.core.enterprise_layout:
                u.set_group('/'.join(lvar_id.split('/')[:-1]))
            if append_item(u, start=False):
                _loaded[lvar_id] = u
        load_lvar_db_state(_loaded, clean=True)
        if start:
            for i, v in _loaded.items():
                v.start_processors()
        return True
    except:
        logging.error('LVars load error')
        eva.core.log_traceback()
        return False


def load_remote_ucs():
    logging.info('Loading remote UCs')
    try:
        fnames = eva.core.format_cfg_fname(eva.core.product_code + \
                '_remote_uc.d/*.json', runtime = True)
        for ucfg in glob.glob(fnames):
            uc_id = os.path.splitext(os.path.basename(ucfg))[0]
            u = eva.lm.lremote.LRemoteUC(uc_id)
            if u.load():
                remote_ucs[uc_id] = u
        return True
    except:
        logging.error('UCs load error')
        eva.core.log_traceback()
        return False


@with_item_lock
def load_macros():
    logging.info('Loading macro configs')
    try:
        fnames = eva.core.format_cfg_fname(eva.core.product_code + \
                '_lmacro.d/*.json', runtime = True)
        for mcfg in glob.glob(fnames):
            m_id = os.path.splitext(os.path.basename(mcfg))[0]
            m = eva.lm.plc.Macro(m_id)
            if m.load():
                macros_by_id[m_id] = m
                macros_by_full_id[m.full_id] = m
                logging.debug('macro "%s" config loaded' % m_id)
        return True
    except:
        logging.error('Macro configs load error')
        eva.core.log_traceback()
        return False


@with_item_lock
def load_cycles():
    logging.info('Loading cycle configs')
    try:
        fnames = eva.core.format_cfg_fname(eva.core.product_code + \
                '_lcycle.d/*.json', runtime = True)
        for mcfg in glob.glob(fnames):
            m_id = os.path.splitext(os.path.basename(mcfg))[0]
            m = eva.lm.plc.Cycle(m_id)
            if m.load():
                cycles_by_id[m_id] = m
                cycles_by_full_id[m.full_id] = m
                logging.debug('cycle "%s" config loaded' % m_id)
        return True
    except:
        logging.error('Cycle configs load error')
        eva.core.log_traceback()
        return False


@with_item_lock
def load_dm_rules():
    logging.info('Loading DM rules')
    try:
        fnames = eva.core.format_cfg_fname(eva.core.product_code + \
                '_dmatrix_rule.d/*.json', runtime = True)
        for rcfg in glob.glob(fnames):
            r_id = os.path.splitext(os.path.basename(rcfg))[0]
            r = eva.lm.dmatrix.DecisionRule(r_id)
            if r.load():
                dm_rules[r_id] = r
                if eva.core.development:
                    rule_id = r_id
                else:
                    rule_id = r_id[:14] + '...'
                logging.debug('DM rule %s loaded' % rule_id)
        return True
    except:
        logging.error('DM rules load error')
        eva.core.log_traceback()
        return False


@with_item_lock
def create_macro(m_id, group=None, save=False):
    _m_id = oid_to_id(m_id, 'lmacro')
    if not _m_id: raise InvalidParameter('macro id not specified')
    if group and _m_id.find('/') != -1:
        raise InvalidParameter('group specified but macro id contains /')
    if _m_id.find('/') == -1:
        i = _m_id
        grp = group
    else:
        i = _m_id.split('/')[-1]
        grp = '/'.join(_m_id.split('/')[:-1])
    if not grp: grp = 'nogroup'
    if not re.match("^[A-Za-z0-9_\.-]*$", i) or \
        not re.match("^[A-Za-z0-9_\./-]*$", grp):
            raise InvalidParameter('Invalid symbols in macro id')
    i_full = grp + '/' + i
    if i in macros_by_id or i_full in macros_by_full_id:
        raise ResourceAlreadyExists
    m = eva.lm.plc.Macro(i)
    m.set_prop('action_enabled', 'true', False)
    if grp: m.update_config({'group': grp})
    macros_by_id[i] = m
    macros_by_full_id[m.full_id] = m
    if save: m.save()
    logging.info('macro "%s" created' % m.full_id)
    return m


@with_item_lock
def destroy_macro(m_id):
    i = get_macro(m_id)
    if not i: raise ResourceNotFound
    try:
        i.destroy()
        if eva.core.db_update == 1 and i.config_file_exists:
            try:
                os.unlink(i.get_fname())
            except:
                logging.error('Can not remove macro "%s" config' % \
                        m_id)
                eva.core.log_traceback()
        elif i.config_file_exists:
            configs_to_remove.add(i.get_fname())
        del (macros_by_id[i.item_id])
        del (macros_by_full_id[i.full_id])
        logging.info('macro "%s" removed' % i.full_id)
        return True
    except:
        eva.core.log_traceback()
        raise FunctionFailed


@with_item_lock
def create_cycle(m_id, group=None, save=False):
    _m_id = oid_to_id(m_id, 'lcycle')
    if not _m_id: return False
    if group and _m_id.find('/') != -1: return False
    if _m_id.find('/') == -1:
        i = _m_id
        grp = group
    else:
        i = _m_id.split('/')[-1]
        grp = '/'.join(_m_id.split('/')[:-1])
    if not grp: grp = 'nogroup'
    if not re.match("^[A-Za-z0-9_\.-]*$", i) or \
        not re.match("^[A-Za-z0-9_\./-]*$", grp):
        return False
    i_full = grp + '/' + i
    if i in cycles_by_id or i_full in cycles_by_full_id: return False
    m = eva.lm.plc.Cycle(i)
    if grp: m.update_config({'group': grp})
    cycles_by_id[i] = m
    cycles_by_full_id[m.full_id] = m
    if save: m.save()
    logging.info('cycle "%s" created' % m.full_id)
    return True


@with_item_lock
def destroy_cycle(m_id):
    i = get_cycle(m_id)
    if not i: return None
    try:
        i.destroy()
        if eva.core.db_update == 1 and i.config_file_exists:
            try:
                os.unlink(i.get_fname())
            except:
                logging.error('Can not remove cycle "%s" config' % \
                        m_id)
                eva.core.log_traceback()
        elif i.config_file_exists:
            configs_to_remove.add(i.get_fname())
        del (cycles_by_id[i.item_id])
        del (cycles_by_full_id[i.full_id])
        logging.info('cycle "%s" removed' % i.full_id)
        return True
    except:
        eva.core.log_traceback()
        return False


@with_item_lock
def create_dm_rule(save=False, rule_uuid=None):
    if rule_uuid in dm_rules:
        raise ResourceAlreadyExists
    r = eva.lm.dmatrix.DecisionRule(rule_uuid=rule_uuid)
    dm_rules[r.item_id] = r
    if save: r.save()
    DM.append_rule(r)
    logging.info('new rule created: %s' % r.item_id)
    return r


@with_item_lock
def destroy_dm_rule(r_id):
    r_id = format_rule_id(r_id)
    if r_id not in dm_rules:
        raise ResourceNotFound
    try:
        i = dm_rules[r_id]
        i.destroy()
        DM.remove_rule(i)
        if eva.core.db_update == 1 and i.config_file_exists:
            try:
                os.unlink(i.get_fname())
            except:
                logging.error('Can not remove DM rule %s config' % \
                        r_id)
                eva.core.log_traceback()
        elif i.config_file_exists:
            configs_to_remove.add(i.get_fname())
        del (dm_rules[r_id])
        logging.info('DM rule %s removed' % r_id)
        return True
    except Exception as e:
        eva.core.log_traceback()
        return FunctionFailed(e)


def handle_discovered_controller(notifier_id, controller_id, **kwargs):
    try:
        ct, c_id = controller_id.split('/')
        if ct != 'uc':
            return True
        if c_id in uc_pool.controllers:
            logging.debug(
                'Controller {} already exists, skipped (discovered from {})'.
                format(controller_id, notifier_id))
            return True
        key = eva.apikey.key_by_id('default')
        if not key:
            logging.debug('Controller {} discovered, (discovered from {}), '.
                          format(controller_id, notifier_id) +
                          'but no API key with ID=default')
            return False
        logging.info(
            'Controller {} discovered, appending (discovered from {})'.format(
                controller_id, notifier_id))
        return append_controller(
            'mqtt:{}:{}'.format(notifier_id, controller_id),
            key="$default",
            mqtt_update=notifier_id,
            static=False)
    except:
        logging.warning('Unable to process controller, discovered from ' +
                        notifier_id)
        eva.core.log_traceback()
        return False


def append_controller(uri,
                      key=None,
                      mqtt_update=None,
                      ssl_verify=True,
                      timeout=None,
                      save=False,
                      static=True):
    api = eva.client.coreapiclient.CoreAPIClient()
    api.set_product('uc')
    if key is not None: api.set_key(eva.apikey.format_key(key))
    if timeout is not None:
        try:
            t = float(timeout)
        except:
            return False
        api.set_timeout(t)
    else:
        api.set_timeout(eva.core.timeout)
    uport = ''
    if uri.startswith('http://') or uri.startswith('https://'):
        if uri.count(':') == 1 and uri.count('/') == 2:
            uport = ':8812'
    else:
        if uri.find(':') == -1 and uri.find('/') == -1:
            uport = ':8812'
    api.set_uri(uri + uport)
    mqu = mqtt_update
    if mqu is None: mqu = eva.core.mqtt_update_default
    u = eva.lm.lremote.LRemoteUC(None, api=api, mqtt_update=mqu, static=static)
    u._key = key
    if not uc_pool.append(u): return False
    remote_ucs[u.item_id] = u
    if save: u.save()
    logging.info('controller %s added to pool' % u.item_id)
    return True


def remove_controller(controller_id):
    _controller_id = oid_to_id(controller_id, 'remote_uc')
    if not _controller_id: return False
    if _controller_id.find('/') != -1:
        _controller_id = _controller_id.split('/')[-1]
    if _controller_id not in remote_ucs:
        return None
    try:
        i = remote_ucs[_controller_id]
        i.destroy()
        if eva.core.db_update == 1 and i.config_file_exists:
            try:
                os.unlink(i.get_fname())
            except:
                logging.error('Can not remove controller %s config' % \
                        _controller_id)
                eva.core.log_traceback()
        elif i.config_file_exists:
            configs_to_remove.add(i.get_fname())
        del (remote_ucs[_controller_id])
        logging.info('controller %s removed' % _controller_id)
        return True
    except:
        eva.core.log_traceback()
        return False


@with_item_lock
def create_item(item_id, item_type, group=None, virtual=False, save=False):
    if not item_id: raise InvalidParameter('item id not specified')
    if group and item_id.find('/') != -1:
        raise InvalidParameter(
            'Unable to create item: invalid symbols in ID {}'.format(item_id))
    if item_id.find('/') == -1:
        i = item_id
        grp = group
    else:
        i = item_id.split('/')[-1]
        grp = '/'.join(item_id.split('/')[:-1])
    if not grp:
        grp = 'nogroup'
    if not re.match("^[A-Za-z0-9_\.-]*$", i) or \
        not re.match("^[A-Za-z0-9_\./-]*$", grp):
        raise InvalidParameter(
            'Unable to create item: invalid symbols in ID {}'.format(item_id))
    i_full = grp + '/' + i
    if (not eva.core.enterprise_layout and i in items_by_id) or \
            i_full in items_by_full_id:
        raise ResourceAlreadyExists(get_item(i_full).oid)
    item = None
    if item_type == 'LV' or item_type == 'lvar':
        item = eva.lm.lvar.LVar(i)
    if not item: return False
    if virtual: virt = True
    else: virt = False
    cfg = {'group': grp, 'virtual': virt}
    if eva.core.mqtt_update_default:
        cfg['mqtt_update'] = eva.core.mqtt_update_default
    item.update_config(cfg)
    append_item(item, start=True, load=False)
    if save: item.save()
    if item_type == 'LV' or item_type == 'lvar':
        item.notify()
    logging.info('created new %s %s' % (item.item_type, item.full_id))
    return True


@with_item_lock
def create_lvar(lvar_id, group=None, save=False):
    return create_item(
        item_id=lvar_id, item_type='LV', group=group, virtual=False, save=save)


@with_item_lock
def destroy_item(item):
    try:
        if isinstance(item, str):
            i = get_item(item)
            if not i: raise ResourceNotFound
        else:
            i = item
        if not eva.core.enterprise_layout:
            del items_by_id[i.item_id]
        del items_by_full_id[i.full_id]
        del items_by_group[i.group][i.item_id]
        if i.item_type == 'lvar':
            if not eva.core.enterprise_layout:
                del lvars_by_id[i.item_id]
            del lvars_by_full_id[i.full_id]
            del lvars_by_group[i.group][i.item_id]
            if not lvars_by_group[i.group]:
                del lvars_by_group[i.group]
        if not items_by_group[i.group]:
            del items_by_group[i.group]
        i.destroy()
        if eva.core.db_update == 1 and i.config_file_exists:
            try:
                os.unlink(i.get_fname())
            except:
                logging.error('Can not remove %s config' % i.full_id)
                eva.core.log_traceback()
        elif i.config_file_exists:
            configs_to_remove.add(i.get_fname())
        logging.info('%s destroyed' % i.full_id)
        return True
    except exception as e:
        eva.core.log_traceback()
        raise functionfailed(e)


@with_item_lock
def save_lvars():
    logging.info('Saving lvars')
    for i, u in lvars_by_full_id.items():
        u.save()


def notify_all(skip_subscribed_mqtt=False):
    notify_all_lvars(skip_subscribed_mqtt=skip_subscribed_mqtt)


@with_item_lock
def notify_all_lvars(skip_subscribed_mqtt=False):
    for i, u in lvars_by_full_id.items():
        u.notify(skip_subscribed_mqtt=skip_subscribed_mqtt)


def serialize():
    d = {}
    d['lvars'] = serialize_lvars(full=True)
    d['lvars_config'] = serialize_lvars(config=True)
    return d


@with_item_lock
def serialize_lvars(full=False, config=False):
    d = {}
    for i, u in lvars_by_full_id.items():
        d[i] = u.serialize(full, config)
    return d


def pdme(item, ns=False):
    if not DM: return False
    return DM.process(item, ns=ns)


def start():
    global uc_pool
    global plc
    global Q
    global DM
    eva.lm.extapi.start()
    Q = eva.lm.lmqueue.LM_Queue('lm_queue')
    Q.start()
    DM = eva.lm.dmatrix.DecisionMatrix()
    for i, r in dm_rules.items():
        DM.append_rule(r, do_sort=False)
    DM.sort()
    plc = eva.lm.plc.PLC()
    plc.start_processors()
    uc_pool = eva.client.remote_controller.RemoteUCPool()
    uc_pool.start()
    for i, v in remote_ucs.items():
        background_job(connect_remote_controller, daemon=True)(v)
    for i, v in lvars_by_full_id.items():
        v.start_processors()
    for i, v in cycles_by_id.copy().items():
        v.start(autostart=True)


def connect_remote_controller(v):
    if uc_pool.append(v):
        logging.info('%s added to the controller pool' % \
                v.full_id)
    else:
        logging.error('Failed to add %s to the controller pool' % \
                v.full_id)


@eva.core.stop
def stop():
    # save modified items on exit, for db_update = 2 save() is called by core
    if eva.core.db_update == 1: save()
    for i, v in cycles_by_id.copy().items():
        v.stop(wait=False)
    for i, v in items_by_full_id.copy().items():
        v.stop_processors()
    if uc_pool:
        uc_pool.stop()
    if plc: plc.stop_processors()
    if Q: Q.stop()
    eva.lm.extapi.stop()


def exec_macro(macro,
               argv=[],
               kwargs={},
               priority=None,
               q_timeout=None,
               wait=0,
               action_uuid=None,
               source=None,
               is_shutdown_func=None):
    if isinstance(macro, str):
        m = get_macro(macro)
    else:
        m = macro
    if not m: return None
    if q_timeout: qt = q_timeout
    else: qt = eva.core.timeout
    if argv is None: _argv = []
    else: _argv = argv
    _argvf = []
    for x in _argv:
        try:
            _value = float(x)
            if _value == int(_value): _value = int(_value)
        except:
            _value = x
        _argvf.append(_value)
    a = eva.lm.plc.MacroAction(
        m,
        argv=_argvf,
        kwargs=kwargs,
        priority=priority,
        action_uuid=action_uuid,
        source=source,
        is_shutdown_func=is_shutdown_func)
    Q.put_task(a)
    if not eva.core.wait_for(a.is_processed, q_timeout):
        if a.set_dead():
            return a
    if wait: eva.core.wait_for(a.is_finished, wait)
    return a


@eva.core.dump
def dump(item_id=None):
    if item_id: return items_by_full_id[item_id]
    rcs = {}
    for i, v in remote_ucs.copy().items():
        rcs[i] = v.serialize()
    else:
        return {
            'lm_items': items_by_full_id,
            'remote_ucs': rcs,
            'macros': macros_by_full_id,
            'dm_rules': dm_rules
        }


def init():
    eva.lm.macro_api.init()


eva.api.mqtt_discovery_handler = handle_discovered_controller
eva.api.remove_controller = remove_controller
