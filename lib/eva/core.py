__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.0"

import sys
import platform
import os
import stat
import logging
import configparser
import traceback
import time
import jsonpickle
import signal
import psutil
import threading
import inspect
import sqlalchemy as sa
import faulthandler

from eva.tools import format_json
from eva.tools import wait_for as _wait_for

from eva.tools import Locker as GenericLocker

from eva.exceptions import FunctionFailed

from pyaltt import g
from pyaltt import FunctionCollecton
from pyaltt import background_job

from twisted.internet import reactor

from types import SimpleNamespace

version = __version__

timeout = 5

system_name = platform.node()

keep_logmem = 3600

keep_action_history = 3600

action_cleaner_interval = 60

max_shutdown_time = 15

default_action_cleaner_interval = 60

dir_eva_default = '/opt/eva'

debug = False

setup_mode = False

development = False

show_traceback = False

stop_on_critical = 'always'

dump_on_critical = True

env = os.environ.copy()

cvars = {}

cvars_modified = False

_flags = SimpleNamespace(
    ignore_critical=False,
    sigterm_sent=False,
    started=False,
    shutdown_requested=False)

product = SimpleNamespace(name='', code='', build=None)

config = SimpleNamespace(
    pid_file = None,
    log_file = None,
    db_uri = None,
    userdb_uri = None)

polldelay = 0.01

db_update = 0

db_pool_size = 15

sleep_step = 0.1

keep_exceptions = 100

reactor_thread_pool = 15

_exceptions = []

_exception_log_lock = threading.RLock()

_db_lock = threading.RLock()
_userdb_lock = threading.RLock()

db_update_codes = ['manual', 'instant', 'on_exit']

notify_on_start = True

dir_eva = os.environ['EVA_DIR'] if 'EVA_DIR' in os.environ \
                                            else dir_eva_default
dir_var = dir_eva + '/var'
dir_etc = dir_eva + '/etc'
dir_xc = dir_eva + '/xc'
dir_ui = dir_eva + '/ui'
dir_pvt = dir_eva + '/pvt'
dir_lib = dir_eva + '/lib'
dir_runtime = dir_eva + '/runtime'


db_engine = None
userdb_engine = None

logger = None

log_file_handler = None

exec_before_save = None
exec_after_save = None

mqtt_update_default = None

start_time = time.time()

enterprise_layout = True

user_hook = None

_flags.shutdown_requested = False

default_log_level_name = 'info'
default_log_level_id = 20
default_log_level = logging.INFO


def critical(log=True, from_driver=False):
    if _flags.ignore_critical: return
    try:
        caller = inspect.getouterframes(inspect.currentframe(), 2)[1]
        caller_info = '%s:%s %s' % (caller.filename, caller.lineno,
                                    caller.function)
    except:
        caller_info = ''
    if log: log_traceback(force=True)
    if dump_on_critical:
        _flags.ignore_critical = True
        logging.critical('critical exception. dump file: %s' % create_dump(
            'critical', caller_info))
        _flags.ignore_critical = False
    if stop_on_critical in ['always', 'yes'] or (not from_driver and
                                                 stop_on_critical == 'core'):
        _flags.ignore_critical = True
        logging.critical('critical exception, shutting down')
        sighandler_term(None, None)


class Locker(GenericLocker):

    def __init__(self, mod=''):

        super().__init__(mod=mod, relative=False)
        self.critical = critical


class RLocker(GenericLocker):

    def __init__(self, mod=''):

        super().__init__(mod=mod, relative=True)
        self.critical = critical


def log_traceback(display=False, notifier=False, force=False, e=None):
    e_msg = traceback.format_exc()
    if (show_traceback or force) and not display:
        pfx = '.' if notifier else ''
        logging.error(pfx + e_msg)
    elif display:
        print(e_msg)
    if not _exception_log_lock.acquire(timeout=timeout):
        logging.critical('log_traceback locking broken')
        critical(log=False)
        return
    try:
        e = {'t': time.strftime('%Y/%m/%d %H:%M:%S %z'), 'e': e_msg}
        _exceptions.append(e)
        if len(_exceptions) > keep_exceptions:
            del _exceptions[0]
    finally:
        _exception_log_lock.release()


cvars_lock = RLocker('core')

