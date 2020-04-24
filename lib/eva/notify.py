__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2020 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.3.0"

import logging
import eva.core
import rapidjson
import msgpack
import requests
import paho.mqtt.client as mqtt
import time
from queue import Queue
import glob
import os
import sys
import ssl
import uuid
import threading
import sqlalchemy as sa
import pyaltt2.logs

from pyaltt2.converters import mq_topic_match

from sqlalchemy import text as sql

import yaml
try:
    yaml.warnings({'YAMLLoadWarning': False})
except:
    pass

from neotasker import BackgroundIntervalWorker
from neotasker import BackgroundQueueWorker
from neotasker import background_worker
from neotasker import g

from eva.tools import format_json
from eva.tools import val_to_boolean

from eva.types import CT_JSON, CT_MSGPACK

from eva.client.apiclient import pack_msgpack

from ws4py.websocket import WebSocket

from types import SimpleNamespace

default_log_level = 20

notifier_client_clean_delay = 30

default_mqtt_qos = 1

db_default_keep = 86400
default_stats_notifier_id = 'db_1'

default_notifier_id = 'eva_1'

logging.getLogger('requests').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)

notifiers = {}

_flags = SimpleNamespace(action_subscribed=False)

_ne_kw = {'notifier': True}

notify_leave_data = set()

with_notify_lock = eva.core.RLocker('notify')


class Event(object):

    def __init__(self, subject):
        self.subject = subject

    def serialize(self):
        d = {}
        d['subject'] = self.subject
        return d


class EventItem(Event):

    def __init__(self, subject, items, groups, item_types):
        super().__init__(subject=subject)
        if isinstance(groups, list):
            self.groups = groups
        elif groups:
            self.groups = [groups]
        else:
            self.groups = []
        if isinstance(item_types, list):
            self.item_types = item_types
        elif item_types:
            self.item_types = [item_types]
        else:
            self.item_types = []
        self.item_ids = set()
        if isinstance(items, list):
            for i in items:
                if isinstance(i, str):
                    self.item_ids.add(i)
                else:
                    self.item_ids.add(i.item_id)
        else:
            if isinstance(items, str):
                self.item_ids.add(items)
            elif items:
                self.item_ids.add(items.item_id)

    def append_item(self, item):
        if isinstance(item, str):
            self.item_ids.add(item)
        else:
            self.item_ids.add(item.item_id)

    def remove_item(self, item):
        if isinstance(item, str):
            try:
                self.item_ids.remove(item)
            except:
                pass
        else:
            try:
                self.item_ids.remove(item.item_id)
            except:
                pass

    def append_group(self, group):
        self.groups.append(group)

    def remove_group(self, group):
        try:
            self.groups.remove(group)
        except:
            pass

    def serialize(self):
        d = {}
        if self.item_ids:
            d['items'] = list(self.item_ids)
        if self.groups:
            d['groups'] = self.groups
        if self.item_types:
            d['types'] = self.item_types
        d.update(super().serialize())
        return d


class EventState(EventItem):

    def __init__(self, items, groups, item_types):
        super().__init__('state', items, groups, item_types)


class EventAction(EventItem):

    def __init__(self, items, groups, item_types, action_status):
        super().__init__('action', items, groups, item_types)
        if isinstance(action_status, list):
            self.action_status = action_status
        else:
            self.action_status = [action_status]

    def serialize(self):
        d = {}
        if self.action_status:
            d['action_status'] = self.action_status
        d.update(super().serialize())
        return d


class EventLog(Event):

    def __init__(self, log_level=None):
        super().__init__(subject='log')
        self.log_level = log_level

    def get_log_level(self):
        return self.log_level if self.log_level else default_log_level

    def serialize(self):
        d = {}
        if (self.log_level):
            d['level'] = self.log_level
        d.update(super().serialize())
        return d


class EventServer(Event):

    def __init__(self):
        super().__init__(subject='server')


class GenericNotifier(object):

    class NotifierWorker(BackgroundQueueWorker):

        def __init__(self, **kwargs):
            super().__init__(on_error=eva.core.log_traceback,
                             on_error_kwargs=_ne_kw,
                             **kwargs)

        def run(self, event, o, **kwargs):
            o.send_notification(subject=event[0],
                                data=event[1],
                                retain=event[2],
                                unpicklable=event[3])

    class ScheduledNotifyWorker(BackgroundIntervalWorker):

        def __init__(self, o, **kwargs):
            self.need_notify = False
            super().__init__(on_error=eva.core.log_traceback,
                             on_error_kwargs=_ne_kw,
                             o=o,
                             **kwargs)

        def run(self, o, **kwargs):
            e = o.is_subscribed('state')
            if o.can_notify() and e:
                if self.need_notify:
                    logging.debug('.{} sending scheduled notifications'.format(
                        o.notifier_id))
                    import eva.core
                    for c in eva.core.controllers:
                        for i, v in c._get_all_items().items():
                            if e.item_types and ('#' in e.item_types
                                            or v.item_type in e.item_types) \
                                            and eva.item.item_match(v, e.item_ids,
                                                    e.groups):
                                o.notify('state', (v, v.serialize(notify=True)))
                else:
                    self.need_notify = True

    def __init__(self,
                 notifier_id,
                 notifier_type=None,
                 space=None,
                 interval=None,
                 timeout=None):
        self.notifier_id = notifier_id
        self.notifier_type = notifier_type
        self.space = space
        self.interval = interval
        self.events = set()
        self.timeout = timeout
        self.enabled = False
        self.test_only_mode = False
        self.connected = False
        self.nt_client = False
        self._skip_test = None
        self.last_state_event = {}
        self.lse_lock = threading.RLock()
        self.notifier_worker = self.NotifierWorker(o=self,
                                                   name='notifier:' +
                                                   self.notifier_id)
        if self.interval:
            self.scheduled_notify_worker = self.ScheduledNotifyWorker(
                o=self,
                name='notifier:' + self.notifier_id,
                interval=self.interval)
        self.state_storage = None

    def subscribe(self,
                  subject,
                  items=[],
                  groups=[],
                  item_types=[],
                  action_status=[],
                  log_level=None):
        _e = self.is_subscribed(subject)
        if subject == 'state':
            if _e:
                self.events.remove(_e)
            e = EventState(items=items, groups=groups, item_types=item_types)
            self.events.add(e)
        elif subject == 'action':
            if _e:
                self.events.remove(_e)
            e = EventAction(items=items,
                            groups=groups,
                            item_types=item_types,
                            action_status=action_status)
            self.events.add(e)
            if self.enabled:
                _flags.action_subscribed = True
        elif subject == 'log':
            if log_level is not None:
                try:
                    _log_level = int(log_level)
                except:
                    return False
            if not _e:
                e = EventLog(log_level)
                self.events.add(e)
            else:
                _e.log_level = log_level
        elif subject == 'server':
            e = EventServer()
            self.events.add(e)
        else:
            return False
        return True

    def is_subscribed(self, subject):
        for e in self.events.copy():
            if e.subject == subject:
                return e
        return None

    def unsubscribe(self, subject):
        if isinstance(subject, list):
            for s in subject:
                self.unsubscribe(s)
        else:
            if subject == '#':
                self.events = []
            else:
                for e in self.events.copy():
                    if e.subject == subject:
                        self.events.remove(e)
        return True

    def subscribe_item(self, subject, item):
        if subject == '#' or subject == 'action':
            e = self.is_subscribed('action')
            if e:
                e.append_item(item)
        if subject == '#' or subject == 'state':
            e = self.is_subscribed('state')
            if e:
                e.append_item(item)

    def subscribe_group(self, subject, item):
        if subject == '#' or subject == 'action':
            e = self.is_subscribed('action')
            if e:
                e.append_group(item)
        if subject == '#' or subject == 'state':
            e = self.is_subscribed('state')
            if e:
                e.append_group(item)

    def unsubscribe_item(self, subject, item):
        if subject == '#' or subject == 'action':
            e = self.is_subscribed('action')
            if e:
                e.remove_item(item)
        if subject == '#' or subject == 'state':
            e = self.is_subscribed('state')
            if e:
                e.remove_item(item)

    def unsubscribe_group(self, subject, item):
        if subject == '#' or subject == 'action':
            e = self.is_subscribed('action')
            if e:
                e.remove_group(item)
        if subject == '#' or subject == 'state':
            e = self.is_subscribed('state')
            if e:
                e.remove_group(item)

    def format_data(self, subject, data):
        if not subject or not data:
            return None
        import eva.item
        import eva.core
        try:
            if isinstance(data, list):
                data_in = data
            else:
                data_in = [data]
            fdata = None
            e = self.is_subscribed(subject)
            if not e:
                return None
            if subject == 'log':
                fdata = []
                for d in data_in:
                    if d['l'] >= e.get_log_level() and 'msg' in d \
                                    and d['msg'][0] != '.':
                        fdata.append(d)
            elif subject == 'server':
                return data_in
            elif subject == 'state':
                fdata = []
                for din in data_in:
                    d, dts = din
                    if e.item_types and ('#' in e.item_types
                                    or d.item_type in e.item_types) \
                                    and eva.item.item_match(d, e.item_ids,
                                            e.groups):
                        if not self.lse_lock.acquire(
                                timeout=eva.core.config.timeout):
                            logging.critical(
                                '.GenericNotifier::format_data locking broken')
                            eva.core.critical()
                            return None
                        need_notify = False
                        try:
                            if d.item_id in self.last_state_event:
                                lse = self.last_state_event[d.item_id]
                                for k in dts:
                                    if k not in lse or \
                                            dts[k] != lse[k]:
                                        need_notify = True
                                        break
                            else:
                                need_notify = True
                            if need_notify:
                                self.last_state_event[d.item_id] = dts
                                fdata.append(dts)
                        except:
                            eva.core.log_traceback(notifier=True)
                        finally:
                            self.lse_lock.release()
            elif subject == 'action':
                fdata = []
                for din in data_in:
                    d, dts = din
                    if e.item_types and ('#' in e.item_types \
                                    or d.item.item_type in e.item_types) \
                            and e.action_status and ('#' in e.action_status \
                                or d.get_status_name() in e.action_status) \
                            and eva.item.item_match(d.item, e.item_ids,
                                    e.groups):
                        fdata.append(dts)
            else:
                return None
            return fdata
        except:
            logging.error('.Notifier data format error')
            eva.core.log_traceback(notifier=True)
            return None

    def get_timeout(self):
        return self.timeout if self.timeout else eva.core.config.timeout

    def log_error(self, code=None, message=None):
        if not code and not message:
            logging.error('.Failed to notify %s, can not send data' % \
                    self.notifier_id)
        elif not message:
            logging.error('.Failed to notify %s, error response code: %s' % \
                    (self.notifier_id, code))
        else:
            logging.error('.Failed to notify %s, error response: %s' % \
                    (self.notifier_id, message))

    def can_notify(self):
        return self.enabled and self.connected

    def start(self):
        self.connect()
        if not self.test_only_mode:
            self.notifier_worker.start()
            if self.interval:
                self.scheduled_notify_worker.start()

    def stop(self):
        if not self.test_only_mode:
            self.notifier_worker.stop()
            if self.interval:
                self.scheduled_notify_worker.stop()
        self.disconnect()

    def notify(self, subject, data, unpicklable=False, retain=False):
        if not self.can_notify():
            return False
        data_to_send = self.format_data(subject, data)
        if not data_to_send:
            return None
        self.log_notify()
        self.notifier_worker.put_threadsafe(
            (subject, data_to_send, retain, unpicklable))
        return True

    def serialize(self, props=False):
        d = {}
        if not props:
            d['id'] = self.notifier_id
            d['type'] = self.notifier_type
            if self.events:
                d['events'] = []
                for e in self.events.copy():
                    d['events'].append(e.serialize())
        if self.space or props:
            d['space'] = self.space
        if self.interval or props:
            d['interval'] = self.interval
        if self._skip_test is not None or props:
            d['skip_test'] = self._skip_test
        d['enabled'] = self.enabled
        if self.timeout or props:
            d['timeout'] = self.timeout
        return d

    def set_prop(self, prop, value):
        if prop == 'enabled':
            if value is None:
                self.enabled = False
                return True
            val = val_to_boolean(value)
            if val is None:
                return False
            self.enabled = val
            return True
        if prop == 'skip_test':
            if value is None:
                self._skip_test = None
                return True
            val = val_to_boolean(value)
            if val is None:
                return False
            self._skip_test = val
            return True
        elif prop == 'space':
            self.space = value
            return True
        elif prop == 'interval':
            if not value:
                self.interval = None
                return True
            try:
                self.interval = float(value)
            except:
                return False
            return True
        elif prop == 'timeout':
            if not value:
                self.timeout = None
                return True
            try:
                self.timeout = float(value)
            except:
                return False
            return True
        return False

    # The following methods always need to be overrided in custom notifiers
    #
    # !IMPORTANT: when use logging, always start message from dot ('.')
    #             to prevent double logging notifications

    def send_notification(self, subject, data, retain=None, unpicklable=False):
        """
        Executed with data the current notifier is subscribed to.

        Args:
            subject: Notification subject: 'state', 'log' or other.
            data: Array of notification data hashmaps.
            retain: if specified, the notification will be forcely retained
                    or not (if retain is supported by notifier)
            unpicklable: Reserved, in case the system requests the data to be
                        deserialized or not in future. Just keep as is.

        Returns:
            True if successful notification, False if error.

        Raises:
            If the method raise an exception, log_error() is being called.
        """
        return False

    def test(self):
        self.connect()
        return True

    def connect(self):
        self.connected = True

    def disconnect(self):
        self.connected = False

    def load_config(self):
        """
        Executed when system is loading or reloading global notifiers config
        """
        pass

    def save_config(self):
        """
        Executed when system is saving global notifiers config.
            
        """
        pass

    def log_notify(self):
        """
        Executed before send_notification method
        """
        logging.debug('.sending data notification to %s, method = %s' % \
                                (self.notifier_id, self.notifier_type))


