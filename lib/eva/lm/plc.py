__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.0"

import eva.core
import eva.item
import eva.lm.controller
import eva.lm.macro_api
import eva.lm.extapi
import threading
import time
import logging

from eva.tools import val_to_boolean


class PLC(eva.item.ActiveItem):

    def __init__(self):
        super().__init__(eva.core.system_name, 'plc')
        self.update_config({
            'group': 'lm',
            'action_enabled': True,
            'action_queue': 1,
            'action_allow_termination': False,
        })

    def _t_action_processor(self):
        logging.debug('%s action processor started' % self.full_id)
        while self.action_processor_active:
            try:
                self.current_action = None
                self.action_before_get_task()
                a = self.q_get_task()
                self.action_after_get_task(a)
                if not a or not a.item: continue
                if not self.queue_lock.acquire(timeout=eva.core.timeout):
                    logging.critical(
                        'ActiveItem::_t_action_processor locking broken')
                    eva.core.critical()
                    continue
                self.current_action = a
                if not self.action_enabled:
                    self.queue_lock.release()
                    logging.info(
                     '%s actions disabled, canceling action %s' % \
                     (self.full_id, a.uuid))
                    a.set_canceled()
                if not a.item.action_enabled:
                    self.queue_lock.release()
                    logging.info(
                     '%s actions disabled, canceling action %s' % \
                     (a.item.full_id, a.uuid))
                    a.set_canceled()
                else:
                    if not self.action_may_run(a):
                        self.queue_lock.release()
                        logging.info(
                                '%s ignoring action %s' % \
                                 (self.full_id, a.uuid))
                        a.set_ignored()
                    elif a.is_status_queued() and a.set_running():
                        t = threading.Thread(target = self._t_action,
                                name = 'macro_' + a.item.full_id + \
                                        '_' + a.uuid,
                                args = (a,))
                        t.start()
                    else:
                        self.queue_lock.release()
            except:
                logging.critical(
                        '%s action processor got an error, restarting' % \
                                (self.full_id))
                eva.core.log_traceback()
            if not self.queue_lock.acquire(timeout=eva.core.timeout):
                logging.critical(
                    'ActiveItem::_t_action_processor locking broken')
                eva.core.critical()
                continue
            self.current_action = None
            self.action_xc = None
            self.queue_lock.release()
        logging.debug('%s action processor stopped' % self.full_id)

    def _t_action(self, a):
        import eva.runner
        self.action_log_run(a)
        self.action_before_run(a)
        env_globals = {}
        env_globals.update(eva.lm.extapi.env)
        env_globals.update(a.item.api.get_globals())
        env_globals['_source'] = a.source
        env_globals['argv'] = a.argv.copy()
        env_globals['kwargs'] = a.kwargs.copy()
        env_globals['is_shutdown'] = a.is_shutdown_func
        env_globals['_polldelay'] = eva.core.polldelay
        env_globals['_timeout'] = eva.core.timeout
        for i, v in env_globals['kwargs'].items():
            env_globals[i] = v
        env_globals['_0'] = a.item.item_id
        env_globals['_00'] = a.item.full_id
        for i, v in eva.core.cvars.copy().items():
            try:
                value = v
                env_globals[i] = value
            except:
                env_globals[i] = v
        for i in range(1, 9):
            try:
                env_globals['_%u' % i] = a.argv[i - 1]
            except:
                env_globals['_%u' % i] = ''
        xc = eva.runner.PyThread(
            item=a.item,
            env_globals=env_globals,
            bcode=eva.lm.macro_api.mbi_code)
        self.queue_lock.release()
        xc.run()
        self.action_after_run(a, xc)
        if xc.exitcode < 0:
            a.set_terminated(exitcode=xc.exitcode, out=xc.out, err=xc.err)
            logging.error('macro %s action %s terminated' % \
                    (a.item.full_id, a.uuid))
        elif xc.exitcode == 0:
            a.set_completed(exitcode=xc.exitcode, out=xc.out, err=xc.err)
            logging.debug('macro %s action %s completed' % \
                    (a.item.full_id, a.uuid))
        else:
            a.set_failed(exitcode=xc.exitcode, out=xc.out, err=xc.err)
            logging.error('macro %s action %s failed, code: %u' % \
                    (a.item.full_id, a.uuid, xc.exitcode))
        self.action_after_finish(a, xc)