dump = FunctionCollecton(on_error=log_traceback, include_exceptions=True)
save = FunctionCollecton(on_error=log_traceback)
shutdown = FunctionCollecton(on_error=log_traceback)
stop = FunctionCollecton(on_error=log_traceback)


def format_db_uri(db_uri):
    if not db_uri: return None
    if db_uri.find('://') == -1:
        if db_uri[0] == '/':
            _uri = db_uri
        else:
            _uri = dir_eva + '/' + db_uri
        _uri = 'sqlite:///' + _uri
    else:
        _uri = db_uri
    return _uri


def create_db_engine(db_uri):
    if not db_uri: return None
    if db_uri.startswith('sqlite:///'):
        return sa.create_engine(db_uri)
    else:
        return sa.create_engine(
            db_uri, pool_size=db_pool_size, max_overflow=db_pool_size * 2)


def sighandler_hup(signum, frame):
    logging.info('got HUP signal, rotating logs')
    try:
        reset_log()
    except:
        log_traceback()


def suicide(**kwargs):
    time.sleep(max_shutdown_time)
    logging.critical('SUICIDE')
    if show_traceback:
        faulthandler.dump_traceback()
    os.kill(os.getpid(), signal.SIGKILL)


def sighandler_term(signum=None, frame=None):
    if _flags.sigterm_sent: return
    _flags.sigterm_sent = True
    background_job(suicide, daemon=True)()
    logging.info('got TERM signal, exiting')
    if db_update == 2:
        try:
            do_save()
        except:
            eva.core.log_traceback()
    core_shutdown()
    unlink_pid_file()
    logging.info('EVA core shut down')


def sighandler_int(signum, frame):
    pass


def prepare_save():
    if not exec_before_save: return True
    logging.debug('executing before save command "%s"' % \
        exec_before_save)
    code = os.system(exec_before_save)
    if code:
        logging.error('before save command exited with code %u' % \
            code)
        raise FunctionFailed('exec_before_save failed')
    return True


def finish_save():
    if not exec_after_save: return True
    logging.debug('executing after save command "%s"' % \
        exec_after_save)
    code = os.system(exec_after_save)
    if code:
        logging.error('after save command exited with code %u' % \
            code)
        raise FunctionFailed('exec_before_save failed')
    return True


def do_save():
    prepare_save()
    try:
        success = save.execute()[1]
    finally:
        finish_save()
    return success


def block():
    _flags.started = True
    reactor.run(installSignalHandlers=False)


def is_shutdown_requested():
    return _flags.shutdown_requested


def is_started():
    return _flags.started


def core_shutdown():
    _flags.shutdown_requested = True
    shutdown()
    stop()
    reactor.callFromThread(reactor.stop)


def create_dump(e='request', msg=''):
    import gzip
    try:
        result = dump.run()
        result.update({'reason': {'event': e, 'info': str(msg)}})
        filename = dir_var + '/' + time.strftime('%Y%m%d%H%M%S') + \
                '.dump.gz'
        gzip.open(filename, 'w')
        os.chmod(filename, stat.S_IRUSR | stat.S_IWUSR)
        gzip.open(filename, 'a').write(
            format_json(result, minimal=not development,
                        unpicklable=True).encode())
        logging.warning(
            'dump created, file: %s, event: %s (%s)' % (filename, e, msg))
    except:
        log_traceback()
        return None
    return filename


@cvars_lock
@dump
def serialize():
    d = {}
    proc = psutil.Process()
    d['version'] = version
    d['timeout'] = timeout
    d['system_name'] = system_name
    d['product_name'] = product.name
    d['product_code'] = product.code
    d['product_build'] = product.build
    d['keep_logmem'] = keep_logmem
    d['keep_action_history'] = keep_action_history
    d['action_cleaner_interval'] = action_cleaner_interval
    d['debug'] = debug
    d['development'] = development
    d['show_traceback'] = show_traceback
    d['stop_on_critical'] = stop_on_critical
    d['cvars'] = cvars
    d['env'] = env
    d['polldelay'] = polldelay
    d['db_update'] = db_update
    d['notify_on_start'] = notify_on_start
    d['dir_eva'] = dir_eva
    d['db_uri'] = config.db_uri
    d['userdb_uri'] = config.userdb_uri
    d['pid_file'] = config.pid_file
    d['log_file'] = config.log_file
    d['threads'] = {}
    d['uptime'] = int(time.time() - start_time)
    d['exceptions'] = _exceptions
    d['fd'] = proc.open_files()
    for t in threading.enumerate().copy():
        d['threads'][t.name] = {}
        d['threads'][t.name]['daemon'] = t.daemon
        d['threads'][t.name]['alive'] = t.is_alive()
    return d