class GenericNotifier_Client(GenericNotifier):

    def __init__(self,
                 notifier_id=None,
                 notifier_subtype=None,
                 apikey=None,
                 token=None):
        if not notifier_id:
            _id = str(uuid.uuid4())
        else:
            _id = notifier_id
        _tp = 'client'
        if notifier_subtype:
            _tp += notifier_subtype
        else:
            _tp += 'generic'
        super().__init__(_id, _tp)
        self.nt_client = True
        self.enabled = True
        self.apikey = apikey
        self.token = token
        self.subscribe('server')

    def format_data(self, subject, data):
        if not subject or not data:
            return None
        from eva import apikey
        if apikey.check(self.apikey, master=True):
            return super().format_data(subject, data)
        if subject == 'log':
            if not apikey.check(self.apikey, sysfunc=True):
                return None
            else:
                return super().format_data(subject, data)
        if isinstance(data, list):
            data_in = data
        else:
            data_in = [data]
        fdata = []
        if subject == 'state':
            for d in data_in:
                if apikey.check(self.apikey, d, ro_op=True):
                    fdata.append(d)
        elif subject == 'action':
            for din in data_in:
                d, dts = din
                if apikey.check(self.apikey, d.item, ro_op=True):
                    fdata.append(dts)
        elif subject == 'server':
            fdata = data
        return super().format_data(subject, fdata)

    def is_client_dead(self):
        return False

    def register(self):
        if not self.notifier_id in notifiers:
            logging.debug('Registering client notifier %s' % self.notifier_id)
            notifiers[self.notifier_id] = self

    def unregister(self):
        try:
            if self.notifier_id in notifiers:
                logging.debug('Unregistering client notifier %s' % \
                        self.notifier_id)
                notifiers[self.notifier_id].stop()
                del notifiers[self.notifier_id]
        except:
            eva.core.log_traceback(notifier=True)

    def cleanup(self):
        from eva.tokens import is_token_alive
        if self.is_client_dead() or (self.token and
                                     not is_token_alive(self.token)):
            self.connected = False
            self.unregister()


class SQLANotifier(GenericNotifier):

    class HistoryCleaner(BackgroundIntervalWorker):

        def __init__(self, **kwargs):
            super().__init__(interval=60,
                             on_error=eva.core.log_traceback,
                             on_error_kwargs=_ne_kw,
                             loop='cleaners',
                             **kwargs)

        def run(self, o, **kwargs):
            dbconn = o.db()
            space = o.space if o.space is not None else ''
            logging.debug('.cleaning records older than %u sec' % o.keep)
            result = dbconn.execute(
                sql('select oid, max(t) as maxt from state_history where ' +
                    'space = :space and t < :t group by oid'),
                space=space,
                t=time.time() - o.keep)
            for r in result:
                dbconn.execute(
                    sql('delete from state_history where space = :space ' +
                        'and oid = :oid and t < :maxt'),
                    space=space,
                    oid=r.oid,
                    maxt=r.maxt)

    def __init__(self,
                 notifier_id,
                 db_uri=None,
                 keep=None,
                 space=None,
                 interval=None):
        notifier_type = 'db'
        super().__init__(notifier_id=notifier_id,
                         notifier_type=notifier_type,
                         space=space,
                         interval=interval)
        self.state_storage = 'sql'
        self.keep = keep if keep else \
            db_default_keep
        self._keep = keep
        self.history_cleaner = self.HistoryCleaner(name='history_claner:' +
                                                   self.notifier_id,
                                                   o=self)
        self.db_lock = threading.RLock()
        self.set_db(db_uri)

    def set_db(self, db_uri=None):
        self._db = db_uri
        self.db_uri = eva.core.format_db_uri(db_uri)
        self.init_db_engine()

    def init_db_engine(self):
        self.db_engine = eva.core.create_db_engine(self.db_uri,
                                                   timeout=self.timeout)

    def test(self):
        if self.connected:
            return True
        self.connect()
        return self.connected

    def db(self):
        n = 'notifier_{}_db'.format(self.notifier_id)
        with self.db_lock:
            if not g.has(n):
                c = self.db_engine.connect()
                g.set(n, c)
            else:
                c = g.get(n)
                try:
                    c.execute('select 1')
                except:
                    try:
                        c.close()
                    except:
                        pass
                    c = self.db_engine.connect()
                    g.set(n, c)
            return c

    def get_state(self,
                  oid,
                  t_start=None,
                  t_end=None,
                  fill=None,
                  limit=None,
                  prop=None,
                  time_format=None,
                  xopts=None,
                  **kwargs):
        import pytz
        import dateutil.parser
        from datetime import datetime
        l = int(limit) if limit and not fill else None
        if t_start:
            try:
                t_s = float(t_start)
            except:
                try:
                    t_s = dateutil.parser.parse(t_start).timestamp()
                except:
                    t_s = None
        else:
            t_s = None
        if t_end:
            try:
                t_e = float(t_end)
            except:
                try:
                    t_e = dateutil.parser.parse(t_end).timestamp()
                except:
                    t_e = None
        else:
            t_e = None
        q = ''
        if t_s:
            q += ' and t>%f' % t_s
        if t_e:
            q += ' and t<=%f' % t_e
        if l:
            q += ' order by t desc limit %u' % l
        req_status = False
        req_value = False
        if prop in ['status', 'S']:
            props = 'status'
            req_status = True
        elif prop in ['value', 'V']:
            props = 'value'
            req_value = True
        else:
            props = 'status, value'
            req_status = True
            req_value = True
        dbconn = self.db()
        result = []
        space = self.space if self.space is not None else ''
        tz = pytz.timezone(time.tzname[0])
        data = []
        # if we have start time - fetch newest record before it
        if t_s:
            r = dbconn.execute(
                sql('select ' + props +
                    ' from state_history where space = :space and oid = :oid' +
                    ' and t <= :t order by t desc limit 1'),
                space=space,
                oid=oid,
                t=t_s).fetchone()
            if r:
                r = (t_s,) + tuple(r)
                data += [r]
        data += list(
            dbconn.execute(
                sql('select t, ' + props +
                    ' from state_history where space = :space and oid = :oid' +
                    q),
                space=space,
                oid=oid).fetchall())
        if l and len(data) > l:
            data = data[:l]
        for d in data:
            h = {}
            if time_format == 'iso':
                h['t'] = datetime.fromtimestamp(float(d[0]), tz).isoformat()
            elif time_format == 'dt_utc':
                h['t'] = datetime.fromtimestamp(float(d[0]), tz)
            else:
                h['t'] = float(d[0])
            if req_status:
                h['status'] = d[1]
            if req_value:
                if req_status:
                    v = d[2]
                else:
                    v = d[1]
                try:
                    h['value'] = float(v)
                except:
                    h['value'] = v if v else None
            result.append(h)
        return sorted(result, key=lambda k: k['t'])

    def connect(self):
        try:
            if self.db_engine:
                dbconn = self.db()
                meta = sa.MetaData()
                t_state_history = sa.Table(
                    'state_history', meta,
                    sa.Column('space', sa.String(64), primary_key=True),
                    sa.Column('t', sa.Numeric(20, 8), primary_key=True),
                    sa.Column('oid', sa.String(256), primary_key=True),
                    sa.Column('status', sa.Integer),
                    sa.Column('value', sa.String(256)))
                sa.Index('i_t_oid', t_state_history.c.space,
                         t_state_history.c.t, t_state_history.c.oid)
                sa.Index('i_oid', t_state_history.c.space,
                         t_state_history.c.oid)
                try:
                    meta.create_all(dbconn)
                except:
                    logging.error('.%s: failed to create state_history table' %
                                  self.db_uri)
                    eva.core.log_traceback(notifier=True)
                    self.connected = False
                    return False
                if not self.test_only_mode:
                    self.history_cleaner.start(_name=self.notifier_id +
                                               '_cleaner')
                self.connected = True
            else:
                self.connected = False
        except:
            eva.core.log_traceback(notifier=True)
            self.connected = False

    def send_notification(self, subject, data, retain=None, unpicklable=False):
        if subject == 'state':
            t = time.time()
            for d in data:
                v = d['value'] if 'value' in d and \
                        d['value'] != '' else None
                space = self.space if self.space is not None else ''
                dbconn = self.db()
                dbconn.execute(
                    sql('insert into state_history (space, t, oid, status, ' +
                        'value) values (:space, :t, :oid, :status, :value)'),
                    space=space,
                    t=t,
                    oid=d['oid'],
                    status=d['status'],
                    value=v)
        return True

    def set_prop(self, prop, value):
        if prop == 'db':
            if value is None or value == '':
                return False
            self.set_db(value)
            return True
        elif prop == 'keep':
            if value is None:
                self.keep = db_default_keep
                self._keep = None
                return True
            try:
                self.keep = int(value)
            except:
                return False
            self._keep = self.keep
            return True
        elif prop == 'timeout':
            if super().set_prop(prop, value):
                self.init_db_engine()
                return True
            else:
                return False
        return super().set_prop(prop, value)

    def serialize(self, props=False):
        d = super().serialize(props)
        if self._keep or props:
            d['keep'] = self._keep
        if self._db or props:
            d['db'] = self._db
        return d

    def disconnect(self):
        self.history_cleaner.stop()


