__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "3.1.2"

import eva.core
import eva.item
import eva.lm.macro_api
import eva.lm.extapi
import threading
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
        self.action_log_run(a)
        self.action_before_run(a)
        env_globals = {}
        env_globals.update(eva.lm.extapi.env)
        env_globals.update(a.item.api.get_globals())
        env_globals['_source'] = a.source
        argv = []
        for x in a.argv:
            try:
                value = float(x)
            except:
                value = x
            argv.append(value)
        env_globals['argv'] = argv
        env_globals['kwargs'] = a.kwargs
        for i, v in a.kwargs.items():
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
                 source=None):
        self.argv = argv
        self.kwargs = kwargs
        self.source = source
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
        self.api = eva.lm.macro_api.MacroAPI(pass_errors=False)

    def update_config(self, data):
        if 'pass_errors' in data:
            self.api.pass_errors = data['pass_errors']
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
