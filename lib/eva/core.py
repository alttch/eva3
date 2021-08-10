from __future__ import print_function

__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"

import sys
import platform
import os
import stat
import logging
import traceback
import time
import rapidjson
import signal
import psutil
import threading
import sqlalchemy as sa
import faulthandler
import gzip
import timeouter
import uuid
import glob
import importlib
import yaml
import re

# python 3.6 compat
try:
    time.perf_counter_ns()
except:
    time.perf_counter_ns = lambda: int(time.perf_counter() * 1000000000)

try:
    yaml.warnings({'YAMLLoadWarning': False})
except:
    pass

from eva.tools import format_json
from eva.tools import wait_for as _wait_for
from eva.tools import parse_host_port
from eva.tools import get_caller
from eva.tools import SimpleNamespace

from eva.tools import Locker as GenericLocker

from eva.exceptions import FunctionFailed
from eva.exceptions import TimeoutException

from neotasker import g, FunctionCollection, task_supervisor, background_worker

import pyaltt2.logs

import eva.registry

version = __version__

max_shutdown_time = 30

default_action_cleaner_interval = 60

dir_eva_default = '/opt/eva'

env = {}
cvars = {}

controllers = []

plugin_modules = {}

plugin_lock = threading.RLock()

spawn = task_supervisor.spawn

_flags = SimpleNamespace(ignore_critical=False,
                         sigterm_sent=False,
                         started=threading.Event(),
                         shutdown_requested=False,
                         cvars_modified=set(),
                         cs_modified=False,
                         setup_mode=0,
                         boot_id=0,
                         use_reactor=False,
                         critical_raised=False)

product = SimpleNamespace(name='', code='', build=None, usn='')

config = SimpleNamespace(pid_file=None,
                         log_file=None,
                         log_stdout=False,
                         auto_save=False,
                         db_uri=None,
                         userdb_uri=None,
                         keep_api_log=0,
                         debug=False,
                         system_name=platform.node(),
                         controller_name=None,
                         default_cloud_key='default',
                         discover_as_static=False,
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
                         log_format=None,
                         syslog=None,
                         syslog_format=None,
                         reactor_thread_pool=15,
                         pool_min_size='max',
                         pool_max_size=None,
                         user_hook=None,
                         plugins=[])

defaults = {}

db_engine = SimpleNamespace(primary=None, user=None)

log_engine = SimpleNamespace(logger=None,
                             log_file_handler=None,
                             syslog_handler=None)

db_pool_size = 15  # changed to thread count when WEB API is initialized

sleep_step = 0.1

_db_lock = threading.RLock()
_userdb_lock = threading.RLock()

db_update_codes = ['manual', 'instant', 'on-exit']
"""
main EVA ICS directory
"""
dir_eva = os.environ['EVA_DIR'] if 'EVA_DIR' in os.environ \
                                            else dir_eva_default
dir_var = dir_eva + '/var'
dir_etc = dir_eva + '/etc'
dir_xc = dir_eva + '/runtime/xc'
dir_ui = dir_eva + '/ui'
dir_pvt = dir_eva + '/pvt'
dir_lib = dir_eva + '/lib'
dir_runtime = dir_eva + '/runtime'
dir_venv = dir_eva + '/venv'

path = os.environ.get('PATH', '')
if path:
    path = ':' + path
os.environ['PATH'] = dir_venv + '/bin' + path

start_time = time.time()

cs_data = SimpleNamespace(corescripts=[], topics=[], periodic_iteration=0)

cs_shared_namespace = SimpleNamespace()

CS_EVENT_SYSTEM = 0
CS_EVENT_STATE = 1
CS_EVENT_API = 2
CS_EVENT_MQTT = 3
CS_EVENT_RPC = 4
CS_EVENT_PERIODIC = 5

CS_EVENT_PKG_INSTALL = 10
CS_EVENT_PKG_UNINSTALL = 11

DUMP_LOG_RECORDS = 5000

logger = logging.getLogger('eva.core')

