__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.1.2"

import logging
import eva.core
import eva.item
import jsonpickle
import requests
import paho.mqtt.client as mqtt
import time
from datetime import datetime
from queue import Queue
import dateutil.parser
import pytz
import glob
import os
import sys
import uuid
import threading
import sqlalchemy as sa

from sqlalchemy import text as sql

from pyaltt import BackgroundWorker
from pyaltt import BackgroundQueueWorker
from pyaltt import background_worker
from pyaltt import background_job
from pyaltt import g

from eva import apikey
from eva.tools import format_json
from eva.tools import val_to_boolean

from ws4py.websocket import WebSocket

default_log_level = 20

notifier_client_clean_delay = 30

default_mqtt_qos = 1

sqlite_default_keep = 86400
sqlite_default_id = 'db_1'

default_notifier_id = 'eva_1'

logging.getLogger('requests').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)

notifiers = {}

action_subscribed = False

_ne_kw = {'notifier': True}


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
        if isinstance(groups, list): self.groups = groups
        elif groups: self.groups = [groups]
        else: self.groups = []
        if isinstance(item_types, list): self.item_types = item_types
        elif item_types: self.item_types = [item_types]
        else: self.item_types = []
        self.item_ids = set()
        if isinstance(items, list):
            for i in items:
                if isinstance(i, str): self.item_ids.add(i)
                else: self.item_ids.add(i.item_id)
        else:
            if isinstance(items, str): self.item_ids.add(items)
            elif items: self.item_ids.add(items.item_id)

    def append_item(self, item):
        if isinstance(item, str): self.item_ids.add(item)
        else: self.item_ids.add(item.item_id)

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
        if self.item_ids: d['items'] = list(self.item_ids)
        if self.groups: d['groups'] = self.groups
        if self.item_types: d['types'] = self.item_types
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
        if self.action_status: d['action_status'] = self.action_status
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
        if (self.log_level): d['level'] = self.log_level
        d.update(super().serialize())
        return d


class GenericNotifier(object):

    class NotifierWorker(BackgroundQueueWorker):

        def __init__(self, name=None, **kwargs):
            super().__init__(
                name=name,
                on_error=eva.core.log_traceback,
                on_error_kwargs=_ne_kw,
                **kwargs)

        def run(self, event, o, **kwargs):
            o.send_notification(
                subject=event[0],
                data=event[1],
                retain=event[2],
                unpicklable=event[3])

    def __init__(self,
                 notifier_id,
                 notifier_type=None,
                 space=None,
                 timeout=None):
        self.notifier_id = notifier_id
        self.notifier_type = notifier_type
        self.space = space
        self.events = set()
        self.timeout = timeout
        self.enabled = False
        self.test_only_mode = False
        self.connected = False
        self.nt_client = False
        self._skip_test = None
        self.last_state_event = {}
        self.lse_lock = threading.RLock()
        self.notifier_worker = self.NotifierWorker(
            o=self, name='notifier_' + self.notifier_id)

    def subscribe(self,
                  subject,
                  items=[],
                  groups=[],
                  item_types=[],
                  action_status=[],
                  log_level=None):
        global action_subscribed
        _e = self.is_subscribed(subject)
        if subject == 'state':
            if _e: self.events.remove(_e)
            e = EventState(items=items, groups=groups, item_types=item_types)
            self.events.add(e)
        elif subject == 'action':
            if _e: self.events.remove(_e)
            e = EventAction(
                items=items,
                groups=groups,
                item_types=item_types,
                action_status=action_status)
            self.events.add(e)
            if self.enabled:
                action_subscribed = True
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
        else:
            return False
        return True

    def is_subscribed(self, subject):
        for e in self.events.copy():
            if e.subject == subject: return e
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
                    if e.subject == subject: self.events.remove(e)
        return True

    def subscribe_item(self, subject, item):
        if subject == '#' or subject == 'action':
            e = self.is_subscribed('action')
            if e: e.append_item(item)
        if subject == '#' or subject == 'state':
            e = self.is_subscribed('state')
            if e: e.append_item(item)

    def subscribe_group(self, subject, item):
        if subject == '#' or subject == 'action':
            e = self.is_subscribed('action')
            if e: e.append_group(item)
        if subject == '#' or subject == 'state':
            e = self.is_subscribed('state')
            if e: e.append_group(item)

    def unsubscribe_item(self, subject, item):
        if subject == '#' or subject == 'action':
            e = self.is_subscribed('action')
            if e: e.remove_item(item)
        if subject == '#' or subject == 'state':
            e = self.is_subscribed('state')
            if e: e.remove_item(item)

    def unsubscribe_group(self, subject, item):
        if subject == '#' or subject == 'action':
            e = self.is_subscribed('action')
            if e: e.remove_group(item)
        if subject == '#' or subject == 'state':
            e = self.is_subscribed('state')
            if e: e.remove_group(item)

    def format_data(self, subject, data):
        if not subject or not data: return None
        try:
            if isinstance(data, list): data_in = data
            else: data_in = [data]
            fdata = None
            e = self.is_subscribed(subject)
            if not e: return None
            if subject == 'log':
                fdata = []
                for d in data_in:
                    if d['l'] >= e.get_log_level() and 'msg' in d \
                                    and d['msg'][0] != '.':
                        fdata.append(d)
            elif subject == 'state':
                fdata = []
                for din in data_in:
                    d, dts = din
                    if e.item_types and ('#' in e.item_types
                                    or d.item_type in e.item_types) \
                                    and eva.item.item_match(d, e.item_ids,
                                            e.groups):
                        if not self.lse_lock.acquire(timeout=eva.core.timeout):
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
        return self.timeout if self.timeout else eva.core.timeout

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

    def stop(self):
        if not self.test_only_mode:
            self.notifier_worker.stop()
        self.disconnect()

    def notify(self, subject, data, unpicklable=False, retain=False):
        if not self.can_notify(): return False
        data_to_send = self.format_data(subject, data)
        if not data_to_send: return None
        self.log_notify()
        self.notifier_worker.put((subject, data_to_send, retain, unpicklable))
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
        if self.space or props: d['space'] = self.space
        if self._skip_test is not None or props:
            d['skip_test'] = self._skip_test
        d['enabled'] = self.enabled
        if self.timeout or props: d['timeout'] = self.timeout
        return d

    def set_prop(self, prop, value):
        if prop == 'enabled':
            if value is None:
                self.enabled = False
                return True
            val = val_to_boolean(value)
            if val is None: return False
            self.enabled = val
            return True
        if prop == 'skip_test':
            if value is None:
                self._skip_test = None
                return True
            val = val_to_boolean(value)
            if val is None: return False
            self._skip_test = val
            return True
        elif prop == 'space':
            self.space = value
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

    def __init__(self, notifier_id=None, notifier_subtype=None, apikey=None):
        if not notifier_id: _id = str(uuid.uuid4())
        else: _id = notifier_id
        _tp = 'client'
        if notifier_subtype:
            _tp += notifier_subtype
        else:
            _tp += 'generic'
        super().__init__(_id, _tp)
        self.nt_client = True
        self.enabled = True
        self.apikey = apikey

    def format_data(self, subject, data):
        if not subject or not data: return None
        if apikey.check(self.apikey, master=True):
            return super().format_data(subject, data)
        if subject == 'log':
            if not apikey.check(self.apikey, sysfunc=True):
                return None
            else:
                return super().format_data(subject, data)
        if isinstance(data, list): data_in = data
        else: data_in = [data]
        fdata = []
        if subject == 'state':
            for d in data_in:
                if apikey.check(self.apikey, d):
                    fdata.append(d)
        elif subject == 'action':
            for d in data_in:
                if apikey.check(self.apikey, d.item):
                    fdata.append(d)
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
        if self.is_client_dead():
            self.connected = False
            self.unregister()


