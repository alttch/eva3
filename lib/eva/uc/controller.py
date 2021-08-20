__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.1"

import glob
import os
import re
import logging
import threading
import time
import sqlalchemy as sa

from sqlalchemy import text as sql

import eva.core
import eva.uc.ucqueue
import eva.uc.unit
import eva.uc.sensor
import eva.uc.ucmu
import eva.uc.driverapi
import eva.uc.modbus
import eva.uc.owfs
import eva.datapuller
import eva.registry

import rapidjson

from eva.exceptions import FunctionFailed
from eva.exceptions import ResourceNotFound
from eva.exceptions import ResourceAlreadyExists

from eva.exceptions import InvalidParameter

from eva.tools import is_oid
from eva.tools import parse_oid
from eva.tools import oid_type
from eva.tools import oid_to_id

from eva.core import db

from functools import wraps

units_by_id = {}
units_by_group = {}
units_by_full_id = {}

sensors_by_id = {}
sensors_by_group = {}
sensors_by_full_id = {}

mu_by_id = {}
mu_by_group = {}
mu_by_full_id = {}

items_by_id = {}
items_by_group = {}
items_by_full_id = {}

Q = eva.uc.ucqueue.UC_Queue('uc_queue')

configs_to_remove = set()

custom_event_handlers = {}

benchmark_lock = threading.Lock()

with_event_handler_lock = eva.core.RLocker('uc/controller')
with_item_lock = eva.core.RLocker('uc/controller')


@with_event_handler_lock
def handle_event(item):
    oid = item.oid
    if oid in custom_event_handlers:
        for f in custom_event_handlers.get(oid):
            eva.core.spawn(exec_event_handler, f, item)
    return True


def exec_event_handler(func, item):
    try:
        func(item)
    except:
        logging.error('Failed to exec event handler %s' % func)
        eva.core.log_traceback()


@with_event_handler_lock
def register_event_handler(item_id, func):
    item = get_item(item_id)
    if not item:
        return False
    custom_event_handlers.setdefault(item.oid, set()).add(func)
    logging.info('added custom event handler for %s, function %s' %
                 (item.oid, func))
    return True


@with_event_handler_lock
def unregister_event_handler(item_id, func):
    item = get_item(item_id)
    if not item:
        return False
    try:
        custom_event_handlers[item.oid].remove(func)
        logging.debug('removed custom event handler for %s, function %s' %
                      (item.oid, func))
        if not custom_event_handlers.get(item.oid):
            del custom_event_handlers[item.oid]
            logging.debug(
                'removing custom event handler for %s, last handler left' %
                item.oid)
    except:
        return False
    return True


def register_benchmark_handler():
    register_event_handler('sensor:eva_benchmarks/eva_benchmark_sensor',
                           benchmark_handler)


def unregister_benchmark_handler():
    register_event_handler('sensor:eva_benchmarks/eva_benchmark_sensor',
                           benchmark_handler)


def benchmark_handler(item):
    if not benchmark_lock.acquire(timeout=600):
        logging.critical('Core benchmark failed to obtain action lock')
        return False
    try:
        status = item.status
        value = item.value
        if status == 1:
            value = float(value)
            if value > 100:
                exec_unit_action('unit:eva_benchmarks/eva_benchmark_unit',
                                 int(value))
    finally:
        benchmark_lock.release()


@with_item_lock
def _get_all_items():
    return items_by_full_id.copy()


@with_item_lock
def get_item(item_id):
    if not item_id:
        return None
    if is_oid(item_id):
        tp, i = parse_oid(item_id)
    else:
        i = item_id
    item = None
    if i.find('/') > -1:
        if i in items_by_full_id:
            item = items_by_full_id[i]
    elif not eva.core.config.enterprise_layout and i in items_by_id:
        item = items_by_id[i]
    return None if item and is_oid(item_id) and item.item_type != tp else item


@with_item_lock
def get_unit(unit_id):
    if not unit_id:
        return None
    if is_oid(unit_id) and oid_type(unit_id) != 'unit':
        return None
    i = oid_to_id(unit_id)
    if i.find('/') > -1:
        if i in units_by_full_id:
            return units_by_full_id[i]
    elif not eva.core.config.enterprise_layout and i in units_by_id:
        return units_by_id[i]
    return None


