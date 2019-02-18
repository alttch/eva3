__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.1.1"

import logging
import eva.core
import eva.item
import jsonpickle
import requests
import paho.mqtt.client as mqtt
import time
from datetime import datetime
import dateutil.parser
import pytz
import glob
import os
import uuid
import threading
import sqlite3

from eva import apikey
from eva.tools import format_json
from eva.tools import val_to_boolean

from ws4py.websocket import WebSocket

default_log_level = 20

notifier_client_clean_delay = 1

default_mqtt_qos = 1

sqlite_default_keep = 86400
sqlite_default_id = 'db_1'

default_notifier_id = 'eva_1'

logging.getLogger('requests').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)

notifiers = {}

_notifier_client_cleaner_active = False

_notifier_client_cleaner = None


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
        self.connected = False
        self.nt_client = False
        self._skip_test = None
        self.last_state_event = {}
        self.lse_lock = threading.Lock()

    def subscribe(self,
                  subject,
                  items=[],
                  groups=[],
                  item_types=[],
                  action_status=[],
                  log_level=None):
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
                for d in data_in:
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
                        dts = d.serialize(notify=True)
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
                            self.lse_lock.release()
                        except:
                            self.lse_lock.release()
                            eva.core.log_traceback(notifier=True)
            elif subject == 'action':
                fdata = []
                for d in data_in:
                    if e.item_types and ('#' in e.item_types \
                                    or d.item.item_type in e.item_types) \
                            and e.action_status and ('#' in e.action_status \
                                or d.get_status_name() in e.action_status) \
                            and eva.item.item_match(d.item, e.item_ids,
                                    e.groups):
                        fdata.append(d.serialize())
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

    def notify(self, subject, data, unpicklable=False, retain=False):
        if not self.enabled or not self.connected: return False
        data_to_send = self.format_data(subject, data)
        if not data_to_send: return None
        self.log_notify()
        try:
            return self.send_notification(
                subject=subject,
                data=data_to_send,
                retain=retain,
                unpicklable=unpicklable)
        except:
            self.log_error()
            eva.core.log_traceback(notifier=True)
            return False

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
                del notifiers[self.notifier_id]
        except:
            eva.core.log_traceback(notifier=True)

    def cleanup(self):
        if self.is_client_dead():
            self.connected = False
            self.unregister()


