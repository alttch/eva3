__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2020 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.3.1"

import sys
import platform
import os
import stat
import logging
import configparser
import traceback
import time
import rapidjson
import signal
import psutil
import threading
import inspect
import sqlalchemy as sa
import faulthandler
import gzip
import timeouter
import uuid
import glob
import importlib
import yaml

try:
    yaml.warnings({'YAMLLoadWarning': False})
except:
    pass

from eva.tools import format_json
from eva.tools import wait_for as _wait_for
from eva.tools import parse_host_port

from eva.tools import Locker as GenericLocker

from eva.exceptions import FunctionFailed
from eva.exceptions import TimeoutException

from neotasker import g, FunctionCollection, task_supervisor

import pyaltt2.logs

from types import SimpleNamespace

version = __version__

max_shutdown_time = 30

default_action_cleaner_interval = 60

dir_eva_default = '/opt/eva'

env = {}
cvars = {}

controllers = set()

plugin_modules = {}

spawn = task_supervisor.spawn

_flags = SimpleNamespace(ignore_critical=False,
                         sigterm_sent=False,
                         started=threading.Event(),
                         shutdown_requested=False,
                         cvars_modified=False,
                         cs_modified=False,
                         setup_mode=0,
                         use_reactor=False)

product = SimpleNamespace(name='', code='', build=None, usn='')

config = SimpleNamespace(pid_file=None,
                         log_file=None,
                         db_uri=None,
                         userdb_uri=None,
                         keep_api_log=0,
                         debug=False,
                         system_name=platform.node(),
                         controller_name=None,
                         default_cloud_key='default',
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
                         syslog_format=None,
                         reactor_thread_pool=15,
                         pool_min_size='max',
                         pool_max_size=None,
                         user_hook=None,
                         plugins=[])

db_engine = SimpleNamespace(primary=None, user=None)

log_engine = SimpleNamespace(logger=None,
                             log_file_handler=None,
                             syslog_handler=None)

db_pool_size = 15

sleep_step = 0.1

_db_lock = threading.RLock()
_userdb_lock = threading.RLock()

db_update_codes = ['manual', 'instant', 'on_exit']
"""
main EVA ICS directory
"""
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

cs_data = SimpleNamespace(corescripts=[], topics=[])

cs_shared_namespace = SimpleNamespace()

CS_EVENT_STATE = 1
CS_EVENT_API = 2
CS_EVENT_MQTT = 3

corescript_globals = {
    'print': logging.info,
    'logging': logging,
    'json': rapidjson,
    'time': time,
    'spawn': spawn,
    'g': cs_shared_namespace,
    'CS_EVENT_STATE': CS_EVENT_STATE,
    'CS_EVENT_API': CS_EVENT_API,
    'CS_EVENT_MQTT': CS_EVENT_MQTT
}


def critical(log=True, from_driver=False):
    if _flags.ignore_critical:
        return
    try:
        caller = inspect.getouterframes(inspect.currentframe(), 2)[1]
        caller_info = '%s:%s %s' % (caller.filename, caller.lineno,
                                    caller.function)
    except:
        caller_info = ''
    if log:
        log_traceback(force=True)
    if config.dump_on_critical:
        _flags.ignore_critical = True
        logging.critical('critical exception. dump file: %s' %
                         create_dump('critical', caller_info))
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


cvars_lock = RLocker('core')

corescript_lock = RLocker('core')


def log_traceback(*args, notifier=False, **kwargs):
    pyaltt2.logs.log_traceback(*args, use_ignore=notifier, **kwargs)


dump = FunctionCollection(on_error=log_traceback, include_exceptions=True)
save = FunctionCollection(on_error=log_traceback)
shutdown = FunctionCollection(on_error=log_traceback)
stop = FunctionCollection(on_error=log_traceback)


def format_db_uri(db_uri):
    if not db_uri:
        return None
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
    if not db_uri:
        return None
    if db_uri.startswith('sqlite:///'):
        return sa.create_engine(
            db_uri,
            connect_args={'timeout': timeout if timeout else config.timeout})
    else:
        return sa.create_engine(db_uri,
                                pool_size=db_pool_size,
                                max_overflow=db_pool_size * 2,
                                isolation_level='READ UNCOMMITTED')


def sighandler_hup(signum, frame):
    logging.info('got HUP signal')


def suicide(**kwargs):
    time.sleep(max_shutdown_time)
    logging.critical('SUICIDE')
    if config.show_traceback:
        faulthandler.dump_traceback()
    os.kill(os.getpid(), signal.SIGKILL)