class MacroAction(eva.item.ItemAction):

    def __init__(self,
                 item,
                 argv=[],
                 kwargs={},
                 priority=None,
                 action_uuid=None,
                 source=None,
                 is_shutdown_func=None):
        self.argv = argv
        self.kwargs = kwargs
        self.source = source
        self.is_shutdown_func = is_shutdown_func if \
                is_shutdown_func else eva.core.is_shutdown_requested
        super().__init__(item=item, priority=priority, action_uuid=action_uuid)

    def serialize(self):
        d = super().serialize()
        d['argv'] = self.argv
        d['kwargs'] = self.kwargs
        return d


class Macro(eva.item.ActiveItem):

    def __init__(self, item_id):
        super().__init__(item_id, 'lmacro')
        self.respect_layout = False
        self._drivers_allowed = False
        self.api = eva.lm.macro_api.MacroAPI(
            pass_errors=False, send_critical=False)

    def update_config(self, data):
        if 'pass_errors' in data:
            self.api.pass_errors = data['pass_errors']
        if 'send_critical' in data:
            self.api.send_critical = data['send_critical']
        super().update_config(data)

    def set_prop(self, prop, val=None, save=False):
        if prop == 'pass_errors':
            v = val_to_boolean(val)
            if v is not None:
                if self.api.pass_errors != v:
                    self.api.pass_errors = v
                    self.log_set(prop, v)
                    self.set_modified(save)
                return True
            else:
                return False
        if prop == 'send_critical':
            v = val_to_boolean(val)
            if v is not None:
                if self.api.send_critical != v:
                    self.api.send_critical = v
                    self.log_set(prop, v)
                    self.set_modified(save)
                return True
            else:
                return False
        return super().set_prop(prop, val, save)

    def notify(self, retain=None, skip_subscribed_mqtt=False):
        pass

    def serialize(self,
                  full=False,
                  config=False,
                  info=False,
                  props=False,
                  notify=False):
        d = {}
        if full or config or props:
            d['pass_errors'] = self.api.pass_errors
            d['send_critical'] = self.api.send_critical
        d.update(super().serialize(
            full=full, config=config, info=info, props=props, notify=notify))
        if not notify:
            d['action_enabled'] = self.action_enabled
        else:
            if 'action_enabled' in d:
                del d['action_enabled']
        if 'action_queue' in d:
            del d['action_queue']
        if 'action_allow_termination' in d:
            del d['action_allow_termination']
        if 'action_timeout' in d:
            del d['action_timeout']
        if 'mqtt_control' in d:
            del d['mqtt_control']
        if 'term_kill_interval' in d:
            del d['term_kill_interval']
        return d