class SQLiteNotifier(GenericNotifier):

    def __init__(self, notifier_id, db=None, keep=None, space=None):
        notifier_type = 'db'
        super().__init__(
            notifier_id=notifier_id, notifier_type=notifier_type, space=space)
        self.keep = keep if keep else \
            sqlite_default_keep
        self._keep = keep
        self.cleanup_time = 3600
        self._db = db
        if db and db[0] == '/':
            self.db = db
        else:
            self.db = eva.core.dir_runtime + '/' + db
        self.history_cleaner_active = False
        self.history_cleaner = None

    def test(self):
        if self.connected: return True
        self.connect()
        return self.connected

    def get_db(self):
        db = sqlite3.connect(self.db)
        return db

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
        sql = ''
        if t_s:
            sql += ' and t>%f' % t_s
        if t_e:
            sql += ' and t<=%f' % t_e
        if l:
            sql += ' order by t desc limit %u' % l
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
        db = self.get_db()
        c = db.cursor()
        result = []
        space = self.space if self.space is not None else ''
        if time_format == 'iso':
            tz = pytz.timezone(time.tzname[0])
        try:
            data = []
            # if we have start time - fetch newest record before it
            if t_s:
                c.execute(
                    'select ' + props +
                    ' from state_history where space = ? and ' + \
                            'oid = ? and t <= ? order by t desc limit 1', (
                        space,
                        oid,
                        t_s
                    ))
                r = c.fetchone()
                if r:
                    r = (t_s,) + r
                    data += [r]
            c.execute(
                'select t, ' + props +
                ' from state_history where space = ? and oid = ?' + sql, (
                    space,
                    oid,
                ))
            data += c.fetchall()
            for d in data:
                h = {}
                if time_format == 'iso':
                    h['t'] = datetime.fromtimestamp(d[0], tz).isoformat()
                else:
                    h['t'] = d[0]
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
        except:
            c.close()
            db.close()
            raise
        c.close()
        db.close()
        return sorted(result, key=lambda k: k['t'])

    def connect(self):
        try:
            if self.db:
                db = self.get_db()
                try:
                    c = db.cursor()
                    c.execute('select t from state_history limit 1')
                    c.close()
                except:
                    logging.info(
                        '.%s: no state_history table, crating new' % self.db)
                    c.close()
                    c = db.cursor()
                    try:
                        c.execute(
                            'create table state_history(space, t, oid,' + \
                            ' status, value, primary key(space, t, oid))'
                        )
                        c.execute(
                            'create index i_t_oid on state_history(space,t,oid)'
                        )
                        c.execute(
                            'create index i_oid on state_history(space,oid)')
                        db.commit()
                        c.close()
                    except:
                        logging.error(
                            '.%s: failed to create state_history table' %
                            self.db)
                        eva.core.log_traceback(notifier=True)
                        db.close()
                        self.connected = False
                        return False
                db.close()
                self.history_cleaner_active = True
                self.history_cleaner = threading.Thread(
                    target=self._t_history_cleaner,
                    name=self.notifier_id + '._t_history_cleaner')
                self.history_cleaner.start()
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
                db = self.get_db()
                c = db.cursor()
                space = self.space if self.space is not None else ''
                try:
                    c.execute(
                        'insert into state_history ' + \
                                '(space, t, oid, status, value)' + \
                                ' values (?, ?, ?, ?, ?)',
                        (space, t, d['oid'], d['status'], v))
                except:
                    c.close()
                    db.close()
                    raise
                db.commit()
                c.close()
                db.close()
        return True

    def set_prop(self, prop, value):
        if prop == 'db':
            if value is None or value == '': return False
            self._db = value
            if self._db[0] == '/':
                self.db = self._db
            else:
                self.db = eva.core.dir_runtime + '/' + self._db
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
        # sqlite sqlite has no timeout
        try:
            del d['timeout']
        except:
            pass
        if self._keep or props: d['keep'] = self._keep
        if self._db or props: d['db'] = self._db
        return d

    def _t_history_cleaner(self):
        logging.debug('.' + self.notifier_id +
                      ' item state history cleaner started')
        while self.history_cleaner_active:
            try:
                db = self.get_db()
                c = db.cursor()
                try:
                    space = self.space if self.space is not None else ''
                    logging.debug('.%s: cleaning records older than %u sec' %
                                  (self.db, self.keep))
                    c.execute('select oid, max(t) from state_history ' + \
                            ' where space = ? and t < ? group by oid',
                            (space, time.time() - self.keep))
                    c2 = db.cursor()
                    try:
                        for r in c:
                            c2.execute(
                            'delete from state_history where ' + \
                                    ' space = ? and oid = ? and t < ?',
                                    (space, r[0], r[1]))
                    except:
                        c2.close()
                        raise
                    db.commit()
                    c2.close()
                    c.close()
                    db.close()
                except:
                    c.close()
                    db.close()
                    eva.core.log_traceback(notifier=True)
            except:
                eva.core.log_traceback(notifier=True)
            i = 0
            while i < self.cleanup_time and \
                    self.history_cleaner_active:
                time.sleep(eva.core.sleep_step)
                i += eva.core.sleep_step
        logging.debug('.' + self.notifier_id +
                      ' item state history cleaner stopped')

    def disconnect(self):
        self.history_cleaner_active = False
        if self.history_cleaner and self.history_cleaner.isAlive():
            self.history_cleaner.join()


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
        if r.status_code == 200: result = jsonpickle.decode(r.text)
        if r.status_code == 200 and result['result'] == 'OK': return True
        elif r.status_code != 200:
            self.log_error(code=r.status_code)
            return False
        else:
            self.log_error(result=result)
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
            result = jsonpickle.decode(r.text)
            if result['result'] != 'OK': return False
        except:
            eva.core.log_traceback(notifier=True)
            return False
        return True