class SQLANotifier(GenericNotifier):

    class HistoryCleaner(BackgroundWorker):

        def __init__(self, name=None, **kwargs):
            super().__init__(
                name=name,
                interval=60,
                on_error=eva.core.log_traceback,
                on_error_kwargs=_ne_kw,
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

    def __init__(self, notifier_id, db_uri=None, keep=None, space=None):
        notifier_type = 'db'
        super().__init__(
            notifier_id=notifier_id, notifier_type=notifier_type, space=space)
        self.keep = keep if keep else \
            sqlite_default_keep
        self._keep = keep
        self.history_cleaner = self.HistoryCleaner(
            name=self.notifier_id + '_cleaner', o=self)
        self.db_lock = threading.RLock()
        self.set_db(db_uri)

    def set_db(self, db_uri=None):
        self._db = db_uri
        self.db_uri = eva.core.format_db_uri(db_uri)
        self.db_engine = eva.core.create_db_engine(self.db_uri)

    def test(self):
        if self.connected: return True
        self.connect()
        return self.connected

    def db(self):
        n = 'notifier_{}_db'.format(self.notifier_id)
        with self.db_lock:
            if not g.has(n):
                g.set(n, self.db_engine.connect())
            return g.get(n)

    def get_state(self,
                  oid,
                  t_start=None,
                  t_end=None,
                  limit=None,
                  prop=None,
                  time_format=None):
        l = int(limit) if limit else None
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
        if time_format == 'iso':
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
        for d in data:
            h = {}
            if time_format == 'iso':
                h['t'] = datetime.fromtimestamp(float(d[0]), tz).isoformat()
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
                    h['value'] = v
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
                        d['value'] != 'null' else None
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
            if value is None or value == '': return False
            self.set_db(db_uri)
            return True
        elif prop == 'keep':
            if value is None:
                self.keep = sqlite_default_keep
                self._keep = None
                return True
            try:
                self.keep = int(value)
            except:
                return False
            self._keep = self.keep
            return True
        return super().set_prop(prop, value)

    def serialize(self, props=False):
        d = super().serialize(props)
        # sqla has no timeout
        try:
            del d['timeout']
        except:
            pass
        if self._keep or props: d['keep'] = self._keep
        if self._db or props: d['db'] = self._db
        return d

    def disconnect(self):
        self.history_cleaner.stop()


class GenericHTTPNotifier(GenericNotifier):

    def __init__(self,
                 notifier_id,
                 notifier_subtype=None,
                 uri=None,
                 notify_key=None,
                 space=None,
                 timeout=None,
                 ssl_verify=True):
        notifier_type = 'http'
        if notifier_subtype: notifier_type += '-' + notifier_subtype
        super().__init__(
            notifier_id=notifier_id,
            notifier_type=notifier_type,
            space=space,
            timeout=timeout)
        self.ssl_verify = ssl_verify
        self.uri = uri
        self.notify_key = notify_key
        self.uri = uri
        self.connected = True

    def log_notify(self):
        logging.debug('.sending data notification to ' + \
                            '%s method = %s,uri: %s' % (self.notifier_id,
                                    self.notifier_type, self.uri))

    def log_error(self, code=None, message=None, result=None):
        if not result:
            super().log_error(code=code, message=message)
        else:
            msg = result['result']
            if 'remark' in result: msg += ' (' + result['remark'] + ')'
            super().log_error(message=msg)

    def serialize(self, props=False):
        d = {}
        d['uri'] = self.uri
        if (self.ssl_verify is not None and \
                self.ssl_verify is not True) or props:
            d['ssl_verify'] = self.ssl_verify
        if self.notify_key or props: d['notify_key'] = self.notify_key
        d.update(super().serialize(props=props))
        return d

    def set_prop(self, prop, value):
        if prop == 'uri':
            if value is None: return False
            self.uri = value
            return True
        elif prop == 'ssl_verify':
            if value is None:
                self.ssl_verify = None
                return True
            val = val_to_boolean(value)
            if val is None: return False
            self.ssl_verify = val
            return True
        elif prop == 'notify_key':
            self.notify_key = value
            return True
        return super().set_prop(prop, value)


class HTTPNotifier(GenericHTTPNotifier):

    def __init__(self,
                 notifier_id,
                 uri,
                 notify_key=None,
                 space=None,
                 timeout=None,
                 ssl_verify=True,
                 stop_on_error=None):
        super().__init__(
            notifier_id=notifier_id,
            uri=uri,
            notify_key=notify_key,
            space=space,
            timeout=timeout,
            ssl_verify=ssl_verify)
        self.stop_on_error = stop_on_error
        # constant to short subject in get notifications
        self.get_subject = 's'

    def send_notification(self, subject, data, retain=None, unpicklable=False):
        for d in data:
            try:
                params = {self.get_subject: subject}
                key = apikey.format_key(self.notify_key)
                if key: params['k'] = key
                if self.space: params['space'] = self.space
                params.update(d)
                r = requests.get(
                    self.uri,
                    params=params,
                    timeout=self.get_timeout(),
                    verify=self.ssl_verify)
                if r.status_code == 200: result = jsonpickle.decode(r.text)
                if r.status_code != 200:
                    self.log_error(code=r.status_code)
                elif result['result'] != 'OK':
                    self.log_error(result=result)
                    if self.stop_on_error:
                        self.log_datastop()
                        return False
            except:
                self.log_error()
                eva.core.log_traceback(notifier=True)
                if self.stop_on_error:
                    self.log_datastop()
                    return False
        return True

    def log_datastop(self):
        logging.error('.Notification data sending stopped for %s' % \
                                                         self.notifier_id)

    def serialize(self, props=False):
        d = {}
        if (self.stop_on_error or self.stop_on_error is False) or props:
            d['stop_on_error'] = self.stop_on_error
        d.update(super().serialize(props=props))
        return d

    def set_prop(self, prop, value):
        if prop == 'stop_on_error':
            if value is None:
                self.stop_on_error = None
                return True
            val = val_to_boolean(value)
            if val is None: return False
            self.stop_on_error = val
            return True
        return super().set_prop(prop, value)

    def test(self):
        self.connect()
        try:
            logging.debug('.Testing http notifier %s (%s)' % \
                    (self.notifier_id,self.uri))
            params = {self.get_subject: 'test', 'k': self.notify_key}
            r = requests.get(
                self.uri,
                params=params,
                timeout=self.get_timeout(),
                verify=self.ssl_verify)
            if r.status_code != 200: return False
            result = jsonpickle.decode(r.text)
            if result['result'] != 'OK': return False
        except:
            eva.core.log_traceback(notifier=True)
            return False
        return True


class HTTP_POSTNotifier(GenericHTTPNotifier):

    def __init__(self,
                 notifier_id,
                 uri,
                 notify_key=None,
                 space=None,
                 timeout=None,
                 ssl_verify=True):
        super().__init__(
            notifier_id=notifier_id,
            notifier_subtype='post',
            ssl_verify=ssl_verify,
            uri=uri,
            notify_key=notify_key,
            space=space,
            timeout=timeout)

    def send_notification(self, subject, data, retain=None, unpicklable=False):
        params = {
            'subject': subject,
            'data': jsonpickle.encode(data, unpicklable=unpicklable)
        }
        key = apikey.format_key(self.notify_key)
        if key: params['k'] = key
        if self.space: params['space'] = self.space
        r = requests.post(
            self.uri,
            data=params,
            timeout=self.get_timeout(),
            verify=self.ssl_verify)
        if r.status_code == 202: return True
        if r.status_code == 200:
            result = r.json()
            if result['result'] == 'OK':
                return True
            else:
                self.log_error(result=result)
                return False
        else:
            self.log_error(code=r.status_code)
            return False

    def test(self):
        self.connect()
        try:
            logging.debug('.Testing http-post notifier %s (%s)' % \
                    (self.notifier_id,self.uri))
            params = {'subject': 'test', 'k': self.notify_key}
            r = requests.post(
                self.uri,
                data=params,
                timeout=self.get_timeout(),
                verify=self.ssl_verify)
            if r.status_code != 200: return False
            if r.json()['result'] != 'OK': return False
        except:
            eva.core.log_traceback(notifier=True)
            return False
        return True


class HTTP_JSONNotifier(GenericHTTPNotifier):

    def __init__(self,
                 notifier_id,
                 uri,
                 method=None,
                 notify_key=None,
                 space=None,
                 timeout=None,
                 ssl_verify=True):
        self.method = method
        super().__init__(
            notifier_id=notifier_id,
            notifier_subtype='json',
            ssl_verify=ssl_verify,
            uri=uri,
            notify_key=notify_key,
            space=space,
            timeout=timeout)

    def send_notification(self, subject, data, retain=None, unpicklable=False):
        d = {'subject': subject}
        key = apikey.format_key(self.notify_key)
        if key: d['k'] = key
        if self.space: d['space'] = self.space
        if self.method:
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
        r = requests.post(
            self.uri,
            json=data_ts,
            timeout=self.get_timeout(),
            verify=self.ssl_verify)
        if self.method:
            if r.status_code in [200, 202]:
                return True
            else:
                self.log_error(code=r.status_code)
                return False
        if r.status_code == 200:
            result = r.json()
            if result['result'] == 'OK': return True
            else:
                self.log_error(result=result)
                return False
        self.log_error(code=r.status_code)
        return False

    def test(self):
        self.connect()
        try:
            logging.debug('.Testing http-json notifier %s (%s)' % \
                    (self.notifier_id,self.uri))
            d = {'subject': 'test', 'k': self.notify_key}
            if self.method:
                req_id = str(uuid.uuid4())
                data_ts = {
                    'jsonrpc': '2.0',
                    'method': self.method,
                    'params': d,
                    'id': req_id
                }
            else:
                data_ts = d
            r = requests.post(
                self.uri,
                json=data_ts,
                timeout=self.get_timeout(),
                verify=self.ssl_verify)
            if r.status_code != 200: return False
            result = r.json()
            if self.method:
                if result.get('jsonrpc') != '2.0' or \
                        result.get('id') != req_id or 'error' in result:
                    return False
            elif result['result'] != 'OK':
                return False
        except:
            eva.core.log_traceback(notifier=True)
            return False
        return True

    def serialize(self, props=False):
        d = {}
        if props:
            d['method'] = self.method
        elif self.method:
            d['method'] = self.method
        d.update(super().serialize(props=props))
        return d

    def set_prop(self, prop, value):
        if prop == 'method':
            self.method = value
            return True
        else:
            return super().set_prop(prop, value)


class GenericMQTTNotifier(GenericNotifier):

    class Announcer(BackgroundWorker):

        def __init__(self, name=None, **kwargs):
            super().__init__(
                name=name,
                on_error=eva.core.log_traceback,
                on_error_kwargs=_ne_kw,
                **kwargs)

        def run(self, o, **kwargs):
            o.send_message(
                o.announce_topic,
                o.announce_msg,
                qos=o.qos['system'],
                use_space=False)

    def __init__(self,
                 notifier_id,
                 host,
                 port=None,
                 space=None,
                 username=None,
                 password=None,
                 qos=None,
                 keepalive=None,
                 timeout=None,
                 collect_logs=None,
                 api_enabled=None,
                 discovery_enabled=None,
                 announce_interval=None,
                 ca_certs=None,
                 certfile=None,
                 keyfile=None):
        notifier_type = 'mqtt'
        super().__init__(
            notifier_id=notifier_id,
            notifier_type=notifier_type,
            space=space,
            timeout=timeout)
        self.host = host
        if port: self.port = port
        else: self.port = 1883
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
        if ca_certs:
            try:
                self.mq.tls_set(
                    ca_certs=ca_certs, certfile=certfile, keyfile=keyfile)
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
        self.controller_topic = '{}controller/{}/{}/'.format(
            pfx, eva.core.product_code, eva.core.system_name)
        self.api_request_topic = self.controller_topic + 'api/request'
        self.api_response_topic = self.controller_topic + 'api/response'
        self.announce_topic = self.pfx + 'controller/discovery'
        self.announce_msg = eva.core.product_code + '/' + eva.core.system_name
        self.api_handler = eva.api.mqtt_api_handler
        self.discovery_handler = eva.api.mqtt_discovery_handler
        # dict of tuples (topic, handler)
        self.api_callback = {}
        self.api_callback_lock = threading.RLock()
        self.announcer = self.Announcer(
            name=self.notifier_id + '_announcer',
            o=self,
            interval=self.announce_interval)

    def connect(self):
        self.check_connection()

    def disconnect(self):
        super().disconnect()
        self.mq.loop_stop()
        self.mq.disconnect()
        self.announcer.stop()

    def on_connect(self, client, userdata, flags, rc):
        logging.debug('%s mqtt reconnect' % self.notifier_id)
        self.connected = True
        if self.announce_interval and not self.test_only_mode:
            self.announcer.start(_name=self.notifier_id + '_announcer')
        try:
            for i, v in self.api_callback.copy():
                client.subscribe(v[0], qos=self.qos['system'])
                logging.debug('%s resubscribed to %s q%u API response' % \
                        (self.notifier_id, i, self.qos['system']))
            for i, v in self.items_to_update_by_topic.copy().items():
                client.subscribe(i, qos=v.mqtt_update_qos)
                logging.debug('%s resubscribed to %s q%u updates' % \
                        (self.notifier_id, i, v.mqtt_update_qos))
            for i, v in self.items_to_control_by_topic.copy().items():
                client.subscribe(i, qos=v.mqtt_control_qos)
                logging.debug('%s resubscribed to %s q%u control' % \
                        (self.notifier_id, i, v.mqtt_control_qos))
            for i in list(self.custom_handlers):
                qos = self.custom_handlers_qos.get(i)
                client.subscribe(i, qos=qos)
                logging.debug('%s resubscribed to %s q%u custom' % \
                        (self.notifier_id, i, qos))
            if self.collect_logs:
                client.subscribe(self.log_topic, qos=self.qos['log'])
                logging.debug('%s subscribed to %s' % \
                        (self.notifier_id, self.log_topic))
            if self.api_enabled:
                client.subscribe(self.api_request_topic, qos=self.qos['system'])
                logging.debug('%s subscribed to %s' % \
                        (self.notifier_id, self.api_request_topic))
            if self.discovery_enabled:
                client.subscribe(self.announce_topic, qos=self.qos['system'])
                logging.debug('%s subscribed to %s' % \
                        (self.notifier_id, self.announce_topic))
        except:
            eva.core.log_traceback(notifier=True)

    def handler_append(self, topic, func, qos=1):
        _topic = self.space + '/' + topic if \
                self.space is not None else topic
        if not self.custom_handlers.get(_topic):
            self.custom_handlers[_topic] = set()
            self.custom_handlers_qos[_topic] = qos
            self.mq.subscribe(_topic, qos=qos)
            logging.debug(
                '%s subscribed to %s for handler' % (self.notifier_id, _topic))
        self.custom_handlers[_topic].add(func)
        logging.debug('%s new handler for topic %s: %s' % (self.notifier_id,
                                                           _topic, func))

    def handler_remove(self, topic, func):
        _topic = self.space + '/' + topic if \
                self.space is not None else topic
        if _topic in self.custom_handlers:
            self.custom_handlers[_topic].remove(func)
            logging.debug('%s removed handler for topic %s: %s' %
                          (self.notifier_id, _topic, func))
        if not self.custom_handlers.get(_topic):
            self.mq.unsubscribe(_topic)
            del self.custom_handlers[_topic]
            del self.custom_handlers_qos[_topic]
            logging.debug('%s unsubscribed from %s, last handler left' %
                          (self.notifier_id, _topic))

    def update_item_append(self, item):
        logging.debug('%s subscribing to %s updates' % \
                (self.notifier_id, item.full_id))
        self.items_to_update.add(item)
        for t in item.mqtt_update_topics:
            topic = self.pfx + item.item_type + '/' + \
                    item.full_id + '/' + t
            self.items_to_update_by_topic[topic] = item
            self.mq.subscribe(topic, qos=item.mqtt_update_qos)
            logging.debug('%s subscribed to %s q%u updates' %
                          (self.notifier_id, topic, item.mqtt_update_qos))
        return True

    def control_item_append(self, item):
        logging.debug('%s subscribing to %s control' % \
                (self.notifier_id, item.full_id))
        topic_control = self.pfx + item.item_type + '/' +\
                item.full_id + '/control'
        self.items_to_control.add(item)
        self.items_to_control_by_topic[topic_control] = item
        self.mq.subscribe(topic_control, qos=item.mqtt_control_qos)
        logging.debug('%s subscribed to %s q%u control' %
                      (self.notifier_id, topic_control, item.mqtt_control_qos))
        return True

    def update_item_remove(self, item):
        logging.debug('%s unsubscribing from %s updates' % \
                (self.notifier_id, item.full_id))
        if item not in self.items_to_update: return False
        try:
            for t in item.mqtt_update_topics:
                topic = self.pfx + item.item_type + '/' + \
                        item.full_id + '/' + t
                self.mq.unsubscribe(topic)
                logging.debug('%s unsubscribed from %s updates' %
                              (self.notifier_id, topic))
                del self.items_to_update_by_topic[topic]
            self.items_to_update.remove(item)
        except:
            eva.core.log_traceback(notifier=True)
        return True

    def control_item_remove(self, item):
        logging.debug('%s unsubscribing from %s control' % \
                (self.notifier_id, item.full_id))
        if item not in self.items_to_control: return False
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
            logging.error('Unable to process topic ' + \
                            '%s with custom handler %s' % (t, func))
            eva.core.log_traceback(notifier=True)

    def on_message(self, client, userdata, msg):
        if not self.enabled: return
        t = msg.topic
        try:
            d = msg.payload.decode()
        except:
            logging.warning('Invalid message from MQTT server: {}'.format(
                msg.payload))
            eva.core.log_traceback()
            return
        if t == self.announce_topic and \
                d != self.announce_msg and \
                self.discovery_handler:
            background_job(self.discovery_handler)(self.notifier_id, d)
            return
        if t == self.api_request_topic and self.api_handler:
            background_job(self.api_handler)(self.notifier_id, d,
                                             self.send_api_response)
            return
        if t.startswith(self.pfx_api_response):
            response_id = t.split('/')[-1]
            if response_id in self.api_callback:
                background_job(self.api_callback[response_id][1])(d)
                self.finish_api_request(response_id)
                return
        if t in self.custom_handlers:
            for h in self.custom_handlers.get(t):
                background_job(self.exec_custom_handler)(h, d, t, msg.qos,
                                                         msg.retain)
        if self.collect_logs and t == self.log_topic:
            try:
                r = jsonpickle.decode(d)
                if r['h'] != eva.core.system_name or \
                        r['p'] != eva.core.product_code:
                    eva.logs.log_append(rd=r, skip_mqtt=True)
            except:
                eva.core.log_traceback(notifier=True)
        elif t in self.items_to_update_by_topic:
            i = self.items_to_update_by_topic[t]
            i.mqtt_set_state(t, d)
        elif t in self.items_to_control_by_topic:
            i = self.items_to_control_by_topic[t]
            i.mqtt_action(msg=d)

    def on_publish_msg(self, client, userdata, mid):
        logging.debug('.Notification data #%u delivered to %s:%u' %
                      (mid, self.host, self.port))

    def check_connection(self):
        if self.mq._state != mqtt.mqtt_cs_connected:
            self.mq.loop_stop()
            self.mq.connect(
                host=self.host, port=self.port, keepalive=self.keepalive)
            self.mq.loop_start()

    def send_notification(self, subject, data, retain=None, unpicklable=False):
        self.check_connection()
        if self.qos and subject in self.qos: qos = self.qos[subject]
        else: qos = 1
        if subject == 'state':
            if retain is not None: _retain = retain
            else: _retain = True
            for i in data:
                for k in i:
                    if not k in ['id', 'group', 'type', 'full_id', 'oid']:
                        self.mq.publish(self.pfx + i['type'] + '/' + \
                                i['group'] + '/' + i['id'] + '/' + k, i[k], qos,
                                    retain = _retain)
        elif subject == 'action':
            if retain is not None: _retain = retain
            else: _retain = False
            for i in data:
                self.mq.publish(self.pfx + i['item_type'] + '/' + \
                        i['item_group'] + '/' + i['item_id'] + '/action',
                    jsonpickle.encode(i, unpicklable=unpicklable),
                    qos, retain = _retain)
        elif subject == 'log':
            if retain is not None: _retain = retain
            else: _retain = False
            for i in data:
                self.mq.publish(
                    self.log_topic,
                    jsonpickle.encode(i, unpicklable=False),
                    qos,
                    retain=_retain)

    def send_message(self, topic, data, retain=None, qos=1, use_space=True):
        self.check_connection()
        if isinstance(data, list):
            _data = data
        else:
            _data = [data]
        if retain is not None: _retain = retain
        else: _retain = False
        for d in _data:
            if isinstance(d, dict):
                _d = jsonpickle.encode(data, unpicklable=False)
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
        if not self.api_enabled: return False
        self.mq.publish(
            self.api_response_topic + '/' + call_id,
            data,
            self.qos['system'],
            retain=False)
        return True

    def send_api_request(self, request_id, controller_id, data, callback):
        if request_id in self.api_callback:
            logging.error('.GenericMQTTNotifier: duplicate API request ID')
            return False
        if not self.api_callback_lock.acquire(timeout=eva.core.timeout):
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
        return self.send_message(
            'controller/' + controller_id + '/api/request',
            data,
            qos=self.qos['system'])

    def finish_api_request(self, request_id):
        if request_id not in self.api_callback:
            logging.warning('.GenericMQTTNotifier: API request ID not found')
            return False
        if not self.api_callback_lock.acquire(timeout=eva.core.timeout):
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
            self.check_connection()
            result = self.mq.publish(self.pfx + 'test', 1, qos=2, retain=False)
            return eva.core.wait_for(result.is_published, self.get_timeout())
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
        if self.host or props: d['host'] = self.host
        if self._port or props: d['port'] = self._port
        if self.username or props: d['username'] = self.username
        if self.password or props: d['password'] = self.password
        if self._qos or props: d['qos'] = self._qos
        if self._keepalive or props: d['keepalive'] = self._keepalive
        if self.collect_logs or props: d['collect_logs'] = self.collect_logs
        if self.api_enabled or props: d['api_enabled'] = self.api_enabled
        if self.discovery_enabled or props:
            d['discovery_enabled'] = self.discovery_enabled
        if self.announce_interval or props:
            d['announce_interval'] = self.announce_interval
        if self.ca_certs or props: d['ca_certs'] = self.ca_certs
        if self.certfile or props: d['certfile'] = self.certfile
        if self.keyfile or props: d['keyfile'] = self.keyfile
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
            if announce_interval < 0: return False
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
            if not value: return False
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
        elif prop == 'qos':
            if not value:
                self._qos = None
                return True
            try:
                val = int(value)
            except:
                return False
            if not 0 <= val <= 2: return False
            self._qos = {'action': val, 'state': val, 'log': val, 'system': val}
            return True
        elif prop[:4] == 'qos.':
            q = prop[4:]
            if not q in ['action', 'state', 'log', 'system']: return False
            if not value:
                if self._qos and q in self._qos:
                    del self._qos[q]
                return True
            try:
                val = int(value)
            except:
                return False
            if not 0 <= val <= 2: return False
            if not self._qos: self._qos = {}
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
                 username=None,
                 password=None,
                 qos=None,
                 keepalive=None,
                 timeout=None,
                 collect_logs=None,
                 api_enabled=None,
                 discovery_enabled=None,
                 announce_interval=None,
                 ca_certs=None,
                 certfile=None,
                 keyfile=None):
        super().__init__(
            notifier_id=notifier_id,
            host=host,
            port=port,
            space=space,
            username=username,
            password=password,
            qos=qos,
            keepalive=keepalive,
            timeout=timeout,
            collect_logs=collect_logs,
            api_enabled=api_enabled,
            discovery_enabled=discovery_enabled,
            announce_interval=announce_interval,
            ca_certs=ca_certs,
            certfile=certfile,
            keyfile=keyfile)