corescript_globals = {
    'print': logging.info,
    'logging': logging,
    'json': rapidjson,
    'time': time,
    'spawn': spawn,
    'logger': logger,
    'g': cs_shared_namespace,
    'dir_eva': dir_eva,
    'CS_EVENT_STATE': CS_EVENT_STATE,
    'CS_EVENT_API': CS_EVENT_API,
    'CS_EVENT_MQTT': CS_EVENT_MQTT,
    'CS_EVENT_SYSTEM': CS_EVENT_SYSTEM,
    'CS_EVENT_RPC': CS_EVENT_RPC,
    'CS_EVENT_PERIODIC': CS_EVENT_PERIODIC,
    'CS_EVENT_PKG_INSTALL': CS_EVENT_PKG_INSTALL,
    'CS_EVENT_PKG_UNINSTALL': CS_EVENT_PKG_UNINSTALL
}

OID_ALLOWED_SYMBOLS = '^[A-Za-z0-9_\.\(\)\[\]-]*$'
GROUP_ALLOWED_SYMBOLS = '^[A-Za-z0-9_\./\(\)\[\]-]*$'
ID_ALLOWED_SYMBOLS = '^[A-Za-z0-9_\.\(\)\[\]-]*$'


def critical(log=True, from_driver=False):
    if _flags.ignore_critical:
        return
    try:
        caller = get_caller()
        caller_info = '%s:%s %s' % (caller.filename, caller.lineno,
                                    caller.function)
    except:
        caller_info = ''
    if log:
        log_traceback(force=True, critical=True)
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
        _flags.critical_raised = True
        sighandler_term(None, None)


def is_critical_raised():
    return _flags.critical_raised


def spawn_thread(fn, *args, **kwargs):
    t = threading.Thread(target=fn, args=args, kwargs=kwargs)
    t.start()
    return t


def spawn_daemon(fn, *args, **kwargs):
    t = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    t.start()
    return t


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


class CoreAction:

    def __init__(self, fn, *args, _name=None, _call_for=None, **kwargs):
        self.fn = fn
        self.name = _name if _name else fn.__name__
        self.args = args
        self.call_for = _call_for
        self.kwargs = kwargs
        self.uuid = str(uuid.uuid4())
        self.started = threading.Event()
        self.finished = threading.Event()
        self.exitcode = None
        self.out = None
        self.err = None
        self.time = {'created': time.time()}

    def serialize(self):
        return {
            'uuid': self.uuid,
            'call_for': self.call_for,
            'finished': self.finished.is_set(),
            'exitcode': self.exitcode,
            'out': self.out,
            'err': self.err,
            'function': self.name,
            'time': self.time.copy()
        }

    def run(self, wait=None):
        spawn(self.spawn, self.fn, *self.args, **self.kwargs)
        self.started.wait(config.timeout)
        if wait:
            self.wait(wait)

    def wait(self, timeout=None):
        self.finished.wait(timeout=timeout)

    def spawn(self, fn, *args, **kwargs):
        self.started.set()
        self.time['running'] = time.time()
        try:
            self.out = fn(*args, **kwargs)
            self.exitcode = 0
            self.time['completed'] = time.time()
        except Exception as e:
            logging.error(f'core action error {e}')
            self.exitcode = 1
            self.err = traceback.format_exc()
            self.time['failed'] = time.time()
            log_traceback()
        finally:
            self.finished.set()


def action(fn, *args, _wait=None, _name=None, _call_for=None, **kwargs):
    action = CoreAction(fn, *args, _name=_name, _call_for=_call_for, **kwargs)
    action.run(wait=_wait)
    return action.serialize()


dump = FunctionCollection(on_error=log_traceback, include_exceptions=True)
save = FunctionCollection(on_error=log_traceback)
shutdown = FunctionCollection(on_error=log_traceback)
stop = FunctionCollection(on_error=log_traceback)


def format_db_uri(db_uri):
    """
    Formats short database URL to SQLAlchemy URI

    - if no DB engine specified, SQLite is used
    - if relative SQLite db path is used, it's created under EVA dir
    """
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
    """
    Create SQLAlchemy database Engine

    - database timeout is set to core timeout, if not specified
    - database pool size is auto-configured
    - for all engines, except SQLite, "READ UNCOMMITED" isolation level is used
    """
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
    try:
        logging.critical('SUICIDE')
        if config.show_traceback:
            faulthandler.dump_traceback()
    finally:
        try:
            parent = psutil.Process(os.getpid())
            for child in parent.children(recursive=True):
                try:
                    child.kill()
                except:
                    log_traceback()
        finally:
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