@with_item_lock
def get_sensor(sensor_id):
    if not sensor_id:
        return None
    if is_oid(sensor_id) and oid_type(sensor_id) != 'sensor':
        return None
    i = oid_to_id(sensor_id)
    if i.find('/') > -1:
        if i in sensors_by_full_id:
            return sensors_by_full_id[i]
    elif not eva.core.config.enterprise_layout and i in sensors_by_id:
        return sensors_by_id[i]
    return None


@with_item_lock
def get_mu(mu_id):
    if not mu_id:
        return None
    if is_oid(mu_id) and oid_type(mu_id) != 'mu':
        return None
    i = oid_to_id(mu_id)
    if i.find('/') > -1:
        if i in mu_by_full_id:
            return mu_by_full_id[i]
    elif not eva.core.config.enterprise_layout and i in mu_by_id:
        return mu_by_id[i]
    return None


@with_item_lock
def append_item(item, start=False):
    if item.item_type == 'unit':
        if not eva.core.config.enterprise_layout:
            units_by_id[item.item_id] = item
        units_by_group.setdefault(item.group, {})[item.item_id] = item
        units_by_full_id[item.full_id] = item
    elif item.item_type == 'sensor':
        if not eva.core.config.enterprise_layout:
            sensors_by_id[item.item_id] = item
        sensors_by_group.setdefault(item.group, {})[item.item_id] = item
        sensors_by_full_id[item.full_id] = item
    elif item.item_type == 'mu':
        if not eva.core.config.enterprise_layout:
            mu_by_id[item.item_id] = item
        mu_by_group.setdefault(item.group, {})[item.item_id] = item
        mu_by_full_id[item.group + '/' + item.item_id] = item
    if not eva.core.config.enterprise_layout:
        items_by_id[item.item_id] = item
    items_by_group.setdefault(item.group, {})[item.item_id] = item
    items_by_full_id[item.full_id] = item
    if start:
        item.start_processors()
    logging.debug('+ %s %s' % (item.item_type, item.item_id))
    return True


@eva.core.save
@with_item_lock
def save():
    if not eva.core.config.state_to_registry:
        db = eva.core.db()
        if eva.core.config.db_update != 1:
            db = db.connect()
        dbt = db.begin()
    try:
        for i, v in items_by_full_id.items():
            if isinstance(v, eva.uc.unit.Unit) or \
                    isinstance(v, eva.uc.sensor.Sensor):
                if eva.core.config.state_to_registry:
                    if not save_item_state_to_registry(v):
                        return False
                else:
                    if not save_item_state(v, db):
                        return False
            if v.config_changed:
                if not v.save():
                    return False
            try:
                configs_to_remove.remove(v.get_rkn())
            except:
                pass
            if eva.core.config.state_to_registry:
                try:
                    configs_to_remove.remove(v.get_rskn())
                except:
                    pass
        if not eva.core.config.state_to_registry:
            dbt.commit()
    except:
        if not eva.core.config.state_to_registry:
            dbt.rollback()
        raise
    finally:
        if not eva.core.config.state_to_registry and \
                eva.core.config.db_update != 1:
            db.close()
    for f in configs_to_remove:
        try:
            eva.registry.key_delete(f)
            logging.info('Removed unused config %s' % f)
        except:
            logging.error('Can not remove %s' % f)
            eva.core.log_traceback()
    return True


@with_item_lock
def save_item_state_to_registry(item):
    try:
        eva.registry.key_set(
            item.get_rskn(), {
                'oid': item.oid,
                'set-time': item.set_time,
                'ieid': item.ieid,
                'status': item.status,
                'value': item.value
            })
    except:
        logging.critical('registry error')
        return False


@with_item_lock
def save_item_state(item, db=None):
    if eva.core.config.state_to_registry:
        return save_item_state_to_registry(item)
    dbconn = db if db else eva.core.db()
    dbt = dbconn.begin()
    try:
        _id = item.full_id if \
                eva.core.config.enterprise_layout else item.item_id
        if dbconn.execute(sql('update state set status=:status, value=:value, '
                              'set_time=:set_time, '
                              'ieid_b=:ieid_b, ieid_i=:ieid_i where id=:id'),
                          set_time=item.set_time,
                          ieid_b=item.ieid[0],
                          ieid_i=item.ieid[1],
                          status=item.status,
                          value=item.value,
                          id=_id).rowcount:
            logging.debug('{} state updated in db'.format(item.oid))
        else:
            tp = ''
            if item.item_type == 'unit':
                tp = 'U'
            elif item.item_type == 'sensor':
                tp = 'S'
            dbconn.execute(sql(
                'insert into state (id, tp, set_time,'
                ' ieid_b, ieid_i, status, value) '
                'values(:id, :tp, :set_time, :ieid_b, :ieid_i, :status, :value)'
            ),
                           id=_id,
                           tp=tp,
                           set_time=item.set_time,
                           ieid_b=item.ieid[0],
                           ieid_i=item.ieid[1],
                           status=item.status,
                           value=item.value)
            logging.debug('{} state inserted into db'.format(item.oid))
        dbt.commit()
        return True
    except:
        dbt.rollback()
        logging.critical('db error')
        return False