class HTTP_JSONNotifier(GenericHTTPNotifier):

    def __init__(self,
                 notifier_id,
                 uri,
                 notify_key=None,
                 space=None,
                 timeout=None,
                 ssl_verify=True):
        super().__init__(
            notifier_id=notifier_id,
            notifier_subtype='json',
            ssl_verify=ssl_verify,
            uri=uri,
            notify_key=notify_key,
            space=space,
            timeout=timeout)

    def send_notification(self, subject, data, retain=None, unpicklable=False):
        params = {'subject': subject, 'data': data}
        key = apikey.format_key(self.notify_key)
        if key: params['k'] = key
        if self.space: params['space'] = self.space
        r = requests.post(
            self.uri,
            json=params,
            timeout=self.get_timeout(),
            verify=self.ssl_verify)
        if r.status_code == 200: result = jsonpickle.decode(r.text)
        if r.status_code == 200 and result['result'] == 'OK': return True
        elif r.status_code != 200:
            self.log_error(code=r.status_code)
            return False
        else:
            self.log_error(result=result)
            return False

    def test(self):
        self.connect()
        try:
            logging.debug('.Testing http-json notifier %s (%s)' % \
                    (self.notifier_id,self.uri))
            params = {'subject': 'test', 'k': self.notify_key}
            r = requests.post(
                self.uri,
                json=params,
                timeout=self.get_timeout(),
                verify=self.ssl_verify)
            if r.status_code != 200: return False
            result = jsonpickle.decode(r.text)
            if result['result'] != 'OK': return False
        except:
            eva.core.log_traceback(notifier=True)
            return False
        return True