def set_product(code, build):
    product.code = code
    product.build = build
    config.pid_file = '%s/%s.pid' % (dir_var, product.code)
    config.db_uri = format_db_uri('db/%s.db' % product.code)
    config.userdb_uri = config.db_uri
    set_db(config.db_uri, config.userdb_uri)


def set_db(db_uri=None, userdb_uri=None):
    global db_engine, userdb_engine
    db_engine = create_db_engine(db_uri)
    userdb_engine = create_db_engine(userdb_uri)


def db():
    with _db_lock:
        if not g.has('db'):
            if db_update == 1:
                g.db = db_engine.connect()
            else:
                g.db = db_engine
        return g.db


def userdb():
    with _userdb_lock:
        if not g.has('userdb'):
            if db_update == 1:
                g.userdb = userdb_engine.connect()
            else:
                g.userdb = userdb_engine
        return g.userdb


def reset_log(initial=False):
    global logger, log_file_handler
    if logger and not config.log_file: return
    logger = logging.getLogger()
    try:
        log_file_handler.stream.close()
    except:
        pass
    if initial:
        for h in logger.handlers:
            logger.removeHandler(h)
    else:
        logger.removeHandler(log_file_handler)
    if not development:
        formatter = logging.Formatter('%(asctime)s ' + system_name + \
            '  %(levelname)s ' + product.code + ' %(threadName)s: %(message)s')
    else:
        formatter = logging.Formatter('%(asctime)s ' + system_name + \
            ' %(levelname)s f:%(filename)s mod:%(module)s fn:%(funcName)s ' + \
            'l:%(lineno)d th:%(threadName)s :: %(message)s')
    if config.log_file: log_file_handler = logging.FileHandler(config.log_file)
    else: log_file_handler = logging.StreamHandler(sys.stdout)
    log_file_handler.setFormatter(formatter)
    logger.addHandler(log_file_handler)
    if initial:
        from eva.logs import MemoryLogHandler
        logger.addHandler(MemoryLogHandler())