def load_drivers():
    eva.uc.owfs.load()
    eva.uc.modbus.load()
    eva.uc.driverapi.load()


@with_item_lock
def load_db_state(items, item_type, clean=False):
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
            'state', meta, sa.Column('id', sa.String(256), primary_key=True),
            sa.Column('tp', sa.String(10)),
            sa.Column('set_time', sa.Numeric(20, 8)),
            sa.Column('ieid_b', sa.Numeric(38, 0)),
            sa.Column('ieid_i', sa.Numeric(38, 0)),
            sa.Column('status', sa.Integer), sa.Column('value',
                                                       sa.String(8192)))
        try:
            meta.create_all(dbconn)
        except:
            logging.critical('Failed to create state table')
            eva.core.critical()
            return False
        r = dbconn.execute(sql(
            'select id, set_time, ieid_b, ieid_i, status, value'
            ' from state where tp = :tp'),
                           tp=item_type)
        while True:
            d = r.fetchone()
            if not d:
                break
            if d.id in items.keys():
                try:
                    items[d.id].status = int(d.status)
                except:
                    eva.core.log_traceback()
                    items[d.id].status = 0
                items[d.id].value = d.value if d.value != 'null' else ''
                if item_type == 'U':
                    items[d.id].nstatus = items[d.id].status
                    items[d.id].nvalue = items[d.id].value
                if d.set_time:
                    try:
                        items[d.id].set_time = float(d.set_time)
                    except:
                        eva.core.log_traceback()
                        items[d.id].set_time = time.time()
                try:
                    if d.ieid_b and d.ieid_i and \
                            d.ieid_b != '0' and d.ieid_i != '0':
                        items[d.id].ieid = eva.core.parse_ieid(
                            [d.ieid_b, d.ieid_i])
                    else:
                        # generate IEID if missing or broken
                        items[d.id].ieid = eva.core.generate_ieid()
                except:
                    eva.core.log_traceback()
                    items[d.id].ieid = eva.core.generate_ieid()
                _db_loaded_ids.append(d.id)
                logging.debug(
                    '{}:{} state loaded, status={}, value="{}"'.format(
                        item_type, d.id, items[d.id].status, items[d.id].value))
            else:
                _db_to_clean_ids.append(d.id)
        for i, v in items.items():
            if i not in _db_loaded_ids:
                dbconn.execute(
                    sql('insert into state (id, tp, '
                        'set_time, ieid_b, ieid_i, status, value) '
                        'values (:id, :tp, :set_time,'
                        ' :ieid_b, :ieid_i, :status, :value)'),
                    id=v.full_id if \
                            eva.core.config.enterprise_layout else v.item_id,
                    tp=item_type,
                    set_time=v.set_time,
                    ieid_b=v.ieid[0],
                    ieid_i=v.ieid[1],
                    status=v.status,
                    value=v.value)
                logging.debug('{} state inserted into db'.format(v.oid))
        if clean:
            for i in _db_to_clean_ids:
                dbconn.execute(sql('delete from state where id=:id'), id=i)
                logging.debug('{} state removed from db'.format(i))
        try:
            dbconn.close()
        except:
            pass
    except:
        logging.critical('db error')
        eva.core.critical()


def load_registry_state(items, item_type):
    for k, v in eva.registry.key_get_recursive(f'state/{item_type}'):
        if k in items:
            items[k].status = v['status']
            items[k].value = v['value']
            if item_type == 'unit':
                items[k].nstatus = v['status']
                items[k].nvalue = v['value']
            items[k].ieid = v['ieid']
            items[k].set_time = v['set-time']


