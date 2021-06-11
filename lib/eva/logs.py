__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"

import logging
import eva.core
import time
import sys
import os

import pyaltt2.logs

from eva.exceptions import InvalidParameter

from eva.tools import SimpleNamespace

from functools import partial

KEEP_EXCEPTIONS = 100

log_levels_by_name = {
    'debug': 10,
    'info': 20,
    'warning': 30,
    'error': 40,
    'critical': 50
}

log_levels_by_id = {v: k for k, v in log_levels_by_name.items()}


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
        level = log_levels_by_id.get(l, logging.getLevelName(l))
    return level


def handle_append(rd, **kwargs):
    import eva.notify
    rd['lvl'] = get_log_level_by_id(rd['l'])
    eva.notify.notify('log', [rd], **kwargs)


def init():
    if eva.core.config.log_format:
        log_format = eva.core.config.log_format
    else:
        log_format = ('%(asctime)s ' + \
                eva.core.config.system_name + \
            ' %(levelname)s f:%(filename)s mod:%(module)s fn:%(funcName)s ' + \
            'l:%(lineno)d th:%(threadName)s :: %(message)s') if \
                eva.core.config.development else \
                ('%(asctime)s ' + eva.core.config.system_name + \
                '  %(levelname)s ' + eva.core.product.code + \
                ' %(threadName)s: %(message)s')
    formatter = logging.Formatter(log_format)
    pyaltt2.logs.handle_append = handle_append
    pyaltt2.logs.init(
        name=eva.core.product.code,
        host=eva.core.config.system_name,
        log_file=eva.core.config.log_file,
        log_stdout=1 if os.environ.get('EVA_CORE_LOG_STDOUT') else 0,
        syslog=eva.core.config.syslog,
        level=eva.core.config.default_log_level_id,
        tracebacks=eva.core.config.show_traceback,
        ignore='.',
        ignore_mods=['_cplogging'],
        stdout_ignore=os.environ.get('EVA_CORE_SNLSO') == '1',
        keep_logmem=eva.core.config.keep_logmem,
        keep_exceptions=KEEP_EXCEPTIONS,
        colorize=os.environ.get('EVA_CORE_RAW_STDOUT') != '1',
        formatter=formatter,
        syslog_formatter=logging.Formatter(eva.core.config.syslog_format)
        if eva.core.config.syslog_format else None,
        log_json=log_format.startswith('{') or log_format.endswith('}'),
        syslog_json=eva.core.config.syslog_format and
        (eva.core.config.syslog_format.startswith('{') or
         eva.core.config.syslog_format.endswith('}')),
    )


def start():
    pyaltt2.logs.start(loop='cleaners')


@eva.core.stop
def stop():
    pyaltt2.logs.stop()