class GenericHTTPNotifier(GenericNotifier):

    def __init__(self,
                 notifier_id,
                 notifier_subtype=None,
                 uri=None,
                 username=None,
                 password=None,
                 space=None,
                 interval=None,
                 timeout=None,
                 ssl_verify=True):
        notifier_type = 'http'
        if notifier_subtype:
            notifier_type += '-' + notifier_subtype
        super().__init__(notifier_id=notifier_id,
                         notifier_type=notifier_type,
                         space=space,
                         interval=interval,
                         timeout=timeout)
        self.ssl_verify = ssl_verify
        self.uri = uri
        self.username = username
        self.password = password
        self.xrargs = {'verify': self.ssl_verify}
        if self.username is not None and self.password is not None:
            self.xrargs['auth'] = requests.auth.HTTPBasicAuth(
                self.username, self.password)
        self.connected = True

    def rsession(self):
        n = 'notifier_{}_rsession'.format(self.notifier_id)
        if not g.has(n):
            c = requests.Session()
            g.set(n, c)
        else:
            c = g.get(n)
        return c

    def log_notify(self):
        logging.debug('.sending data notification to ' + \
                            '%s method = %s,uri: %s' % (self.notifier_id,
                                    self.notifier_type, self.uri))

    def log_error(self, code=None, message=None, result=None):
        super().log_error(code=code, message=message)

    def serialize(self, props=False):
        d = {}
        d['uri'] = self.uri
        if (self.ssl_verify is not None and \
                self.ssl_verify is not True) or props:
            d['ssl_verify'] = self.ssl_verify
        if self.username or props:
            d['username'] = self.username
        if self.password or props:
            d['password'] = self.password
        d.update(super().serialize(props=props))
        return d

    def set_prop(self, prop, value):
        if prop == 'uri':
            if value is None:
                return False
            self.uri = value
            return True
        elif prop == 'username':
            self.username = value
            return True
        elif prop == 'password':
            self.password = value
            return True
        elif prop == 'ssl_verify':
            if value is None:
                self.ssl_verify = None
                return True
            val = val_to_boolean(value)
            if val is None:
                return False
            self.ssl_verify = val
            return True
        return super().set_prop(prop, value)


class HTTP_JSONNotifier(GenericHTTPNotifier):

    def __init__(self,
                 notifier_id,
                 uri,
                 username=None,
                 password=None,
                 method=None,
                 notify_key=None,
                 space=None,
                 interval=None,
                 timeout=None,
                 ssl_verify=True):
        super().__init__(notifier_id=notifier_id,
                         notifier_subtype='json',
                         ssl_verify=ssl_verify,
                         uri=uri,
                         username=username,
                         password=password,
                         space=space,
                         interval=interval,
                         timeout=timeout)
        self.method = method
        self.notify_key = notify_key

    def send_notification(self, subject, data, retain=None, unpicklable=False):
        from eva import apikey
        d = {'subject': subject}
        key = apikey.format_key(self.notify_key)
        if key:
            d['k'] = key
        if self.space:
            d['space'] = self.space
        if self.method == 'jsonrpc':
            data_ts = []
            for dd in data:
                dts = {'jsonrpc': '2.0', 'method': self.method}
                p = d.copy()
                p['data'] = dd
                dts['params'] = p
                if len(data) == 1:
                    data_ts = dts
                    break
                data_ts.append(dts)
        else:
            data_ts = d
            data_ts['data'] = data
        r = self.rsession().post(self.uri,
                                 json=data_ts,
                                 timeout=self.get_timeout(),
                                 **self.xrargs)
        if self.method == 'jsonrpc':
            if r.ok:
                return True
            else:
                self.log_error(code=r.status_code)
                return False
        if r.ok:
            if r.status_code != 202:
                result = r.json()
                if not result.get('ok'):
                    error = result.get('error')
                    if isinstance(error, dict):
                        code = error.get('code')
                        message = error.get('message')
                    else:
                        code = None
                        message = 'unknown error'
                    self.log_error(code=code, message=message)
                    return False
            return True
        self.log_error(code=r.status_code)
        return False

    def test(self):
        self.connect()
        try:
            logging.debug('.Testing http-json notifier %s (%s)' % \
                    (self.notifier_id,self.uri))
            d = {'subject': 'test'}
            if self.notify_key:
                d['k'] = self.notify_key
            if self.method == 'jsonrpc':
                req_id = str(uuid.uuid4())
                data_ts = {
                    'jsonrpc': '2.0',
                    'method': self.method,
                    'params': d,
                    'id': req_id
                }
            else:
                data_ts = d
            r = self.rsession().post(self.uri,
                                     json=data_ts,
                                     timeout=self.get_timeout(),
                                     **self.xrargs)
            if not r.ok:
                return False
            result = r.json()
            if self.method == 'jsonrpc':
                if result.get('jsonrpc') != '2.0' or \
                        result.get('id') != req_id or 'error' in result:
                    return False
            elif not result.get('ok'):
                return False
            return True
        except:
            eva.core.log_traceback(notifier=True)
            return False

    def serialize(self, props=False):
        d = {}
        if self.method or props:
            d['method'] = self.method
        if self.notify_key or props:
            d['notify_key'] = self.notify_key
        d.update(super().serialize(props=props))
        return d

    def set_prop(self, prop, value):
        if prop == 'method':
            if value is not None and value not in ['jsonrpc']:
                return False
            else:
                self.method = value
                return True
        elif prop == 'notify_key':
            self.notify_key = value
            return True
        else:
            return super().set_prop(prop, value)


class InfluxDB_Notifier(GenericHTTPNotifier):

    def __init__(self,
                 notifier_id,
                 uri,
                 db=None,
                 username=None,
                 password=None,
                 method=None,
                 notify_key=None,
                 space=None,
                 interval=None,
                 timeout=None,
                 ssl_verify=True):
        super().__init__(notifier_id=notifier_id,
                         ssl_verify=ssl_verify,
                         uri=uri,
                         username=username,
                         password=password,
                         space=space,
                         interval=interval,
                         timeout=timeout)
        self.method = method
        self.notify_key = notify_key
        self.notifier_type = 'influxdb'
        self.db = db
        self.state_storage = 'tsdb'

    __fills = {'S': 's', 'T': 'm', 'H': 'h', 'D': 'd', 'w': 'w'}

    def get_state(self,
                  oid,
                  t_start=None,
                  t_end=None,
                  fill=None,
                  limit=None,
                  prop=None,
                  time_format=None,
                  xopts=None,
                  **kwargs):
        import pytz
        import dateutil.parser
        import eva.item
        from datetime import datetime
        l = int(limit) if limit else None
        sfr = False
        if t_start:
            try:
                t_s = float(t_start)
            except:
                try:
                    t_s = dateutil.parser.parse(t_start).timestamp()
                except:
                    t_s = None
            if t_s and fill:
                t_s -= int(fill[:-1]) * eva.item._p_periods[fill[-1].upper()]
                sfr = True
        else:
            t_s = None
        if t_end:
            try:
                t_e = float(t_end)
            except:
                try:
                    t_e = dateutil.parser.parse(t_end).timestamp()
                except:
                    t_e = None
        else:
            t_e = None
        q = ''
        rp = ''
        if xopts and 'rp' in xopts:
            rp = '"{}".'.format(xopts['rp'])
        if t_s:
            q += 'where time>%u' % (t_s * 1000000000)
        if t_e:
            q += ' and' if q else 'where'
            q += ' time<=%u' % (t_e * 1000000000)
        if prop in ['status', 'S']:
            props = 'status' if not fill else 'mode(status)'
        elif prop in ['value', 'V']:
            props = 'value' if not fill else 'mean(value)'
        else:
            props = 'status,value' if not fill else 'mode(status),mean(value)'
        data = []
        space = (self.space + '/') if self.space is not None else ''
        if time_format == 'iso':
            tz = pytz.timezone(time.tzname[0])
        q = 'select {} from {}"{}" {}'.format(props, rp, oid, q)
        try:
            if fill:
                q += ' group by time({}{}) fill(previous)'.format(
                    fill[:-1], self.__fills[fill[-1].upper()])
            if l:
                q += ' limit %u' % l
            r = self.rsession().post(url=self.uri +
                                     '/query?db={}'.format(self.db),
                                     data={
                                         'q': q,
                                         'epoch': 'ms'
                                     },
                                     timeout=self.get_timeout(),
                                     **self.xrargs)
            if not r.ok:
                raise Exception('influxdb server error HTTP code {}'.format(
                    r.status_code))
            data = r.json()
            if 'error' in data['results'][0]:
                self.log_error(message=data['results'][0]['error'])
                raise Exception
            if not data['results'][0] or 'series' not in data['results'][0]:
                return []
            else:
                data = data['results'][0]['series'][0]['values']
        except:
            eva.core.log_traceback()
            self.log_error(message='unable to get state for {}'.format(oid))
            raise
        for d in data[1:] if sfr else data:
            if time_format == 'iso':
                d[0] = datetime.fromtimestamp(d[0] / 1000, tz).isoformat()
            else:
                d[0] = d[0] / 1000
        return data[1:] if sfr else data

    def send_notification(self, subject, data, retain=None, unpicklable=False):
        space = (self.space + '/') if self.space is not None else ''
        if subject == 'state':
            t = int(time.time() * 1000000000)
            for d in data:
                q = space + '{} status={}i'.format(d['oid'], d['status'])
                if d['value'] is not None and d['value'] != '':
                    try:
                        value = float(d['value'])
                        q += ',value={}'.format(value)
                    except:
                        q += ',value="{}"'.format(d['value'])
                q += ' {}'.format(t)
                r = self.rsession().post(
                    url=self.uri + '/write?db={}'.format(self.db),
                    data=q,
                    headers={'Content-Type': 'application/octet-stream'},
                    timeout=self.get_timeout(),
                    **self.xrargs)
                if not r.ok:
                    self.log_error(code=r.status_code)
                    return False
            return True

    def log_notify(self):
        logging.debug('.sending data notification to ' + \
                '%s method = %s, uri: %s, db: %s' % (self.notifier_id,
                                    self.notifier_type, self.uri, self.db))

    def test(self):
        self.connect()
        if self.db is None:
            return False
        space = self.space if self.space is not None else ''
        try:
            logging.debug('.Testing influxdb notifier %s (%s)' % \
                    (self.notifier_id,self.uri))
            r = self.rsession().post(
                url=self.uri + '/write?db={}'.format(self.db),
                data=space + ':eva_test test="passed"',
                headers={'Content-Type': 'application/octet-stream'},
                timeout=self.get_timeout(),
                **self.xrargs)
            return r.ok
        except:
            eva.core.log_traceback(notifier=True)
            return False

    def serialize(self, props=False):
        d = {}
        if self.method or props:
            d['method'] = self.method
        d['db'] = self.db
        d.update(super().serialize(props=props))
        return d

    def set_prop(self, prop, value):
        if prop == 'db':
            self.db = value
            return True
        else:
            return super().set_prop(prop, value)


