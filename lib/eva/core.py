__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.4"

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
import gzip

from eva.tools import format_json
from eva.tools import wait_for as _wait_for
from eva.tools import parse_host_port

from eva.tools import Locker as GenericLocker

from eva.exceptions import FunctionFailed

from pyaltt import g
from pyaltt import FunctionCollecton
from pyaltt import background_job

from twisted.internet import reactor

from types import SimpleNamespace

version = __version__

max_shutdown_time = 30

default_action_cleaner_interval = 60

dir_eva_default = '/opt/eva'

env = {}
cvars = {}

_flags = SimpleNamespace(
    ignore_critical=False,
    sigterm_sent=False,
    started=False,
    shutdown_requested=False,
    cvars_modified=False,
    setup_mode=0)

product = SimpleNamespace(name='', code='', build=None)

config = SimpleNamespace(
    pid_file=None,
    log_file=None,
    db_uri=None,
    userdb_uri=None,
    debug=False,
    system_name=platform.node(),
    controller_name=None,
    development=False,
    show_traceback=False,
    stop_on_critical='always',
    dump_on_critical=True,
    polldelay=0.01,
    db_update=0,
    keep_action_history=3600,
    action_cleaner_interval=60,
    notify_on_start=True,
    keep_logmem=3600,
    default_log_level_name='info',
    default_log_level_id=20,
    default_log_level=logging.INFO,
    timeout=5,
    exec_before_save=None,
    exec_after_save=None,
    mqtt_update_default=None,
    enterprise_layout=True,
    syslog=None,
    reactor_thread_pool=15,
    user_hook=None)

db_engine = SimpleNamespace(primary=None, user=None)

log_engine = SimpleNamespace(
    logger=None, log_file_handler=None, syslog_handler=None)

db_pool_size = 15

sleep_step = 0.1

keep_exceptions = 100

_exceptions = []

_exception_log_lock = threading.RLock()

_db_lock = threading.RLock()
_userdb_lock = threading.RLock()

db_update_codes = ['manual', 'instant', 'on_exit']

dir_eva = os.environ['EVA_DIR'] if 'EVA_DIR' in os.environ \
                                            else dir_eva_default
dir_var = dir_eva + '/var'
dir_etc = dir_eva + '/etc'
dir_xc = dir_eva + '/xc'
dir_ui = dir_eva + '/ui'
dir_pvt = dir_eva + '/pvt'
dir_lib = dir_eva + '/lib'
dir_runtime = dir_eva + '/runtime'

start_time = time.time()


def critical(log=True, from_driver=False):
    if _flags.ignore_critical: return
    try:
        caller = inspect.getouterframes(inspect.currentframe(), 2)[1]
        caller_info = '%s:%s %s' % (caller.filename, caller.lineno,
                                    caller.function)
    except:
        caller_info = ''
    if log: log_traceback(force=True)
    if config.dump_on_critical:
        _flags.ignore_critical = True
        logging.critical('critical exception. dump file: %s' % create_dump(
            'critical', caller_info))
        _flags.ignore_critical = False
    if config.stop_on_critical in [
            'always', 'yes'
    ] or (not from_driver and config.stop_on_critical == 'core'):
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
    if (config.show_traceback or force) and not display:
        pfx = '.' if notifier else ''
        logging.error(pfx + e_msg)
    elif display:
        print(e_msg)
    if not _exception_log_lock.acquire(timeout=config.timeout):
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
    _db_uri = db_uri
    if _db_uri.startswith('sqlite:///'):
        _db_uri = _db_uri[10:]
    if _db_uri.find('://') == -1:
        if _db_uri[0] == '/':
            _uri = _db_uri
        else:
            _uri = dir_eva + '/' + _db_uri
        _uri = 'sqlite:///' + _uri
    else:
        _uri = _db_uri
    return _uri


def create_db_engine(db_uri, timeout=None):
    if not db_uri: return None
    if db_uri.startswith('sqlite:///'):
        return sa.create_engine(
            db_uri,
            connect_args={'timeout': timeout if timeout else config.timeout})
    else:
        return sa.create_engine(
            db_uri,
            pool_size=db_pool_size,
            max_overflow=db_pool_size * 2,
            isolation_level='READ UNCOMMITTED')


def sighandler_hup(signum, frame):
    logging.info('got HUP signal, rotating logs')
    try:
        reset_log()
    except:
        log_traceback()