def sighandler_term(signum=None, frame=None):
    if _flags.sigterm_sent:
        return
    _flags.sigterm_sent = True
    threading.Thread(target=suicide, daemon=True).start()
    logging.info('got TERM signal, exiting')
    if config.db_update == 2:
        try:
            do_save()
        except:
            log_traceback()
    core_shutdown()
    unlink_pid_file()
    logging.info('EVA core shut down')


def sighandler_int(signum, frame):
    pass


def prepare_save():
    if not config.exec_before_save:
        return True
    logging.debug('executing before save command "%s"' % \
        config.exec_before_save)
    code = os.system(config.exec_before_save)
    if code:
        logging.error('before save command exited with code %u' % \
            code)
        raise FunctionFailed('exec_before_save failed')
    return True


def finish_save():
    if not config.exec_after_save:
        return True
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
    _flags.started.set()
    if _flags.use_reactor:
        from twisted.internet import reactor
        reactor.run(installSignalHandlers=False)
    else:
        task_supervisor.block()


def is_shutdown_requested():
    return _flags.shutdown_requested


def is_started():
    return _flags.started.is_set()


def core_shutdown():
    _flags.shutdown_requested = True
    shutdown()
    stop()
    if _flags.use_reactor:
        from twisted.internet import reactor
        reactor.callFromThread(reactor.stop)
    task_supervisor.stop(wait=True)


def serialize_plugin(plugin_name, plugin_module):
    result = {
        'name': plugin_name,
        'author': getattr(plugin_module, '__author__', None),
        'version': getattr(plugin_module, '__version__', None),
        'license': getattr(plugin_module, '__license__', None)
    }
    try:
        result['ready'] = plugin_module.flags.ready
    except:
        result['ready'] = None
    return result


def serialize_plugins():
    return [serialize_plugin(p, v) for p, v in plugin_modules.items()]


def create_dump(e='request', msg=''):
    try:
        result = dump.run()
        result.update({'reason': {'event': e, 'info': str(msg)}})
        result['plugin_modules'] = serialize_plugins()
        result['plugins'] = {
            p: exec_plugin_func(p, v, 'dump')
            for p, v in plugin_modules.items()
        }
        filename = dir_var + '/' + time.strftime('%Y%m%d%H%M%S') + \
                '.dump.gz'
        dmp = format_json(result,
                          minimal=not config.development,
                          unpicklable=True).encode()
        with gzip.open(filename, 'w') as fd:
            pass
        os.chmod(filename, stat.S_IRUSR | stat.S_IWUSR)
        with gzip.open(filename, 'a') as fd:
            fd.write(dmp)
        logging.warning('dump created, file: %s, event: %s (%s)' %
                        (filename, e, msg))
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
    d['python'] = sys.version
    d['system_name'] = config.system_name
    d['product_name'] = product.name
    d['product_code'] = product.code
    d['product_build'] = product.build
    d['keep_logmem'] = config.keep_logmem
    d['keep_api_log'] = config.keep_api_log
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
    d['fd'] = proc.open_files()
    for t in threading.enumerate().copy():
        d['threads'][t.name] = {}
        d['threads'][t.name]['daemon'] = t.daemon
        d['threads'][t.name]['alive'] = t.is_alive()
    d.update(pyaltt2.logs.serialize())
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
    """
    get SQLAlchemy connection to primary DB
    """
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
    """
    get SQLAlchemy connection to user DB
    """
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