class PrometheusNotifier(GenericNotifier):

    def __init__(self, notifier_id, space=None, username=None, password=None):
        notifier_type = 'prometheus'
        super().__init__(notifier_id=notifier_id,
                         notifier_type=notifier_type,
                         space=space)
        self.username = username
        self.password = password
        self._mounted = False

    class Metrics():

        def __init__(self, n):
            self.n = n

        def default(self):
            import cherrypy
            if self.n.username and self.n.password:
                import base64
                auth_header = cherrypy.serving.request.headers.get(
                    'authorization')
                try:
                    scheme, params = auth_header.split(' ', 1)
                    if scheme.lower() == 'basic':
                        u, p = base64.b64decode(params).decode().split(':', 1)
                        u = u.strip()
                    if u != self.n.username or p != self.n.password:
                        raise Exception
                except:
                    import eva.api
                    raise eva.api.cp_forbidden_key('invalid username/password')
            result = []
            cherrypy.serving.response.headers[
                'Content-Type'] = 'text/plain; charset=utf-8'
            e = self.n.is_subscribed('state')
            if not e:
                return '\n'
            import eva.core
            for c in eva.core.controllers:
                for i, v in c._get_all_items().items():
                    if e.item_types and ('#' in e.item_types
                                    or v.item_type in e.item_types) \
                                    and eva.item.item_match(v, e.item_ids,
                                            e.groups):
                        d = v.serialize(full=True)
                        oid = d.get('oid')
                        descr = d.get('description')
                        if oid:
                            oid = oid.replace('/', ':')
                            if 'status' in d:
                                try:
                                    val = int(d['status'])
                                    if descr:
                                        result.append(
                                            '# HELP {}:status {} status'.format(
                                                oid, descr))
                                    result.append('{}:status {}'.format(
                                        oid, val))
                                except:
                                    pass
                            if 'value' in d:
                                try:
                                    val = d['value']
                                    if val is None or val == '':
                                        val = 'NaN'
                                    else:
                                        val = float(val)
                                    if descr:
                                        result.append(
                                            '# HELP {}:value {} value'.format(
                                                oid, descr))
                                    result.append('{}:value {}'.format(
                                        oid, val))
                                except:
                                    pass
            return '\n'.join(result) + '\n'

        default.exposed = True

    def set_prop(self, prop, value):
        if prop == 'username':
            self.username = value
            return True
        elif prop == 'password':
            self.password = value
            return True
        elif prop == 'interval':
            return False
        return super().set_prop(prop, value)

    def serialize(self, props=False):
        d = super().serialize(props=False)
        if 'timeout' in d:
            del d['timeout']
        d['username'] = self.username
        d['password'] = self.password
        try:
            del d['interval']
        except:
            pass
        return d

    def can_notify(self):
        return False

    def start(self):
        if self.test_only_mode or self._mounted or not self.enabled:
            return
        import cherrypy
        cherrypy.tree.mount(self.Metrics(self),
                            '/ns/{}/metrics'.format(self.notifier_id))

    def stop(self):
        pass

    def test(self):
        return True


