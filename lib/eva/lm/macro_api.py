__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.0"

import logging
import sys
import os
import glob
import eva.core
import eva.sysapi
import eva.apikey
import eva.mailer
import eva.lm.controller
import time
import requests
import threading
import shlex

from eva.tools import is_oid
from eva.tools import oid_to_id
from eva.tools import parse_oid
from eva.tools import oid_type

from eva.exceptions import FunctionFailed
from eva.exceptions import ResourceAlreadyExists
from eva.exceptions import ResourceNotFound
from eva.exceptions import ResourceBusy
from eva.exceptions import AccessDenied
from eva.exceptions import InvalidParameter

from eva.exceptions import ecall

from eva.tools import dict_from_str

from functools import wraps

_shared = {}
_shared_lock = threading.RLock()

mbi_code = ''


def shared(name, default=None):
    if not _shared_lock.acquire(timeout=eva.core.timeout):
        logging.critical('macro_api shared locking broken')
        eva.core.critical()
        return None
    try:
        value = _shared.get(name, default)
        return value
    finally:
        _shared_lock.release()


def set_shared(name, value=None):
    if not _shared_lock.acquire(timeout=eva.core.timeout):
        logging.critical('macro_api set_shared locking broken')
        eva.core.critical()
        return None
    try:
        if value is None:
            if name in _shared: del _shared[name]
        else:
            _shared[name] = value
        return True
    finally:
        _shared_lock.release()


