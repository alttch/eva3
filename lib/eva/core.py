__author__ = "Altertech Group, http://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2017 Altertech Group"
__license__ = "See http://www.eva-ics.com/"
__version__ = "3.0.1"

import sys
import platform
import os
import stat
import logging
import configparser
import traceback
import time
import sqlite3
import jsonpickle
import signal
import psutil
import threading

from eva.tools import format_json
from eva.tools import wait_for as _wait_for

from eva.logs import MemoryLogHandler


version = __version__

timeout = 5

system_name = platform.node()

product_name = ''

product_code = ''

product_build = None

keep_logmem = 3600

keep_action_history = 3600

dir_eva_default = '/opt/eva'

debug = False

development = False

show_traceback = False

env = os.environ.copy()

cvars = {}

cvars_modified = False

polldelay = 0.01

db_update = 0

sleep_step = 0.1

db_update_codes = [ 'manual', 'instant', 'on_exit' ]

notify_on_start = True

dir_eva = os.environ['EVA_DIR'] if 'EVA_DIR' in os.environ \
                                            else dir_eva_default
dir_var = dir_eva + '/var'
dir_etc = dir_eva + '/etc'
dir_xc = dir_eva + '/xc'
dir_runtime = dir_eva + '/runtime'

userdb_file = None
db_file = None

pid_file = None

log_file = None

primary_config = None

logger = None

log_file_handler = None

exec_before_save = None
exec_after_save = None

mqtt_update_default = None

_save_func = set()
_dump_func = {}
_stop_func = set()

_sigterm_sent = False


def sighandler_hup(signum, frame):
    logging.info('got HUP signal, rotating logs')
    try:
        reset_log()
    except:
        log_traceback()


def sighandler_term(signum, frame):
    global _sigterm_sent
    logging.info('got TERM signal, exiting')
    if db_update == 2:
        save()
    shutdown()
    unlink_pid_file()
    _sigterm_sent = True
    logging.info('EVA core shut down')
    sys.exit(0)


def save(func = None):
    result = True
    if exec_before_save:
        logging.debug('executing before save command "%s"' % \
                exec_before_save)
        code = os.system(exec_before_save)
        if code:
            logging.error('before save command exited with code %u' % \
                    result)
            return False
    if func and func in _save_func:
        if not func(): result = False
    else:
        for f in _save_func:
            try:
                if not f(): result = False
            except:
                log_traceback()
    if exec_after_save:
        logging.debug('executing after save command "%s"' % \
                exec_after_save)
        code = os.system(exec_after_save)
        if code:
            logging.error('after save command exited with code %u' % \
                    result)
            return False
    return result


def block():
    while not _sigterm_sent:
        time.sleep(sleep_step)


def shutdown():
    for f in _stop_func:
        try:
            f()
        except:
            log_traceback()


def append_save_func(func):
    _save_func.add(func)


def remove_save_func(func):
    try:
        _save_func.remove(func)
    except:
        log_traceback()


def append_dump_func(fid, func):
    if not fid in _dump_func:
        _dump_func[fid] = func


def remove_dump_func(fid):
    try:
        del _dump_func[fid]
    except:
        log_traceback()


def append_stop_func(func):
    _stop_func.add(func)


def remove_stop_func(func):
    try:
        _stop_func.remove(func)
    except:
        log_traceback()


def create_dump():
    dump = {}
    try:
        for i, f in _dump_func.items():
            dump[i] = f()
        filename = dir_var + '/' + time.strftime('%Y%m%d%H%M%S') + \
                '.dump.json';
        open(filename,'w')
        os.chmod(filename, stat.S_IRUSR | stat.S_IWUSR)
        open(filename,'a').write(format_json(dump,
            minimal = not development))
    except:
        log_traceback()
        return None
    return filename


def serialize():
    d = {}
    d['version'] = version
    d['timeout'] = timeout
    d['system_name'] = system_name
    d['product_name'] = product_name
    d['product_code'] = product_code
    d['product_buld'] = product_build
    d['keep_logmem'] = keep_logmem
    d['keep_action_history'] = keep_action_history
    d['debug'] = debug
    d['development'] = development
    d['show_traceback'] = show_traceback
    d['cvars'] = cvars
    d['env'] = env
    d['polldelay'] = polldelay
    d['db_update'] = db_update
    d['notify_on_start'] = notify_on_start
    d['dir_eva'] = dir_eva
    d['userdb_file']= userdb_file
    d['db_file']= db_file
    d['pid_file'] = pid_file
    d['log_file'] = log_file
    d['threads'] = {}
    for t in threading.enumerate().copy():
        d['threads'][t.name] = {}
        d['threads'][t.name]['daemon'] = t.daemon
        d['threads'][t.name]['alive'] = t.is_alive()
    return d