class Cycle(eva.item.Item):

    def __init__(self, item_id):
        super().__init__(item_id, 'lcycle')
        self.respect_layout = False
        self.macro = None
        self.on_error = None
        self.interval = 1
        self.ict = 100
        self.c = 0
        self.tc = 0
        self.autostart = False
        self.cycle_thread = None
        self.cycle_enabled = False
        self.cycle_status = 0
        self.iterations = 0
        self.stats_lock = threading.Lock()

    def update_config(self, data):
        if 'macro' in data:
            self.macro = eva.lm.controller.get_macro(data['macro'])
        if 'on_error' in data:
            self.on_error = eva.lm.controller.get_macro(data['on_error'])
        if 'interval' in data:
            self.interval = data['interval']
        if 'ict' in data:
            self.ict = data['ict']
        if 'autostart' in data:
            self.autostart = data['autostart']
        super().update_config(data)

    def set_prop(self, prop, val=None, save=False):
        if prop == 'macro':
            if self.cycle_enabled:
                return False
            if val is None:
                if self.macro is not None:
                    self.macro = val
                    self.log_set(prop, val)
                    self.set_modified(save)
                return True
            macro = eva.lm.controller.get_macro(val)
            if macro:
                if not self.macro or self.macro.oid != macro.oid:
                    self.macro = macro
                    self.log_set(prop, val)
                    self.set_modified(save)
                return True
            else:
                return False
        elif prop == 'on_error':
            if val is None:
                if self.on_error is not None:
                    self.on_error = val
                    self.log_set(prop, val)
                    self.set_modified(save)
                return True
            macro = eva.lm.controller.get_macro(val)
            if macro:
                if not self.on_error or self.on_error.oid != macro.oid:
                    self.on_error = macro
                    self.log_set(prop, val)
                    self.set_modified(save)
                return True
            else:
                return False
        elif prop == 'interval':
            if self.cycle_enabled:
                return False
            try:
                interval = float(val)
            except:
                return False
            if interval > 0:
                if self.interval != interval:
                    self.interval = interval
                    self.log_set(prop, val)
                    self.set_modified(save)
                return True
            else:
                return False
        elif prop == 'ict':
            try:
                ict = int(val)
            except:
                return False
            if ict > 0:
                if self.ict != ict:
                    self.ict = ict
                    self.log_set(prop, val)
                    self.set_modified(save)
                return True
            else:
                return False
        elif prop == 'autostart':
            try:
                autostart = val_to_boolean(val)
                if autostart is None: raise ('Invalid val')
            except:
                return False
            if self.autostart != autostart:
                self.autostart = autostart
                self.log_set(prop, val)
                self.set_modified(save)
            return True
        else:
            return super().set_prop(prop, val, save)

    def _t_cycle(self):
        logging.debug('%s cycle thread started' % self.full_id)
        self.cycle_status = 1
        self.notify()
        prev = None
        c = 0
        tc = 0
        while self.cycle_enabled:
            cycle_start = time.time()
            cycle_end = cycle_start + self.interval
            if self.macro:
                self.iterations += 1
                try:
                    result = eva.lm.controller.exec_macro(
                        self.macro,
                        wait=self.interval,
                        source=self,
                        is_shutdown_func=self.is_shutdown)
                except Exception as e:
                    ex = e
                    result = None
                if not result:
                    logging.error('cycle %s exception %s' % (self.full_id, ex))
                    if self.on_error:
                        eva.lm.controller.exec_macro(
                            self.on_error, argv=['exception', ex], source=self)
                elif time.time() > cycle_end:
                    logging.error('cycle %s timeout' % (self.full_id))
                    if self.on_error:
                        eva.lm.controller.exec_macro(
                            self.on_error,
                            argv=['timeout', result.serialize()],
                            source=self)
                elif not result.is_status_completed():
                    logging.error('cycle %s exec error' % (self.full_id))
                    eva.lm.controller.exec_macro(
                        self.on_error,
                        argv=['exec_error', result.serialize()],
                        source=self)
            t = time.time()
            if prev is not None:
                real_interval = t - prev
                c += 1
                tc += real_interval
                self.stats_lock.acquire()
                try:
                    self.c += 1
                    self.tc += real_interval
                except:
                    self.c = 0
                    self.tc = 0
                self.stats_lock.release()
                if c >= self.ict:
                    corr = tc / c - self.interval
                    c = 0
                    tc = 0
                    threading.Thread(target=self.notify).start()
            else:
                corr = 0
            prev = t
            cycle_end -= corr
            while time.time() < cycle_end and self.cycle_enabled:
                time.sleep(eva.core.polldelay)
        logging.debug('%s cycle thread stopped' % self.full_id)
        self.cycle_status = 0
        # dirty - wait for prev. state to be sent
        # time.sleep(eva.core.sleep_step)
        self.notify()

    def start(self, autostart=False):
        if (autostart and
                not self.autostart) or not self.macro or self.cycle_enabled:
            self.notify()
            return False
        self.c = 0
        self.tc = 0
        self.cycle_enabled = True
        self.cycle_thread = threading.Thread(target=self._t_cycle)
        self.cycle_thread.start()
        return True

    def stop(self, wait=True):
        if self.cycle_thread and self.cycle_thread.isAlive():
            self.cycle_status = 2
            self.notify()
            self.cycle_enabled = False
            if wait: self.cycle_thread.join()
        else:
            self.cycle_enabled = False
        return True

    def reset_stats(self):
        self.stats_lock.acquire()
        self.c = 0
        self.tc = 0
        self.iterations = 0
        self.stats_lock.release()
        self.notify()
        return True

    def is_running(self):
        return self.cycle_enabled

    def is_shutdown(self):
        return not self.cycle_enabled

    def serialize(self,
                  full=False,
                  config=False,
                  info=False,
                  props=False,
                  notify=False):
        d = {}
        d.update(super().serialize(
            full=full, config=config, info=info, props=props, notify=notify))
        d['interval'] = self.interval
        if not config and not props:
            d['status'] = self.cycle_status
            d['value'] = '{},{:.4f},'.format(self.iterations,
                                             (self.tc / self.c
                                              if self.c else self.interval))
        if not notify:
            d['ict'] = self.ict
            d['macro'] = self.macro.full_id if self.macro else None
            d['on_error'] = self.on_error.full_id if self.on_error else None
        if config or props:
            d['autostart'] = self.autostart
        return d
