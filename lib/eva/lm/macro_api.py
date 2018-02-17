__author__ = "Altertech Group, http://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2017 Altertech Group"
__license__ = "See http://www.eva-ics.com/"
__version__ = "3.0.1"

import logging
import sys
import os
import eva.sysapi
import eva.mailer
import eva.lm.controller
import time
import requests
import threading

_shared = {}
_shared_lock = threading.Lock()


def shared(name):
    if not _shared_lock.acquire(timeout = eva.core.timeout):
        logging.critical('macro_api shared locking broken')
        return None
    value = _shared[name] if name in _shared else None
    _shared_lock.release()
    return value


def set_shared(name, value = None):
    if not _shared_lock.acquire(timeout = eva.core.timeout):
        logging.critical('macro_api set_shared locking broken')
        return None
    if value is None:
        if name in _shared: del _shared[name]
    else:
        _shared[name] = value
    _shared_lock.release()


class MacroAPI(object):

    def __init__(self, pass_errors = False):
        self.pass_errors = pass_errors
        self.on = 1
        self.off = 0
        self.yes = True
        self.no = False


    def get_globals(self):
        return {
                'on': self.on,
                'off': self.off,
                'yes': self.yes,
                'no': self.no,

                'shared': shared,
                'set_shared': set_shared,

                'sleep': self.sleep,
                'print': self.info,

                'mail': eva.mailer.send,
                'get': requests.get,
                'post': requests.post,

                'debug': self.debug,
                'info': self.info,
                'warning': self.warning,
                'error': self.error,
                'critical': self.critical,

                'exit': self.exit,
                'lock': self.lock,
                'unlock': self.unlock,

                'lvar_status': self.lvar_status,
                'lvar_value': self.lvar_value,
                'is_expired': self.is_expired,

                'unit_status': self.unit_status,
                'unit_value': self.unit_value,
                'unit_nstatus': self.unit_nstatus,
                'unit_nvalue': self.unit_nvalue,
                'is_busy': self.is_busy,

                'sensor_status': self.sensor_status,
                'sensor_value': self.sensor_value,

                'set': self.set,
                'value': self.lvar_value,
                'reset': self.reset,

                'expires': self.expires,
                'action': self.action,
                'start': self.action_start,
                'stop': self.action_stop,
                'terminate': self.terminate,
                'q_clean': self.q_clean,
                'kill': self.kill,

                'run': self.run,

                'cmd': self.cmd,
                
                'system': os.system
                }

    def debug(self, msg):
        logging.debug(msg)


    def info(self, msg):
        logging.info(msg)

    def warning(self, msg):
        logging.warning(msg)

    def error(self, msg):
        logging.error(msg)

    def critical(self, msg):
        logging.critical(msg)

    def exit(self, code = 0):
        sys.exit(code)

    def sleep(self, t):
        time.sleep(t)

    def lock(self, lock_id, timeout = None, expires = None):
        result = eva.sysapi.api.lock(
                l = lock_id,
                timeout = timeout,
                expires = expires
                )
        if not result and not self.pass_errors:
            raise Exception('Error obtaining lock')
        return result


    def unlock(self, lock_id):
        result = eva.sysapi.api.unlock(l = lock_id)
        return True


    def lvar_status(self, lvar_id):
        lvar = eva.lm.controller.get_lvar(lvar_id)
        if not lvar:
            if not self.pass_errors:
                raise Exception('lvar unknown: ' + lvar_id)
            return None
        return lvar.status


    def lvar_value(self, lvar_id):
        lvar = eva.lm.controller.get_lvar(lvar_id)
        if not lvar:
            if not self.pass_errors:
                raise Exception('lvar unknown: ' + lvar_id)
            return None
        if lvar.value == 'null': return ''
        try: v = float(lvar.value)
        except: v = lvar.value
        return v


    def is_expired(self, lvar_id):
        return self.lvar_status(lvar_id) == -1 and \
                self.lvar_value(lvar_id) == ''


    def unit_status(self, unit_id):
        unit = eva.lm.controller.uc_pool.get_unit(unit_id)
        if not unit:
            if not self.pass_errors:
                raise Exception('unit unknown: ' + unit_id)
            return None
        return unit.status


    def unit_nstatus(self, unit_id):
        unit = eva.lm.controller.uc_pool.get_unit(unit_id)
        if not unit:
            if not self.pass_errors:
                raise Exception('unit unknown: ' + unit_id)
            return None
        return unit.nstatus


    def unit_value(self, unit_id):
        unit = eva.lm.controller.uc_pool.get_unit(unit_id)
        if not unit:
            if not self.pass_errors:
                raise Exception('unit unknown: ' + unit_id)
            return None
        if unit.value == 'null': return ''
        try: v = float(unit.value)
        except: v = unit.value
        return v


    def unit_nvalue(self, unit_id):
        unit = eva.lm.controller.uc_pool.get_unit(unit_id)
        if not unit:
            if not self.pass_errors:
                raise Exception('unit unknown: ' + unit_id)
            return None
        if unit.nvalue == 'null': return ''
        try: v = float(unit.nvalue)
        except: v = unit.nvalue
        return v


    def is_busy(self, unit_id):
        unit = eva.lm.controller.uc_pool.get_unit(unit_id)
        if not unit:
            if not self.pass_errors:
                raise Exception('unit unknown: ' + unit_id)
            return None
        return unit.status != unit.nstatus or unit.value != unit.nvalue


    def sensor_status(self, sensor_id):
        sensor = eva.lm.controller.uc_pool.get_sensor(sensor_id)
        if not sensor:
            if not self.pass_errors:
                raise Exception('sensor unknown: ' + sensor_id)
            return None
        return sensor.status


    def sensor_value(self, sensor_id):
        sensor = eva.lm.controller.uc_pool.get_sensor(sensor_id)
        if not sensor:
            if not self.pass_errors:
                raise Exception('sensor unknown: ' + sensor_id)
            return None
        if sensor.value == 'null': return ''
        try: v = float(sensor.value)
        except: v = sensor.value
        return v


    def set(self, lvar_id, value = None):
        lvar = eva.lm.controller.get_lvar(lvar_id)
        if not lvar:
            if not self.pass_errors:
                raise Exception('lvar unknown: ' + lvar_id)
            return False
        if value is None: v = 'null'
        else: v = value
        result = lvar.update_set_state(value = v)
        if not result:
            if not self.pass_errors:
                raise Exception('lvar set error: %s, value = "%s"' % \
                        (lvar_id, v))
            return False
        return True


    def reset(self, lvar_id):
        return self.set(lvar_id = lvar_id, value = 1)


    def expires(self, lvar_id, expires = 0):
        lvar = eva.lm.controller.get_lvar(lvar_id)
        if not lvar:
            if not self.pass_errors:
                raise Exception('lvar unknown: ' + lvar_id)
            return False
        try:
            result = lvar.set_prop('expires', expires, save = False)
            if not self.pass_errors and not result:
                raise Exception('lvar expire set error')
            return result
        except:
            if self.pass_errors: return False
            raise Exception('lvar expire set error')
        return True


    def action(self, unit_id, status, value = None, wait = 0,
            uuid = None, priority = None):
        unit = eva.lm.controller.uc_pool.get_unit(unit_id)
        if not unit:
            if not self.pass_errors:
                raise Exception('unit unknown: ' + unit_id)
            return None
        return eva.lm.controller.uc_pool.action(
                unit_id = unit_id,
                status = status,
                value = value,
                wait = wait,
                uuid = uuid,
                priority = priority
                )


    def action_start(self, unit_id, value = None, wait = 0,
            uuid = None, priority = None):
        return self.action(unit_id = unit_id, status = 1, value = value,
                wait = wait, uuid = uuid, priority = priority)


    def action_stop(self, unit_id, value = None, wait = 0,
            uuid = None, priority = None):
        return self.action(unit_id = unit_id, status = 0, value = value,
                wait = wait, uuid = uuid, priority = priority)


    def terminate(self, unit_id):
        unit = eva.lm.controller.uc_pool.get_unit(unit_id)
        if not unit:
            if not self.pass_errors:
                raise Exception('unit unknown: ' + unit_id)
            return None
        result = eva.lm.controller.uc_pool.terminate(
                unit_id = unit_id
                )
        if 'result' not in result or result['result'] != 'OK':
            if not self.pass_errors:
                raise Exception('terminate error, unit ' + unit_id)
            return False
        return True


    def q_clean(self, unit_id):
        unit = eva.lm.controller.uc_pool.get_unit(unit_id)
        if not unit:
            if not self.pass_errors:
                raise Exception('unit unknown: ' + unit_id)
            return None
        result = eva.lm.controller.uc_pool.q_clean(
                unit_id = unit_id
                )
        if 'result' not in result or result['result'] != 'OK':
            if not self.pass_errors:
                raise Exception('q_clean error, unit ' + unit_id)
            return False
        return True


    def kill(self, unit_id):
        unit = eva.lm.controller.uc_pool.get_unit(unit_id)
        if not unit:
            if not self.pass_errors:
                raise Exception('unit unknown: ' + unit_id)
            return None
        result = eva.lm.controller.uc_pool.kill(
                unit_id = unit_id
                )
        if 'result' not in result or result['result'] != 'OK':
            if not self.pass_errors:
                raise Exception('kill error, unit ' + unit_id)
            return False
        return True


    def run(self, macro, argv = None, wait = 0, uuid = None, priority = None):
        _argv = []
        if isinstance(argv, str):
            _argv = argv.split(' ')
        elif isinstance(argv, list):
            _argv = argv
        return eva.lm.controller.exec_macro(macro = macro, argv = _argv,
                priority = priority, action_uuid = uuid, wait = wait)


    def cmd(self, controller_id, command, args = None,
            wait = None, timeout = None):
        return eva.lm.controller.uc_pool.cmd(
                controller_id = controller_id,
                command = command,
                args = args,
                wait = wait,
                timeout = timeout
                )