class GenericMQTTNotifier(GenericNotifier):

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
                'log': default_mqtt_qos
            }
        else:
            self.qos = qos
            if not 'state' in qos:
                self.qos['state'] = default_mqtt_qos
            if not 'action' in qos:
                self.qos['action'] = default_mqtt_qos
            if not 'log' in qos:
                self.qos['log'] = default_mqtt_qos
        self._qos = qos
        self.collect_logs = collect_logs
        if space is not None:
            pfx = space + '/'
        else:
            pfx = ''
        self.log_topic = pfx + 'log'

    def connect(self):
        self.check_connection()

    def disconnect(self):
        super().disconnect()
        self.mq.loop_stop()
        self.mq.disconnect()

    def on_connect(self, client, userdata, flags, rc):
        logging.debug('%s mqtt reconnect' % self.notifier_id)
        self.connected = True
        try:
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
        if self.space is not None:
            pfx = self.space + '/'
        else:
            pfx = ''
        for t in item.mqtt_update_topics:
            topic = pfx + item.item_type + '/' + \
                    item.full_id + '/' + t
            self.items_to_update_by_topic[topic] = item
            self.mq.subscribe(topic, qos=item.mqtt_update_qos)
            logging.debug('%s subscribed to %s q%u updates' %
                          (self.notifier_id, topic, item.mqtt_update_qos))
        return True

    def control_item_append(self, item):
        logging.debug('%s subscribing to %s control' % \
                (self.notifier_id, item.full_id))
        if self.space is not None:
            pfx = self.space + '/'
        else:
            pfx = ''
        topic_control = pfx + item.item_type + '/' +\
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
        if self.space is not None:
            pfx = self.space + '/'
        else:
            pfx = ''
        if item not in self.items_to_update: return False
        try:
            for t in item.mqtt_update_topics:
                topic = pfx + item.item_type + '/' + \
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
        if self.space is not None:
            pfx = self.space + '/'
        else:
            pfx = ''
        if item not in self.items_to_control: return False
        topic_control = pfx + item.item_type + '/' +\
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
        d = msg.payload.decode()
        if t in self.custom_handlers:
            for h in self.custom_handlers.get(t):
                try:
                    t = threading.Thread(
                        target=self.exec_custom_handler,
                        args=(h, d, t, msg.qos, msg.retain))
                    t.start()
                except:
                    eva.core.log_traceback(notifier=True)
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
        if self.space: pfx = self.space + '/'
        else: pfx = ''
        if subject == 'state':
            if retain is not None: _retain = retain
            else: _retain = True
            for i in data:
                for k in i:
                    if not k in ['id', 'group', 'type', 'full_id', 'oid']:
                        self.mq.publish(pfx + i['type'] + '/' + i['group'] +\
                                    '/' + i['id'] + '/' + k, i[k], qos,
                                    retain = _retain)
        elif subject == 'action':
            if retain is not None: _retain = retain
            else: _retain = False
            for i in data:
                self.mq.publish(pfx + i['item_type'] + '/' + i['item_group'] +\
                    '/' + i['item_id'] + '/action',
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
            except:
                eva.core.log_traceback(notifier=True)

    def test(self):
        try:
            logging.debug('.Testing mqtt notifier %s (%s:%u)' % \
                    (self.notifier_id,self.host, self.port))
            self.check_connection()
            if self.space: pfx = self.space + '/'
            else: pfx = ''
            result = self.mq.publish(pfx + 'test', 1, qos=2, retain=False)
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
            self._qos = {'action': val, 'state': val, 'log': val}
            return True
        elif prop[:4] == 'qos.':
            q = prop[4:]
            if not q in ['action', 'state', 'log']: return False
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
            logging.debug('.WS %s:%u got bad JSON data: %s' % \
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
        if 'host' in ncfg: host = ncfg['host']
        else: host = None
        if 'port' in ncfg: port = ncfg['port']
        else: port = None
        if 'ca_certs' in ncfg: ca_certs = ncfg['ca_certs']
        else: ca_certs = None
        if 'certfile' in ncfg: certfile = ncfg['certfile']
        else: certfile = None
        if 'keyfile' in ncfg: keyfile = ncfg['keyfile']
        else: keyfile = None
        if 'space' in ncfg: space = ncfg['space']
        else: space = None
        if 'username' in ncfg: username = ncfg['username']
        else: username = None
        if 'password' in ncfg: password = ncfg['password']
        else: password = None
        if 'qos' in ncfg: qos = ncfg['qos']
        else: qos = None
        if 'keepalive' in ncfg: keepalive = ncfg['keepalive']
        else: keepalive = None
        if 'timeout' in ncfg: timeout = ncfg['timeout']
        else: timeout = None
        if 'collect_logs' in ncfg: collect_logs = ncfg['collect_logs']
        else: collect_logs = False
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
            ca_certs=ca_certs,
            certfile=certfile,
            keyfile=keyfile)
    elif ncfg['type'] == 'db':
        if 'db' in ncfg: db = ncfg['db']
        else: db = None
        if 'keep' in ncfg: keep = ncfg['keep']
        else: keep = None
        if 'space' in ncfg: space = ncfg['space']
        else: space = None
        n = SQLiteNotifier(_notifier_id, db=db, keep=keep, space=space)
    elif ncfg['type'] in ['http', 'http-post', 'http-json']:
        if 'space' in ncfg: space = ncfg['space']
        else: space = None
        if 'ssl_verify' in ncfg: ssl_verify = ncfg['ssl_verify']
        else: ssl_verify = None
        if 'uri' in ncfg: uri = ncfg['uri']
        else: uri = None
        if 'notify_key' in ncfg: notify_key = ncfg['notify_key']
        else: notify_key = None
        if 'timeout' in ncfg: timeout = ncfg['timeout']
        else: timeout = None
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
                notify_key=notify_key,
                space=space,
                timeout=timeout)
    else:
        logging.error('Bad notifier type = %s' % ncfg['type'])
        return None
    if 'skip_test' in ncfg: skip_test = ncfg['skip_test']
    else: skip_test = None
    n._skip_test = skip_test
    if 'enabled' in ncfg:
        n.enabled = ncfg['enabled']
        if n.enabled:
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
    if 'events' in ncfg:
        for e in ncfg['events']:
            subject = e['subject']
            if 'level' in e: log_level = e['level']
            else: log_level = None
            if 'items' in e: items = e['items']
            else: items = []
            if 'groups' in e: groups = e['groups']
            else: groups = []
            if 'types' in e: item_types = e['types']
            else: item_types = []
            if 'action_status' in e:
                action_status = e['action_status']
            else:
                action_status = []
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


