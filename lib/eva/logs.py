__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.3"

import logging
import eva.core
import time
import sys
import os
import threading
from pyaltt import background_worker

from eva.exceptions import InvalidParameter

from types import SimpleNamespace
from termcolor import colored

from functools import partial

_log_records = []

_flags = SimpleNamespace(mute=False)

log_cleaner_delay = 60

_log_record_lock = threading.RLock()

log_levels_by_name = {
    'debug': 10,
    'info': 20,
    'warning': 30,
    'error': 40,
    'critical': 50
}

log_levels_by_id = {
    10: 'debug',
    20: 'info',
    30: 'warning',
    40: 'error',
    50: 'critical'
}


def get_log_level_by_name(l):
    for k, v in log_levels_by_name.items():
        if l == k[:len(l)]:
            return v
    raise InvalidParameter('Invalid log level specified: {}'.format(l))


def get_log_level_by_id(l):
    level = None
    if isinstance(l, str):
        lv = l.lower()
        if lv in log_levels_by_name:
            return lv
    else:
        level = log_levels_by_id(l)
    if not level:
        raise InvalidParameter('Invalid log level specified: {}'.format(l))
    return level


class StdoutHandler(logging.StreamHandler):

    def __init__(self):
        self.colorize = sys.stdout.isatty(
        ) and not os.environ.get('EVA_CORE_RAW_STDOUT')
        self.suppress_notifier_logs = os.environ.get('EVA_CORE_SNLSO')
        self.cfunc = {
            10: partial(colored, color='grey', attrs=['bold']),
            30: partial(colored, color='yellow'),
            40: partial(colored, color='red'),
            50: partial(colored, color='red', attrs=['bold'])
        }
        super().__init__(sys.stdout)

    def emit(self, record):
        if not self.suppress_notifier_logs or not record.getMessage(
        ).startswith('.'):
            super().emit(record)

    def format(self, record):
        if self.colorize:
            r = super().format(record)
            cfunc = self.cfunc.get(record.levelno)
            return cfunc(r) if cfunc else r
        else:
            return super().format(record)


class MemoryLogHandler(logging.Handler):

    def emit(self, record):
        log_append(record)


def log_append(record=None, rd=None, skip_mqtt=False):
    if record:
        _r = {}
        _r['t'] = record.created
        _r['msg'] = record.getMessage()
        _r['l'] = record.levelno
        _r['th'] = record.threadName
        _r['mod'] = record.module
        _r['h'] = eva.core.config.system_name
        _r['p'] = eva.core.product.code
    elif rd:
        _r = rd
    else:
        return
    if not _flags.mute and _r['msg'] and _r['msg'][0] != '.' and \
            _r['mod'] != '_cplogging':
        if not _log_record_lock.acquire(timeout=eva.core.config.timeout):
            logging.critical('log_append locking broken')
            eva.core.critical()
            return
        try:
            _log_records.append(_r)
        except:
            eva.core.log_traceback()
        finally:
            _log_record_lock.release()
        eva.notify.notify('log', [_r], skip_mqtt=skip_mqtt)


def mute():
    _flags.mute = True


def unmute():
    _flags.mute = False


def start():
    log_cleaner.start()


@eva.core.stop
def stop():
    log_cleaner.stop()


def log_get(logLevel=0, t=0, n=None):
    _lr = []
    if n:
        max_entries = n
    else:
        max_entries = 100
    if max_entries > 10000: max_entries = 10000
    if t:
        _t = time.time() - t
    else:
        _t = 0
    if logLevel is None: _ll = 0
    else: _ll = logLevel
    for r in reversed(_log_records):
        if r['t'] > _t and r['l'] >= _ll:
            _lr = [r] + _lr
            if len(_lr) >= max_entries:
                break
    return _lr


@background_worker(delay=log_cleaner_delay, on_error=eva.core.log_traceback)
def log_cleaner(**kwargs):
    if not _log_record_lock.acquire(timeout=eva.core.config.timeout):
        logging.critical('_t_log_cleaner locking(1) broken')
        eva.core.critical()
        return
    try:
        _l = _log_records.copy()
    except:
        eva.core.log_traceback()
    finally:
        _log_record_lock.release()
    for l in _l:
        if time.time() - l['t'] > eva.core.config.keep_logmem:
            if not _log_record_lock.acquire(timeout=eva.core.config.timeout):
                logging.critical('_t_log_cleaner locking(1) broken')
                eva.core.critical()
                break
            try:
                _log_records.remove(l)
            except:
                eva.core.log_traceback()
            finally:
                _log_record_lock.release()