def set_product(code, build):
    global product_code, product_build
    global pid_file, log_file, db_file
    global primary_config
    product_code = code
    product_build = build
    pid_file = '%s/%s.pid' % (dir_var, product_code)
    primary_config = '%s/etc/%s.ini' % (dir_eva, product_code)
    db_file = '%s/db/%s.db' % (dir_runtime, product_code)

def get_db():
    db = sqlite3.connect(db_file)
    return db

def get_user_db():
    if userdb_file:
        f = userdb_file
    else:
        f = db_file
    db = sqlite3.connect(f)
    return db

def reset_log(initial = False):
    global logger, log_file_handler
    if logger and not log_file: return
    logger = logging.getLogger()
    try: log_file_handler.stream.close()
    except: pass
    if initial:
        for h in logger.handlers: logger.removeHandler(h)
    else:
        logger.removeHandler(log_file_handler)
    if not development:
        formatter = logging.Formatter('%(asctime)s ' + system_name + \
            '  %(levelname)s ' + product_code + ' %(threadName)s: %(message)s')
    else:
        formatter = logging.Formatter('%(asctime)s ' + system_name + \
            ' %(levelname)s f:%(filename)s mod:%(module)s fn:%(funcName)s ' + \
            'l:%(lineno)d th:%(threadName)s :: %(message)s')
    if log_file: log_file_handler = logging.FileHandler(log_file)
    else: log_file_handler = logging.StreamHandler(sys.stdout)
    log_file_handler.setFormatter(formatter)
    logger.addHandler(log_file_handler)
    if initial:
        logger.addHandler(MemoryLogHandler())



def load(fname = None, initial = False, init_log = True):
    global system_name, log_file, pid_file, debug, development, show_traceback
    global notify_on_start, db_file, userdb_file
    global polldelay, db_update, keep_action_history, keep_logmem
    global timeout
    global exec_before_save
    global exec_after_save
    global mqtt_update_default
    fname_full = format_cfg_fname(fname)
    cfg = configparser.ConfigParser(inline_comment_prefixes=';')
    try:
        cfg.readfp(open(fname_full))
        if initial:
            try:
                pid_file = cfg.get('server', 'pid_file')
                if pid_file and pid_file[0] != '/':
                    pid_file = dir_eva + '/' + pid_file
            except:
                pass
            try:
                pid = int(open(pid_file).readline().strip())
                p = psutil.Process(pid)
                print('Can not start %s with config %s. ' % \
                        (product_name, fname_full), end = '')
                print('Another process is already running')
                return None
            except: log_traceback()
            try: log_file = cfg.get('server', 'log_file')
            except: log_file = None
            if log_file and log_file[0] != '/':
                log_file = dir_eva + '/' + log_file
            if init_log: reset_log(initial)
            try:
                development = (cfg.get('server','development') == 'yes')
                if development:
                    show_traceback = True
            except:
                development = False
            if development:
                show_traceback = True
                debug_on()
                logging.critical('DEVELOPMENT MODE STARTED')
                debug = True
            else:
                try:
                    show_traceback = (cfg.get('server',
                                        'show_traceback') == 'yes')
                except:
                    show_traceback = False
            if not development and not debug:
                try:
                    debug = (cfg.get('server','debug') == 'yes')
                    if debug: debug_on()
                except:
                    pass
                if not debug:
                        logging.basicConfig(level=logging.INFO)
                        if logger: logger.setLevel(logging.INFO)
            try: system_name = cfg.get('server', 'name')
            except: pass
            logging.info('Loading server config')
            logging.debug('server.pid_file = %s' % pid_file)
            try:
                notify_on_start = (
                        cfg.get('server','notify_on_start') == 'yes')
            except: pass
            try:
                db_file = cfg.get('server', 'db_file')
                if db_file and db_file[0] != '/':
                    db_file = dir_eva + '/' + db_file
            except:
                pass
            logging.debug('server.db_file = %s' % db_file)
            try:
                userdb_file = cfg.get('server', 'userdb_file')
                if userdb_file and userdb_file[0] != '/':
                    userdb_file = dir_eva + '/' + userdb_file
            except:
                pass
            if userdb_file is None: f = db_file
            else: f = userdb_file
            logging.debug('server.userdb_file = %s' % f)
            try:
                notify_on_start = (
                        cfg.get('server','notify_on_start') == 'yes')
            except: pass
            logging.debug('server.notify_on_start = %s' % ('yes' \
                                        if notify_on_start else 'no'))
        try: polldelay = float(cfg.get('server', 'polldelay'))
        except: pass
        try: timeout = float(cfg.get('server', 'timeout'))
        except: pass
        logging.debug('server.timeout = %s' % timeout)
        logging.debug('server.polldelay = %s  ( %s msec )' % \
                                            (polldelay, int(polldelay * 1000)))
        try: db_update = db_update_codes.index(cfg.get('server', 'db_update'))
        except: pass
        logging.debug('server.db_update = %s' % db_update_codes[db_update])
        try:
            keep_action_history = int(cfg.get('server', 'keep_action_history'))
        except: pass
        logging.debug('server.keep_action_history = %s sec' % \
                keep_action_history)
        try:
            keep_logmem = int(cfg.get('server', 'keep_logmem'))
        except: pass
        logging.debug('server.keep_logmem = %s sec' % keep_logmem)
        try:
            exec_before_save = cfg.get('server', 'exec_before_save')
        except: pass
        logging.debug('server.exec_before_save = %s' % exec_before_save)
        try:
            exec_after_save = cfg.get('server', 'exec_after_save')
        except: pass
        logging.debug('server.exec_after_save = %s' % exec_after_save)
        try:
            mqtt_update_default = cfg.get('server', 'mqtt_update_default')
        except: pass
        logging.debug('server.mqtt_update_default = %s' % mqtt_update_default)
        return cfg
    except:
        print('Can not read primary config %s' % fname_full)
        log_traceback(True)
    return False