def suicide(**kwargs):
    time.sleep(max_shutdown_time)
    logging.critical('SUICIDE')
    if config.show_traceback:
        faulthandler.dump_traceback()
    os.kill(os.getpid(), signal.SIGKILL)


def sighandler_term(signum=None, frame=None):
    if _flags.sigterm_sent: return
    _flags.sigterm_sent = True
    background_job(suicide, daemon=True)()
    logging.info('got TERM signal, exiting')
    if config.db_update == 2:
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
    if not config.exec_before_save: return True
    logging.debug('executing before save command "%s"' % \
        config.exec_before_save)
    code = os.system(config.exec_before_save)
    if code:
        logging.error('before save command exited with code %u' % \
            code)
        raise FunctionFailed('exec_before_save failed')
    return True


def finish_save():
    if not config.exec_after_save: return True
    logging.debug('executing after save command "%s"' % \
        config.exec_after_save)
    code = os.system(config.exec_after_save)
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
    try:
        result = dump.run()
        result.update({'reason': {'event': e, 'info': str(msg)}})
        filename = dir_var + '/' + time.strftime('%Y%m%d%H%M%S') + \
                '.dump.gz'
        dmp = format_json(
            result, minimal=not config.development, unpicklable=True).encode()
        gzip.open(filename, 'w')
        os.chmod(filename, stat.S_IRUSR | stat.S_IWUSR)
        gzip.open(filename, 'a').write(dmp)
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
    d['timeout'] = config.timeout
    d['system_name'] = config.system_name
    d['product_name'] = product.name
    d['product_code'] = product.code
    d['product_build'] = product.build
    d['keep_logmem'] = config.keep_logmem
    d['keep_action_history'] = config.keep_action_history
    d['action_cleaner_interval'] = config.action_cleaner_interval
    d['debug'] = config.debug
    d['setup_mode'] = _flags.setup_mode
    d['setup_mode_on'] = is_setup_mode()
    d['development'] = config.development
    d['show_traceback'] = config.show_traceback
    d['stop_on_critical'] = config.stop_on_critical
    d['cvars'] = cvars
    d['env'] = env
    d['polldelay'] = config.polldelay
    d['db_update'] = config.db_update
    d['notify_on_start'] = config.notify_on_start
    d['dir_eva'] = dir_eva
    d['db_uri'] = config.db_uri
    d['userdb_uri'] = config.userdb_uri
    d['pid_file'] = config.pid_file
    d['log_file'] = config.log_file
    d['threads'] = {}
    d['uptime'] = int(time.time() - start_time)
    d['time'] = time.time()
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
    update_controller_name()


def update_controller_name():
    config.controller_name = '{}/{}'.format(product.code, config.system_name)


def set_db(db_uri=None, userdb_uri=None):
    db_engine.primary = create_db_engine(db_uri)
    db_engine.user = create_db_engine(userdb_uri)


def db():
    with _db_lock:
        if not g.has('db'):
            if config.db_update == 1:
                g.db = db_engine.primary.connect()
            else:
                g.db = db_engine.primary
        elif config.db_update == 1:
            try:
                g.db.execute('select 1')
            except:
                try:
                    g.db.close()
                except:
                    pass
                g.db = db_engine.primary.connect()
        return g.db


def userdb():
    with _userdb_lock:
        if not g.has('userdb'):
            if config.db_update == 1:
                g.userdb = db_engine.user.connect()
            else:
                g.userdb = db_engine.user
        elif config.db_update == 1:
            try:
                g.userdb.execute('select 1')
            except:
                try:
                    g.userdb.close()
                except:
                    pass
                g.userdb = db_engine.user.connect()
        return g.userdb