def load(fname=None, initial=False, init_log=True, check_pid=True):

    def secure_file(f):
        fn = dir_eva + '/' + f
        with open(fn, 'a'):
            pass
        os.chmod(fn, mode=0o600)

    from eva.logs import log_levels_by_name, init as init_logs
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
                if not check_pid:
                    raise Exception('no check required')
                with open(config.pid_file) as fd:
                    pid = int(fd.readline().strip())
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
            try:
                config.syslog_format = cfg.get('server', 'syslog_format')
            except:
                pass
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
            if init_log:
                init_logs()
            try:
                config.development = (cfg.get('server', 'development') == 'yes')
            except:
                config.development = False
            if config.development:
                config.show_traceback = True
                pyaltt2.logs.config.tracebacks = True,
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
                    if config.debug:
                        debug_on()
                except:
                    pass
                if not config.debug:
                    logging.basicConfig(level=config.default_log_level)
                    if log_engine.logger:
                        log_engine.logger.setLevel(config.default_log_level)
            if config.show_traceback:
                pyaltt2.logs.config.tracebacks = True
            try:
                config.system_name = cfg.get('server', 'name')
                update_controller_name()
            except:
                pass
            logging.info('Loading server config')
            logging.debug('server.pid_file = %s' % config.pid_file)
            logging.debug('server.logging_level = %s' %
                          config.default_log_level_name)
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
            logging.debug('server.stop_on_critical = %s' %
                          config.stop_on_critical)
            try:
                config.dump_on_critical = (cfg.get('server',
                                                   'dump_on_critical') == 'yes')
            except:
                pass
            logging.debug('server.dump_on_critical = %s' % ('yes' \
                                        if config.dump_on_critical else 'no'))
            prepare_save()
            try:
                db_file = cfg.get('server', 'db_file')
                secure_file(db_file)
            except:
                db_file = None
            try:
                db_uri = cfg.get('server', 'db')
            except:
                if db_file:
                    db_uri = db_file
            config.db_uri = format_db_uri(db_uri)
            logging.debug('server.db = %s' % config.db_uri)
            try:
                userdb_file = cfg.get('server', 'userdb_file')
                secure_file(userdb_file)
            except:
                userdb_file = None
            finish_save()
            try:
                userdb_uri = cfg.get('server', 'userdb')
            except:
                if userdb_file:
                    userdb_uri = userdb_file
                else:
                    userdb_uri = None
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
        if not config.polldelay:
            config.polldelay = 0.01
        logging.debug('server.timeout = %s' % config.timeout)
        logging.debug('server.polldelay = %s  ( %s msec )' % \
                            (config.polldelay, int(config.polldelay * 1000)))
        try:
            config.pool_min_size = int(cfg.get('server', 'pool_min_size'))
        except:
            pass
        logging.debug('server.pool_min_size = %s' % config.pool_min_size)
        try:
            config.pool_max_size = int(cfg.get('server', 'pool_max_size'))
        except:
            pass
        logging.debug('server.pool_max_size = %s' %
                      (config.pool_max_size
                       if config.pool_max_size is not None else 'auto'))
        try:
            config.reactor_thread_pool = int(
                cfg.get('server', 'reactor_thread_pool'))
        except:
            pass
        logging.debug('server.reactor_thread_pool = %s' %
                      config.reactor_thread_pool)
        try:
            config.db_update = db_update_codes.index(
                cfg.get('server', 'db_update'))
        except:
            pass
        logging.debug('server.db_update = %s' %
                      db_update_codes[config.db_update])
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
            config.keep_api_log = int(cfg.get('server', 'keep_api_log'))
        except:
            pass
        logging.debug('server.keep_api_log = %s sec' % config.keep_api_log)
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
        logging.debug('server.mqtt_update_default = %s' %
                      config.mqtt_update_default)
        try:
            config.plugins = [
                x.strip() for x in cfg.get('server', 'plugins').split(',')
            ]
        except:
            pass
        logging.debug('server.plugins = %s' % ', '.join(config.plugins))
        try:
            config.default_cloud_key = cfg.get('cloud', 'default_key')
        except:
            pass
        logging.debug('cloud.default_key = %s' % config.default_cloud_key)
        # init plugins
        for p in config.plugins:
            fname = f'{dir_eva}/plugins/{p}.py'
            if os.path.isfile(fname):
                try:
                    with open(fname) as fh:
                        n = {}
                        exec(fh.read(), n)
                        plugin_modules[p] = SimpleNamespace(**n)
                except:
                    logging.error(f'unable to load plugin {p} ({fname})')
                    log_traceback()
                    continue
            else:
                try:
                    modname = f'evacontrib.{p}'
                    importlib.import_module(modname)
                except:
                    logging.error(f'unable to load plugin {p} ({modname})')
                    log_traceback()
                    continue
            logging.info(f'+ plugin {p}')
        load_plugin_config(cfg)
        return cfg
    except:
        print('Can not read primary config %s' % fname_full)
        log_traceback(display=True)
    return False


def load_plugin_config(cfg):
    c = dict(cfg)
    for p, v in plugin_modules.items():
        plugin_config = dict(c.get(p, {}))
        exec_plugin_func(p, v, 'init', plugin_config)


def plugins_exec(method, *args, **kwargs):
    for p, v in plugin_modules.items():
        exec_plugin_func(p, v, method, *args, **kwargs)