class GenericMQTTNotifier(GenericNotifier):

    class Announcer(BackgroundIntervalWorker):

        def __init__(self, **kwargs):
            super().__init__(on_error=eva.core.log_traceback,
                             on_error_kwargs=_ne_kw,
                             **kwargs)

        def run(self, o, **kwargs):
            if eva.core.is_shutdown_requested():
                return False
            eva.core._flags.started.wait(timeout=60)
            o.send_message(o.announce_topic,
                           o.announce_msg,
                           qos=o.qos['system'],
                           use_space=False)

    def __init__(self,
                 notifier_id,
                 host,
                 port=None,
                 space=None,
                 interval=None,
                 username=None,
                 password=None,
                 qos=None,
                 keepalive=None,
                 timeout=None,
                 collect_logs=None,
                 api_enabled=None,
                 discovery_enabled=None,
                 announce_interval=None,
                 retain_enabled=True,
                 ca_certs=None,
                 certfile=None,
                 keyfile=None):
        notifier_type = 'mqtt'
        super().__init__(notifier_id=notifier_id,
                         notifier_type=notifier_type,
                         space=space,
                         interval=interval,
                         timeout=timeout)
        self.host = host
        if port:
            self.port = port
        else:
            self.port = 1883
        self._port = port
        try:
            self.keepalive = int(keepalive)
        except:
            self.keepalive = 60
        self._keepalive = keepalive
        self.mq = mqtt.Client()
        self.mq.on_publish = self.on_publish_msg
        self.mq.on_connect = self.on_connect
        self.mq.on_message = self.on_message
        self.username = username
        self.password = password
        self.ca_certs = ca_certs
        self.certfile = certfile
        self.keyfile = keyfile
        self.retain_enabled = retain_enabled
        if ca_certs:
            try:
                if certfile and keyfile:
                    cf, kf = certfile, keyfile
                else:
                    cf, kf = None, None
                self.mq.tls_set(ca_certs=ca_certs, certfile=cf, keyfile=kf)
            except:
                eva.core.log_traceback(notifier=True)
                self.log_error(message='can not load ssl files')
                pass
        self.items_to_update = set()
        self.items_to_update_by_topic = {}
        self.items_to_control = set()
        self.items_to_control_by_topic = {}
        self.custom_handlers = {}
        self.custom_handlers_qos = {}
        if (username is not None and password is not None):
            self.mq.username_pw_set(username, password)
        if not qos:
            self.qos = {
                'state': default_mqtt_qos,
                'action': default_mqtt_qos,
                'log': default_mqtt_qos,
                'system': default_mqtt_qos
            }
        else:
            self.qos = qos
            if not 'state' in qos:
                self.qos['state'] = default_mqtt_qos
            if not 'action' in qos:
                self.qos['action'] = default_mqtt_qos
            if not 'log' in qos:
                self.qos['log'] = default_mqtt_qos
            if not 'system' in qos:
                self.qos['system'] = default_mqtt_qos
        self._qos = qos
        self.collect_logs = collect_logs
        if space is not None:
            pfx = space + '/'
        else:
            pfx = ''
        self.pfx = pfx
        self.pfx_api_response = pfx + 'controller/'
        self.log_topic = pfx + 'log'
        self.api_enabled = api_enabled
        self.discovery_enabled = discovery_enabled
        self.announce_interval = announce_interval
        import eva.core
        self.controller_topic = '{}controller/{}/{}/'.format(
            pfx, eva.core.product.code, eva.core.config.system_name)
        self.api_request_topic = self.controller_topic + 'api/request'
        self.api_response_topic = self.controller_topic + 'api/response'
        self.server_events_topic = self.controller_topic + 'events'
        self.announce_topic = self.pfx + 'controller/discovery'
        self.announce_msg = eva.core.product.code + \
                            '/' + eva.core.config.system_name
        import eva.api
        self.api_handler = eva.api.mqtt_api_handler
        self.discovery_handler = eva.api.controller_discovery_handler
        # dict of tuples (topic, handler)
        self.api_callback = {}
        self.api_callback_lock = threading.RLock()
        self.announcer = self.Announcer(name='mqtt_announcer:' +
                                        self.notifier_id,
                                        o=self,
                                        interval=self.announce_interval)
        self.handler_lock = threading.RLock()

    def connect(self):
        self.connected = True
        self.check_connection()

    def disconnect(self):
        super().disconnect()
        self.mq.loop_stop()
        self.mq.disconnect()
        self.announcer.stop()

    def on_connect(self, client, userdata, flags, rc):
        if eva.core.is_shutdown_requested():
            return
        logging.debug('.%s mqtt reconnect' % self.notifier_id)
        if self.announce_interval and not self.test_only_mode:
            self.announcer.start()
        if not self.api_callback_lock.acquire(timeout=eva.core.config.timeout):
            logging.critical('.GenericMQTTNotifier::on_connect locking broken')
            eva.core.critical()
            return False
        try:
            if not self.handler_lock.acquire(timeout=eva.core.config.timeout):
                logging.critical(
                    '.GenericMQTTNotifier::on_connect locking (2) broken')
                eva.core.critical()
                return False
            custom_handlers = self.custom_handlers.copy()
            custom_handlers_qos = self.custom_handlers_qos.copy()
        finally:
            self.handler_lock.release()
        try:
            for i, v in self.api_callback.items():
                client.subscribe(v[0], qos=self.qos['system'])
                logging.debug('.%s resubscribed to %s q%u API response' % \
                        (self.notifier_id, i, self.qos['system']))
            for i, v in self.items_to_update_by_topic.copy().items():
                client.subscribe(i, qos=v.mqtt_update_qos)
                logging.debug('.%s resubscribed to %s q%u topic' % \
                        (self.notifier_id, i, v.mqtt_update_qos))
            for i, v in self.items_to_control_by_topic.copy().items():
                client.subscribe(i, qos=v.mqtt_control_qos)
                logging.debug('.%s resubscribed to %s q%u control' % \
                        (self.notifier_id, i, v.mqtt_control_qos))
            for i in list(custom_handlers):
                qos = custom_handlers_qos.get(i)
                client.subscribe(i, qos=qos)
                logging.debug('.%s resubscribed to %s q%u custom' % \
                        (self.notifier_id, i, qos))
            if self.collect_logs:
                client.subscribe(self.log_topic, qos=self.qos['log'])
                logging.debug('.%s subscribed to %s' % \
                        (self.notifier_id, self.log_topic))
            if self.api_enabled:
                client.subscribe(self.api_request_topic, qos=self.qos['system'])
                logging.debug('.%s subscribed to %s' % \
                        (self.notifier_id, self.api_request_topic))
            if self.discovery_enabled:
                client.subscribe(self.announce_topic, qos=self.qos['system'])
                logging.debug('.%s subscribed to %s' % \
                        (self.notifier_id, self.announce_topic))
        except:
            eva.core.log_traceback(notifier=True)
        finally:
            self.api_callback_lock.release()

    def handler_append(self, topic, func, qos=None):
        if not self.handler_lock.acquire(timeout=eva.core.config.timeout):
            logging.critical(
                '.GenericMQTTNotifier::handler_append locking broken')
            eva.core.critical()
            return False
        try:
            if qos is None:
                qos = 1
            _topic = self.space + '/' + topic if \
                    self.space is not None else topic
            if not self.custom_handlers.get(_topic):
                self.custom_handlers[_topic] = set()
                self.custom_handlers_qos[_topic] = qos
                self.mq.subscribe(_topic, qos=qos)
                logging.debug('.%s subscribed to %s for handler' %
                              (self.notifier_id, _topic))
            self.custom_handlers[_topic].add(func)
            logging.debug('.%s new handler for topic %s: %s' %
                          (self.notifier_id, _topic, func))
        finally:
            self.handler_lock.release()

    def handler_remove(self, topic, func):
        if not self.handler_lock.acquire(timeout=eva.core.config.timeout):
            logging.critical(
                '.GenericMQTTNotifier::handler_remove locking broken')
            eva.core.critical()
            return False
        try:
            _topic = self.space + '/' + topic if \
                    self.space is not None else topic
            if _topic in self.custom_handlers:
                self.custom_handlers[_topic].remove(func)
                logging.debug('.%s removed handler for topic %s: %s' %
                              (self.notifier_id, _topic, func))
            if not self.custom_handlers.get(_topic):
                self.mq.unsubscribe(_topic)
                try:
                    del self.custom_handlers[_topic]
                except:
                    pass
                try:
                    del self.custom_handlers_qos[_topic]
                except:
                    pass
                logging.debug('.%s unsubscribed from %s, last handler left' %
                              (self.notifier_id, _topic))
        finally:
            self.handler_lock.release()

    def update_item_append(self, item):
        logging.debug('.%s subscribing to %s updates' % \
                (self.notifier_id, item.oid))
        self.items_to_update.add(item)
        for t in item.mqtt_update_topics:
            topic = self.pfx + item.item_type + '/' + \
                    item.full_id + (('/' + t) if t else '')
            self.items_to_update_by_topic[topic] = item
            self.mq.subscribe(topic, qos=item.mqtt_update_qos)
            logging.debug('.%s subscribed to %s q%u topic' %
                          (self.notifier_id, topic, item.mqtt_update_qos))
        return True

    def control_item_append(self, item):
        logging.debug('.%s subscribing to %s control' % \
                (self.notifier_id, item.oid))
        topic_control = self.pfx + item.item_type + '/' +\
                item.full_id + '/control'
        self.items_to_control.add(item)
        self.items_to_control_by_topic[topic_control] = item
        self.mq.subscribe(topic_control, qos=item.mqtt_control_qos)
        logging.debug('.%s subscribed to %s q%u topic' %
                      (self.notifier_id, topic_control, item.mqtt_control_qos))
        return True

    def update_item_remove(self, item):
        logging.debug('.%s unsubscribing from %s updates' % \
                (self.notifier_id, item.oid))
        if item not in self.items_to_update:
            return False
        try:
            for t in item.mqtt_update_topics:
                topic = self.pfx + item.item_type + '/' + \
                        item.full_id + (('/' + t) if t else '')
                self.mq.unsubscribe(topic)
                logging.debug('.%s unsubscribed from %s updates' %
                              (self.notifier_id, topic))
                del self.items_to_update_by_topic[topic]
            self.items_to_update.remove(item)
        except:
            eva.core.log_traceback(notifier=True)
        return True

    def control_item_remove(self, item):
        logging.debug('.%s unsubscribing from %s control' % \
                (self.notifier_id, item.oid))
        if item not in self.items_to_control:
            return False
        topic_control = self.pfx + item.item_type + '/' +\
                item.full_id + '/control'
        self.mq.unsubscribe(topic_control)
        try:
            self.items_to_control.remove(item)
            del self.items_to_control_by_topic[topic_control]
        except:
            eva.core.log_traceback(notifier=True)
            return False
        return True

    def update_item_exists(self, item):
        return item in self.items_to_update

    def control_item_exists(self, item):
        return item in self.items_to_control

    def exec_custom_handler(self, func, d, t, qos, retain):
        try:
            func(d, t, qos, retain)
        except:
            logging.error('.Unable to process topic ' + \
                            '%s with custom handler %s' % (t, func))
            eva.core.log_traceback(notifier=True)

    def on_message(self, client, userdata, msg):
        if not self.enabled:
            return
        t = msg.topic
        try:
            d = msg.payload if msg.payload.startswith(
                b'\x00') else msg.payload.decode()
        except:
            logging.warning('.Invalid message from MQTT server: {}'.format(
                msg.payload))
            eva.core.log_traceback(notifier=True)
            return
        try:
            if t == self.announce_topic and \
                    d != self.announce_msg and \
                    self.discovery_handler and \
                    not eva.core.is_setup_mode() and eva.core.is_started():
                eva.core.spawn(self.discovery_handler, self.notifier_id, d,
                               f'mqtt://{self.notifier_id}:{d}')
                return
            if t == self.api_request_topic and self.api_handler:
                eva.core.spawn(self.api_handler, self.notifier_id, d,
                               self.send_api_response)
                return
            if t.startswith(self.pfx_api_response):
                response_id = t.split('/')[-1]
                if response_id in self.api_callback:
                    eva.core.spawn(self.api_callback[response_id][1], d)
                    self.finish_api_request(response_id)
                    return
            hte = set()
            if not self.handler_lock.acquire(timeout=eva.core.config.timeout):
                logging.critical(
                    '.GenericMQTTNotifier::on_message locking broken')
                eva.core.critical()
                return False
            try:
                for ct in self.custom_handlers:
                    if mq_topic_match(t, ct):
                        for h in self.custom_handlers.get(ct, []):
                            hte.add(h)
            finally:
                self.handler_lock.release()
            for h in hte:
                eva.core.spawn(self.exec_custom_handler, h, d, t, msg.qos,
                               msg.retain)
            if self.collect_logs and t == self.log_topic:
                r = rapidjson.loads(d)
                if r['h'] != eva.core.config.system_name or \
                        r['p'] != eva.core.product.code:
                    pyaltt2.logs.append(rd=r, skip_mqtt=True)
            elif t in self.items_to_update_by_topic:
                i = self.items_to_update_by_topic[t]
                i.mqtt_set_state(
                    t[0 if not self.space else len(self.space) + 1:], d)
            elif t in self.items_to_control_by_topic:
                i = self.items_to_control_by_topic[t]
                i.mqtt_action(msg=d)
        except:
            eva.core.log_traceback(notifier=True)

    def on_publish_msg(self, client, userdata, mid):
        logging.debug('.Notification data #%u delivered to %s:%u' %
                      (mid, self.host, self.port))

    def check_connection(self):
        try:
            if self.mq._state != mqtt.mqtt_cs_connected:
                self.mq.loop_stop()
                if self.test_only_mode:
                    self.mq.enable_logger()
                self.mq.connect(host=self.host,
                                port=self.port,
                                keepalive=self.keepalive)
                self.mq.loop_start()
            return True
        except:
            eva.core.log_traceback(notifier=True)
            return False

    def send_notification(self, subject, data, retain=None, unpicklable=False):
        self.check_connection()
        if self.qos and subject == 'server' and 'system' in self.qos:
            qos = self.qos['system']
        elif self.qos and subject in self.qos:
            qos = self.qos[subject]
        else:
            qos = 1
        if subject == 'state':
            if retain is not None and self.retain_enabled:
                _retain = retain
            else:
                _retain = True if self.retain_enabled else False
            for i in data:
                if i.get('destroyed'):
                    dts = ''
                else:
                    dts = {
                        't': time.time(),
                        'c': eva.core.config.controller_name
                    }
                    for k in i:
                        if not k in ['id', 'group', 'type', 'full_id', 'oid']:
                            dts[k] = i[k]
                    dts = format_json(dts)
                self.mq.publish(self.pfx + i['type'] + '/' + i['group'] + '/' +
                                i['id'],
                                dts,
                                qos,
                                retain=_retain)
        elif subject == 'action':
            if retain is not None and self.retain_enabled:
                _retain = retain
            else:
                _retain = False
            for i in data:
                i['t'] = time.time()
                i['c'] = eva.core.config.controller_name
                self.mq.publish(self.pfx + i['item_type'] + '/' + \
                        i['item_group'] + '/' + i['item_id'] + '/action',
                    format_json(i, unpicklable=unpicklable),
                    qos, retain = _retain)
        elif subject == 'log':
            if retain is not None and self.retain_enabled:
                _retain = retain
            else:
                _retain = False
            for i in data:
                i['t'] = time.time()
                i['c'] = eva.core.config.controller_name
                self.mq.publish(self.log_topic,
                                format_json(i, unpicklable=False),
                                qos,
                                retain=_retain)
        elif subject == 'server':
            if retain is not None and self.retain_enabled:
                _retain = retain
            else:
                _retain = False
            for i in data:
                if not isinstance(i, dict):
                    i = {'e': i}
                i['t'] = time.time()
                i['c'] = eva.core.config.controller_name
                self.mq.publish(self.server_events_topic,
                                format_json(i, unpicklable=False),
                                qos,
                                retain=_retain)

    def send_message(self, topic, data, retain=None, qos=1, use_space=True):
        self.check_connection()
        if isinstance(data, list):
            _data = data
        else:
            _data = [data]
        if retain is not None:
            _retain = retain
        else:
            _retain = False
        for d in _data:
            if isinstance(d, dict):
                _d = format_json(data, unpicklable=False)
            else:
                _d = d
            if use_space and self.space is not None:
                _topic = self.space + '/' + topic
            else:
                _topic = topic
            try:
                self.mq.publish(_topic, _d, qos, retain=_retain)
                return True
            except:
                eva.core.log_traceback(notifier=True)
                return False

    def send_api_response(self, call_id, data):
        if not self.api_enabled:
            return False
        self.mq.publish(self.api_response_topic + '/' + call_id,
                        data,
                        self.qos['system'],
                        retain=False)
        return True

    def send_api_request(self, request_id, controller_id, data, callback):
        if request_id in self.api_callback:
            logging.error('.GenericMQTTNotifier: duplicate API request ID')
            return False
        if not self.api_callback_lock.acquire(timeout=eva.core.config.timeout):
            logging.critical(
                '.GenericMQTTNotifier::api_callback locking broken')
            eva.core.critical()
            return False
        try:
            t = '{}controller/{}/api/response/{}'.format(
                self.pfx, controller_id, request_id)
            self.api_callback[request_id] = (t, callback)
        finally:
            self.api_callback_lock.release()
        self.mq.subscribe(t, qos=self.qos['system'])
        return self.send_message('controller/' + controller_id + '/api/request',
                                 data,
                                 qos=self.qos['system'])

    def finish_api_request(self, request_id):
        if request_id not in self.api_callback:
            logging.warning('.GenericMQTTNotifier: API request ID not found')
            return False
        if not self.api_callback_lock.acquire(timeout=eva.core.config.timeout):
            logging.critical(
                '.GenericMQTTNotifier::api_callback locking broken')
            eva.core.critical()
            return False
        try:
            t = self.api_callback[request_id][0]
            del self.api_callback[request_id]
            self.mq.unsubscribe(t)
        finally:
            self.api_callback_lock.release()

    def test(self):
        try:
            logging.debug('.Testing mqtt notifier %s (%s:%u)' % \
                    (self.notifier_id,self.host, self.port))
            if not self.check_connection():
                return False
            result = self.mq.publish(self.pfx + 'test',
                                     1,
                                     qos=self.qos['system'],
                                     retain=False)
            result = eva.core.wait_for(result.is_published, self.get_timeout())
            if self.test_only_mode:
                self.disconnect()
            return result
        except:
            eva.core.log_traceback(notifier=True)
            return False

    def log_notify(self):
        logging.debug('.sending data notification to ' + \
                '%s method = %s, server: %s:%u' % \
                            (self.notifier_id,
                           self.notifier_type, self.host,
                           self.port))

    def serialize(self, props=False):
        d = {}
        if self.host or props:
            d['host'] = self.host
        if self._port or props:
            d['port'] = self._port
        if self.username or props:
            d['username'] = self.username
        if self.password or props:
            d['password'] = self.password
        if self._qos or props:
            d['qos'] = self._qos
        if self._keepalive or props:
            d['keepalive'] = self._keepalive
        if self.collect_logs or props:
            d['collect_logs'] = self.collect_logs
        if self.api_enabled or props:
            d['api_enabled'] = self.api_enabled
        if self.discovery_enabled or props:
            d['discovery_enabled'] = self.discovery_enabled
        if self.announce_interval or props:
            d['announce_interval'] = self.announce_interval
        if self.ca_certs or props:
            d['ca_certs'] = self.ca_certs
        if self.certfile or props:
            d['certfile'] = self.certfile
        if self.keyfile or props:
            d['keyfile'] = self.keyfile
        d['retain_enabled'] = self.retain_enabled
        d.update(super().serialize(props=props))
        return d

    def set_prop(self, prop, value):
        if prop == 'collect_logs':
            v = eva.tools.val_to_boolean(value)
            self.collect_logs = v
            return True
        elif prop == 'api_enabled':
            v = eva.tools.val_to_boolean(value)
            self.api_enabled = v
            return True
        elif prop == 'discovery_enabled':
            v = eva.tools.val_to_boolean(value)
            self.discovery_enabled = v
            return True
        elif prop == 'announce_interval':
            if value is None:
                announce_interval = 0
            else:
                try:
                    announce_interval = float(value)
                except:
                    return False
            if announce_interval < 0:
                return False
            self.announce_interval = announce_interval
            return True
        elif prop == 'ca_certs':
            if value is None:
                self.ca_certs = None
            elif os.path.isfile(value):
                self.ca_certs = value
            else:
                self.log_error(message='unable to open ' + value)
                return False
            return True
        elif prop == 'certfile':
            if value is None:
                self.certfile = None
            elif os.path.isfile(value):
                self.certfile = value
            else:
                self.log_error(message='unable to open ' + value)
                return False
            return True
        elif prop == 'keyfile':
            if value is None:
                self.keyfile = None
            elif os.path.isfile(value):
                self.keyfile = value
            else:
                self.log_error(message='unable to open ' + value)
                return False
            return True
        elif prop == 'host':
            if not value:
                return False
            self.host = value
            return True
        elif prop == 'port':
            if not value:
                self._port = None
                return True
            try:
                self._port = int(value)
            except:
                return False
            return True
        elif prop == 'keepalive':
            if not value:
                self._keepalive = None
                return True
            try:
                self._keepalive = int(value)
            except:
                return False
            return True
        elif prop == 'username':
            self.username = value
            return True
        elif prop == 'password':
            self.password = value
            return True
        elif prop == 'retain_enabled':
            v = val_to_boolean(value)
            if v is None:
                return False
            self.retain_enabled = v
            return True
        elif prop == 'qos':
            if not value:
                self._qos = None
                return True
            try:
                val = int(value)
            except:
                return False
            if not 0 <= val <= 2:
                return False
            self._qos = {'action': val, 'state': val, 'log': val, 'system': val}
            return True
        elif prop[:4] == 'qos.':
            q = prop[4:]
            if not q in ['action', 'state', 'log', 'system']:
                return False
            if not value:
                if self._qos and q in self._qos:
                    del self._qos[q]
                return True
            try:
                val = int(value)
            except:
                return False
            if not 0 <= val <= 2:
                return False
            if not self._qos:
                self._qos = {}
            self._qos[q] = val
            return True
        else:
            return super().set_prop(prop, value)


