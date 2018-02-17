__author__ = "Altertech Group, http://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2017 Altertech Group"
__license__ = "See http://www.eva-ics.com/"
__version__ = "3.0.0"

import glob
import os
import re
import logging
import threading
import time

import eva.core
import eva.uc.ucqueue
import eva.uc.unit
import eva.uc.sensor
import eva.uc.ucmu

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

Q = None

configs_to_remove = set()


def get_item(item_id):
    if not item_id: return None
    if item_id.find('/') > -1:
        if item_id in items_by_full_id: return items_by_full_id[item_id]
    else:
        if item_id in items_by_id: return items_by_id[item_id]
    return None


def get_unit(unit_id):
    if not unit_id: return None
    if unit_id.find('/') > -1:
        if unit_id in units_by_full_id: return units_by_full_id[unit_id]
    else:
        if unit_id in units_by_id: return units_by_id[unit_id]
    return None


def get_sensor(sensor_id):
    if not sensor_id: return None
    if sensor_id.find('/') > -1:
        if sensor_id in sensors_by_full_id:
            return sensors_by_full_id[sensor_id]
    else:
        if sensor_id in sensors_by_id: return sensors_by_id[sensor_id]
    return None


def get_mu(mu_id):
    if not mu_id: return None
    if mu_id.find('/') > -1:
        if mu_id in mu_by_full_id: return mu_by_full_id[mu_id]
    else:
        if mu_id in mu_by_id: return mu_by_id[mu_id]
    return None


def append_item(item, start = False, load = True):
    try:
        if load and not item.load(): return False
    except:
        eva.core.log_traceback()
        return False
    if item.item_type == 'unit':
        units_by_id[item.item_id] = item
        if item.group not in units_by_group:
            units_by_group[item.group] = {}
        units_by_group[item.group][item.item_id] = item
        units_by_full_id[item.full_id] = item
    elif item.item_type == 'sensor':
        sensors_by_id[item.item_id] = item
        if item.group not in sensors_by_group:
            sensors_by_group[item.group] = {}
        sensors_by_group[item.group][item.item_id] = item
        sensors_by_full_id[item.full_id] = item
    elif item.item_type == 'mu':
        mu_by_id[item.item_id] = item
        if item.group not in mu_by_group:
            mu_by_group[item.group] = {}
        mu_by_group[item.group][item.item_id] = item
        mu_by_full_id[item.group + '/' + item.item_id] = item
    items_by_id[item.item_id] = item
    if item.group not in items_by_group:
        items_by_group[item.group] = {}
    items_by_group[item.group][item.item_id] = item
    items_by_full_id[item.full_id] = item
    if start: item.start_processors()
    logging.debug('+ %s %s' % (item.item_type, item.item_id))
    return True


def create_state_table():
    try:
        db = eva.core.get_db()
        c = db.cursor()
        c.execute('create table state(id primary key, tp, status, value)')
        db.commit()
        c.close()
    except:
        logging.critical('unable to create state table in db')
    db.close()


def save():
    for i, v in items_by_id.items():
        if isinstance(v, eva.uc.unit.Unit) or \
                isinstance(v, eva.uc.sensor.Sensor):
            if not save_item_state(v):
                return False
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
            logging.info('Removed unused config %s', f)
        except:
            logging.error('Can not remove %s' % f)
            eva.core.log_traceback()
    return True


def save_item_state(item):
    try:
        db = eva.core.get_db()
        c = db.cursor()
        c.execute('update state set status=?, value=? where id=?',
                (item.status, item.value, item.item_id))
        if not c.rowcount:
            c.close()
            tp = ''
            if item.item_type == 'unit':
                tp = 'U'
            elif item.item_type == 'sensor':
                tp = 'S'
            c = db.cursor()
            c.execute('insert into state (id, tp, status, value) ' +\
                    'values(?,?,?,?)',
                    (item.item_id, tp, item.status, item.value))
            logging.debug('%s state inserted into db' % item.full_id)
        else:
            logging.debug('%s state updated in db' % item.full_id)
        db.commit()
        c.close()
        db.close()
        return True
    except:
        logging.critical('db error')
        eva.core.log_traceback()
        return False