def parse_ieid(ieid):
    if ieid is not None:
        ieid[0] = int(ieid[0])
        ieid[1] = int(ieid[1])
    return ieid


def is_ieid_gt(id1, id2):
    return (id1 is not None and
            id2 is None) or id1[0] > id2[0] or (id1[0] == id2[0] and
                                                id1[1] > id2[1])


def generate_ieid():
    return [_flags.boot_id, time.perf_counter_ns()]


def get_boot_id():
    return _flags.boot_id


def generate_boot_id():
    try:
        if not prepare_save():
            raise RuntimeError('Unable to prepare save')
        _flags.boot_id = eva.registry.key_increment(
            f'data/{product.code}/boot-id')
        if not finish_save():
            raise RuntimeError('Unable to finish save')
        logging.debug(f'BOOT ID: {_flags.boot_id}')
    except Exception as e:
        logging.error(e)
        critical()


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
    exec_corescripts(
        event=SimpleNamespace(type=CS_EVENT_SYSTEM, topic='startup'))
    cs_intervaller.start()
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
    cs_intervaller.stop()
    _t_exec_corescripts(
        event=SimpleNamespace(type=CS_EVENT_SYSTEM, topic='shutdown'))
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
        result['log'] = pyaltt2.logs.get(n=DUMP_LOG_RECORDS)
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
    d['neotasker'] = {'supervisor': task_supervisor.get_info()}
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


