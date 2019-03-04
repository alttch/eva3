__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.1.2"

import threading
from queue import PriorityQueue
import logging
import eva.core
import eva.item
import time


class ActiveItemQueue(object):

    def __init__(self,
                 queue_id,
                 keep_history=None,
                 default_priority=100,
                 enterprise_layout=False):
        self.default_priority = default_priority
        self.q_id = queue_id
        if keep_history: self.keep_history = keep_history
        else: self.keep_history = eva.core.keep_action_history

        self.actions = []
        self.actions_by_id = {}
        self.actions_by_item_id = {}
        self.actions_by_item_full_id = {}

        self.actions_lock = threading.Lock()

        self.action_cleaner_interval = eva.core.action_cleaner_interval
        self.action_cleaner = None
        self.action_cleaner_active = False

        self.action_processor = None
        self.action_cleaner_active = False
        self.q = PriorityQueue()

        self.enterprise_layout = enterprise_layout

    def put_task(self, action, priority=None):
        if priority: p = priority
        else: p = self.default_priority
        if self.keep_history:
            self.history_append(action)
        if action.set_pending():
            self.q.put(action, p)
            return True
        return False

    def serialize(self):
        d = []
        if not self.actions_lock.acquire(timeout=eva.core.timeout):
            logging.critical('ActiveItemQueue::serialize_action locking broken')
            eva.core.critical()
            return
        try:
            _actions = self.actions.copy()
        except:
            eva.core.log_traceback()
        self.actions_lock.release()
        for a in _actions:
            d.append(a.serialize())
        return d

    def history_get(self, action_uuid):
        try:
            if action_uuid in self.actions_by_id:
                return self.actions_by_id[action_uuid]
        except:
            return None

    def history_append(self, action):
        if not self.actions_lock.acquire(timeout=eva.core.timeout):
            logging.critical('ActiveItemQueue::history_append locking broken')
            eva.core.critical()
            return False
        try:
            self.actions.append(action)
            self.actions_by_id[action.uuid] = action
            if not self.enterprise_layout:
                self.actions_by_item_id.setdefault(action.item.item_id,
                                                   []).append(action)
            self.actions_by_item_full_id.setdefault(action.item.full_id,
                                                    []).append(action)
        except:
            self.actions_lock.release()
            eva.core.log_traceback()
            return False
        self.actions_lock.release()
        return True

    def history_remove(self, action):
        if not self.actions_lock.acquire(timeout=eva.core.timeout):
            logging.critical('ActiveItemQueue::history_remove locking broken')
            eva.core.critical()
            return False
        try:
            if not self.enterprise_layout:
                self.actions_by_item_id[action.item.item_id].remove(action)
            self.actions_by_item_full_id[action.item.full_id].remove(action)
            self.actions.remove(action)
            del self.actions_by_id[action.uuid]
        except:
            self.actions_lock.release()
            eva.core.log_traceback()
            return False
        self.actions_lock.release()
        return True

    def _t_action_cleaner(self):
        logging.debug('%s item queue cleaner started' % self.q_id)
        while self.action_cleaner_active:
            try:
                if not self.actions_lock.acquire(timeout=eva.core.timeout):
                    logging.critical(
                        'ActiveItemQueue::_t_action_cleanup locking broken')
                    eva.core.critical()
                    continue
                try:
                    _actions = self.actions.copy()
                except:
                    _actions = []
                    eva.core.log_traceback()
                self.actions_lock.release()
                for a in _actions:
                    try:
                        tk = list(a.time.keys()).copy()
                    except:
                        eva.core.log_traceback()
                    maxtime = 0
                    for t in tk:
                        try:
                            maxtime = max(maxtime, a.time[t])
                        except:
                            pass
                    if maxtime and \
                            maxtime < time.time() - self.keep_history:
                        if a.is_finished():
                            logging.debug(
                                    '%s action %s too old, removing' % \
                                    (self.q_id, a.uuid))
                            self.history_remove(a)
                        else:
                            logging.warning(
                                '%s action %s too old, status is %s ' % \
                                (self.q_id, a.uuid,
                                    eva.item.ia_status_names[status]))
            except:
                eva.core.log_traceback()
            i = 0
            while i < self.action_cleaner_interval and \
                    self.action_cleaner_active:
                time.sleep(eva.core.sleep_step)
                i += eva.core.sleep_step
        logging.debug('%s item queue cleaner stopped' % self.q_id)

    def start(self, loop=True):
        if loop:
            eva.core.stop.append(self.stop)
            self.action_processor = threading.Thread(
                target=self._t_action_processor,
                name='_t_itemqueue_processor_' + self.q_id,
                args=(True,))
            self.action_processor_active = True
            self.action_processor.start()
            self.action_cleaner = threading.Thread(
                target=self._t_action_cleaner,
                name='_t_itemqueue_cleaner_' + self.q_id)
            if self.keep_history:
                self.action_cleaner_active = True
                self.action_cleaner.start()
        else:
            self._t_action_processor(False)

    def stop(self):
        if self.action_cleaner_active:
            self.action_cleaner_active = False
            self.action_cleaner.join()
        if self.action_processor_active:
            self.action_processor_active = False
            a = eva.item.ItemAction(None)
            self.q.put(a)
            self.action_processor.join()

    def process_action(self, action):
        return action.item.q_put_task(action)

    def _t_action_processor(self, loop):
        logging.debug('%s item queue processor started' % self.q_id)
        if not loop: runonce = True
        else: runonce = False
        while (loop or runonce) and self.action_processor_active:
            action = self.q.get()
            if not action or not action.item: continue
            logging.debug('new action to toss, uuid: %s, priority: %u' % \
                    (action.uuid, action.priority))
            try:
                if self.process_action(action):
                    logging.debug(
                            'action %s requeued into local queue of %s' % \
                            (action.uuid, action.item.full_id))
                else:
                    logging.debug(
                     'action %s failed to requeue into local queue of %s' %\
                     (action.uuid, action.item.full_id))
            except:
                eva.core.log_traceback()
        logging.debug('%s item queue processor stopped' % self.q_id)