def load_db_state(items, item_type, clean = False, create = True):
    _db_loaded_ids = []
    _db_to_clean_ids = []
    db = eva.core.get_db()
    c = db.cursor()
    try:
        c.execute(
                'select id, status, value from state where tp = ?',
                (item_type,))
        try:
            for d in c:
                if d[0] in items.keys():
                    items[d[0]].status = int(d[1])
                    items[d[0]].value = d[2]
                    if item_type == 'U':
                        items[d[0]].nstatus = int(d[1])
                        items[d[0]].nvalue = d[2]
                    _db_loaded_ids.append(d[0])
                    logging.debug('%s state loaded, status=%u, value="%s"' % \
                            (
                            items[d[0]].full_id,
                            items[d[0]].status,
                            items[d[0]].value))
                else:
                    _db_to_clean_ids.append(d[0])
            c.close()
            c = db.cursor()
            for i,v in items.items():
                if i not in _db_loaded_ids:
                    c.execute(
                        'insert into state (id, tp, status, value) ' + \
                        'values (?, ?, ?, ?)',
                            (v.item_id, item_type, v.status, v.value))
                    logging.debug('%s state inserted into db' % v.full_id)
            if clean:
                for i in _db_to_clean_ids:
                    c.execute('delete from state where id=?' , (i,))
                    logging.debug('%s state removed from db' % i)
        except:
            logging.critical('db error')
            eva.core.log_traceback()
        db.commit()
        c.close()
    except:
        if not create:
            logging.critical('db error')
            eva.core.log_traceback()
        else:
            c.close()
            logging.info('No state table in db, creating new')
            create_state_table()
            load_db_state(items, item_type, clean, create = False)
    db.close()


def load_units(start = False):
    _loaded = {}
    logging.info('Loading units')
    try:
        fnames = eva.core.format_cfg_fname(eva.core.product_code + \
                '_unit.d/*.json', runtime = True)
        for ucfg in glob.glob(fnames):
            unit_id = os.path.splitext(os.path.basename(ucfg))[0]
            u = eva.uc.unit.Unit(unit_id)
            if append_item(u, start = False):
                _loaded[unit_id] = u
        load_db_state(_loaded, 'U', clean = True)
        if start:
            for i, v in _loaded.items(): v.start_processors()
        return True
    except:
        logging.error('Units load error')
        eva.core.log_traceback()
        return False


def load_sensors(start = False):
    _loaded = {}
    logging.info('Loading sensors')
    try:
        fnames = eva.core.format_cfg_fname(eva.core.product_code + \
                '_sensor.d/*.json', runtime = True)
        for ucfg in glob.glob(fnames):
            sensor_id = os.path.splitext(os.path.basename(ucfg))[0]
            u = eva.uc.sensor.Sensor(sensor_id)
            if append_item(u, start = False):
                _loaded[sensor_id] = u
        load_db_state(_loaded, 'S', clean = True)
        if start:
            for i, v in _loaded.items(): v.start_processors()
        return True
    except:
        logging.error('sensors load error')
        eva.core.log_traceback()
        return False


def create_item(item_id, item_type, group = None,
        virtual = False, start = True, save = False):
    if not item_id: return False
    if group and item_id.find('/') != -1: return False
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
            return False
    i_full = grp + '/' + i
    if i in items_by_id or i_full in items_by_full_id: return False
    item = None
    if item_type == 'U' or item_type == 'unit':
        item = eva.uc.unit.Unit(i)
    elif item_type == 'S' or item_type == 'sensor':
        item = eva.uc.sensor.Sensor(i)
    elif item_type == 'MU' or item_type == 'mu':
        item = eva.uc.ucmu.UCMultiUpdate(i)
    if not item: return False
    if virtual: virt = True
    else: virt = False
    cfg = { 'group': grp, 'virtual': virt }
    if eva.core.mqtt_update_default:
        cfg['mqtt_update'] = eva.core.mqtt_update_default
    item.update_config(cfg)
    append_item(item, start = start, load = False)
    if save: item.save()
    logging.info('created new %s %s' % (item.item_type, item.full_id))
    return item


def create_unit(unit_id, group = None, virtual = False, save = False):
    return create_item(item_id = unit_id, item_type = 'U', group = group,
            virtual = virtual, start = True, save = save)


def create_sensor(sensor_id, group = None, virtual = False, save = False):
    return create_item(item_id = sensor_id, item_type = 'S', group = group,
            virtual = virtual, start = True, save = save)


def create_mu(mu_id, group = None, virtual = False, save = False):
    return create_item(item_id = mu_id, item_type = 'MU', group = group,
            virtual = virtual, start = True, save = save)


def clone_item(item_id, new_item_id = None, group = None, save = False):
    i = get_item(item_id)
    ni = get_item(new_item_id)
    if not i or not new_item_id or ni or i.is_destroyed(): return None
    ni = create_item(new_item_id, i.item_type, group, start = False,
            save = False)
    cfg = i.serialize(props = True)
    if 'description' in cfg: del cfg['description']
    ni.update_config(cfg)
    if save: ni.save()
    ni.start_processors()
    return ni


def clone_group(group = None, new_group = None,\
        prefix = None, new_prefix = None, save = False):
    if not group or not group in items_by_group \
            or not prefix or not new_prefix: return False
    to_clone = []
    for i in items_by_group[group].copy():
        if i[:len(prefix)] == prefix:
            new_id = i.replace(prefix, new_prefix, 1)
            if get_item(new_id): return False
            to_clone.append([i, new_id])
    for i in to_clone:
        if not clone_item(i[0], i[1], new_group, save): return False
    return True