@with_item_lock
def load_units(start=False):
    _loaded = {}
    logging.info('Loading units')
    try:
        for i, ucfg in eva.registry.key_get_recursive('inventory/unit'):
            u = eva.uc.unit.Unit(oid=f'unit:{i}')
            u.load(ucfg)
            if append_item(u, start=False):
                _loaded[i] = u
        if eva.core.config.state_to_registry:
            load_registry_state(_loaded, 'unit')
        else:
            load_db_state(_loaded, 'U', clean=True)
        if start:
            for i, v in _loaded.items():
                v.start_processors()
        return True
    except Exception as e:
        logging.error(f'Units load error: {e}')
        eva.core.log_traceback()
        return False


@with_item_lock
def load_sensors(start=False):
    _loaded = {}
    logging.info('Loading sensors')
    try:
        for i, ucfg in eva.registry.key_get_recursive('inventory/sensor'):
            u = eva.uc.sensor.Sensor(oid=f'sensor:{i}')
            u.load(ucfg)
            if append_item(u, start=False):
                _loaded[i] = u
        if eva.core.config.state_to_registry:
            load_registry_state(_loaded, 'sensor')
        else:
            load_db_state(_loaded, 'S', clean=True)
        if start:
            for i, v in _loaded.items():
                v.start_processors()
        return True
    except Exception as e:
        logging.error(f'sensors load error {e}')
        eva.core.log_traceback()
        return False


@with_item_lock
def load_mu(start=False):
    logging.info('Loading multi updates')
    try:
        for i, ucfg in eva.registry.key_get_recursive('inventory/mu'):
            u = eva.uc.ucmu.UCMultiUpdate(oid=f'mu:{i}')
            u.get_item_func = get_item
            u.load(ucfg)
            append_item(u, start=False)
            if start:
                u.start_processors()
        return True
    except Exception as e:
        logging.error(f'multi updates load error: {e}')
        eva.core.log_traceback()
        return False


@with_item_lock
def create_item(item_id,
                item_type,
                group=None,
                start=True,
                create=False,
                save=False):
    if not item_id:
        raise InvalidParameter('item id not specified')
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
    if not re.match(eva.core.OID_ALLOWED_SYMBOLS, i) or \
        not re.match(eva.core.GROUP_ALLOWED_SYMBOLS, grp):
        raise InvalidParameter(
            'Unable to create item: invalid symbols in ID {}'.format(item_id))
    i_full = grp + '/' + i
    if (not eva.core.config.enterprise_layout and i in items_by_id) or \
            i_full in items_by_full_id:
        raise ResourceAlreadyExists(get_item(i_full).oid)
    item = None
    if item_type == 'U' or item_type == 'unit':
        item = eva.uc.unit.Unit(i, create=create)
    elif item_type == 'S' or item_type == 'sensor':
        item = eva.uc.sensor.Sensor(i, create=create)
    elif item_type == 'MU' or item_type == 'mu':
        item = eva.uc.ucmu.UCMultiUpdate(i)
    if not item:
        raise FunctionFailed
    cfg = {'group': grp}
    if eva.core.config.mqtt_update_default:
        cfg['mqtt_update'] = eva.core.config.mqtt_update_default
    item.update_config(cfg)
    append_item(item, start=start)
    if save:
        item.save()
    logging.info('created new %s %s' % (item.item_type, item.full_id))
    return item


@with_item_lock
def create_unit(unit_id, group=None, enabled=None, save=False):
    unit = create_item(item_id=unit_id,
                       item_type='U',
                       group=group,
                       start=False,
                       create=True,
                       save=save and not enabled)
    if enabled:
        unit.set_prop('action_enabled', True, save=save)
        unit.ieid = eva.core.generate_ieid()
        unit.notify()
    unit.start_processors()
    return unit


@with_item_lock
def create_sensor(sensor_id, group=None, enabled=None, save=False):
    sensor = create_item(item_id=sensor_id,
                         item_type='S',
                         group=group,
                         start=False,
                         create=True,
                         save=save)
    if enabled:
        sensor.update_set_state(status=1)
    sensor.start_processors()
    return sensor


@with_item_lock
def create_mu(mu_id, group=None, save=False):
    return create_item(item_id=mu_id,
                       item_type='MU',
                       group=group,
                       start=True,
                       save=save)