def _t_notify(notifier, subject, data, retain):
    try:
        logging.debug('.notify %s' % notifier.notifier_id)
        notifier.notify(subject, data, retain=retain)
    except:
        logging.error('.Can not notify %s' % notifier.notifier_id)
        eva.core.log_traceback(notifier=True)


def notify(subject,
           data,
           notifier_id=None,
           wait=False,
           retain=None,
           skip_subscribed_mqtt_item=None,
           skip_mqtt=False):
    if notifier_id:
        try:
            if skip_mqtt and notifiers[notifier_id].notifier_type[:4] == 'mqtt':
                return
            if skip_subscribed_mqtt_item and \
                notifiers[notifier_id].notifier_type[:4] == 'mqtt' and \
                notifiers[notifier_id].update_item_exists(
                        skip_subscribed_mqtt_item
                        ):
                return
            nt = threading.Thread(
                target=_t_notify,
                name='_t_notify_%f' % time.time(),
                args=(notifiers[notifier_id], subject, data, retain))
            nt.start()
            if wait: nt.join()
        except:
            eva.core.log_traceback(notifier=True)
    else:
        for i in notifiers.copy():
            notify(
                subject=subject,
                data=data,
                notifier_id=i,
                wait=wait,
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


def dump(notifier_id=None):
    if notifier_id: return notifiers[notifier_id].serialize()
    return serialize()


def start():
    global _notifier_client_cleaner
    global _notifier_client_cleaner_active
    _notifier_client_cleaner = threading.Thread(
        target=_t_notifier_client_cleaner, name='_t_notifier_client_cleaner')
    _notifier_client_cleaner_active = True
    _notifier_client_cleaner.start()


def stop():
    global _notifier_client_cleaner
    global _notifier_client_cleaner_active
    notify_restart()
    for i, n in notifiers.copy().items():
        t = threading.Thread(target = n.disconnect,
                name = '_t_notifier_disconnect_%s_%f' % \
                        (n.notifier_id, time.time()))
        t.start()
    if _notifier_client_cleaner_active:
        _notifier_client_cleaner_active = False
        _notifier_client_cleaner.join()


def reload_clients():
    logging.warning('sending reload event to clients')
    for k, n in notifiers.copy().items():
        if n.nt_client: n.send_reload()


def notify_restart():
    logging.warning('sending server restart event to clients')
    for k, n in notifiers.copy().items():
        if n.nt_client: n.send_server_event('restart')


def _t_notifier_client_cleaner():
    logging.debug('notifier client cleaner started')
    while _notifier_client_cleaner_active:
        for k, n in notifiers.copy().items():
            if n.nt_client: n.cleanup()
        i = 0
        while i < notifier_client_clean_delay and \
                _notifier_client_cleaner_active:
            time.sleep(eva.core.sleep_step)
            i += eva.core.sleep_step
    logging.debug('notifier client cleaner stopped')


def init():
    eva.core.append_dump_func('notify', dump)
    eva.core.append_stop_func(stop)