def destroy_item(item):
    try:
        if isinstance(item, str):
            i = get_item(item)
            if not i: return False
        else:
            i = item
        del items_by_id[i.item_id]
        del items_by_full_id[i.full_id]
        del items_by_group[i.group][i.item_id]
        if i.item_type == 'unit':
            del units_by_id[i.item_id]
            del units_by_full_id[i.full_id]
            del units_by_group[i.group][i.item_id]
        if i.item_type == 'sensor':
            del sensors_by_id[i.item_id]
            del sensors_by_full_id[i.full_id]
            del sensors_by_group[i.group][i.item_id]
        if i.item_type == 'mu':
            del mu_by_id[i.item_id]
            del mu_by_full_id[i.full_id]
            del mu_by_group[i.group][i.item_id]
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
    except:
        eva.core.log_traceback()


def load_mu(start = False):
    logging.info('Loading multi updates')
    try:
        fnames = eva.core.format_cfg_fname(eva.core.product_code + \
                '_mu.d/*.json', runtime = True)
        for ucfg in glob.glob(fnames):
            mu_id = os.path.splitext(os.path.basename(ucfg))[0]
            u = eva.uc.ucmu.UCMultiUpdate(mu_id)
            u.get_item_func = get_item
            if u.load():
                append_item(u, start = False)
                if start: u.start_processors()
        return True
    except:
        logging.error('multi updates load error')
        eva.core.log_traceback()
        return False


def save_units():
    logging.info('Saving units')
    for i, u in units_by_id.items():
        u.save()


def save_sensors():
    logging.info('Saving sensors')
    for i, u in sensors_by_id.items():
        u.save()


def save_mu():
    logging.info('Saving multi updates')
    for i, u in mu_by_id.items():
        u.save()


def notify_all():
    notify_all_units()
    notify_all_sensors()


def notify_all_units():
    for i, u in units_by_id.items():
        u.notify()


def notify_all_sensors():
    for i, u in sensors_by_id.items():
        u.notify()


def serialize():
    d = {}
    d['units'] = serialize_units(full = True)
    d['units_config'] = serialize_units(config = True)
    d['sensors'] = serialize_sensors(full = True)
    d['sensors_config'] = serialize_sensors(config = True)
    d['mu_config'] = serialize_mu(config = True)
    return d


def serialize_units(full = False, config = False):
    d = {}
    for i, u in units_by_id.items():
        d[i] = u.serialize(full, config)
    return d


def serialize_sensors(full = False, config = False):
    d = {}
    for i, u in sensors_by_id.items():
        d[i] = u.serialize(full, config)
    return d


def serialize_mu(full = False, config = False):
    d = {}
    for i, u in mu_by_id.items():
        d[i] = u.serialize(full, config)
    return d


def serialize_actions():
    return Q.serialize()


def start():
    global Q
    Q = eva.uc.ucqueue.UC_Queue('uc_queue')
    Q.start()
    logging.info('UC action queue started')
    for i, v in items_by_id.items():
        v.start_processors()


def stop():
    # save modified items on exit, for db_update = 2 save() is called by core
    if eva.core.db_update == 1: save()
    for i, v in items_by_id.copy().items():
        v.stop_processors()
    if Q: Q.stop()


def exec_mqtt_unit_action(unit, msg):
    status = None
    value = None
    priority = None
    try:
        cmd = msg.split(' ')
        status = int(cmd[0])
        if len(cmd) > 1:
            value = cmd[1]
        if len(cmd) > 2:
            priority = int(cmd[2])
        if value == 'None': value = None
        logging.debug('mqtt cmd msg unit = %s' % unit.full_id)
        logging.debug('mqtt cmd msg status = %s' % status)
        logging.debug('mqtt cmd msg value = "%s"' % value)
        logging.debug('mqtt cmd msg priority = "%s"' % priority)
        exec_unit_action(unit = unit, nstatus = status,
                nvalue = value, priority = priority)
        return
    except:
        logging.error('%s got bad mqtt action msg' % unit.full_id)
        eva.core.log_traceback()


def exec_unit_action(unit, nstatus, nvalue = None, priority = None,
        q_timeout = None, wait = 0, action_uuid = None):
    if isinstance(unit, str):
        u = get_unit(unit)
    else:
        u = unit
    if not u: return None
    if q_timeout: qt = q_timeout
    else: qt = eva.core.timeout
    a = u.create_action(nstatus, nvalue, priority, action_uuid)
    Q.put_task(a)
    if not eva.core.wait_for(a.is_processed, q_timeout):
        if a.set_dead():
            return a
    if wait: eva.core.wait_for(a.is_finished, wait)
    return a


def dump(item_id = None):
    if item_id: return items_by_id[item_id]
    else: return {
            'uc_items': items_by_full_id,
            'uc_actions': Q.actions_by_item_full_id
            }


def init():
    eva.core.append_save_func(save)
    eva.core.append_dump_func('uc', dump)
    eva.core.append_stop_func(stop)

