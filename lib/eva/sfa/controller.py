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

import eva.core
import eva.api
import eva.apikey
import eva.item
import eva.client.remote_controller
import eva.client.coreapiclient

from eva.tools import is_oid
from eva.tools import oid_to_id
from eva.tools import parse_oid

from eva.exceptions import FunctionFailed
from eva.exceptions import ResourceNotFound
from eva.exceptions import ResourceAlreadyExists

from eva.exceptions import InvalidParameter

from types import SimpleNamespace

remote_ucs = {}
remote_lms = {}

configs_to_remove = set()

uc_pool = eva.client.remote_controller.RemoteUCPool()
lm_pool = eva.client.remote_controller.RemoteLMPool()

config = SimpleNamespace(cloud_manager=False)

controller_lock = threading.RLock()


def get_item(i):
    if is_oid(i):
        _tp, _i = parse_oid(i)
    else:
        return None
    if _tp == 'unit':
        gi = eva.sfa.controller.uc_pool.units
    elif _tp == 'sensor':
        gi = eva.sfa.controller.uc_pool.sensors
    elif _tp == 'lvar':
        gi = eva.sfa.controller.lm_pool.lvars
    else:
        return None
    if not _i in gi: return None
    return gi[_i]


def get_controller(controller_id):
    controller_lock.acquire()
    try:
        if not controller_id:
            raise InvalidParameter('controller id not specified')
        if is_oid(controller_id):
            tp, i = parse_oid(controller_id)
        else:
            tp, i = None, controller_id
        if i.find('/') > -1:
            i = i.split('/')
            if len(i) > 2:
                raise InvalidParameter('controller type unknown')
            if i[0] == 'uc' and i[1] in remote_ucs and (tp is None or
                                                        tp == 'remote_uc'):
                return remote_ucs[i[1]]
            if i[0] == 'lm' and i[1] in remote_lms and (tp is None or
                                                        tp == 'remote_lm'):
                return remote_lms[i[1]]
        else:
            raise ResourceNotFound
    finally:
        controller_lock.release()


def get_uc(controller_id):
    controller_lock.acquire()
    try:
        if not controller_id: return None
        if controller_id.find('/') > -1:
            return get_controller(controller_id)
        else:
            if controller_id in remote_ucs:
                return remote_ucs[controller_id]
    finally:
        controller_lock.release()


def get_lm(controller_id):
    controller_lock.acquire()
    try:
        if not controller_id: return None
        if controller_id.find('/') > -1:
            return get_controller(controller_id)
        else:
            if controller_id in remote_lms:
                return remote_lms[controller_id]
    finally:
        controller_lock.release()


@eva.core.save
def save():
    for i, v in remote_ucs.items():
        if v.config_changed:
            if not v.save():
                return False
        try:
            if i.static:
                configs_to_remove.remove(v.get_fname())
        except:
            pass
    for i, v in remote_lms.items():
        if v.config_changed:
            if not v.save():
                return False
        try:
            if i.static:
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


def load_remote_ucs():
    logging.info('Loading remote UCs')
    try:
        fnames = eva.core.format_cfg_fname(eva.core.product.code + \
                '_remote_uc.d/*.json', runtime = True)
        for ucfg in glob.glob(fnames):
            uc_id = os.path.splitext(os.path.basename(ucfg))[0]
            u = eva.client.remote_controller.RemoteUC(uc_id)
            if u.load():
                controller_lock.acquire()
                try:
                    remote_ucs[uc_id] = u
                finally:
                    controller_lock.release()
        return True
    except:
        logging.error('UCs load error')
        eva.core.log_traceback()
        return False


def load_remote_lms():
    logging.info('Loading remote LMs')
    try:
        fnames = eva.core.format_cfg_fname(eva.core.product.code + \
                '_remote_lm.d/*.json', runtime = True)
        for lmfg in glob.glob(fnames):
            lm_id = os.path.splitext(os.path.basename(lmfg))[0]
            u = eva.client.remote_controller.RemoteLM(lm_id)
            if u.load():
                controller_lock.acquire()
                try:
                    remote_lms[lm_id] = u
                finally:
                    controller_lock.release()
        return True
    except:
        logging.error('LMs load error')
        eva.core.log_traceback()
        return False


def handle_discovered_controller(notifier_id, controller_id, **kwargs):
    try:
        ct, c_id = controller_id.split('/')
        if ct not in ['uc', 'lm']:
            return True
        controller_lock.acquire()
        try:
            if (ct == 'uc' and c_id in uc_pool.controllers) or \
                    (ct == 'lm' and c_id in lm_pool.controllers):
                logging.debug('Controller ' +
                              '{} already exists, skipped (discovered from {})'.
                              format(controller_id, notifier_id))
                return True
        finally:
            controller_lock.release()
        key = eva.apikey.key_by_id('default')
        if not key:
            logging.debug('Controller {} discovered, (discovered from {}), '.
                          format(controller_id, notifier_id) +
                          'but no API key with ID=default')
            return False
        logging.info(
            'Controller {} discovered, appending (discovered from {})'.format(
                controller_id, notifier_id))
        if ct == 'uc':
            _append_controller = append_uc
        elif ct == 'lm':
            _append_controller = append_lm
        else:
            return False
        return _append_controller(
            'mqtt:{}:{}'.format(notifier_id, controller_id),
            key="$default",
            mqtt_update=notifier_id,
            static=False)
    except:
        logging.warning('Unable to process controller, discovered from ' +
                        notifier_id)
        eva.core.log_traceback()
        return False