@with_item_lock
def clone_item(item_id, new_item_id=None, group=None, save=False):
    i = get_item(item_id)
    ni = get_item((group + '/') if group else '' + new_item_id)
    if not i or not new_item_id or i.is_destroyed() or \
            i.item_type not in ['unit', 'sensor']:
        raise ResourceNotFound
    if ni:
        raise ResourceAlreadyExists(ni.oid)
    if group and new_item_id.find('/') != -1:
        raise InvalidParameter('Group specified but item id contains /')
    if is_oid(new_item_id):
        if oid_type(new_item_id) != i.item_type:
            return InvalidParameter('oids should be equal')
        _ni = oid_to_id(new_item_id)
    else:
        _ni = new_item_id
    if _ni.find('/') == -1:
        ni_id = _ni
        _g = i.group if group is None else group
    else:
        ni_id = _ni.split('/')[-1]
        _g = '/'.join(_ni.split('/')[:-1])
    ni = create_item(ni_id, i.item_type, _g, start=False, save=False)
    cfg = i.serialize(props=True)
    if 'description' in cfg:
        del cfg['description']
    ni.update_config(cfg)
    if save:
        ni.save()
    ni.start_processors()
    return ni


@with_item_lock
def clone_group(group = None, new_group = None,\
        prefix = None, new_prefix = None, save = False):
    if not group or not group in items_by_group:
        raise ResourceNotFound
    to_clone = []
    for i in items_by_group[group].copy():
        io = get_item(group + '/' + i)
        if io.item_type not in ['unit', 'sensor']:
            continue
        new_id = io.item_id
        if prefix and new_prefix:
            if i[:len(prefix)] == prefix:
                new_id = i.replace(prefix, new_prefix, 1)
        ni = get_item(new_group + '/' + new_id)
        if ni:
            raise ResourceAlreadyExists(ni.oid)
        to_clone.append((io.full_id, new_id))
    for i in to_clone:
        clone_item(i[0], i[1], new_group, save)
    return True


@with_item_lock
def destroy_group(group=None):
    if group is None or group not in items_by_group:
        raise ResourceNotFound
    for i in items_by_group[group].copy():
        destroy_item('{}/{}'.format(group, i))
    return True


@with_item_lock
def destroy_item(item):
    try:
        if isinstance(item, str):
            i = get_item(item)
            if not i:
                raise ResourceNotFound
        else:
            i = item
        if not eva.core.config.enterprise_layout:
            del items_by_id[i.item_id]
        del items_by_full_id[i.full_id]
        del items_by_group[i.group][i.item_id]
        if i.item_type == 'unit':
            if not eva.core.config.enterprise_layout:
                del units_by_id[i.item_id]
            del units_by_full_id[i.full_id]
            del units_by_group[i.group][i.item_id]
            if not units_by_group[i.group]:
                del units_by_group[i.group]
        if i.item_type == 'sensor':
            if not eva.core.config.enterprise_layout:
                del sensors_by_id[i.item_id]
            del sensors_by_full_id[i.full_id]
            del sensors_by_group[i.group][i.item_id]
            if not sensors_by_group[i.group]:
                del sensors_by_group[i.group]
        if i.item_type == 'mu':
            if not eva.core.config.enterprise_layout:
                del mu_by_id[i.item_id]
            del mu_by_full_id[i.full_id]
            del mu_by_group[i.group][i.item_id]
            if not mu_by_group[i.group]:
                del mu_by_group[i.group]
        if not items_by_group[i.group]:
            del items_by_group[i.group]
        i.destroy()
        if eva.core.config.auto_save:
            if i.config_file_exists:
                try:
                    eva.registry.key_delete(i.get_rkn())
                except:
                    logging.error('Can not remove %s config' % i.full_id)
                    eva.core.log_traceback()
            if eva.core.config.state_to_registry:
                try:
                    eva.registry.key_delete(i.get_rskn())
                except:
                    logging.error('Can not remove %s state key' % i.full_id)
                    eva.core.log_traceback()
        else:
            if i.config_file_exists:
                configs_to_remove.add(i.get_rkn())
            if eva.core.config.state_to_registry:
                configs_to_remove.add(i.get_rskn())
        logging.info('%s destroyed' % i.full_id)
        return True
    except ResourceNotFound:
        raise
    except Exception as e:
        eva.core.log_traceback()
        raise FunctionFailed(e)


@with_item_lock
def save_units():
    logging.info('Saving units')
    for i, u in units_by_full_id.items():
        u.save()


@with_item_lock
def save_sensors():
    logging.info('Saving sensors')
    for i, u in sensors_by_full_id.items():
        u.save()