class MQTTNotifier(GenericMQTTNotifier):

    def __init__(self,
                 notifier_id,
                 host,
                 port=None,
                 space=None,
                 interval=None,
                 username=None,
                 password=None,
                 qos=None,
                 keepalive=None,
                 timeout=None,
                 collect_logs=None,
                 api_enabled=None,
                 discovery_enabled=None,
                 announce_interval=None,
                 retain_enabled=True,
                 ca_certs=None,
                 certfile=None,
                 keyfile=None):
        super().__init__(notifier_id=notifier_id,
                         host=host,
                         port=port,
                         space=space,
                         interval=interval,
                         username=username,
                         password=password,
                         qos=qos,
                         keepalive=keepalive,
                         timeout=timeout,
                         collect_logs=collect_logs,
                         api_enabled=api_enabled,
                         discovery_enabled=discovery_enabled,
                         announce_interval=announce_interval,
                         retain_enabled=retain_enabled,
                         ca_certs=ca_certs,
                         certfile=certfile,
                         keyfile=keyfile)


class GCP_IoT(GenericNotifier):

    def __init__(self,
                 notifier_id,
                 keepalive=None,
                 timeout=None,
                 interval=None,
                 apikey=None,
                 ca_certs=None,
                 keyfile=None,
                 mapfile=None,
                 project=None,
                 region=None,
                 registry=None,
                 token_expire=None):

        notifier_type = 'gcpiot'
        super().__init__(notifier_id=notifier_id,
                         notifier_type=notifier_type,
                         timeout=timeout,
                         interval=interval)
        try:
            self.keepalive = int(keepalive)
        except:
            self.keepalive = 60
        self._keepalive = keepalive
        self.apikey = apikey
        self.ca_certs = ca_certs
        self.keyfile = keyfile
        self.mapfile = mapfile
        self.project = project
        self.region = region
        self.registry = registry
        self.host = 'mqtt.googleapis.com'
        self.port = 8883
        try:
            self.token_expire = int(token_expire)
            if self.token_expire > 300:
                self.token_expire = 300
        except:
            self.token_expire = 300
        self._token_expire = token_expire
        self.lock = threading.Lock()
        self.mq = None
        self.mq_connected = threading.Event()
        self.map_rev = {}
        try:
            with open(self.mapfile) as fd:
                self.map = yaml.load(fd.read())
            for k, v in self.map.items():
                self.map_rev[v] = k
        except:
            self.map = None
        self.error_topic = '/devices/{}/errors'.format(self.notifier_id)
        self.command_topic = '/devices/{}/commands/#'.format(self.notifier_id)

    @background_worker
    def reset_connection(o, **kwargs):
        o.check_connection(reconnect=True)

    def connect(self):
        self.connected = True
        self.check_connection()

    def start(self):
        super().start()
        if not self.test_only_mode:
            if self.map is None:
                self.log_error(message='map file not specified or invalid')
            self.reset_connection.start(delay=self.token_expire -
                                        self.get_timeout(),
                                        o=self)

    def stop(self):
        if not self.test_only_mode:
            self.reset_connection.stop()
        super().stop()

    def disconnect(self, full=True, lock=True):
        if lock:
            if not self.lock.acquire(timeout=self.get_timeout()):
                self.log_error(message='disconnect failed')
                return False
        try:
            if full:
                super().disconnect()
            if self.mq:
                self.mq.loop_stop()
                self.mq.disconnect()
        finally:
            if lock:
                self.lock.release()

    def create_jwt(self):
        token = {
            'iat': time.time(),
            'exp': time.time() + self.token_expire,
            'aud': self.project
        }
        try:
            import jwt
            with open(self.keyfile, 'r') as f:
                private_key = f.read()
            return jwt.encode(token, private_key, algorithm='RS256')
        except:
            self.log_error(message='unable to encode token, key file: {}'.
                           format(self.keyfile))

    def on_message(self, client, userdata, msg):
        t = msg.topic
        try:
            d = msg.payload.decode()
        except:
            logging.warning('.Invalid message from MQTT server: {}'.format(
                msg.payload))
            import eva.core
            eva.core.log_traceback()
            return
        if t == self.error_topic:
            self.log_error(message=d)
            return
        if not self.enabled:
            return
        x = t.split('/')
        if 'commands' in x:
            dev = x[2]
            try:
                payload = rapidjson.loads(d)
                if 'params' not in payload or not isinstance(
                        payload['params'], dict):
                    payload['params'] = {}
                if dev != self.notifier_id:
                    i = payload['params'].get('i')
                    if i is not None:
                        if i != dev:
                            raise Exception(
                                'item ID should not be specified for item cmd')
                    else:
                        payload['params']['i'] = dev
                    item = self.map.get(payload['params']['i'])
                    if not item:
                        logging.warning('.{}: item not mapped {}'.format(
                            self.notifier_id, payload['params']['i']))
                        raise Exception('Item not mapped')
                    payload['params']['i'] = item
                if 'k' not in payload['params']:
                    import eva.apikey
                    payload['params']['k'] = eva.apikey.format_key(self.apikey)
                import eva.api
                import eva.core
                g.set('eva_ics_gw', 'gcpiot:' + self.notifier_id)
                eva.core.spawn(eva.api.jrpc, p=payload)
            except:
                logging.warning(
                    '.Invalid command message from MQTT server: {}'.format(
                        msg.payload))
                import eva.core
                eva.core.log_traceback()
                return

    def check_connection(self, reconnect=False):
        if self.map is None:
            self.log_error(message='No map file provided')
            return False
        if not self.lock.acquire(timeout=self.get_timeout()):
            self.log_error(message='Locking failed')
            return False
        try:
            if self.mq and not reconnect:
                mq = self.mq
                first_connect = False
            else:
                first_connect = True
                self.mq_connected.clear()
                mq = mqtt.Client(client_id=(
                    'projects/{}/locations/{}/registries/{}/devices/{}'.format(
                        self.project, self.region, self.registry,
                        self.notifier_id)))
                mq.tls_set(ca_certs=self.ca_certs,
                           tls_version=ssl.PROTOCOL_TLSv1_2)
                mq.username_pw_set(username='unused',
                                   password=self.create_jwt())
                mq.on_connect = self.on_connect
                mq.on_message = self.on_message
                if self.test_only_mode:
                    mq.enable_logger()
            if first_connect or mq._state != mqtt.mqtt_cs_connected:
                if not first_connect:
                    mq.loop_stop()
                mq.connect(host=self.host,
                           port=self.port,
                           keepalive=self.keepalive)
                mq.loop_start()
                if not self.mq_connected.wait(timeout=self.get_timeout()):
                    raise Exception('Connection timeout')
                # sleep until attached
                time.sleep(3)
                for i in self.map:
                    mq.subscribe('/devices/{}/commands/#'.format(i))
                if reconnect:
                    self.disconnect(full=False, lock=False)
                self.mq = mq
            return True
        except:
            eva.core.log_traceback(notifier=True)
            return False
        finally:
            self.lock.release()

    def send_notification(self, subject, data, retain=None, unpicklable=False):
        if not self.check_connection():
            self.log_error(message='connection failed')
            return
        if subject == 'state':
            for d in data:
                if not d.get('destroyed'):
                    oid = d.get('oid')
                    dev = self.map_rev.get(oid)
                    if not dev:
                        logging.warning('.{}: no mapping for {}'.format(
                            self.notifier_id, oid))
                        continue
                    payload = {}
                    try:
                        status = int(d.get('status'))
                    except:
                        eva.core.log_traceback()
                        return
                    value = d.get('value')
                    if value:
                        try:
                            value = float(value)
                        except:
                            try:
                                value = jsonpikcle.decode(value)
                            except:
                                pass
                    elif value == '':
                        value = None
                    payload['status'] = status
                    payload['value'] = value
                    if not self.lock.acquire(timeout=self.get_timeout()):
                        self.log_error(message='Unable to get MQTT lock')
                        return
                    try:
                        if not self.mq:
                            self.log_error(message='not connected')
                        else:
                            self.mq.publish('/devices/{}/events'.format(dev),
                                            format_json(payload))
                    finally:
                        self.lock.release()

    def on_connect(self, client, userdata, flags, rc):
        logging.debug('.%s mqtt reconnect' % self.notifier_id)
        self.mq_connected.set()
        client.subscribe(self.error_topic)
        client.subscribe(self.command_topic)
        if self.map:
            for i in self.map:
                client.publish('/devices/{}/attach'.format(i),
                               format_json({'authorization': ''}))

    def test(self):
        result = self.check_connection()
        if self.test_only_mode:
            self.disconnect()
        return result

    def serialize(self, props=False):
        d = {}
        if self._keepalive or props:
            d['keepalive'] = self._keepalive
        if self.apikey or props:
            d['apikey'] = self.apikey
        if self.ca_certs or props:
            d['ca_certs'] = self.ca_certs
        if self.keyfile or props:
            d['keyfile'] = self.keyfile
        if self.mapfile or props:
            d['mapfile'] = self.mapfile
        if self.project or props:
            d['project'] = self.project
        if self.region or props:
            d['region'] = self.region
        if self.registry or props:
            d['registry'] = self.registry
        if self._token_expire or props:
            d['token_expire'] = self._token_expire
        d.update(super().serialize(props=props))
        if 'space' in d:
            del d['space']
        return d

    def set_prop(self, prop, value):
        if prop == 'keepalive':
            if not value:
                self._keepalive = None
                return True
            try:
                self._keepalive = int(value)
            except:
                return False
            return True
        elif prop == 'apikey':
            self.apikey = value
            return True
        elif prop == 'ca_certs':
            if value is None:
                self.ca_certs = None
            elif os.path.isfile(value):
                self.ca_certs = value
            else:
                self.log_error(message='unable to open ' + value)
                return False
            return True
        elif prop == 'keyfile':
            if value is None:
                self.keyfile = None
            elif os.path.isfile(value):
                self.keyfile = value
            else:
                self.log_error(message='unable to open ' + value)
                return False
            return True
        elif prop == 'mapfile':
            if value is None:
                self.mapfile = None
            elif os.path.isfile(value):
                self.mapfile = value
            else:
                self.log_error(message='unable to open ' + value)
                return False
            return True
        elif prop == 'project':
            self.project = value
            return True
        elif prop == 'region':
            self.region = value
            return True
        elif prop == 'registry':
            self.registry = value
            return True
        if prop == 'token_expire':
            if not value:
                self._token_expire = None
                return True
            try:
                self._token_expire = int(value)
            except:
                return False
            return True
        else:
            return super().set_prop(prop, value)