def load(initial=False, init_log=True, check_pid=True, omit_plugins=False):

    def secure_file(f):
        fn = dir_eva + '/' + f
        with open(fn, 'a'):
            pass
        os.chmod(fn, mode=0o600)

    from eva.logs import log_levels_by_name, init as init_logs
    try:
        cfg = eva.registry.config_get(f'config/{product.code}/main')
    except:
        critical()
        raise
    if initial:
        try:
            config.pid_file = cfg.get('server/pid-file')
            if config.pid_file and config.pid_file[0] != '/':
                config.pid_file = dir_eva + '/' + config.pid_file
        except LookupError:
            pass
        try:
            if not check_pid:
                raise Exception('no check required')
            with open(config.pid_file) as fd:
                pid = int(fd.readline().strip())
            p = psutil.Process(pid)
            print(f'Can not start {product.name}, '
                  'another process is already running')
            return None
        except:
            pass
        if not os.environ.get('EVA_CORE_LOG_STDOUT'):
            try:
                config.log_file = cfg.get('server/log-file')
            except LookupError:
                config.log_file = None
        if config.log_file and config.log_file[0] != '/':
            config.log_file = dir_eva + '/' + config.log_file
        try:
            config.syslog = cfg.get('server/syslog')
            if config.syslog is True:
                config.syslog = '/dev/log'
        except LookupError:
            pass
        try:
            config.log_format = cfg.get('server/log-format').strip()
        except LookupError:
            pass
        try:
            config.syslog_format = cfg.get('server/syslog-format').strip()
        except LookupError:
            pass
        try:
            log_level = cfg.get('server/logging-level').lower()
            if log_level in log_levels_by_name:
                config.default_log_level_name = log_level
                config.default_log_level_id = log_levels_by_name.get(log_level)
                config.default_log_level = getattr(logging, log_level.upper())
        except LookupError:
            pass
        try:
            config.log_stdout = cfg.get('server/log-stdout')
        except LookupError:
            pass
        if init_log:
            init_logs()
        try:
            config.development = cfg.get('server/development')
        except LookupError:
            config.development = False
        if config.development:
            config.show_traceback = True
            pyaltt2.logs.config.tracebacks = True,
            debug_on()
            logging.critical('DEVELOPMENT MODE STARTED')
            config.debug = True
        else:
            try:
                config.show_traceback = cfg.get('server/show-traceback')
            except LookupError:
                config.show_traceback = False
        if not config.development and not config.debug:
            try:
                if os.environ.get('EVA_CORE_DEBUG') == '1':
                    config.debug = True
                    config.show_traceback = True
                else:
                    config.debug = cfg.get('server/debug')
                if config.debug:
                    debug_on()
            except LookupError:
                pass
            if not config.debug:
                logging.basicConfig(level=config.default_log_level)
                if log_engine.logger:
                    log_engine.logger.setLevel(config.default_log_level)
        if config.show_traceback:
            pyaltt2.logs.config.tracebacks = True
        config.system_name = eva.registry.SYSTEM_NAME
        update_controller_name()
        logging.info('Loading server config')
        logging.debug(f'server.pid_file = {config.pid_file}')
        logging.debug(f'server.logging_level = {config.default_log_level_name}')
        try:
            config.notify_on_start = cfg.get('server/notify-on-start')
        except LookupError:
            pass
        logging.debug(f'server.notify_on_start = {config.notify_on_start}')
        try:
            config.stop_on_critical = cfg.get('server/stop-on-critical')
        except LookupError:
            pass
        if config.stop_on_critical == 'yes' or config.stop_on_critical is True:
            config.stop_on_critical = 'always'
        elif config.stop_on_critical is False:
            config.stop_on_critical = 'no'
        elif config.stop_on_critical not in ['no', 'always', 'core']:
            config.stop_on_critical = 'no'
        logging.debug(f'server.stop_on_critical = {config.stop_on_critical}')
        try:
            config.dump_on_critical = cfg.get('server/dump-on-critical')
        except LookupError:
            pass
        logging.debug(f'server.dump_on_critical = {config.dump_on_critical}')
        prepare_save()
        try:
            db_file = cfg.get('server/db-file')
            secure_file(db_file)
        except LookupError:
            db_file = None
        try:
            db_uri = cfg.get('server/db')
        except LookupError:
            if db_file:
                db_uri = db_file
        config.db_uri = format_db_uri(db_uri)
        logging.debug(f'server.db = {config.db_uri}')
        try:
            userdb_file = cfg.get('server/userdb-file')
            secure_file(userdb_file)
        except:
            userdb_file = None
        finish_save()
        try:
            userdb_uri = cfg.get('server/userdb')
        except:
            if userdb_file:
                userdb_uri = userdb_file
            else:
                userdb_uri = None
        if userdb_uri:
            config.userdb_uri = format_db_uri(userdb_uri)
        else:
            config.userdb_uri = config.db_uri
        logging.debug(f'server.userdb = {config.userdb_uri}')
        try:
            uh = cfg.get('server/user-hook')
            if not uh.startswith('/'):
                uh = dir_eva + '/' + uh
            config.user_hook = uh.split()
        except LookupError:
            pass
        _uh = ' '.join(config.user_hook) if config.user_hook else None
        logging.debug(f'server.user_hook = {_uh}')
        # end if initial
    try:
        config.polldelay = float(cfg.get('server/polldelay'))
    except LookupError:
        pass
    try:
        config.timeout = float(cfg.get('server/timeout'))
    except LookupError:
        pass
    if not config.polldelay:
        config.polldelay = 0.01
    logging.debug(f'server.timeout = {config.timeout}')
    logging.debug('server.polldelay = %s  ( %s msec )' % \
                        (config.polldelay, int(config.polldelay * 1000)))
    try:
        config.pool_min_size = int(cfg.get('server/pool-min-size'))
    except LookupError:
        pass
    logging.debug(f'server.pool_min_size = {config.pool_min_size}')
    try:
        config.pool_max_size = int(cfg.get('server/pool-max-size'))
    except:
        pass
    logging.debug(
        'server.pool_max_size = %s' %
        (config.pool_max_size if config.pool_max_size is not None else 'auto'))
    try:
        config.reactor_thread_pool = int(cfg.get('server/reactor-thread-pool'))
    except:
        pass
    logging.debug(f'server.reactor_thread_pool = {config.reactor_thread_pool}')
    try:
        config.db_update = db_update_codes.index(cfg.get('server/db-update'))
    except LookupError:
        pass
    logging.debug('server.db_update = %s' % db_update_codes[config.db_update])
    try:
        config.keep_action_history = int(cfg.get('server/keep-action-history'))
    except:
        pass
    logging.debug(
        f'server.keep_action_history = {config.keep_action_history} sec')
    try:
        config.action_cleaner_interval = int(
            cfg.get('server/action-cleaner-interval'))
        if config.action_cleaner_interval < 0:
            raise Exception('invalid interval')
    except:
        config.action_cleaner_interval = default_action_cleaner_interval
    logging.debug(
        f'server.action_cleaner_interval = {config.action_cleaner_interval} sec'
    )
    try:
        config.keep_logmem = int(cfg.get('server/keep-logmem'))
    except:
        pass
    logging.debug('server.keep_logmem = %s sec' % config.keep_logmem)
    try:
        config.keep_api_log = int(cfg.get('server/keep-api-log'))
    except:
        pass
    logging.debug(f'server.keep_api_log = {config.keep_api_log} sec')
    try:
        config.auto_save = cfg.get('server/auto-save', default=True)
    except:
        pass
    logging.debug(f'server.auto_save = {config.auto_save}')
    try:
        config.exec_before_save = cfg.get('server/exec-before-save')
    except:
        pass
    logging.debug(f'server.exec_before_save = {config.exec_before_save}')
    try:
        config.exec_after_save = cfg.get('server/exec-after-save')
    except:
        pass
    logging.debug(f'server.exec_after_save = {config.exec_after_save}')
    try:
        config.mqtt_update_default = cfg.get('server/mqtt-update-default')
    except:
        pass
    logging.debug(f'server.mqtt_update_default = {config.mqtt_update_default}')
    try:
        config.default_cloud_key = str(cfg.get('cloud/default-key'))
    except LookupError:
        pass
    logging.debug(f'cloud.default_key = {config.default_cloud_key}')
    try:
        config.discover_as_static = cfg.get('cloud/discover-as-static')
    except LookupError:
        pass
    logging.debug(f'cloud.discover_as_static = {config.discover_as_static}')
    defaults.clear()
    d = eva.registry.key_get(f'config/{product.code}/defaults', default=None)
    if d:
        defaults.update(d)
    for k, v in defaults.items():
        if isinstance(v, dict):
            for k2, v2 in v.items():
                logging.debug(f'defaults.{k}.{k2} = {v2}')
        else:
            logging.debug(f'defaults.{k} = {v}')
    if not omit_plugins:
        plugin_cfg = cfg.get('plugins', default={})
        plugin_cfg.update(
            eva.registry.get_subkeys(f'config/{product.code}/plugins'))
        config.plugins = []
        for k, v in plugin_cfg.items():
            if v.get('enabled'):
                config.plugins.append(k)
        logging.debug('plugins = %s' % ', '.join(config.plugins))
        # init plugins
        for p in config.plugins:
            fname = f'{dir_runtime}/plugins/{p}.py'
            if os.path.exists(fname):
                try:
                    plugin_modules[p] = importlib.import_module(
                        f'eva.plugins.{p}')
                except:
                    logging.error(f'unable to load plugin {p} ({fname})')
                    log_traceback()
                    continue
            else:
                try:
                    modname = f'evacontrib.{p}'
                    plugin_modules[p] = importlib.import_module(modname)
                except:
                    logging.error(f'unable to load plugin {p} ({modname})')
                    log_traceback()
                    continue
            logging.info(f'+ plugin {p}')
        load_plugin_config(plugin_cfg)
    return cfg