def reset_log(initial=False):
    if log_engine.logger and not config.log_file: return
    log_engine.logger = logging.getLogger()
    try:
        log_engine.log_file_handler.stream.close()
    except:
        pass
    if initial:
        for h in log_engine.logger.handlers:
            log_engine.logger.removeHandler(h)
    else:
        log_engine.logger.removeHandler(log_engine.log_file_handler)
    if not config.development:
        formatter = logging.Formatter('%(asctime)s ' + config.system_name + \
            '  %(levelname)s ' + product.code + ' %(threadName)s: %(message)s')
    else:
        formatter = logging.Formatter('%(asctime)s ' + config.system_name + \
            ' %(levelname)s f:%(filename)s mod:%(module)s fn:%(funcName)s ' + \
            'l:%(lineno)d th:%(threadName)s :: %(message)s')
    if config.log_file:
        log_engine.log_file_handler = logging.FileHandler(config.log_file)
    else:
        log_engine.log_file_handler = logging.StreamHandler(sys.stdout)
    log_engine.log_file_handler.setFormatter(formatter)
    log_engine.logger.addHandler(log_engine.log_file_handler)
    if initial:
        from eva.logs import MemoryLogHandler
        log_engine.logger.addHandler(MemoryLogHandler())
        if config.syslog:
            if config.syslog.startswith('/'):
                syslog_addr = config.syslog
            else:
                addr, port = parse_host_port(config.syslog, 514)
                if addr:
                    syslog_addr = (addr, port)
                else:
                    logging.error('Invalid syslog configuration: {}'.format(
                        config.syslog))
                    syslog_addr = None
            if syslog_addr:
                log_engine.syslog_handler = logging.handlers.SysLogHandler(
                    address=syslog_addr)
                log_engine.syslog_handler.setFormatter(formatter)
                log_engine.logger.addHandler(log_engine.syslog_handler)


def load(fname=None, initial=False, init_log=True, check_pid=True):
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
            try:
                config.syslog = cfg.get('server', 'syslog')
                if config.syslog == 'yes':
                    config.syslog = '/dev/log'
            except:
                pass
            if init_log: reset_log(initial)
            try:
                log_level = cfg.get('server', 'logging_level')
                if log_level in log_levels_by_name:
                    config.default_log_level_name = log_level
                    config.default_log_level_id = log_levels_by_name.get(
                        log_level)
                    config.default_log_level = getattr(logging,
                                                       log_level.upper())
            except:
                pass
            try:
                config.development = (cfg.get('server', 'development') == 'yes')
            except:
                config.development = False
            if config.development:
                config.show_traceback = True
                debug_on()
                logging.critical('DEVELOPMENT MODE STARTED')
                config.debug = True
            else:
                try:
                    config.show_traceback = (cfg.get('server',
                                                     'show_traceback') == 'yes')
                except:
                    config.show_traceback = False
            if not config.development and not config.debug:
                try:
                    if os.environ.get('EVA_CORE_DEBUG'):
                        config.debug = True
                        config.show_traceback = True
                    else:
                        config.debug = (cfg.get('server', 'debug') == 'yes')
                    if config.debug: debug_on()
                except:
                    pass
                if not config.debug:
                    logging.basicConfig(level=config.default_log_level)
                    if log_engine.logger:
                        log_engine.logger.setLevel(config.default_log_level)
            try:
                config.system_name = cfg.get('server', 'name')
                update_controller_name()
            except:
                pass
            logging.info('Loading server config')
            logging.debug('server.pid_file = %s' % config.pid_file)
            logging.debug(
                'server.logging_level = %s' % config.default_log_level_name)
            try:
                config.notify_on_start = (cfg.get('server',
                                                  'notify_on_start') == 'yes')
            except:
                pass
            logging.debug('server.notify_on_start = %s' % ('yes' \
                                        if config.notify_on_start else 'no'))
            try:
                config.stop_on_critical = (cfg.get('server',
                                                   'stop_on_critical'))
            except:
                pass
            if config.stop_on_critical == 'yes':
                config.stop_on_critical = 'always'
            elif config.stop_on_critical not in ['no', 'always', 'core']:
                stop_on_critical = 'no'
            logging.debug(
                'server.stop_on_critical = %s' % config.stop_on_critical)
            try:
                config.dump_on_critical = (cfg.get('server',
                                                   'dump_on_critical') == 'yes')
            except:
                pass
            logging.debug('server.dump_on_critical = %s' % ('yes' \
                                        if config.dump_on_critical else 'no'))
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
                uh = cfg.get('server', 'user_hook')
                if not uh.startswith('/'):
                    uh = dir_eva + '/' + uh
                config.user_hook = uh.split()
            except:
                pass
            _uh = ' '.join(config.user_hook) if config.user_hook else None
            logging.debug('server.user_hook = %s' % _uh)
            try:
                config.enterprise_layout = (cfg.get('server', 'layout') !=
                                            'simple')
            except:
                pass
            logging.debug('server.layout = %s' % ('enterprise' \
                                    if config.enterprise_layout else 'simple'))
        try:
            config.polldelay = float(cfg.get('server', 'polldelay'))
        except:
            pass
        try:
            config.timeout = float(cfg.get('server', 'timeout'))
        except:
            pass
        if not config.polldelay: config.polldelay = 0.01
        logging.debug('server.timeout = %s' % config.timeout)
        logging.debug('server.polldelay = %s  ( %s msec )' % \
                            (config.polldelay, int(config.polldelay * 1000)))
        try:
            config.reactor_thread_pool = int(
                cfg.get('server', 'reactor_thread_pool'))
        except:
            pass
        logging.debug(
            'server.reactor_thread_pool = %s' % config.reactor_thread_pool)
        try:
            config.db_update = db_update_codes.index(
                cfg.get('server', 'db_update'))
        except:
            pass
        logging.debug(
            'server.db_update = %s' % db_update_codes[config.db_update])
        try:
            config.keep_action_history = int(
                cfg.get('server', 'keep_action_history'))
        except:
            pass
        logging.debug('server.keep_action_history = %s sec' % \
                config.keep_action_history)
        try:
            config.action_cleaner_interval = int(
                cfg.get('server', 'action_cleaner_interval'))
            if config.action_cleaner_interval < 0:
                raise Exception('invalid interval')
        except:
            config.action_cleaner_interval = default_action_cleaner_interval
        logging.debug('server.action_cleaner_interval = %s sec' % \
                config.action_cleaner_interval)
        try:
            config.keep_logmem = int(cfg.get('server', 'keep_logmem'))
        except:
            pass
        logging.debug('server.keep_logmem = %s sec' % config.keep_logmem)
        try:
            config.exec_before_save = cfg.get('server', 'exec_before_save')
        except:
            pass
        logging.debug('server.exec_before_save = %s' % config.exec_before_save)
        try:
            config.exec_after_save = cfg.get('server', 'exec_after_save')
        except:
            pass
        logging.debug('server.exec_after_save = %s' % config.exec_after_save)
        try:
            config.mqtt_update_default = cfg.get('server',
                                                 'mqtt_update_default')
        except:
            pass
        logging.debug(
            'server.mqtt_update_default = %s' % config.mqtt_update_default)
        return cfg
    except:
        print('Can not read primary config %s' % fname_full)
        log_traceback(True)
    return False