class MacroAPI(object):

    def __init__(self, pass_errors=False, send_critical=False):
        self.pass_errors = pass_errors
        self.send_critical = send_critical
        self.on = 1
        self.off = 0
        self.yes = True
        self.no = False

    def macro_function(self, f):

        @wraps(f)
        def do(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except:
                if self.pass_errors:
                    return None
                else:
                    raise

        return do

    def get_globals(self):
        return {
            'FunctionFailed': FunctionFailed,
            'ResourceAlreadyExists': ResourceAlreadyExists,
            'ResourceNotFound': ResourceNotFound,
            'ResourceAlreadyExists': ResourceBusy,
            'AccessDenied': AccessDenied,
            'InvalidParameter': InvalidParameter,
            'on': self.on,
            'off': self.off,
            'yes': self.yes,
            'no': self.no,
            'shared': self.macro_function(shared),
            'set_shared': self.macro_function(set_shared),
            'print': self.macro_function(self.info),
            'mail': self.macro_function(eva.mailer.send),
            'debug': self.macro_function(self.debug),
            'info': self.macro_function(self.info),
            'warning': self.macro_function(self.warning),
            'error': self.macro_function(self.error),
            'critical': self.macro_function(self.critical),
            'exit': self.macro_function(self.exit),
            'sleep': self.macro_function(time.sleep),
            'lock': self.macro_function(self.lock),
            'unlock': self.macro_function(self.unlock),
            'lvar_status': self.macro_function(self.lvar_status),
            'lvar_value': self.macro_function(self.lvar_value),
            'is_expired': self.macro_function(self.is_expired),
            'unit_status': self.macro_function(self.unit_status),
            'unit_value': self.macro_function(self.unit_value),
            'unit_nstatus': self.macro_function(self.unit_nstatus),
            'unit_nvalue': self.macro_function(self.unit_nvalue),
            'nstatus': self.macro_function(self.unit_nstatus),
            'nvalue': self.macro_function(self.unit_nvalue),
            'is_busy': self.macro_function(self.is_busy),
            'sensor_status': self.macro_function(self.sensor_status),
            'sensor_value': self.macro_function(self.sensor_value),
            'set': self.macro_function(self.set),
            'status': self.macro_function(self.status),
            'value': self.macro_function(self.value),
            'reset': self.macro_function(self.reset),
            'clear': self.macro_function(self.clear),
            'toggle': self.macro_function(self.toggle),
            'expires': self.macro_function(self.expires),
            'action': self.macro_function(self.action),
            'action_toggle': self.macro_function(self.action_toggle),
            'result': self.macro_function(self.result),
            'start': self.macro_function(self.action_start),
            'stop': self.macro_function(self.action_stop),
            'terminate': self.macro_function(self.terminate),
            'q_clean': self.macro_function(self.q_clean),
            'kill': self.macro_function(self.kill),
            'run': self.macro_function(self.run),
            'cmd': self.macro_function(self.cmd),
            'history': self.macro_function(self.history),
            'system': self.macro_function(os.system),
            'time': self.macro_function(time.time),
            'ls': self.macro_function(self.ls),
            'open_oldest': self.macro_function(self.open_oldest),
            'open_newest': self.macro_function(self.open_newest),
            'deploy_device': self.macro_function(self.deploy_device),
            'update_device': self.macro_function(self.update_device),
            'undeploy_device': self.macro_function(self.undeploy_device),
            'set_rule_prop': self.macro_function(self.set_rule_prop),
            'start_cycle': self.macro_function(self.start_cycle),
            'stop_cycle': self.macro_function(self.stop_cycle),
            'reset_cycle_stats': self.macro_function(self.reset_cycle_stats),
            'list_cycle_props': self.macro_function(self.list_cycle_props),
            'set_cycle_prop': self.macro_function(self.set_cycle_prop),
            'get_cycle_info': self.macro_function(self.get_cycle_info),
            'is_cycle_running': self.macro_function(self.is_cycle_running)
        }

    def history(self,
                lvar_id,
                t_start=None,
                t_end=None,
                limit=None,
                prop=None,
                time_format=None,
                fill=None,
                fmt=None,
                db=None):
        return eva.lm.lmapi.api.state_history(
            k=eva.apikey.masterkey,
            a=db,
            i=oid_to_id(lvar_id, 'lvar'),
            s=t_start,
            e=t_end,
            l=limit,
            x=prop,
            t=time_format,
            w=fill,
            g=fmt)

    def debug(self, msg):
        logging.debug(msg)

    def info(self, msg):
        logging.info(msg)

    def warning(self, msg):
        logging.warning(msg)

    def error(self, msg):
        logging.error(msg)

    def critical(self, msg, send_event=False):
        logging.critical(msg)
        if send_event and self.send_critical:
            t = threading.Thread(target=eva.core.critical, args=(True, True))
            t.start()

    def exit(self, code=0):
        sys.exit(code)

    def lock(self, lock_id, timeout=None, expires=None):
        return eva.sysapi.api.lock(
            k=eva.apikey.masterkey, l=lock_id, t=timeout, e=expires)

    def unlock(self, lock_id):
        return eva.sysapi.api.unlock(k=eva.apikey.masterkey, l=lock_id)

    def status(self, item_id):
        if is_oid(item_id):
            tp, i = parse_oid(item_id)
        else:
            tp = 'lvar'
            i = item_id
        if tp == 'unit':
            return self.unit_status(i)
        if tp == 'sensor':
            return self.sensor_status(i)
        if tp == 'lvar':
            return self.lvar_status(i)
        raise ResourceNotFound

    def lvar_status(self, lvar_id):
        lvar = eva.lm.controller.get_lvar(lvar_id)
        if not lvar:
            raise ResourceNotFound
        return lvar.status

    def value(self, item_id, default=''):
        if is_oid(item_id):
            tp, i = parse_oid(item_id)
        else:
            tp = 'lvar'
            i = item_id
        if tp == 'unit':
            return self.unit_value(i, default)
        if tp == 'sensor':
            return self.sensor_value(i, default)
        if tp == 'lvar':
            return self.lvar_value(i, default)
        raise ResourceNotFound

    def lvar_value(self, lvar_id, default=''):
        lvar = eva.lm.controller.get_lvar(lvar_id)
        if not lvar:
            raise ResourceNotFound
        if lvar.value == 'null': return default
        try:
            v = float(lvar.value)
        except:
            v = lvar.value
        return v

    def is_expired(self, lvar_id):
        return self.lvar_status(lvar_id) == -1 and \
                self.lvar_value(lvar_id) == ''

    def unit_status(self, unit_id):
        unit = eva.lm.controller.uc_pool.get_unit(oid_to_id(unit_id, 'unit'))
        if not unit:
            raise ResourceNotFound
        return unit.status

    def unit_nstatus(self, unit_id):
        unit = eva.lm.controller.uc_pool.get_unit(oid_to_id(unit_id, 'unit'))
        if not unit:
            raise ResourceNotFound
        return unit.nstatus

    def unit_value(self, unit_id, default=''):
        unit = eva.lm.controller.uc_pool.get_unit(oid_to_id(unit_id, 'unit'))
        if not unit:
            raise ResourceNotFound
        if unit.value == 'null': return default
        try:
            v = float(unit.value)
        except:
            v = unit.value
        return v

    def unit_nvalue(self, unit_id, default=''):
        unit = eva.lm.controller.uc_pool.get_unit(oid_to_id(unit_id, 'unit'))
        if not unit:
            raise ResourceNotFound
        if unit.nvalue == 'null': return default
        try:
            v = float(unit.nvalue)
        except:
            v = unit.nvalue
        return v

    def is_busy(self, unit_id):
        unit = eva.lm.controller.uc_pool.get_unit(oid_to_id(unit_id, 'unit'))
        if not unit:
            raise ResourceNotFound
        return unit.status != unit.nstatus or unit.value != unit.nvalue

    def sensor_status(self, sensor_id):
        sensor = eva.lm.controller.uc_pool.get_sensor(
            oid_to_id(sensor_id, 'sensor'))
        if not sensor:
            raise ResourceNotFound
        return sensor.status

    def sensor_value(self, sensor_id, default=''):
        sensor = eva.lm.controller.uc_pool.get_sensor(
            oid_to_id(sensor_id, 'sensor'))
        if not sensor:
            raise ResourceNotFound
        if sensor.value == 'null': return default
        try:
            v = float(sensor.value)
        except:
            v = sensor.value
        return v

    def set(self, lvar_id, value=None):
        lvar = eva.lm.controller.get_lvar(lvar_id)
        if not lvar:
            raise ResourceNotFound
        if value is None: v = 'null'
        else: v = value
        result = lvar.update_set_state(value=v)
        if not result:
            raise FunctionFailed('lvar set error: %s, value = "%s"' % \
                    (lvar_id, v))
        return True

    def reset(self, lvar_id):
        lvar = eva.lm.controller.get_lvar(lvar_id)
        if not lvar:
            raise ResourceNotFound
        lvar.update_set_state(status=1)
        return self.set(lvar_id=lvar_id, value=1)

    def clear(self, lvar_id):
        lvar = eva.lm.controller.get_lvar(lvar_id)
        if not lvar:
            raise ResourceNotFound
        if lvar.expires > 0:
            lvar.update_set_state(status=0)
            if lvar.status != 0:
                raise FunctionFailed('lvar clear error: %s' % lvar_id)
            return True
        else:
            return self.set(lvar_id=lvar_id, value=0)

    def toggle(self, item_id, wait=None, uuid=None, priority=None):
        if is_oid(item_id) and oid_type(item_id) == 'unit':
            return self.action_toggle(
                unit_id=item_id, wait=wait, uuid=uuid, priority=priority)
        v = self.lvar_value(item_id)
        if v is None:
            raise FunctionFailed('lvar value is null')
        if v:
            return self.clear(item_id)
        else:
            return self.reset(item_id)

    def expires(self, lvar_id, etime=0):
        lvar = eva.lm.controller.get_lvar(lvar_id)
        if not lvar:
            raise ResourceNotFound
        try:
            result = lvar.set_prop('expires', etime, save=False)
            if not result:
                raise FunctionFailed('lvar expire set error')
            return result
        except:
            raise FunctionFailed('lvar expire set error')
        return True

    def action(self,
               unit_id,
               status,
               value=None,
               wait=0,
               uuid=None,
               priority=None):
        unit = eva.lm.controller.uc_pool.get_unit(oid_to_id(unit_id, 'unit'))
        if not unit:
            raise ResourceNotFound
        return ecall(
            eva.lm.controller.uc_pool.action(
                unit_id=oid_to_id(unit_id, 'unit'),
                status=status,
                value=value,
                wait=wait,
                uuid=uuid,
                priority=priority))

    def action_toggle(self, unit_id, wait=0, uuid=None, priority=None):
        unit = eva.lm.controller.uc_pool.get_unit(oid_to_id(unit_id, 'unit'))
        if not unit:
            raise ResourceNotFound
        return ecall(
            eva.lm.controller.uc_pool.action_toggle(
                unit_id=oid_to_id(unit_id),
                wait=wait,
                uuid=uuid,
                priority=priority))

    def result(self, unit_id=None, uuid=None, group=None, status=None):
        if unit_id:
            unit = eva.lm.controller.uc_pool.get_unit(
                oid_to_id(unit_id, 'unit'))
            if not unit:
                raise ResourceNotFound
        return ecall(
            eva.lm.controller.uc_pool.result(
                oid_to_id(unit_id, 'unit'), uuid, group, status))

    def action_start(self,
                     unit_id,
                     value=None,
                     wait=0,
                     uuid=None,
                     priority=None):
        return self.action(
            unit_id=oid_to_id(unit_id, 'unit'),
            status=1,
            value=value,
            wait=wait,
            uuid=uuid,
            priority=priority)

    def action_stop(self, unit_id, value=None, wait=0, uuid=None,
                    priority=None):
        return self.action(
            unit_id=oid_to_id(unit_id, 'unit'),
            status=0,
            value=value,
            wait=wait,
            uuid=uuid,
            priority=priority)

    def terminate(self, unit_id=None, uuid=None):
        if unit_id:
            unit = eva.lm.controller.uc_pool.get_unit(
                oid_to_id(unit_id, 'unit'))
            if not unit:
                raise ResourceNotFound
        return ecall(
            eva.lm.controller.uc_pool.terminate(
                oid_to_id(unit_id, 'unit'), uuid))

    def q_clean(self, unit_id):
        unit = eva.lm.controller.uc_pool.get_unit(oid_to_id(unit_id, 'unit'))
        if not unit:
            raise ResourceNotFound
        return ecall(
            eva.lm.controller.uc_pool.q_clean(
                unit_id=oid_to_id(unit_id, 'unit')))

    def kill(self, unit_id):
        unit = eva.lm.controller.uc_pool.get_unit(oid_to_id(unit_id, 'unit'))
        if not unit:
            raise ResourceNotFound
        return ecall(
            eva.lm.controller.uc_pool.kill(unit_id=oid_to_id(unit_id, 'unit')))

    def run(self,
            macro,
            argv=None,
            kwargs=None,
            wait=0,
            uuid=None,
            priority=None):
        _argv = []
        if isinstance(argv, str):
            try:
                _argv = shlex.split(argv)
            except:
                _argv = argv.split(' ')
        elif isinstance(argv, float) or isinstance(argv, int):
            _argv = [argv]
        elif isinstance(argv, list):
            _argv = argv
        if isinstance(kwargs, str):
            try:
                kw = dict_from_str(kwargs)
            except:
                kw = {}
        elif isinstance(kwargs, dict):
            kw = kwargs
        else:
            kw = {}
        a = eva.lm.controller.exec_macro(
            macro=oid_to_id(macro, 'lmacro'),
            argv=_argv,
            kwargs=kw,
            priority=priority,
            action_uuid=uuid,
            wait=wait)
        if not a:
            raise ResourceNotFound
        elif a.is_status_dead():
            raise FunctionFailed('queue error')
        else:
            return a.serialize()

    def cmd(self, controller_id, command, args=None, wait=None, timeout=None):
        return ecall(
            eva.lm.controller.uc_pool.cmd(
                controller_id=controller_id,
                command=command,
                args=args,
                wait=wait,
                timeout=timeout))

    def ls(self, mask):
        fls = [x for x in glob.glob(mask) if os.path.isfile(x)]
        l = []
        for x in fls:
            l.append({
                'name': os.path.basename(x),
                'size': os.path.getsize(x),
                'time': {
                    'c': os.path.getctime(x),
                    'm': os.path.getmtime(x)
                }
            })
        return l

    def open_oldest(self, mask, mode='r'):
        try:
            fls = [x for x in glob.glob(mask) if os.path.isfile(x)]
            if not fls: return None
            return open(min(fls, key=os.path.getmtime), mode)
        except:
            raise FunctionFailed('file open error')

    def open_newest(self, mask, mode='r', alt=True):
        try:
            fls = [x for x in glob.glob(mask) if os.path.isfile(x)]
            if not fls: return None
            _f = max(fls, key=os.path.getmtime)
            fls.remove(_f)
            if fls: _f_alt = max(fls, key=os.path.getmtime)
            else: _f_alt = None
            try:
                o = open(_f, mode)
            except:
                if not alt or not _f_alt: raise
                o = open(_f_alt, mode)
            return o
        except:
            raise FunctionFailed('file open error')

    def deploy_device(self, controller_id, device_tpl, cfg=None, save=None):
        return ecall(
            eva.lm.controller.uc_pool.deploy_device(
                controller_id=controller_id,
                device_tpl=device_tpl,
                cfg=cfg,
                save=save))

    def update_device(self, controller_id, device_tpl, cfg=None, save=None):
        return ecall(
            eva.lm.controller.uc_pool.update_device(
                controller_id=controller_id,
                device_tpl=device_tpl,
                cfg=cfg,
                save=save))

    def undeploy_device(self, controller_id, device_tpl, cfg=None):
        return ecall(
            eva.lm.controller.uc_pool.undeploy_device(
                controller_id=controller_id, device_tpl=device_tpl, cfg=cfg))

    def set_rule_prop(self, rule_id, prop, value=None, save=False):
        result = eva.lm.lmapi.api.set_rule_prop(
            k=eva.apikey.masterkey, i=rule_id, p=prop, v=value, save=save)
        return result

    def start_cycle(self, cycle_id):
        cycle = eva.lm.controller.get_cycle(cycle_id)
        if not cycle:
            raise ResourceNotFound
        return cycle.start()

    def stop_cycle(self, cycle_id):
        cycle = eva.lm.controller.get_cycle(cycle_id)
        if not cycle:
            raise ResourceNotFound
        return cycle.stop()

    def reset_cycle_stats(self, cycle_id):
        cycle = eva.lm.controller.get_cycle(cycle_id)
        if not cycle:
            raise ResourceNotFound
        return cycle.reset_stats()

    def list_cycle_props(self, cycle_id):
        cycle = eva.lm.controller.get_cycle(cycle_id)
        if not cycle:
            raise ResourceNotFound
        return cycle.serialize(props=True)

    def set_cycle_prop(self, cycle_id, prop=None, value=None, save=False):
        cycle = eva.lm.controller.get_cycle(cycle_id)
        if not cycle:
            raise ResourceNotFound
        return cycle.set_prop(prop, value, save)

    def get_cycle_info(self, cycle_id):
        cycle = eva.lm.controller.get_cycle(cycle_id)
        if not cycle:
            raise ResourceNotFound
        return cycle.serialize(info=True)

    def is_cycle_running(self, cycle_id):
        cycle = eva.lm.controller.get_cycle(cycle_id)
        if not cycle:
            raise ResourceNotFound
        return cycle.is_running()


def init():
    global mbi_code
    mbi_code = open(eva.core.dir_lib +
                    '/eva/lm/macro_builtins.py').read() + '\n\n'


@eva.core.shutdown
def shutdown():
    eva.lm.controller.exec_macro(
        'system/shutdown', priority=1, wait=eva.core.timeout)