class WSNotifier_Client(GenericNotifier_Client):

    def __init__(self, notifier_id=None, apikey=None, ws=None):
        super().__init__(notifier_id, 'ws', apikey)
        self.ws = ws
        if self.ws:
            self.ws.notifier = self
            self.connected = True

    def send_notification(self, subject, data, retain=None, unpicklable=False):
        if not self.is_client_dead() and self.connected:
            try:
                msg = {'s': subject, 'd': data}
                logging.debug('.notifying WS %s' % self.notifier_id)
                self.ws.send(jsonpickle.encode(msg, unpicklable=unpicklable))
            except:
                eva.core.log_traceback(notifier=True)

    def send_reload(self):
        self.send_notification('reload', 'asap')

    def send_server_event(self, event):
        self.send_notification('server', event)

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
            data = jsonpickle.decode(message.data.decode())
            subject = data['s']
            if subject == 'bye':
                self.close()
                return
            elif subject == 'ping':
                msg = {'s': 'pong'}
                self.send(jsonpickle.encode(msg, unpicklable=True))
            elif subject == 'u' and self.notifier:
                topic = data['t']
                if isinstance(topic, list):
                    for t in topic:
                        self.notifier.unsubscribe(t)
                else:
                    self.notifier.unsubscribe(topic)
                return
            elif self.notifier:
                if 'l' in data: log_level = int(data['l'])
                else: log_level = 20
                if 'i' in data: items = data['i']
                else: items = s_all
                if 'g' in data: groups = data['g']
                else: groups = s_all
                if 'tp' in data: item_types = data['tp']
                else: item_types = s_all
                if 'a' in data: action_status = data['a']
                else: action_status = s_all
                self.notifier.subscribe(
                    subject,
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
    if not notifier_id and not fname: return None
    if not fname:
        notifier_fname = eva.core.format_cfg_fname('%s_notify.d/%s.json' % \
                (eva.core.product_code, notifier_id), runtime = True)
    else:
        notifier_fname = fname
    if not notifier_id:
        _notifier_id = os.path.splitext(os.path.basename(notifier_fname))[0]
    else:
        _notifier_id = notifier_id
    raw = ''.join(open(notifier_fname).readlines())
    ncfg = jsonpickle.decode(raw)
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
        collect_logs = ncfg.get('collect_logs', False)
        api_enabled = ncfg.get('api_enabled', False)
        discovery_enabled = ncfg.get('discovery_enabled', False)
        announce_interval = ncfg.get('announce_interval', 0)
        n = MQTTNotifier(
            _notifier_id,
            host=host,
            port=port,
            space=space,
            username=username,
            password=password,
            qos=qos,
            keepalive=keepalive,
            timeout=timeout,
            collect_logs=collect_logs,
            api_enabled=api_enabled,
            discovery_enabled=discovery_enabled,
            announce_interval=announce_interval,
            ca_certs=ca_certs,
            certfile=certfile,
            keyfile=keyfile)
    elif ncfg['type'] == 'db':
        db = ncfg.get('db')
        keep = ncfg.get('keep')
        space = ncfg.get('space')
        n = SQLANotifier(_notifier_id, db_uri=db, keep=keep, space=space)
    elif ncfg['type'] in ['http', 'http-post', 'http-json']:
        space = ncfg.get('space')
        ssl_verify = ncfg.get('ssl_verify')
        uri = ncfg.get('uri')
        notify_key = ncfg.get('notify_key')
        timeout = ncfg.get('timeout')
        method = ncfg.get('method')
        if ncfg['type'] == 'http':
            if 'stop_on_error' in ncfg:
                stop_on_error = ncfg['stop_on_error']
            else:
                stop_on_error = None
            n = HTTPNotifier(
                _notifier_id,
                ssl_verify=ssl_verify,
                uri=uri,
                notify_key=notify_key,
                space=space,
                timeout=timeout,
                stop_on_error=stop_on_error)
        elif ncfg['type'] == 'http-post':
            n = HTTP_POSTNotifier(
                _notifier_id,
                ssl_verify=ssl_verify,
                uri=uri,
                notify_key=notify_key,
                space=space,
                timeout=timeout)
        else:
            n = HTTP_JSONNotifier(
                _notifier_id,
                ssl_verify=ssl_verify,
                uri=uri,
                method=method,
                notify_key=notify_key,
                space=space,
                timeout=timeout)
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
        n.subscribe(
            subject,
            items=items,
            groups=groups,
            item_types=item_types,
            action_status=action_status,
            log_level=log_level)
    return n


def get_notifier_fnames():
    fnames = eva.core.format_cfg_fname(eva.core.product_code + \
            '_notify.d/*.json', runtime = True)
    return glob.glob(fnames)


def load(test=True, connect=True):
    global notifiers
    _notifiers = {}
    logging.info('Loading notifiers')
    try:
        for notifier_fname in get_notifier_fnames():
            try:
                n = load_notifier(
                    notifier_id=None,
                    fname=notifier_fname,
                    test=test,
                    connect=connect)
                if not n: raise
                _notifiers[n.notifier_id] = n
                logging.debug('+ notifier %s' % n.notifier_id)
            except:
                logging.error('Can not load notifier from %s' % notifier_fname)
                eva.core.log_traceback(notifier=True)
    except:
        logging.error('Notifiers load error')
        eva.core.log_traceback(notifier=True)
        return False
    notifiers = _notifiers
    # exec custom load for notifiers
    for i, n in notifiers.copy().items():
        try:
            n.load_config()
        except:
            logging.error('can not load notifier\'s config for %s' % i)
    return True


def serialize(notifier_id=None):
    if notifier_id: return notifiers[notifier_id].serialize()
    d = {}
    for i, n in notifiers.copy().items():
        d[i] = n.serialize()
    return d


def save_notifier(notifier_id):
    fname_full = eva.core.format_cfg_fname(eva.core.product_code + \
            '_notify.d/%s.json' % notifier_id, runtime = True)
    try:
        data = notifiers[notifier_id].serialize()
        open(fname_full, 'w').write(format_json(data, minimal=False))
    except:
        logging.error('can not save notifiers config into %s' % fname_full)
        eva.core.log_traceback(notifier=True)
        return False


def save(notifier_id=None):
    if notifier_id:
        n = notifiers[notifier_id]
        if isinstance(n, HTTPNotifier) or \
            isinstance(n, HTTP_POSTNotifier) or \
            isinstance(n, HTTP_JSONNotifier) or \
            isinstance(n, MQTTNotifier):
            save_notifier(notifier_id)
        else:
            try:
                n.save_config()
            except:
                logging.error('can not save notifier\'s config for %s' % i)
    else:
        for i, n in notifiers.copy().items():
            if i and not n.nt_client: save(i)


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
        for i in notifiers:
            if notifiers[i].can_notify():
                notify(
                    subject=subject,
                    data=data,
                    notifier_id=i,
                    retain=retain,
                    skip_subscribed_mqtt_item=skip_subscribed_mqtt_item,
                    skip_mqtt=skip_mqtt)


def get_notifier(notifier_id=None):
    return notifiers.get(notifier_id) if \
        notifier_id is not None else get_default_notifier()


def get_default_notifier():
    return notifiers.get(default_notifier_id)


def get_db_notifier(notifier_id):
    if notifier_id is None: return get_notifier(sqlite_default_id)
    n = get_notifier(notifier_id)
    return n if n and n.notifier_type == 'db' else None


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
    if notifier_id: return notifiers[notifier_id].serialize()
    return serialize()


def start():
    notifier_client_cleaner.start()
    for i, n in notifiers.copy().items():
        if n.enabled: n.start()


@eva.core.stop
def stop():
    notify_restart()
    for i, n in notifiers.copy().items():
        n.stop()
    notifier_client_cleaner.stop()


def reload_clients():
    logging.warning('sending reload event to clients')
    for k, n in notifiers.copy().items():
        if n.nt_client: n.send_reload()


def notify_restart():
    logging.warning('sending server restart event to clients')
    for k, n in notifiers.copy().items():
        if n.nt_client: n.send_server_event('restart')


@background_worker(
    delay=notifier_client_clean_delay, on_error=eva.core.log_traceback)
def notifier_client_cleaner(**kwargs):
    for k, n in notifiers.copy().items():
        if n.nt_client: n.cleanup()


def init():
    pass