def exec_plugin_func(pname, plugin, func, *args, **kwargs):
    try:
        m = getattr(plugin, func)
    except:
        return None
    try:
        logging.debug(f'Executing plugin func {pname}.{func}')
        return m(*args, **kwargs)
    except:
        logging.error(f'Unable to exec plugin func {pname}.{func}')
        log_traceback()
        return None


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
    if not 'PATH' in env:
        env['PATH'] = ''
    env['PATH'] = '%s/bin:%s/xbin:' % (dir_eva, dir_eva) + env['PATH']
    logging.info('Loading custom vars from %s' % fname_full)
    try:
        with open(fname_full) as fd:
            cvars.update(rapidjson.loads(fd.read()))
    except:
        logging.error('can not load custom vars from %s' % fname_full)
        log_traceback()
        return False
    for i, v in cvars.items():
        logging.debug('custom var %s = "%s"' % (i, v))
    _flags.cvars_modified = False
    return True


@corescript_lock
def load_corescripts(fname=None):
    reload_corescripts()
    fname_full = format_cfg_fname(fname, 'cs', ext='json', runtime=True)
    if not fname_full:
        logging.warning('No file or product specified,' + \
                            ' skipping loading corescript config')
        return False
    cs_data.topics.clear()
    try:
        with open(fname_full) as fd:
            cs_data.topics = rapidjson.loads(fd.read()).get('mqtt-topics', [])
        return True
    except:
        logging.error('can not load corescript config from %s' % fname_full)
        log_traceback()
        return False


@cvars_lock
def save_cvars(fname=None):
    fname_full = format_cfg_fname(fname, 'cvars', ext='json', runtime=True)
    logging.info('Saving custom vars to %s' % fname_full)
    try:
        with open(fname_full, 'w') as fd:
            fd.write(format_json(cvars, minimal=False))
        return True
    except:
        logging.error('can not save custom vars into %s' % fname_full)
        log_traceback()
        return False
    _flags.cvars_modified = False


@corescript_lock
def save_cs(fname=None):
    fname_full = format_cfg_fname(fname, 'cs', ext='json', runtime=True)
    logging.info('Saving corescript config to %s' % fname_full)
    try:
        with open(fname_full, 'w') as fd:
            fd.write(format_json({'mqtt-topics': cs_data.topics},
                                 minimal=False))
        return True
    except:
        logging.error('can not save corescript config to %s' % fname_full)
        log_traceback()
        return False
    _flags.cs_modified = False


@cvars_lock
def get_cvar(var=None):
    if var:
        return cvars[var] if var in cvars else None
    else:
        return cvars.copy()


@cvars_lock
def set_cvar(var, value=None):
    if not var:
        return False
    if value is not None:
        cvars[str(var)] = str(value)
    elif var not in cvars:
        return None
    else:
        try:
            del cvars[str(var)]
        except:
            return False
    if config.db_update == 1:
        save_cvars()
    else:
        _flags.cvars_modified = True
    return True


@save
def save_modified():
    return (save_cvars() if _flags.cvars_modified else True) \
        and (save_cs() if \
        _flags.cs_modified else True)


def debug_on():
    pyaltt2.logs.set_debug(True)
    config.debug = True
    logging.info('Debug mode ON')


def debug_off():
    config.debug = False
    pyaltt2.logs.set_debug(False)
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
        with open(config.pid_file, 'w') as fd:
            fd.write(str(os.getpid()))
    except:
        log_traceback()


def unlink_pid_file():
    try:
        os.unlink(config.pid_file)
    except:
        log_traceback()


def wait_for(func, wait_timeout=None, delay=None, wait_for_false=False):
    if wait_timeout:
        t = wait_timeout
    else:
        t = config.timeout
    if delay:
        p = delay
    else:
        p = config.polldelay
    return _wait_for(func, t, p, wait_for_false, is_shutdown_requested)


def format_xc_fname(item=None,
                    xc_type='',
                    fname=None,
                    update=False,
                    subdir=None):
    path = dir_xc + '/' + product.code
    if subdir:
        path += '/' + subdir
    if fname:
        return fname if fname[0] == '/' else path + '/' + fname
    if not item:
        return None
    fname = item.item_id
    if update:
        fname += '_update'
    if xc_type:
        fname += '.' + xc_type
    return path + '/' + fname


def format_cfg_fname(fname, cfg=None, ext='ini', path=None, runtime=False):
    if path:
        _path = path
    else:
        if runtime:
            _path = dir_runtime
        else:
            _path = dir_etc
    if not fname:
        if cfg:
            sfx = '_' + cfg
        else:
            sfx = ''
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


def start_supervisor():
    task_supervisor.set_thread_pool(min_size=config.pool_min_size,
                                    max_size=config.pool_max_size)
    task_supervisor.timeout_critical_func = critical
    task_supervisor.poll_delay = config.polldelay
    task_supervisor.start()
    task_supervisor.create_aloop('default', default=True)
    task_supervisor.create_aloop('cleaners')
    task_supervisor.create_async_job_scheduler('default', default=True)
    task_supervisor.create_async_job_scheduler('cleaners', aloop='cleaners')