@cvars_lock
def load_cvars(fname=None):
    fname_full = format_cfg_fname(fname, 'cvars', ext='json', runtime=True)
    if not fname_full:
        logging.warning('No file or product specified,' + \
                            ' skipping loading custom variables')
        return False
    cvars.clear()
    env.clear()
    env.update(os.environ.copy())
    if not 'PATH' in env: env['PATH'] = ''
    env['PATH'] = '%s/bin:%s/xbin:' % (dir_eva, dir_eva) + env['PATH']
    logging.info('Loading custom vars from %s' % fname_full)
    try:
        raw = ''.join(open(fname_full).readlines())
        cvars.update(jsonpickle.decode(raw))
    except:
        logging.error('can not load custom vars from %s' % fname_full)
        log_traceback()
        return False
    for i, v in cvars.items():
        logging.debug('custom var %s = "%s"' % (i, v))
    _flags.cvars_modified = False
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
    if config.db_update == 1: save_cvars()
    else: _flags.cvars_modified = True
    return True


@save
def save_modified():
    return save_cvars() if _flags.cvars_modified else True


def debug_on():
    config.debug = True
    logging.basicConfig(level=logging.DEBUG)
    if log_engine.logger: log_engine.logger.setLevel(logging.DEBUG)
    logging.info('Debug mode ON')


def debug_off():
    config.debug = False
    if log_engine.logger: log_engine.logger.setLevel(config.default_log_level)
    logging.info('Debug mode OFF')


def setup_off():
    _flags.setup_mode = 0
    logging.info('Setup mode OFF')


def setup_on(duration):
    import datetime
    _flags.setup_mode = time.time() + duration
    logging.warning('Setup mode ON, ends: {}'.format(
        datetime.datetime.fromtimestamp(
            _flags.setup_mode).strftime('%Y-%m-%d %T')))


def is_setup_mode():
    return _flags.setup_mode > time.time()


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
    else: t = config.timeout
    if delay: p = delay
    else: p = config.polldelay
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
    Locker.timeout = config.timeout
    RLocker.timeout = config.timeout
    if not os.environ.get('EVA_CORE_ENABLE_CC'):
        signal.signal(signal.SIGINT, sighandler_int)
    else:
        signal.signal(signal.SIGINT, sighandler_term)


def start(init_db_only=False):
    if not init_db_only:
        reactor.suggestThreadPoolSize(config.reactor_thread_pool)
    set_db(config.db_uri, config.userdb_uri)


#BD: 20.05.2017