def append_uc(uri,
              key=None,
              makey=None,
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
    u = eva.client.remote_controller.RemoteUC(
        None, api=api, mqtt_update=mqu, static=static)
    u._key = key
    u.set_prop('masterkey', makey)
    if not uc_pool.append(u): return False
    controller_lock.acquire()
    try:
        remote_ucs[u.item_id] = u
    finally:
        controller_lock.release()
    if save: u.save()
    logging.info('controller %s added to pool' % u.full_id)
    return u


def remove_uc(controller_id):
    if controller_id not in remote_ucs:
        raise ResourceNotFound
    controller_lock.acquire()
    try:
        i = remote_ucs[controller_id]
        i.destroy()
        if eva.core.db_update == 1 and i.config_file_exists:
            try:
                os.unlink(i.get_fname())
            except:
                logging.error('Can not remove controller %s config' % \
                        controller_id)
                eva.core.log_traceback()
        elif i.config_file_exists:
            configs_to_remove.add(i.get_fname())
        del (remote_ucs[controller_id])
        logging.info('controller uc/%s removed' % controller_id)
        return True
    except Exception as e:
        eva.core.log_traceback()
        raise FunctionFailed(e)
    finally:
        controller_lock.release()


def append_lm(uri,
              key=None,
              makey=None,
              mqtt_update=None,
              ssl_verify=True,
              timeout=None,
              save=False,
              static=True):
    api = eva.client.coreapiclient.CoreAPIClient()
    api.set_product('lm')
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
            uport = ':8817'
    else:
        if uri.find(':') == -1 and uri.find('/') == -1:
            uport = ':8817'
    api.set_uri(uri + uport)
    mqu = mqtt_update
    if mqu is None: mqu = eva.core.mqtt_update_default
    u = eva.client.remote_controller.RemoteLM(
        None, api=api, mqtt_update=mqu, static=static)
    u._key = key
    u.set_prop('masterkey', makey)
    if not lm_pool.append(u): return False
    controller_lock.acquire()
    try:
        remote_lms[u.item_id] = u
    finally:
        controller_lock.release()
    if save: u.save()
    logging.info('controller %s added to pool' % u.full_id)
    return u


def remove_lm(controller_id):
    if controller_id not in remote_lms:
        raise ResourceNotFound
    controller_lock.acquire()
    try:
        i = remote_lms[controller_id]
        i.destroy()
        if eva.core.db_update == 1 and i.config_file_exists:
            try:
                os.unlink(i.get_fname())
            except:
                logging.error('Can not remove controller %s config' % \
                        controller_id)
                eva.core.log_traceback()
        elif i.config_file_exists:
            configs_to_remove.add(i.get_fname())
        del (remote_lms[controller_id])
        logging.info('controller lm/%s removed' % controller_id)
        return True
    except Exception as e:
        eva.core.log_traceback()
        raise FunctionFailed(e)
    finally:
        controller_lock.release()


def remove_controller(controller_id):
    c = get_controller(controller_id)
    if not c: raise ResourceNotFound
    if c.item_type == 'remote_uc':
        return remove_uc(c.item_id)
    elif c.item_type == 'remote_lm':
        return remove_lm(c.item_id)
    else:
        raise FunctionFailed('controller type unknown')


def serialize():
    d = {}
    return d


def start():
    uc_pool.start()
    for i, v in remote_ucs.items():
        t = threading.Thread(
            target=connect_remote_controller, args=(uc_pool, v))
        t.start()
    lm_pool.start()
    for i, v in remote_lms.items():
        t = threading.Thread(
            target=connect_remote_controller, args=(lm_pool, v))
        t.start()


def connect_remote_controller(pool, v):
    if pool.append(v):
        logging.info('%s added to the controller pool' % \
                v.item_id)
    else:
        logging.error('Failed to add %s to the controller pool' % \
                v.item_id)


@eva.core.stop
def stop():
    # save modified items on exit, for db_update = 2 save() is called by core
    if eva.core.db_update == 1: save()
    if uc_pool:
        uc_pool.stop()
    if lm_pool:
        lm_pool.stop()


@eva.core.dump
def dump():
    r_ucs = {}
    r_lms = {}
    for i, v in remote_ucs.copy().items():
        r_ucs[i] = v.serialize()
    for i, v in remote_lms.copy().items():
        r_lms[i] = v.serialize()
    else:
        return {
            'remote_ucs': r_ucs,
            'remote_lms': r_lms,
        }


def init():
    eva.core.enterprise_layout = None


def update_config(cfg):
    try:
        config.cloud_manager = (cfg.get('cloud', 'cloud_manager') == 'yes')
    except:
        pass
    logging.debug('cloud.cloud_manager = %s' % ('yes' \
                                if config.cloud_manager else 'no'))
    eva.client.remote_controller.cloud_manager = config.cloud_manager


eva.api.mqtt_discovery_handler = handle_discovered_controller
eva.api.remove_controller = remove_controller