def load_plugin_config(cfg):
    for p, v in plugin_modules.items():
        pcfg = cfg.get(p).get('config', {})
        exec_plugin_func(p, v, 'init', pcfg)


def plugins_exec(method, *args, **kwargs):
    for p, v in plugin_modules.copy().items():
        exec_plugin_func(p, v, method, *args, **kwargs)


def exec_plugin_func(pname, plugin, func, *args, raise_err=False, **kwargs):
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
        if raise_err:
            raise
        else:
            return None


@cvars_lock
def load_cvars(fname=None):
    cvars.clear()
    _flags.cvars_modified.clear()
    env.clear()
    env.update(os.environ.copy())
    env['EVA_VERSION'] = __version__
    env['EVA_BUILD'] = str(product.build)
    if not 'PATH' in env:
        env['PATH'] = ''
    env['PATH'] = '%s/bin:%s/xbin:' % (dir_eva, dir_eva) + env['PATH']
    logging.info('Loading custom vars')
    try:
        for i, value in eva.registry.key_get_recursive(
                f'config/{eva.core.product.code}/cvars'):
            cvars[i] = value
    except Exception as e:
        logging.error('Error loading custom vars: {e}')
        log_traceback()
        return False
    for i, v in cvars.items():
        logging.debug('custom var %s = "%s"' % (i, v))
    return True