@with_item_lock
def save_mu():
    logging.info('Saving multi updates')
    for i, u in mu_by_full_id.items():
        u.save()


def notify_all(skip_db=False):
    notify_all_units(skip_db=skip_db)
    notify_all_sensors(skip_db=skip_db)


@with_item_lock
def notify_all_units(skip_db=False):
    for i, u in units_by_full_id.items():
        u.notify(skip_db=skip_db)


@with_item_lock
def notify_all_sensors(skip_db=False):
    for i, u in sensors_by_full_id.items():
        u.notify(skip_db=skip_db)


def serialize():
    d = {}
    d['units'] = serialize_units(full=True)
    d['units_config'] = serialize_units(config=True)
    d['sensors'] = serialize_sensors(full=True)
    d['sensors_config'] = serialize_sensors(config=True)
    d['mu_config'] = serialize_mu(config=True)
    d['actions'] = serialize_actions()
    return d


@with_item_lock
def serialize_units(full=False, config=False):
    d = {}
    for i, u in units_by_full_id.items():
        d[i] = u.serialize(full, config)
    return d


@with_item_lock
def serialize_sensors(full=False, config=False):
    d = {}
    for i, u in sensors_by_full_id.items():
        d[i] = u.serialize(full, config)
    return d


@with_item_lock
def serialize_mu(full=False, config=False):
    d = {}
    for i, u in mu_by_full_id.items():
        d[i] = u.serialize(full, config)
    return d


def serialize_actions():
    return Q.serialize()


@with_item_lock
def start():
    eva.core.plugins_exec('before_start')
    eva.uc.modbus.start()
    eva.uc.owfs.start()
    eva.uc.driverapi.start()
    Q.start()
    logging.info('UC action queue started')
    for i, v in items_by_full_id.items():
        v.start_processors()
    eva.uc.driverapi.start_processors()
    eva.core.plugins_exec('start')
    eva.datapuller.start()


@with_item_lock
@eva.core.stop
def stop():
    eva.datapuller.stop()
    eva.core.plugins_exec('before_stop')
    eva.uc.driverapi.stop_processors()
    # save modified items on exit, for db_update = 2 save() is called by core
    # if eva.core.config.db_update == 1:
    # save()
    for i, v in items_by_full_id.copy().items():
        v.stop_processors()
    if Q:
        Q.stop()
    eva.uc.driverapi.stop()
    eva.uc.owfs.stop()
    eva.uc.modbus.stop()
    eva.core.plugins_exec('stop')


def exec_mqtt_unit_action(unit, msg):
    status = None
    value = None
    priority = None
    try:
        # is json?
        try:
            payload = rapidjson.loads(msg)
            status = int(payload.get('status'))
            value = payload.get('value')
            priority = payload.get('priority')
        except:
            cmd = msg.split(' ')
            status = int(cmd[0])
            if len(cmd) > 1:
                value = cmd[1]
            if len(cmd) > 2:
                priority = int(cmd[2])
            if value == 'None':
                value = None
        logging.debug('mqtt cmd msg unit = %s' % unit.full_id)
        logging.debug('mqtt cmd msg status = %s' % status)
        logging.debug('mqtt cmd msg value = "%s"' % value)
        logging.debug('mqtt cmd msg priority = "%s"' % priority)
        exec_unit_action(unit=unit,
                         nstatus=status,
                         nvalue=value,
                         priority=priority)
        return
    except:
        logging.error('%s got bad mqtt action msg' % unit.full_id)
        eva.core.log_traceback()


def exec_unit_action(unit,
                     nstatus,
                     nvalue=None,
                     priority=None,
                     q_timeout=None,
                     wait=0,
                     action_uuid=None):
    if isinstance(unit, str):
        u = get_unit(unit)
    else:
        u = unit
    if not u:
        return None
    _s = None
    try:
        _s = int(nstatus)
    except:
        _s = u.status_by_label(nstatus)
    if _s is None:
        return None
    if q_timeout:
        qt = q_timeout
    else:
        qt = eva.core.config.timeout
    a = u.create_action(_s, nvalue, priority, action_uuid)
    Q.put_task(a)
    if not a.processed.wait(timeout=qt):
        if a.set_dead():
            return a
    if wait:
        a.finished.wait(timeout=wait)
    return a


@with_item_lock
@eva.core.dump
def dump():
    return serialize()


def init():
    pass