class WSNotifier_Client(GenericNotifier_Client):

    def __init__(self,
                 notifier_id=None,
                 apikey=None,
                 token=None,
                 ws=None,
                 ct=CT_JSON):
        super().__init__(notifier_id, 'ws', apikey, token)
        self.ws = ws
        pm = {'s': 'pong'}
        self.ws.pong_message = rapidjson.dumps(
            pm) if ct == CT_JSON else pack_msgpack(pm)
        self.ct = ct
        if self.ws:
            self.ws.notifier = self
            self.connected = True

    def send_notification(self, subject, data, retain=None, unpicklable=False):
        if not self.is_client_dead() and self.connected:
            try:
                msg = {'s': subject, 'd': data}
                logging.debug('.notifying WS %s' % self.notifier_id)
                if self.ct == CT_JSON:
                    data = format_json(msg, unpicklable=unpicklable)
                else:
                    data = pack_msgpack(msg)
                self.ws.send(data, binary=self.ct == CT_MSGPACK)
            except:
                eva.core.log_traceback(notifier=True)

    def send_reload(self):
        self.send_notification('reload', 'asap')

    def is_client_dead(self):
        if self.ws:
            return self.ws.terminated
        else:
            return False

    def disconnect(self):
        super().disconnect()
        self.ws.close()


class NWebSocket(WebSocket):

    def __init__(self,
                 sock,
                 protocols=None,
                 extensions=None,
                 environ=None,
                 heartbeat_freq=None):
        self.notifier = None
        return super().__init__(sock, protocols, extensions, environ,
                                heartbeat_freq)

    def opened(self):
        logging.debug('.WS opened %s:%u' % \
                (self.peer_address[0], self.peer_address[1]))
        if self.notifier:
            self.notifier.register()
        return super().opened()

    def received_message(self, message):
        s_all = ['#']
        try:
            if self.notifier.ct == CT_MSGPACK:
                data = msgpack.loads(message.data, raw=False)
            else:
                data = rapidjson.loads(message.data.decode())
            subject = data['s']
            if subject == 'bye':
                self.close()
                return
            elif subject == 'ping':
                self.send(self.pong_message,
                          binary=self.notifier.ct == CT_MSGPACK)
            elif subject == 'u' and self.notifier:
                topic = data['t']
                if isinstance(topic, list):
                    for t in topic:
                        self.notifier.unsubscribe(t)
                else:
                    self.notifier.unsubscribe(topic)
                return
            elif self.notifier:
                if 'l' in data:
                    log_level = int(data['l'])
                else:
                    log_level = 20
                if 'i' in data:
                    items = data['i']
                else:
                    items = s_all
                if 'g' in data:
                    groups = data['g']
                else:
                    groups = s_all
                if 'tp' in data:
                    item_types = data['tp']
                else:
                    item_types = s_all
                if 'a' in data:
                    action_status = data['a']
                else:
                    action_status = s_all
                self.notifier.subscribe(subject,
                                        items=items,
                                        groups=groups,
                                        item_types=item_types,
                                        action_status=action_status,
                                        log_level=log_level)
        except:
            logging.debug('.WS %s:%u got invalid JSON data: %s' % \
                    (self.peer_address[0], self.peer_address[1],
                        message.data.decode()))

    def closed(self, code, reason=None):
        logging.debug('.WS closed %s:%u' % \
                (self.peer_address[0], self.peer_address[1]))
        if self.notifier:
            self.notifier.unregister()


def append_notifier(notifier):
    notifiers[notifier.notifier_id] = notifier
    return True


def remove_notifier(notifier_id):
    if notifier_id in notifiers:
        try:
            del notifiers[notifier_id]
        except:
            return False
    return True