@corescript_lock
def load_corescripts(fname=None):
    reload_corescripts()
    cs_data.topics.clear()
    try:
        cfg = eva.registry.key_get(f'config/{eva.core.product.code}/cs', {})
        cs_data.topics = cfg.get('mqtt-topics', [])
        return True
    except Exception as e:
        logging.error('Error loading corescript config: {e}')
        log_traceback()
        return False


@save
@cvars_lock
def save_cvars():
    try:
        prepare_save()
        for i in _flags.cvars_modified:
            kn = f'config/{eva.core.product.code}/cvars/{i}'
            try:
                value = cvars[i]
                eva.registry.key_set(kn, cvars[i])
            except KeyError:
                eva.registry.key_delete(kn)
        _flags.cvars_modified.clear()
        finish_save()
    except Exception as e:
        logging.error(f'Error saving cvars: {e}')
        log_traceback()


@save
@corescript_lock
def save_cs(fname=None):
    if _flags.cs_modified:
        try:
            prepare_save()
            cfg = {'mqtt-topics': cs_data.topics}
            eva.registry.key_set(f'config/{eva.core.product.code}/cs', cfg)
            _flags.cs_modified = False
            finish_save()
            return True
        except Exception as e:
            logging.error(f'Error saving corescript configs: {e}')
            log_traceback()
            return False


@cvars_lock
def get_cvar(var=None):
    if var:
        return cvars[var] if var in cvars else None
    else:
        return cvars.copy()


@cvars_lock
def set_cvar(var, value=None):
    if not var or not re.match(ID_ALLOWED_SYMBOLS, var):
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
    _flags.cvars_modified.add(var)
    if config.auto_save:
        save_cvars()
    return True


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
    if not init_db_only:
        generate_boot_id()
        product.usn = str(
            uuid.uuid5(uuid.NAMESPACE_URL,
                       f'eva://{config.system_name}/{product.code}'))
        update_corescript_globals({
            'product': product,
            'system_name': config.system_name,
            'apikey': eva.apikey
        })


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
                raise LookupError(f'Notifier {notifier_id}')
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
        if config.auto_save:
            save_cs()
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
                if config.auto_save:
                    save_cs()
                return True
            except:
                log_traceback()
                return False
    return False


@corescript_lock
def get_corescript_topics():
    return cs_data.topics.copy()


@corescript_lock
def append_corescript(name):
    if name not in cs_data.corescripts:
        cs_data.corescripts.append(f'{name}.py')


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


def run_corescript_code(code=None, event=None, env_globals={}):
    d = env_globals.copy()
    d['event'] = event
    d.update(corescript_globals)
    logging.debug('running core script, event type={}'.format(event.type))
    exec(code, d, d)


def plugins_event_state(source, data):
    for p, v in plugin_modules.items():
        try:
            f = getattr(v, 'handle_state_event')
            spawn(_t_exec_plugin_method, p, f, source, data)
        except AttributeError:
            pass


def plugins_event_apicall(method, params):
    for p, v in plugin_modules.items():
        try:
            f = getattr(v, 'handle_api_call')
            # do not spawn in bg
            if f(method.__name__, params) is False:
                return False
        except AttributeError:
            pass


def plugins_event_apicall_result(method, params, result):
    for p, v in plugin_modules.items():
        try:
            f = getattr(v, 'handle_api_call_result')
            # do not spawn in bg
            if f(method.__name__, params, result) is False:
                return False
        except AttributeError:
            pass


def _t_exec_plugin_method(p, f, *args, **kwargs):
    try:
        return f(*args, **kwargs)
    except:
        logging.error(f'Error executing {p}.{f.__name__} method')
        log_traceback()


def register_controller(controller):
    controllers.append(controller)


@background_worker(interval=60, on_error=log_traceback)
async def cs_intervaller(**kwargs):
    exec_corescripts(event=SimpleNamespace(
        type=CS_EVENT_PERIODIC, topic='M',
        iteration=cs_data.periodic_iteration))
    logging.debug(f'CS periodic, iteration: {cs_data.periodic_iteration}')
    cs_data.periodic_iteration += 1


timeouter.set_default_exception_class(TimeoutException)

#BD: 20.05.2017