def start(init_db_only=False):
    import eva.apikey
    if not init_db_only:
        from twisted.internet import reactor
        reactor.suggestThreadPoolSize(config.reactor_thread_pool)
    set_db(config.db_uri, config.userdb_uri)
    product.usn = str(
        uuid.uuid5(uuid.NAMESPACE_URL,
                   f'eva://{config.system_name}/{product.code}'))
    update_corescript_globals({'product': product, 'apikey': eva.apikey})


def handle_corescript_mqtt_event(d, t, qos, retain):
    if t:
        ts = t.split('/')
    else:
        ts = []
    exec_corescripts(event=SimpleNamespace(
        type=CS_EVENT_MQTT, topic=t, topic_p=ts, data=d, qos=qos,
        retain=retain))


@corescript_lock
def register_corescript_topics():
    import eva.notify
    for nt in cs_data.topics:
        try:
            t = nt['topic']
            qos = nt.get('qos', 1)
            if ':' in t:
                notifier_id, topic = t.split(':', 1)
                n = eva.notify.get_notifier(notifier_id, get_default=False)
            else:
                n = eva.notify.get_notifier(get_default=True)
                topic = t
            if not n:
                raise LookupError(f('Notifier {notifier_id}'))
            n.handler_append(topic, handle_corescript_mqtt_event, qos)
        except:
            logging.error(f'Unable to register corescript topic {t}')
            log_traceback()


@corescript_lock
def corescript_mqtt_subscribe(topic, qos=None):
    import eva.notify
    if qos is None:
        qos = 1
    for t in cs_data.topics:
        if topic == t['topic']:
            logging.error(f'Core script mqtt topic already subscribed: {topic}')
            return False
    try:
        if ':' in topic:
            notifier_id, topic = topic.split(':', 1)
            n = eva.notify.get_notifier(notifier_id, get_default=False)
        else:
            n = eva.notify.get_notifier(get_default=True)
        if not n:
            logging.error(f'Notifier not found')
            raise LookupError
        n.handler_append(topic, handle_corescript_mqtt_event, qos)
        cs_data.topics.append({'topic': topic, 'qos': qos})
        _flags.cs_modified = True
        return True
    except:
        log_traceback()
        return False


@corescript_lock
def corescript_mqtt_unsubscribe(topic):
    import eva.notify
    for t in cs_data.topics:
        if topic == t['topic']:
            try:
                if ':' in topic:
                    notifier_id, topic = topic.split(':', 1)
                    n = eva.notify.get_notifier(notifier_id, get_default=False)
                else:
                    n = eva.notify.get_notifier(get_default=True)
                if not n:
                    logging.error(f'Notifier not found')
                    raise LookupError
                n.handler_remove(topic, handle_corescript_mqtt_event)
                cs_data.topics.remove(t)
                _flags.cs_modified = True
                return True
            except:
                log_traceback()
                return False
    return False


@corescript_lock
def get_corescript_topics():
    return cs_data.topics.copy()


@corescript_lock
def reload_corescripts():
    cs = [
        os.path.basename(f)
        for f in glob.glob(f'{dir_xc}/{product.code}/cs/*.py')
    ]
    try:
        cs.delete('common.py')
    except:
        pass
    cs_data.corescripts.clear()
    cs_data.corescripts.extend(sorted(cs))
    logging.info('Core scripts reloaded, {} files found'.format(len(cs)))


def update_corescript_globals(data):
    corescript_globals.update(data)


def exec_corescripts(event=None, env_globals={}):
    if cs_data.corescripts:
        spawn(_t_exec_corescripts, event=event, env_globals=env_globals)


def _t_exec_corescripts(event=None, env_globals={}):
    import eva.runner
    d = env_globals.copy()
    d['event'] = event
    d.update(corescript_globals)
    logging.debug('executing core scripts, event type={}'.format(event.type))
    for c in cs_data.corescripts.copy():
        eva.runner.PyThread(script=c, env_globals=d, subdir='cs').run()


def plugins_event_state(source, data):
    for p, v in plugin_modules.items():
        f = getattr(v, 'handle_state_event')
        spawn(_t_handle_state_event, p, f, source, data)


def _t_handle_state_event(p, f, source, data):
    try:
        f(source, data)
    except:
        logging.error(f'Error executing {p}.handle_state_event method')
        log_traceback()


def register_controller(controller):
    controllers.add(controller)


timeouter.set_default_exception_class(TimeoutException)

#BD: 20.05.2017