def load_cvars(fname = None):
    global env, cvars
    fname_full = format_cfg_fname(fname, 'cvars', ext = 'json', runtime = True)
    if not fname_full:
        logging.warning('No file or product specified,' + \
                            ' skipping loading custom variables')
        return False
    _cvars = {}
    _env = {}
    _env = os.environ.copy()
    if not 'PATH' in _env: _env['PATH'] = ''
    _env['PATH'] = '%s/bin:%s/xbin:' % (dir_eva, dir_eva) + _env['PATH']
    logging.info('Loading custom vars from %s' % fname_full)
    try:
        raw = ''.join(open(fname_full).readlines())
        _cvars = jsonpickle.decode(raw)
    except:
        logging.error('can not load custom vars from %s' % fname_full)
        log_traceback()
        return False
    for i, v in _cvars.items():
        logging.debug('custom var %s = "%s"' % (i, v))
    env = _env
    cvars = _cvars
    cvars_modified = False
    return True


def save_cvars(fname = None):
    fname_full = format_cfg_fname(fname, 'cvars', ext = 'json', runtime = True)
    logging.info('Saving custom vars to %s' % fname_full)
    try:
        open(fname_full,'w').write(format_json(cvars, minimal = False))
    except:
        logging.error('can not save custom vars into %s' % fname_full)
        log_traceback()
        return False
    return True


def get_cvar(var):
    return cvars[var] if var in cvars else None


def set_cvar(var, value = None):
    if not var: return False
    if value is not None:
        cvars[var] = value
    else:
        try:
            del cvars[var]
        except:
            return False
    if db_update == 1: save_cvars()
    else: cvars_modified = True
    return True


def save_modified():
    return save_cvars() if cvars_modified else True


def debug_on():
    global debug
    debug = True
    logging.basicConfig(level=logging.DEBUG)
    if logger: logger.setLevel(logging.DEBUG)
    logging.info('Debug mode ON')


def debug_off():
    global debug
    debug = False
    if logger: logger.setLevel(logging.INFO)
    logging.info('Debug mode OFF')


def fork():
    if os.fork(): time.sleep(1);sys.exit()


def write_pid_file():
    try:
        open(pid_file,'w').write(str(os.getpid()))
    except:
        log_traceback()


def unlink_pid_file():
    try:
        os.unlink(pid_file)
    except:
        log_traceback()


def wait_for(func, wait_timeout = None, delay = None, wait_for_false = False):
    if wait_timeout: t = wait_timeout
    else: t = timeout
    if delay: p = delay
    else: p = polldelay
    return _wait_for(func = func, wait_timeout = t, delay = p,
            wait_for_false = wait_for_false)


def log_traceback(display = False, notifier = False, force = False):
    if (show_traceback or force) and not display:
        pfx = '.' if notifier else ''
        logging.debug(pfx + traceback.format_exc())
    elif display:
        print(traceback.format_exc())


def format_xc_fname(item = None, xc_type = '', fname = None, update = False):
    path = dir_xc + '/' + product_code
    if fname:
        return fname if fname[0]=='/' else path + '/' + fname
    if not item: return None
    fname = item.item_id
    if update: fname += '_update'
    if xc_type: fname += '.' + xc_type
    return path + '/' + fname


def format_cfg_fname(fname, cfg = None, ext = 'ini', path = None,
        runtime = False):
    if path: _path = path
    else:
        if runtime: _path = dir_runtime
        else: _path = dir_etc
    if not fname:
        if cfg: sfx = '_' + cfg
        else: sfx = ''
        if product_code:
            return '%s/%s%s.%s' % (_path, product_code, sfx, ext)
        else: return None
    elif fname[0]!='.' and fname[0]!='/': return _path + '/' + fname
    else: return fname


def init():
    append_save_func(save_modified)
    append_dump_func('eva-core', serialize)
    signal.signal(signal.SIGHUP, sighandler_hup)
    signal.signal(signal.SIGTERM, sighandler_term)