def load(fname=None, initial=False, init_log=True, check_pid=True):
    global system_name, debug, development, show_traceback
    global stop_on_critical, dump_on_critical
    global notify_on_start
    global polldelay, db_update, keep_action_history, action_cleaner_interval
    global keep_logmem, default_log_level, default_log_level_name
    global default_log_level_id
    global timeout
    global exec_before_save
    global exec_after_save
    global mqtt_update_default
    global enterprise_layout
    global reactor_thread_pool
    global user_hook
    from eva.logs import log_levels_by_name
    fname_full = format_cfg_fname(fname)
    cfg = configparser.ConfigParser(inline_comment_prefixes=';')
    try:
        cfg.read(fname_full)
        if initial:
            try:
                config.pid_file = cfg.get('server', 'pid_file')
                if config.pid_file and config.pid_file[0] != '/':
                    config.pid_file = dir_eva + '/' + config.pid_file
            except:
                pass
            try:
                if not check_pid: raise Exception('no check required')
                pid = int(open(config.pid_file).readline().strip())
                p = psutil.Process(pid)
                print('Can not start %s with config %s. ' % \
                        (product.name, fname_full), end = '')
                print('Another process is already running')
                return None
            except:
                pass
            if not os.environ.get('EVA_CORE_LOG_STDOUT'):
                try:
                    config.log_file = cfg.get('server', 'log_file')
                except:
                    config.log_file = None
            if config.log_file and config.log_file[0] != '/':
                config.log_file = dir_eva + '/' + config.log_file
            if init_log: reset_log(initial)
            try:
                log_level = cfg.get('server', 'logging_level')
                if log_level in log_levels_by_name:
                    default_log_level_name = log_level
                    default_log_level_id = log_levels_by_name.get(log_level)
                    default_log_level = getattr(logging, log_level.upper())
            except:
                pass
            try:
                development = (cfg.get('server', 'development') == 'yes')
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
                    if os.environ.get('EVA_CORE_DEBUG'):
                        debug = True
                        show_traceback = True
                    else:
                        debug = (cfg.get('server', 'debug') == 'yes')
                    if debug: debug_on()
                except:
                    pass
                if not debug:
                    logging.basicConfig(level=default_log_level)
                    if logger: logger.setLevel(default_log_level)
            try:
                system_name = cfg.get('server', 'name')
            except:
                pass
            logging.info('Loading server config')
            logging.debug('server.pid_file = %s' % config.pid_file)
            logging.debug('server.logging_level = %s' % default_log_level_name)
            try:
                notify_on_start = (cfg.get('server',
                                           'notify_on_start') == 'yes')
            except:
                pass
            logging.debug('server.notify_on_start = %s' % ('yes' \
                                        if notify_on_start else 'no'))
            try:
                stop_on_critical = (cfg.get('server', 'stop_on_critical'))
            except:
                pass
            if stop_on_critical == 'yes': stop_on_critical = 'always'
            elif stop_on_critical not in ('no', 'always', 'core'):
                stop_on_critical = 'no'
            logging.debug('server.stop_on_critical = %s' % stop_on_critical)
            try:
                dump_on_critical = (cfg.get('server',
                                            'dump_on_critical') == 'yes')
            except:
                pass
            logging.debug('server.dump_on_critical = %s' % ('yes' \
                                        if dump_on_critical else 'no'))
            try:
                db_file = cfg.get('server', 'db_file')
            except:
                db_file = None
            try:
                db_uri = cfg.get('server', 'db')
            except:
                if db_file: db_uri = db_file
            config.db_uri = format_db_uri(db_uri)
            logging.debug('server.db = %s' % config.db_uri)
            try:
                userdb_file = cfg.get('server', 'userdb_file')
            except:
                userdb_file = None
            try:
                userdb_uri = cfg.get('server', 'userdb')
            except:
                if userdb_file: userdb_uri = userdb_file
                else: userdb_uri = None
            if userdb_uri:
                config.userdb_uri = format_db_uri(userdb_uri)
            else:
                config.userdb_uri = config.db_uri
            logging.debug('server.userdb = %s' % config.userdb_uri)
            try:
                user_hook = cfg.get('server', 'user_hook').split()
            except:
                pass
            _uh = ' '.join(user_hook) if user_hook else None
            logging.debug('server.user_hook = %s' % _uh)
            try:
                enterprise_layout = (cfg.get('server', 'layout') != 'simple')
            except:
                pass
            logging.debug('server.layout = %s' % ('enterprise' \
                                        if enterprise_layout else 'simple'))
        try:
            polldelay = float(cfg.get('server', 'polldelay'))
        except:
            pass
        try:
            timeout = float(cfg.get('server', 'timeout'))
        except:
            pass
        if not polldelay: polldelay = 0.01
        logging.debug('server.timeout = %s' % timeout)
        logging.debug('server.polldelay = %s  ( %s msec )' % \
                                            (polldelay, int(polldelay * 1000)))
        try:
            reactor_thread_pool = int(cfg.get('server', 'reactor_thread_pool'))
        except:
            pass
        logging.debug('server.reactor_thread_pool = %s' % reactor_thread_pool)
        try:
            db_update = db_update_codes.index(cfg.get('server', 'db_update'))
        except:
            pass
        logging.debug('server.db_update = %s' % db_update_codes[db_update])
        try:
            keep_action_history = int(cfg.get('server', 'keep_action_history'))
        except:
            pass
        logging.debug('server.keep_action_history = %s sec' % \
                keep_action_history)
        try:
            action_cleaner_interval = int(
                cfg.get('server', 'action_cleaner_interval'))
            if action_cleaner_interval < 0: raise Exception('invalid interval')
        except:
            action_cleaner_interval = default_action_cleaner_interval
        logging.debug('server.action_cleaner_interval = %s sec' % \
                action_cleaner_interval)
        try:
            keep_logmem = int(cfg.get('server', 'keep_logmem'))
        except:
            pass
        logging.debug('server.keep_logmem = %s sec' % keep_logmem)
        try:
            exec_before_save = cfg.get('server', 'exec_before_save')
        except:
            pass
        logging.debug('server.exec_before_save = %s' % exec_before_save)
        try:
            exec_after_save = cfg.get('server', 'exec_after_save')
        except:
            pass
        logging.debug('server.exec_after_save = %s' % exec_after_save)
        try:
            mqtt_update_default = cfg.get('server', 'mqtt_update_default')
        except:
            pass
        logging.debug('server.mqtt_update_default = %s' % mqtt_update_default)
        return cfg
    except:
        print('Can not read primary config %s' % fname_full)
        log_traceback(True)
    return False


