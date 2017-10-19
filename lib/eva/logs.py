__author__ = "Altertech Group, http://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2017 Altertech Group"
__license__ = "See http://www.eva-ics.com/"
__version__ = "3.0.0"

import logging
import eva.notify
import eva.core
import time
import threading

_log_records = []
_mute = False

log_cleaner_delay = 5

_log_cleaner_active = False

_log_cleaner = None


class MemoryLogHandler(logging.Handler):

    def emit(self, record):
        log_append(record)


def log_append(record = None, rd = None, skip_mqtt = False):
    if record:
        _r = {} 
        _r['t'] = record.created
        _r['msg'] = record.getMessage()
        _r['l'] = record.levelno
        _r['th'] = record.threadName
        _r['mod'] = record.module
        _r['h'] = eva.core.system_name
        _r['p'] = eva.core.product_code
    elif rd:
        _r = rd
    else:
        return
    if not _mute and _r['msg'] and _r['msg'][0] != '.' and \
            _r['mod'] != '_cplogging':
        _log_records.append(_r)
        eva.notify.notify(
                'log',
                [ _r ],
                skip_mqtt = skip_mqtt
                )


def mute():
    global _mute
    _mute = True

def unmute():
    global _mute
    _mute = False


def start():
    global _log_cleaner
    global _log_cleaner_active
    eva.core.append_stop_func(stop)
    _log_cleaner = threading.Thread(target = _t_log_cleaner,
            name = '_t_log_cleaner')
    _log_cleaner_active = True
    _log_cleaner.start()


def stop():
    global _log_cleaner_active
    if _log_cleaner_active:
        _log_cleaner_active = False
        _log_cleaner.join()


def log_get(logLevel = 0, t = 0, n = None):
    _lr = []
    if n:
        max_entries = n
    else:
        max_entries = -1
    if t:
        _t = time.time() - t
    else:
        _t = 0
    for r in reversed(_log_records):
        if r['t'] > _t and r['l'] >= logLevel:
            _lr = [ r ] + _lr
            if n and len(_lr) >= n:
                break
    return _lr


def _t_log_cleaner():
    logging.debug('memlog cleaner started')
    while _log_cleaner_active:
        try:
            for l in _log_records.copy():
                if time.time() - l['t'] > eva.core.keep_logmem:
                    _log_records.remove(l)
        except:
            eva.core.log_traceback()
        i = 0
        while i < log_cleaner_delay and _log_cleaner_active:
            time.sleep(eva.core.sleep_step); i += eva.core.sleep_step
    logging.debug('memlog cleaner stopped')