def load_notifier(notifier_id, fname=None, test=True, connect=True):
    if not notifier_id and not fname:
        return None
    if not fname:
        notifier_fname = eva.core.format_cfg_fname('%s_notify.d/%s.json' % \
                (eva.core.product.code, notifier_id), runtime = True)
    else:
        notifier_fname = fname
    if not notifier_id:
        _notifier_id = os.path.splitext(os.path.basename(notifier_fname))[0]
    else:
        _notifier_id = notifier_id
    with open(notifier_fname) as fd:
        ncfg = rapidjson.loads(fd.read())
    if ncfg['id'] != _notifier_id:
        raise Exception('notifier id mismatch, file %s' % \
                notifier_fname)
    if ncfg['type'] == 'mqtt':
        host = ncfg.get('host')
        port = ncfg.get('port')
        ca_certs = ncfg.get('ca_certs')
        certfile = ncfg.get('certfile')
        keyfile = ncfg.get('keyfile')
        space = ncfg.get('space')
        username = ncfg.get('username')
        password = ncfg.get('password')
        qos = ncfg.get('qos')
        keepalive = ncfg.get('keepalive')
        timeout = ncfg.get('timeout')
        interval = ncfg.get('interval')
        collect_logs = ncfg.get('collect_logs', False)
        api_enabled = ncfg.get('api_enabled', False)
        discovery_enabled = ncfg.get('discovery_enabled', False)
        announce_interval = ncfg.get('announce_interval', 0)
        retain_enabled = ncfg.get('retain_enabled', True)
        n = MQTTNotifier(_notifier_id,
                         host=host,
                         port=port,
                         space=space,
                         interval=interval,
                         username=username,
                         password=password,
                         qos=qos,
                         keepalive=keepalive,
                         timeout=timeout,
                         collect_logs=collect_logs,
                         api_enabled=api_enabled,
                         discovery_enabled=discovery_enabled,
                         announce_interval=announce_interval,
                         retain_enabled=retain_enabled,
                         ca_certs=ca_certs,
                         certfile=certfile,
                         keyfile=keyfile)
    elif ncfg['type'] == 'gcpiot':
        keepalive = ncfg.get('keepalive')
        timeout = ncfg.get('timeout')
        interval = ncfg.get('interval')
        token_expire = ncfg.get('token_expire')
        ca_certs = ncfg.get('ca_certs')
        keyfile = ncfg.get('keyfile')
        mapfile = ncfg.get('mapfile')
        project = ncfg.get('project')
        region = ncfg.get('region')
        registry = ncfg.get('registry')
        apikey = ncfg.get('apikey')
        n = GCP_IoT(_notifier_id,
                    keepalive=keepalive,
                    timeout=timeout,
                    interval=interval,
                    apikey=apikey,
                    ca_certs=ca_certs,
                    keyfile=keyfile,
                    mapfile=mapfile,
                    project=project,
                    region=region,
                    registry=registry,
                    token_expire=token_expire)
    elif ncfg['type'] == 'db':
        db = ncfg.get('db')
        keep = ncfg.get('keep')
        space = ncfg.get('space')
        interval = ncfg.get('interval')
        n = SQLANotifier(_notifier_id,
                         db_uri=db,
                         keep=keep,
                         space=space,
                         interval=interval)
    elif ncfg['type'] == 'http-json':
        space = ncfg.get('space')
        ssl_verify = ncfg.get('ssl_verify')
        uri = ncfg.get('uri')
        notify_key = ncfg.get('notify_key')
        timeout = ncfg.get('timeout')
        interval = ncfg.get('interval')
        method = ncfg.get('method')
        username = ncfg.get('username')
        password = ncfg.get('password')
        n = HTTP_JSONNotifier(_notifier_id,
                              ssl_verify=ssl_verify,
                              uri=uri,
                              username=username,
                              password=password,
                              method=method,
                              notify_key=notify_key,
                              space=space,
                              interval=interval,
                              timeout=timeout)
    elif ncfg['type'] == 'influxdb':
        space = ncfg.get('space')
        db = ncfg.get('db')
        ssl_verify = ncfg.get('ssl_verify')
        uri = ncfg.get('uri')
        timeout = ncfg.get('timeout')
        interval = ncfg.get('interval')
        method = ncfg.get('method')
        username = ncfg.get('username')
        password = ncfg.get('password')
        n = InfluxDB_Notifier(_notifier_id,
                              ssl_verify=ssl_verify,
                              uri=uri,
                              db=db,
                              username=username,
                              password=password,
                              method=method,
                              space=space,
                              interval=interval,
                              timeout=timeout)
    elif ncfg['type'] == 'prometheus':
        space = ncfg.get('space')
        username = ncfg.get('username')
        password = ncfg.get('password')
        n = PrometheusNotifier(_notifier_id,
                               username=username,
                               password=password)
    else:
        logging.error('Invalid notifier type = %s' % ncfg['type'])
        return None
    skip_test = ncfg.get('skip_test')
    n._skip_test = skip_test
    if ncfg.get('enabled'):
        n.enabled = True
        if not skip_test and test:
            if n.test():
                logging.info(
                    'notifier %s (%s) test passed' % \
                        (_notifier_id, n.notifier_type))
            else:
                logging.error(
                    'notifier %s (%s) test failed' % \
                        (_notifier_id, n.notifier_type))
        elif connect:
            n.connect()
    for e in ncfg.get('events', []):
        subject = e['subject']
        log_level = e.get('level')
        items = e.get('items', [])
        groups = e.get('groups', [])
        item_types = e.get('types', [])
        action_status = e.get('action_status', [])
        n.subscribe(subject,
                    items=items,
                    groups=groups,
                    item_types=item_types,
                    action_status=action_status,
                    log_level=log_level)
    return n


def get_notifier_fnames():
    fnames = eva.core.format_cfg_fname(eva.core.product.code + \
            '_notify.d/*.json', runtime = True)
    return glob.glob(fnames)


def load(test=True, connect=False):
    logging.info('Loading notifiers')
    notifiers.clear()
    try:
        for notifier_fname in get_notifier_fnames():
            try:
                n = load_notifier(notifier_id=None,
                                  fname=notifier_fname,
                                  test=test,
                                  connect=connect)
                if not n:
                    raise Exception('Notifier load error')
                notifiers[n.notifier_id] = n
                logging.debug('+ notifier %s' % n.notifier_id)
            except:
                logging.error('Can not load notifier from %s' % notifier_fname)
                eva.core.log_traceback(notifier=True)
    except:
        logging.error('Notifiers load error')
        eva.core.log_traceback(notifier=True)
        return False
    # exec custom load for notifiers
    for i, n in notifiers.copy().items():
        try:
            n.load_config()
        except:
            logging.error('can not load notifier\'s config for %s' % i)
    return True


def serialize(notifier_id=None):
    if notifier_id:
        return notifiers[notifier_id].serialize()
    d = {}
    for i, n in notifiers.copy().items():
        d[i] = n.serialize()
    return d


def save_notifier(notifier_id):
    fname_full = eva.core.format_cfg_fname(eva.core.product.code + \
            '_notify.d/%s.json' % notifier_id, runtime = True)
    try:
        data = notifiers[notifier_id].serialize()
        with open(fname_full, 'w') as fd:
            fd.write(format_json(data, minimal=False))
    except:
        logging.error('can not save notifiers config into %s' % fname_full)
        eva.core.log_traceback(notifier=True)
        return False


def save(notifier_id=None):
    if notifier_id:
        n = notifiers[notifier_id]
        if isinstance(n, HTTP_JSONNotifier) or \
            isinstance(n, MQTTNotifier) or \
            isinstance(n, SQLANotifier):
            save_notifier(notifier_id)
        else:
            try:
                n.save_config()
            except:
                logging.error('can not save notifier\'s config for %s' % i)
    else:
        for i, n in notifiers.copy().items():
            if i and not n.nt_client:
                save(i)


def __push_notification(notifier, subject, data, retain):
    try:
        logging.debug('.notify %s' % notifier.notifier_id)
        notifier.notify(subject, data, retain=retain)
    except:
        logging.error('.Can not notify %s' % notifier.notifier_id)
        eva.core.log_traceback(notifier=True)


def notify(subject,
           data,
           notifier_id=None,
           retain=None,
           skip_subscribed_mqtt_item=None,
           skip_mqtt=False):
    if notifier_id:
        try:
            if skip_mqtt and \
                    notifiers[notifier_id].notifier_type[:4] == 'mqtt':
                return
            if skip_subscribed_mqtt_item and \
                notifiers[notifier_id].notifier_type[:4] == 'mqtt' and \
                notifiers[notifier_id].update_item_exists(
                        skip_subscribed_mqtt_item
                        ):
                return
            __push_notification(notifiers[notifier_id], subject, data, retain)
        except:
            eva.core.log_traceback(notifier=True)
    else:
        if subject == 'state':
            eva.core.exec_corescripts(event=SimpleNamespace(
                type=eva.core.CS_EVENT_STATE, source=data[0], data=data[1]))
        for i in list(notifiers):
            try:
                if notifiers[i].can_notify():
                    notify(subject=subject,
                           data=data,
                           notifier_id=i,
                           retain=retain,
                           skip_subscribed_mqtt_item=skip_subscribed_mqtt_item,
                           skip_mqtt=skip_mqtt)
            except KeyError:
                pass


def get_notifier(notifier_id=None, get_default=True):
    return notifiers.get(notifier_id) if \
        notifier_id is not None else \
            (get_default_notifier() if get_default else None)


def get_default_notifier():
    return notifiers.get(default_notifier_id)


def get_stats_notifier(notifier_id):
    if notifier_id is None:
        return get_notifier(default_stats_notifier_id)
    n = get_notifier(notifier_id)
    return n if n and n.state_storage else None


def get_notifiers():
    result = []
    for i, n in notifiers.copy().items():
        if not n.nt_client:
            result.append(n)
    return result


def unsubscribe_item(item, subject='#', notifier_id=None):
    if notifier_id:
        notifiers[notifier_id].unsubscribe_item(subject, item)
    else:
        for i in notifiers.copy():
            unsubscribe_item(item, subject, i)


def unsubscribe_group(group, subject='#', notifier_id=None):
    if notifier_id:
        notifiers[notifier_id].unsubscribe_group(subject, group)
    else:
        for i in notifiers.copy():
            unsubscribe_group(group, subject, i)


@eva.core.dump
def dump(notifier_id=None):
    if notifier_id:
        return notifiers[notifier_id].serialize()
    return serialize()


def start():
    notifier_client_cleaner.start()
    th = []
    for i, n in notifiers.copy().items():
        if n.enabled:
            th.append(threading.Thread(target=n.start, daemon=True))
    time_start = time.time()
    [t.start() for t in th]
    while time_start + eva.core.config.timeout > time.time():
        can_break = True
        for t in th:
            if t.is_alive():
                can_break = False
                break
        if can_break:
            break
        time.sleep(eva.core.sleep_step)
    eva.core.register_corescript_topics()


@eva.core.stop
def stop():
    for i, n in notifiers.copy().items():
        n.stop()
    notifier_client_cleaner.stop()


def is_action_subscribed():
    return _flags.action_subscribed


def reload_clients():
    logging.warning('sending reload event to clients')
    for k, n in notifiers.copy().items():
        if n.nt_client:
            n.send_reload()


@eva.core.shutdown
def notify_restart():
    logging.warning('sending server restart event')
    notify('server', 'restart')
    # make sure event is queued
    if eva.core.is_shutdown_requested():
        time.sleep(0.2)


@eva.core.shutdown
def notify_leaving():
    if not notify_leave_data:
        return
    for n in notify_leave_data:
        logging.warning('Sending leaving event to {}'.format(n.notifier_id))
        n.notify('server', 'leaving')
    # make sure event is queued
    time.sleep(0.2)


@with_notify_lock
def mark_leaving(n):
    notify_leave_data.add(n)


@background_worker(delay=notifier_client_clean_delay,
                   name='notify:client_cleaner',
                   on_error=eva.core.log_traceback)
async def notifier_client_cleaner(**kwargs):
    for k, n in notifiers.copy().items():
        if n.nt_client:
            n.cleanup()


def init():
    pass