@cvars_lock
def load_cvars(fname=None):
    global env, cvars
    fname_full = format_cfg_fname(fname, 'cvars', ext='json', runtime=True)
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


@cvars_lock
def save_cvars(fname=None):
    fname_full = format_cfg_fname(fname, 'cvars', ext='json', runtime=True)
    logging.info('Saving custom vars to %s' % fname_full)
    try:
        open(fname_full, 'w').write(format_json(cvars, minimal=False))
    except:
        logging.error('can not save custom vars into %s' % fname_full)
        log_traceback()
        return False
    return True


@cvars_lock
def get_cvar(var=None):
    if var:
        return cvars[var] if var in cvars else None
    else:
        return cvars.copy()


@cvars_lock
def set_cvar(var, value=None):
    if not var: return False
    if value is not None:
        cvars[str(var)] = str(value)
    elif var not in cvars:
        return None
    else:
        try:
            del cvars[str(var)]
        except:
            return False
    if db_update == 1: save_cvars()
    else: cvars_modified = True
    return True


@save
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
    if logger: logger.setLevel(default_log_level)
    logging.info('Debug mode OFF')


def setup_off():
    global setup_mode
    setup_mode = False
    logging.info('Setup mode OFF')


def setup_on():
    global setup_mode
    setup_mode = True
    logging.warning('Setup mode ON')


def fork():
    if os.fork():
        time.sleep(1)
        sys.exit()


def write_pid_file():
    try:
        open(config.pid_file, 'w').write(str(os.getpid()))
    except:
        log_traceback()


def unlink_pid_file():
    try:
        os.unlink(config.pid_file)
    except:
        log_traceback()


def wait_for(func, wait_timeout=None, delay=None, wait_for_false=False):
    if wait_timeout: t = wait_timeout
    else: t = timeout
    if delay: p = delay
    else: p = polldelay
    return _wait_for(func, t, p, wait_for_false, is_shutdown_requested)


def format_xc_fname(item=None, xc_type='', fname=None, update=False):
    path = dir_xc + '/' + product.code
    if fname:
        return fname if fname[0] == '/' else path + '/' + fname
    if not item: return None
    fname = item.item_id
    if update: fname += '_update'
    if xc_type: fname += '.' + xc_type
    return path + '/' + fname


def format_cfg_fname(fname, cfg=None, ext='ini', path=None, runtime=False):
    if path: _path = path
    else:
        if runtime: _path = dir_runtime
        else: _path = dir_etc
    if not fname:
        if cfg: sfx = '_' + cfg
        else: sfx = ''
        if product.code:
            return '%s/%s%s.%s' % (_path, product.code, sfx, ext)
        else:
            return None
    elif fname[0] != '.' and fname[0] != '/':
        return _path + '/' + fname
    else:
        return fname


def report_db_error(raise_exeption=True):
    logging.critical('DB ERROR')
    log_traceback()
    if raise_exeption:
        raise FunctionFailed


def report_userdb_error(raise_exeption=True):
    logging.critical('USERDB ERROR')
    log_traceback()
    if raise_exeption:
        raise FunctionFailed


def dummy_true():
    return True


def dummy_false():
    return False


def init():
    signal.signal(signal.SIGHUP, sighandler_hup)
    signal.signal(signal.SIGTERM, sighandler_term)
    Locker.timeout = timeout
    RLocker.timeout = timeout
    if not os.environ.get('EVA_CORE_ENABLE_CC'):
        signal.signal(signal.SIGINT, sighandler_int)
    else:
        signal.signal(signal.SIGINT, sighandler_term)


def start():
    reactor.suggestThreadPoolSize(reactor_thread_pool)
    set_db(config.db_uri, config.userdb_uri)


#BD: 20.05.2017
