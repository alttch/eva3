__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.1"

import threading
from queue import PriorityQueue
import logging
import eva.core
import eva.item
import time
import asyncio

from neotasker import BackgroundIntervalWorker, BackgroundQueueWorker


class ActiveItemQueue(object):

    def __init__(self,
                 queue_id,
                 keep_history=None,
                 default_priority=100,
                 enterprise_layout=False):
        self.default_priority = default_priority
        self.q_id = queue_id
        self.keep_history = keep_history

        self.actions = []
        self.actions_by_id = {}
        self.actions_by_item_id = {}
        self.actions_by_item_full_id = {}

        self.actions_lock = threading.RLock()

        self.action_processor = None

        self.enterprise_layout = enterprise_layout

        self.action_cleaner = None
        self.action_processor = None

    def put_task(self, action, priority=None):
        if priority:
            p = priority
        else:
            p = self.default_priority
        if self.keep_history:
            self.history_append(action)
        if action.set_pending():
            self.action_processor.put_threadsafe(action)
            return True
        return False

    def serialize(self):
        d = []
        if not self.actions_lock.acquire(timeout=eva.core.config.timeout):
            logging.critical('ActiveItemQueue::serialize_action locking broken')
            eva.core.critical()
            return
        try:
            _actions = self.actions.copy()
        except:
            eva.core.log_traceback()
        finally:
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
        if not self.actions_lock.acquire(timeout=eva.core.config.timeout):
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
            return True
        except:
            eva.core.log_traceback()
            return False
        finally:
            self.actions_lock.release()

    def history_remove(self, action):
        if not self.actions_lock.acquire(timeout=eva.core.config.timeout):
            logging.critical('ActiveItemQueue::history_remove locking broken')
            eva.core.critical()
            return False
        try:
            if not self.enterprise_layout:
                self.actions_by_item_id[action.item.item_id].remove(action)
            self.actions_by_item_full_id[action.item.full_id].remove(action)
            self.actions.remove(action)
            del self.actions_by_id[action.uuid]
            return True
        except:
            eva.core.log_traceback()
            return False
        finally:
            self.actions_lock.release()

    def start(self):
        if self.keep_history is None:
            self.keep_history = eva.core.config.keep_action_history
        self.action_cleaner_interval = eva.core.config.action_cleaner_interval

        self.action_cleaner = BackgroundIntervalWorker(
            fn=action_cleaner,
            name='primary_action_cleaner',
            delay=self.action_cleaner_interval,
            o=self,
            on_error=eva.core.log_traceback,
            loop='cleaners')
        self.action_cleaner.start()
        self.action_processor = BackgroundQueueWorker(
            fn=action_processor,
            name='primary_action_processor',
            on_error=eva.core.log_traceback,
            queue=asyncio.queues.PriorityQueue,
            o=self)
        self.action_processor.start()

    def stop(self):
        self.action_cleaner.stop()
        self.action_processor.stop()

    def process_action(self, action):
        return action.item.q_put_task(action)


async def action_processor(action, **kwargs):
    if not action.item:
        return
    o = kwargs.get('o')
    logging.debug('new action to toss, uuid: %s, priority: %u' % \
            (action.uuid, action.priority))
    try:
        if o.process_action(action):
            logging.debug(
                    'action %s requeued into local queue of %s' % \
                    (action.uuid, action.item.full_id))
        else:
            logging.debug(
             'action %s failed to requeue into local queue of %s' %\
             (action.uuid, action.item.full_id))
    except:
        eva.core.log_traceback()


async def action_cleaner(**kwargs):
    o = kwargs.get('o')
    if not o.actions_lock.acquire(timeout=eva.core.config.timeout):
        logging.critical('ActiveItemQueue::_t_action_cleanup locking broken')
        eva.core.critical()
        return
    logging.debug('cleaning old actions')
    try:
        _actions = o.actions.copy()
    except:
        _actions = []
        eva.core.log_traceback()
    finally:
        o.actions_lock.release()
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
        if maxtime and maxtime < time.time() - o.keep_history:
            if a.is_finished():
                logging.debug(
                        '%s action %s too old, removing' % \
                        (o.q_id, a.uuid))
                o.history_remove(a)
            else:
                logging.warning(
                    '%s action %s too old, status is %s ' % \
                    (o.q_id, a.uuid,
                        eva.item.ia_status_names[a.status]))
