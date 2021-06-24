__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"

import threading
import cherrypy
import logging
import threading
import time
import os
import sys
import shlex

import eva.core

from functools import wraps
from functools import partial

from eva.api import api_need_master
from eva.api import parse_api_params

from eva.api import format_resource_id

from eva.api import MethodNotFound
from eva.api import GenericAPI
from eva.api import GenericHTTP_API

from eva.api import log_d
from eva.api import log_i
from eva.api import log_w
from eva.api import notify_plugins

from eva.api import key_check
from eva.api import key_check_master

from eva.api import api_result_accepted

from eva.tools import format_json
from eva.tools import fname_remove_unsafe
from eva.tools import val_to_boolean
from eva.tools import dict_from_str

from eva.exceptions import FunctionFailed
from eva.exceptions import ResourceNotFound
from eva.exceptions import ResourceAlreadyExists
from eva.exceptions import AccessDenied

from eva.exceptions import InvalidParameter
from eva.tools import parse_function_params

from neotasker import task_supervisor

from eva.tools import SimpleNamespace

import eva.apikey

import eva.tokens as tokens

import eva.users

import eva.notify
import eva.registry

from eva.tools import ConfigFile
from eva.tools import ShellConfigFile

locks_locker = threading.RLock()

locks = {}
lock_expire_jobs = {}


def api_need_file_management(f):
    """
    API method decorator to pass if file management is allowed in server config
    """

    @wraps(f)
    def do(*args, **kwargs):
        if not config.api_file_management_allowed:
            raise AccessDenied
        return f(*args, **kwargs)

    return do


def api_need_rpvt(f):
    """
    API method decorator to pass if rpvt is allowed in server config
    """

    @wraps(f)
    def do(*args, **kwargs):
        if not config.api_rpvt_allowed:
            raise AccessDenied
        return f(*args, **kwargs)

    return do


def api_need_cmd(f):
    """
    API method decorator to pass if API key has "cmd" allowed
    """

    @wraps(f)
    def do(*args, **kwargs):
        if not key_check(kwargs.get('k'), allow=['cmd']):
            raise AccessDenied
        return f(*args, **kwargs)

    return do


def api_need_sysfunc(f):
    """
    API method decorator to pass if API key has "sysfunc" allowed
    """

    @wraps(f)
    def do(*args, **kwargs):
        if not key_check(kwargs.get('k'), sysfunc=True):
            raise AccessDenied
        return f(*args, **kwargs)

    return do


def api_need_lock(f):
    """
    API method decorator to pass if API key has "lock" allowed
    """

    @wraps(f)
    def do(*args, **kwargs):
        if not key_check(kwargs.get('k'), allow=['lock']):
            raise AccessDenied
        return f(*args, **kwargs)

    return do


class LockAPI(object):

    @log_i
    @api_need_lock
    @notify_plugins
    def lock(self, **kwargs):
        """
        acquire lock

        Locks can be used similarly to file locking by the specific process.
        The difference is that SYS API tokens can be:
        
        * centralized for several systems (any EVA server can act as lock
            server)

        * removed from outside

        * automatically unlocked after the expiration time, if the initiator
            failed or forgot to release the lock
        
        used to restrict parallel process starting or access to system
        files/resources. LM PLC :doc:`macro</lm/macros>` share locks with
        extrnal scripts.

        .. note::

            Even if different EVA controllers are working on the same server,
            their lock tokens are stored in different bases. To work with the
            token of each subsystem, use SYS API on the respective
            address/port.

        Args:
            k: .allow=lock
            .l: lock id

        Optional:
            t: maximum time (seconds) to acquire lock
            e: time after which lock is automatically released (if absent,
                lock may be released only via unlock function)
        """
        l, t, e = parse_api_params(kwargs, 'lte', 'S.n',
                                   {'t': eva.core.config.timeout})
        with locks_locker:
            if not l in locks:
                lobj = threading.Lock()
                locks[l] = lobj
        logging.debug(
                'acquiring lock %s, timeout = %s, expires = %s' % \
                            (l, t, e))
        lockobj = locks[l]
        if not locks[l].acquire(timeout=t):
            raise FunctionFailed('Unable to acquire lock')
        if e:
            with locks_locker:
                lock_expire_jobs[l] = task_supervisor.create_async_job(
                    'cleaners',
                    target=self._release_lock,
                    args=(l,),
                    number=1,
                    timer=e)
        return True

    async def _release_lock(self, lock_id):
        logging.debug(f'auto-releasing lock {lock_id}')
        try:
            with locks_locker:
                locks[lock_id].release()
        except:
            pass

    @log_i
    @api_need_lock
    @notify_plugins
    def get_lock(self, **kwargs):
        """
        get lock status

        Args:
            k: .allow=lock
            .l: lock id
        """
        l = parse_api_params(kwargs, 'l', 'S')
        try:
            result = format_resource_id('lock', l)
            with locks_locker:
                result['locked'] = locks[l].locked()
            return result
        except KeyError:
            raise ResourceNotFound
        except Exception as e:
            raise FunctionFailed(e)

    @log_i
    @api_need_lock
    @notify_plugins
    def unlock(self, **kwargs):
        """
        release lock

        Releases the previously acquired lock.

        Args:
            k: .allow=lock
            .l: lock id
        """
        l = parse_api_params(kwargs, 'l', 'S')
        logging.debug('releasing lock %s' % l)
        try:
            with locks_locker:
                if l in lock_expire_jobs:
                    lock_expire_jobs[l].cancel()
                    del lock_expire_jobs[l]
                locks[l].release()
            return True
        except RuntimeError:
            return True
        except KeyError:
            raise ResourceNotFound
        except Exception as e:
            raise FunctionFailed(e)


cmd_status_created = 0
cmd_status_running = 1
cmd_status_completed = 2
cmd_status_failed = 3
cmd_status_terminated = 4

cmd_status_names = ['created', 'running', 'completed', 'failed', 'terminated']


class CMD(object):

    def __init__(self, cmd, args=None, timeout=None, tki=None):
        self.cmd = fname_remove_unsafe(cmd)
        self.args = args if args else ()
        self.timeout = timeout if timeout else eva.core.config.timeout
        self.xc = None
        self.status = cmd_status_created
        self.time = {'created': time.time()}

    def run(self, input_data=None):
        try:
            import eva.runner
            self.xc = eva.runner.ExternalProcess(
                eva.core.dir_xc + '/cmd/' + self.cmd,
                args=self.args,
                timeout=self.timeout,
            )
            self.status = cmd_status_running
            self.time['running'] = time.time()
            self.xc.run(input_data=input_data)
        except:
            eva.core.log_traceback()

    def is_finished(self):
        return False if self.xc is None else self.xc.is_finished()

    def update_status(self):
        if self.status == cmd_status_running:
            if self.xc.is_finished():
                if self.xc.exitcode < 0:
                    self.status = cmd_status_terminated
                elif self.xc.exitcode > 0:
                    self.status = cmd_status_failed
                else:
                    self.status = cmd_status_completed
                self.time[cmd_status_names[self.status]] = time.time()

    def serialize(self):
        self.update_status()
        d = {}
        d['cmd'] = self.cmd
        d['args'] = self.args
        d['timeout'] = self.timeout
        d['time'] = self.time
        d['status'] = cmd_status_names[self.status]
        if self.status not in [cmd_status_created, cmd_status_running]:
            d['exitcode'] = self.xc.exitcode
            d['out'] = self.xc.out
            d['err'] = self.xc.err
        return d


class CMDAPI(object):

    @log_i
    @api_need_cmd
    @notify_plugins
    def cmd(self, **kwargs):
        """
        execute a remote system command

        Executes a :ref:`command script<cmd>` on the server where the
        controller is installed.

        Args:
            k: .allow=cmd
            .c: name of the command script

        Optional:
            a: string of command arguments, separated by spaces (passed to the
                script) or array (list)
            w: wait (in seconds) before API call sends a response. This allows
                to try waiting until command finish
            t: maximum time of command execution. If the command fails to finish
                within the specified time (in sec), it will be terminated
            s: STDIN data
        """
        cmd, args, wait, timeout, input_data = parse_api_params(
            kwargs, 'cawts', 'S.nn.')
        if cmd[0] == '/' or cmd.find('..') != -1:
            return None
        if args is not None:
            if isinstance(args, list) or isinstance(args, tuple):
                _args = tuple(args)
            else:
                try:
                    _args = tuple(shlex.split(str(args)))
                except:
                    _args = tuple(str(args).split(' '))
        else:
            _args = ()
        _args = tuple(str(a) for a in _args)
        _c = CMD(cmd, _args, timeout)
        logging.info('executing "%s %s", timeout = %s' % \
                (cmd, ' '.join(_args), timeout))
        eva.core.spawn(_c.run, input_data)
        if wait:
            eva.core.wait_for(_c.is_finished, wait)
        return _c.serialize()

    @log_w
    @api_need_master
    @notify_plugins
    def update_node(self, **kwargs):
        v, uri, yes = parse_api_params(kwargs, 'vuy', 'sss')
        env = f'EVA_UPDATE_FORCE_VERSION="{v}"' if v else ''
        uri = f'-u {uri}' if uri else ''
        if yes != 'YES':
            raise FunctionFailed('Not confirmed')
        import datetime
        log_file = eva.core.dir_eva + '/log/update.log'
        with open(log_file, 'a') as fh:
            fh.write((f'\n{datetime.datetime.now().isoformat()}\n' + '-' * 26 +
                      '\n'))
            fh.write('Updating EVA ICS to {}\n'.format(v if v else 'latest'))
        os.system(f'(sleep 0.5 && {env} {eva.core.dir_eva}/bin/eva '
                  f'update --YES {uri}) >> {log_file} 2>&1 &')
        return True


class LogAPI(object):

    @log_i
    @api_need_sysfunc
    @notify_plugins
    def log_rotate(self, **kwargs):
        """
        rotate log file
        
        Deprecated, not required since 3.3.0

        Args:
            k: .sysfunc=yes
        """
        parse_api_params(kwargs)
        return True

    @log_d
    @api_need_sysfunc
    @notify_plugins
    def log_debug(self, **kwargs):
        """
        put debug message to log file
        
        An external application can put a message in the logs on behalf of the
        controller.

        Args:
            k: .sysfunc=yes
            m: message text
        """
        m = parse_api_params(kwargs, 'm', '.')
        if m:
            logging.debug(m)
        return True

    @log_d
    @api_need_sysfunc
    @notify_plugins
    def log_info(self, **kwargs):
        """
        put info message to log file
        
        An external application can put a message in the logs on behalf of the
        controller.

        Args:
            k: .sysfunc=yes
            m: message text
        """
        m = parse_api_params(kwargs, 'm', '.')
        if m:
            logging.info(m)
        return True

    @log_d
    @api_need_sysfunc
    @notify_plugins
    def log_warning(self, **kwargs):
        """
        put warning message to log file
        
        An external application can put a message in the logs on behalf of the
        controller.

        Args:
            k: .sysfunc=yes
            m: message text
        """
        m = parse_api_params(kwargs, 'm', '.')
        if m:
            logging.warning(m)
        return True

    @log_d
    @api_need_sysfunc
    @notify_plugins
    def log_error(self, **kwargs):
        """
        put error message to log file
        
        An external application can put a message in the logs on behalf of the
        controller.

        Args:
            k: .sysfunc=yes
            m: message text
        """
        m = parse_api_params(kwargs, 'm', '.')
        if m:
            logging.error(m)
        return True

    @log_d
    @api_need_sysfunc
    @notify_plugins
    def log_critical(self, **kwargs):
        """
        put critical message to log file
        
        An external application can put a message in the logs on behalf of the
        controller.

        Args:
            k: .sysfunc=yes
            m: message text
        """
        m = parse_api_params(kwargs, 'm', '.')
        if m:
            logging.critical(m)
        return True

    @log_d
    @api_need_sysfunc
    @notify_plugins
    def log_get(self, **kwargs):
        """
        get records from the controller log

        Log records are stored in the controllers’ memory until restart or the
        time (keep_logmem) specified in controller configuration passes.

        Args:
            k: .sysfunc=yes

        Optional:
            .l: log level (10 - debug, 20 - info, 30 - warning, 40 - error, 50
                - critical)
            t: get log records not older than t seconds
            n: the maximum number of log records you want to obtain
            x: regex pattern filter
        """
        import pyaltt2.logs
        import eva.logs
        l, t, n, x = parse_api_params(kwargs, 'ltnx', '.iis')
        if not l:
            l = 'i'
        try:
            l = int(l)
        except:
            l = eva.logs.get_log_level_by_name(l)
        try:
            return pyaltt2.logs.get(level=l, t=t, n=n, pattern=x)
        except Exception as e:
            raise FunctionFailed(e)

    # don't wrap - calls other self functions
    def log(self, **kwargs):
        """
        put message to log file
        
        An external application can put a message in the logs on behalf of the
        controller.

        Args:
            k: .sysfunc=yes
            l: log level
            m: message text
        """
        import eva.logs
        k, l, m = parse_function_params(kwargs, 'klm', '.R.', {'l': 'info'})
        log_level = eva.logs.get_log_level_by_id(l)
        f = getattr(self, 'log_' + log_level)
        f(k=k, m=m)
        return True


class FileAPI(object):

    @staticmethod
    def _check_file_name(fname):
        if fname is None or \
                fname[0] == '/' or \
                fname.find('..') != -1:
            raise InvalidParameter('File name contains invalid characters')
        return True

    @staticmethod
    def _file_not_found(fname):
        return ResourceNotFound('file:runtime/{}'.format(fname))

    @log_w
    @api_need_file_management
    @api_need_master
    @notify_plugins
    def install_pkg(self, **kwargs):
        """
        install a package

        Installs the :doc:`package </packages>`

        Args:
            k: .master
            .i: package name
            m: package content (base64-encoded tar/tgz)
            o: package setup options
            w: wait (in seconds) before API call sends a response. This allows
                to try waiting until the package is installed
        """
        i, m, o, u, w = parse_api_params(kwargs, 'imouw', 'SS.bn')
        import base64
        import tarfile

        def save_corescript(name, code):
            import eva.core
            with open(f'{eva.core.dir_xc}/{eva.core.product.code}/cs/{name}.py',
                      'w') as fh:
                fh.write(code)
            eva.core.append_corescript(name)

        def pip_install(mods):
            import os
            code = os.system(f'{eva.core.dir_eva}/venv/bin/pip install {mods}')
            if code:
                raise RuntimeError('pip exited with code {code}')
            from eva.features import append_python_libraries
            if isinstance(mods, str):
                mods = mods.split()
            append_python_libraries(mods)

        try:
            raw = base64.b64decode(m)
            from io import BytesIO
            buf = BytesIO()
            buf.write(raw)
            buf.seek(0)
            pkg = tarfile.open(fileobj=buf)
        except:
            raise FunctionFailed('Invalid package format')
        try:
            code = pkg.extractfile('setup.py').read().decode()
        except:
            raise FunctionFailed('Invalid package: no setup.py found')
        for f in pkg.members.copy():
            if f.name == 'setup.py':
                pkg.members.remove(f)
        env = {
            'extract_package': partial(pkg.extractall, path=eva.core.dir_eva),
            'ConfigFile': ConfigFile,
            'ShellConfigFile': ShellConfigFile,
            'pip_install': pip_install,
            'keep_me': partial(save_corescript, i, code)
        }
        return eva.core.action(eva.core.run_corescript_code,
                               _wait=w,
                               _name='install_pkg',
                               _call_for=i,
                               code=code,
                               event=SimpleNamespace(
                                   type=eva.core.CS_EVENT_PKG_UNINSTALL
                                   if u else eva.core.CS_EVENT_PKG_INSTALL,
                                   data=o),
                               env_globals=env)

    @log_i
    @api_need_file_management
    @api_need_master
    @notify_plugins
    def file_unlink(self, **kwargs):
        """
        delete file from runtime folder

        Args:
            k: .master
            .i: relative path (without first slash)
        """
        i = parse_api_params(kwargs, 'i', 'S')
        self._check_file_name(i)
        if not os.path.isfile(eva.core.dir_runtime + '/' + i):
            raise self._file_not_found(i)
        try:
            eva.core.prepare_save()
            try:
                os.unlink(eva.core.dir_runtime + '/' + i)
                return True
            finally:
                eva.core.finish_save()
        except:
            eva.core.log_traceback()
            raise FunctionFailed

    @log_i
    @api_need_file_management
    @api_need_master
    @notify_plugins
    def file_get(self, **kwargs):
        """
        get file contents from runtime folder

        Args:
            k: .master
            .i: relative path (without first slash)
            b: if True - force getting binary file (base64-encode content)
        """
        i, b = parse_api_params(kwargs, 'ib', 'Sb')
        self._check_file_name(i)
        if not os.path.isfile(eva.core.dir_runtime + '/' + i):
            raise self._file_not_found(i)
        try:
            i = eva.core.dir_runtime + '/' + i
            with open(i, 'rb') as fd:
                data = fd.read()
            return data, os.access(i, os.X_OK)
        except:
            eva.core.log_traceback()
            raise FunctionFailed

    @log_i
    @api_need_file_management
    @api_need_master
    @notify_plugins
    def file_put(self, **kwargs):
        """
        put file to runtime folder

        Puts a new file into runtime folder. If the file with such name exists,
        it will be overwritten. As all files in runtime are text, binary data
        can not be put.

        Args:
            k: .master
            .i: relative path (without first slash)
            m: file content (plain text or base64-encoded)
            b: if True - put binary file (decode base64)
        """
        i, m, b = parse_api_params(kwargs, 'imb', 'Ssb')
        self._check_file_name(i)
        try:
            if m is None:
                raw = b''
            elif b:
                import base64
                raw = base64.b64decode(m)
            else:
                raw = m.encode()
            eva.core.prepare_save()
            if '/' in i:
                path = ''
                for dirname in i.split('/')[:-1]:
                    path += '/' + dirname
                    try:
                        os.mkdir(eva.core.dir_runtime + path)
                    except FileExistsError:
                        pass
            try:
                with open(eva.core.dir_runtime + '/' + i, 'wb') as fd:
                    fd.write(raw)
                return True
            finally:
                eva.core.finish_save()
        except:
            eva.core.log_traceback()
            raise FunctionFailed

    @log_i
    @api_need_file_management
    @api_need_master
    @notify_plugins
    def file_set_exec(self, **kwargs):
        """
        set file exec permission

        Args:
            k: .master
            .i: relative path (without first slash)
            e: *false* for 0x644, *true* for 0x755 (executable)
        """
        i, e = parse_api_params(kwargs, 'ie', 'SB')
        self._check_file_name(i)
        if not os.path.isfile(eva.core.dir_runtime + '/' + i):
            raise self._file_not_found(i)
        try:
            if e:
                perm = 0o755
            else:
                perm = 0o644
            eva.core.prepare_save()
            try:
                os.chmod(eva.core.dir_runtime + '/' + i, perm)
            finally:
                eva.core.finish_save()
            return True
        except:
            eva.core.log_traceback()
            raise FunctionFailed


class CSAPI(object):

    @log_i
    @api_need_master
    @notify_plugins
    def list_corescript_mqtt_topics(self, **kwargs):
        """
        List MQTT topics core scripts react on

        Args:
            k: .master
        """
        parse_api_params(kwargs)
        return eva.core.get_corescript_topics()

    @log_i
    @api_need_master
    @notify_plugins
    def reload_corescripts(self, **kwargs):
        """
        Reload core scripts if some was added or deleted

        Args:
            k: .master
        """
        parse_api_params(kwargs)
        eva.core.reload_corescripts()
        return True

    @log_i
    @api_need_master
    @notify_plugins
    def subscribe_corescripts_mqtt(self, **kwargs):
        """
        Subscribe core scripts to MQTT topic

        The method subscribes core scripts to topic of default MQTT notifier
        (eva_1). To specify another notifier, set topic as <notifer_id>:<topic>

        Args:
            k: .master
            t: MQTT topic ("+" and "#" masks are supported)
            q: MQTT topic QoS
            save: save core script config after modification
        """
        t, q, save = parse_api_params(kwargs, 'tqS', 'Sib')
        save = save or eva.core.config.auto_save
        if q is None:
            q = 1
        elif q < 0 or q > 2:
            raise InvalidParameter('q should be 0..2')
        return eva.core.corescript_mqtt_subscribe(
            t, q) and (eva.core.save_cs() if save else True)

    @log_i
    @api_need_master
    @notify_plugins
    def unsubscribe_corescripts_mqtt(self, **kwargs):
        """
        Unsubscribe core scripts from MQTT topic

        Args:
            k: .master
            t: MQTT topic ("+" and "#" masks are allowed)
            save: save core script config after modification
        """
        t, save = parse_api_params(kwargs, 'tS', 'Sb')
        save = save or eva.core.config.auto_save
        return eva.core.corescript_mqtt_unsubscribe(t) and (eva.core.save_cs()
                                                            if save else True)


class UserAPI(object):

    @log_d
    @notify_plugins
    def api_log_get(self, **kwargs):
        """
        get API call log

        * API call with master permission returns all records requested

        * API call with other API key returns records for the specified key
          only

        * API call with an authentication token returns records for the
          current authorized user

        Args:
            k: any valid API key

        Optional:
            s: start time (timestamp or ISO or e.g. 1D for -1 day)
            e: end time (timestamp or ISO or e.g. 1D for -1 day)
            n: records limit
            t: time format ("iso" or "raw" for unix timestamp, default is "raw")
            f: record filter (requires API key with master permission)

        Returns:
            List of API calls

        Note: API call params are returned as string and can be invalid JSON
        data as they're always truncated to 512 symbols in log database

        Record filter should be specified either as string (k1=val1,k2=val2) or
        as a dict. Valid fields are:

        * gw: filter by API gateway

        * ip: filter by caller IP

        * auth: filter by authentication type

        * u: filter by user

        * utp: filter by user type

        * ki: filter by API key ID

        * func: filter by API function

        * params: filter by API call params (matches if field contains value)

        * status: filter by API call status
        """
        k, s, e, n, t, f = parse_function_params(kwargs, 'ksentf', 'S..i..')
        if f is not None:
            if isinstance(f, str):
                try:
                    f = dict_from_str(f)
                except:
                    raise InvalidParameter('Unable to parse filter')
            elif not isinstance(f, dict):
                raise InvalidParameter('f should be dict or str')
        else:
            f = {}
        # force record filter if not master
        if not key_check_master(k, ro_op=True):
            from eva.api import get_aci
            u = get_aci('u')
            if u is not None:
                f['u'] = u
                f['utp'] = get_aci('utp')
            f['ki'] = eva.apikey.key_id(k)
        try:
            return eva.users.api_log_get(t_start=s,
                                         t_end=e,
                                         limit=n,
                                         time_format=t,
                                         f=f)
        except Exception as e:
            raise FunctionFailed(e)

    @log_w
    @api_need_master
    @notify_plugins
    def create_user(self, **kwargs):
        """
        create user account

        .. note::
        
            All changes to user accounts are instant, if the system works in
            read/only mode, set it to read/write before performing user
            management.

        Args:
            k: .master
            .u: user login
            p: user password
            a: API key to assign (key id, not a key itself)
        """
        u, p, a = parse_api_params(kwargs, 'upa', 'SSR')
        return eva.users.create_user(u, p, a)

    @log_w
    @api_need_master
    @notify_plugins
    def user_set(self, **kwargs):
        """
        .set user property

        Args:
            k: .master
            .u: user login
            p: property (password or key)
            v: value
        """
        u, p, v = parse_api_params(kwargs, 'upv', 'SSR')
        tokens.remove_token(user=u)
        if p == 'password':
            return eva.users.set_user_password(u, v)
        elif p == 'key':
            return eva.users.set_user_key(u, v)
        else:
            raise InvalidParameter('Property unknown: {}'.format(p))

    @log_w
    @notify_plugins
    def set_user_password(self, **kwargs):
        """
        set user password

        Either master key and user login must be specified or a user must be
        logged in and a session token used

        Args:
            k: master key or token
            .u: user login
            p: new password
        """
        k, u, p = parse_function_params(kwargs, 'kup', '.sS')
        if u:
            if not key_check(k, master=True):
                raise AccessDenied('master key is required for "u" param')
            else:
                tokens.remove_token(user=u)
        else:
            from eva.api import get_aci
            if get_aci('utp'):
                raise FunctionFailed(
                    'unable to change password for a non-local user')
            u = get_aci('u')
        if not u:
            raise InvalidParameter(
                'user should be either specified in "u" param or logged in')
        return eva.users.set_user_password(u, p)

    @log_w
    @api_need_master
    @notify_plugins
    def set_user_key(self, **kwargs):
        """
        assign API key to user

        Args:
            k: .master
            .u: user login
            a: API key to assign (key id, not a key itself) or multiple keys,
                comma separated
        """
        u, a = parse_api_params(kwargs, 'ua', 'SS')
        tokens.remove_token(user=u)
        return eva.users.set_user_key(u, a)

    @log_w
    @api_need_master
    @notify_plugins
    def destroy_user(self, **kwargs):
        """
        delete user account

        Args:
            k: .master
            .u: user login
        """
        u = parse_api_params(kwargs, 'u', 'S')
        tokens.remove_token(user=u)
        return eva.users.destroy_user(u)

    @log_i
    @api_need_master
    @notify_plugins
    def list_users(self, **kwargs):
        """
        list user accounts

        Args:
            k: .master
        """
        parse_api_params(kwargs)
        return eva.users.list_users()

    @log_i
    @api_need_master
    @notify_plugins
    def get_user(self, **kwargs):
        """
        get user account info

        Args:
            k: .master
            .u: user login
        """
        u = parse_api_params(kwargs, 'u', 'S')
        return eva.users.get_user(u)

    @log_w
    @api_need_master
    @notify_plugins
    def list_keys(self, **kwargs):
        """
        list API keys

        Args:
            k: .master
        """
        parse_api_params(kwargs)
        result = []
        with eva.apikey.key_lock:
            for _k, v in eva.apikey.keys.items():
                if not v.temporary:
                    r = eva.apikey.serialized_acl(_k)
                    r['dynamic'] = v.dynamic
                    result.append(r)
        return sorted(sorted(result, key=lambda k: k['key_id']),
                      key=lambda k: k['master'],
                      reverse=True)

    @log_w
    @api_need_master
    @notify_plugins
    def create_key(self, **kwargs):
        """
        create API key

        API keys are defined statically in EVA registry
        config/<controller>/apikeys tree or can be created with API and stored
        in the user database.

        Keys with the master permission can not be created.

        Args:
            k: .master
            .i: API key ID
            save: save configuration immediately
        
        Returns:
            JSON with serialized key object
        """
        i, save = parse_api_params(kwargs, 'iS', 'Sb')
        save = save or eva.core.config.auto_save
        return eva.apikey.add_api_key(i, save)

    @log_w
    @api_need_master
    @notify_plugins
    def list_key_props(self, **kwargs):
        """
        list API key permissions

        Lists API key permissons (including a key itself)

        .. note::

            API keys defined in EVA registry can not be managed with API.

        Args:
            k: .master
            .i: API key ID
            save: save configuration immediately
        """
        i = parse_api_params(kwargs, 'i', 'S')
        key = eva.apikey.keys_by_id.get(i)
        return None if not key or not key.dynamic else key.serialize()

    @log_w
    @api_need_master
    @notify_plugins
    def set_key_prop(self, **kwargs):
        """
        set API key permissions

        Args:
            k: .master
            .i: API key ID
            p: property
            v: value (if none, permission will be revoked)
            save: save configuration immediately
        """
        i, p, v, save = parse_api_params(kwargs, 'ipvS', 'SS.b')
        save = save or eva.core.config.auto_save
        tokens.remove_token(key_id=i)
        key = eva.apikey.keys_by_id.get(i)
        if not key:
            raise ResourceNotFound
        return key.set_prop(p, v, save)

    @log_w
    @api_need_master
    @notify_plugins
    def regenerate_key(self, **kwargs):
        """
        regenerate API key

        Args:
            k: .master
            .i: API key ID

        Returns:
            JSON dict with new key value in "key" field
        """
        i, save = parse_api_params(kwargs, 'iS', 'Sb')
        save = save or eva.core.config.auto_save
        tokens.remove_token(key_id=i)
        return eva.apikey.regenerate_key(i, save)

    @log_w
    @api_need_master
    @notify_plugins
    def destroy_key(self, **kwargs):
        """
        delete API key

        Args:
            k: .master
            .i: API key ID
        """
        i = parse_api_params(kwargs, 'i', 'S')
        tokens.remove_token(key_id=i)
        return eva.apikey.delete_api_key(i)

    @log_d
    @api_need_master
    @notify_plugins
    def list_tokens(self, **kwargs):
        """
        List active session tokens

        Args:
            k: .master
        """
        return tokens.list_tokens()

    @log_w
    @api_need_master
    @notify_plugins
    def drop_tokens(self, **kwargs):
        """
        Drop session token(s)

        Args:
            k: .master
            a: session token or
            u: user name or
            i: API key id
        """
        a, u, i = parse_api_params(kwargs, 'aui', 'sss')
        if not a and not u and not i:
            raise InvalidParameter('No drop parameters specified')
        return tokens.remove_token(token=a, user=u, key_id=i)


class SysAPI(CSAPI, LockAPI, CMDAPI, LogAPI, FileAPI, UserAPI, GenericAPI):

    def __init__(self):
        super().__init__()
        self._nofp_log('create_user', 'p')
        self._nofp_log('set_user_password', 'p')
        self._nofp_log('file_put', 'm')
        self._nofp_log('cmd', 's')
        self._nofp_log('install_plugin', ['m', 'c'])
        self._nofp_log('install_pkg', ['m', 'o'])

    @log_d
    @api_need_rpvt
    @notify_plugins
    def rpvt(self, **kwargs):
        k, f, ic, nocache = parse_function_params(kwargs,
                                                  ['k', 'f', 'ic', 'nocache'],
                                                  '.S..')
        if not key_check(k, rpvt_uri=f, ro_op=True):
            logging.warning('rpvt uri %s access forbidden' % (f))
            eva.core.log_traceback()
            raise AccessDenied
        try:
            import requests
            if f.find('//') == -1:
                _f = 'http://' + f
            else:
                _f = f
            r = requests.get(_f, timeout=eva.core.config.timeout)
        except:
            eva.core.log_traceback()
            raise FunctionFailed('remote error')
        if r.status_code != 200:
            raise FunctionFailed('remote response %s' % r.status_code)
        ctype = r.headers.get('Content-Type', 'text/html')
        result = r.content
        if ic:
            try:
                icmd, args, fmt = ic.split(':')
                if icmd == 'resize':
                    x, y, q = args.split('x')
                    x = int(x)
                    y = int(y)
                    q = int(q)
                    from PIL import Image
                    from io import BytesIO
                    image = Image.open(BytesIO(result))
                    image.thumbnail((x, y))
                    result = image.tobytes(fmt, 'RGB', q)
                    ctype = 'image/' + fmt
                else:
                    eva.core.log_traceback()
                    raise FunctionFailed('image processing failed')
            except FunctionFailed:
                eva.core.log_traceback()
                raise
            except:
                eva.core.log_traceback()
                raise FunctionFailed
        return result, ctype

    @log_i
    @api_need_sysfunc
    @notify_plugins
    def save(self, **kwargs):
        """
        save database and runtime configuration

        All modified items, their status, and configuration will be written to
        the disk. If **exec_before_save** command is defined in the
        controller's configuration file, it's called before saving and
        **exec_after_save** after (e.g. to switch the partition to write mode
        and back to read-only).

        Args:
            k: .sysfunc=yes
        """
        parse_api_params(kwargs)
        return eva.core.do_save()

    @log_w
    @api_need_sysfunc
    @notify_plugins
    def registry_safe_purge(self, **kwargs):
        """
        Safely purge registry database

        Clears registry trash and invalid files. Keeps broken keys

        Args:
            k: .sysfunc=yes
        """
        parse_api_params(kwargs)
        try:
            eva.registry.safe_purge()
            return True
        except Exception as e:
            raise FunctionFailed(e)

    @log_w
    @api_need_master
    @notify_plugins
    def dump(self, **kwargs):
        """
        Create crash dump

        Args:
            k: .master
        """
        parse_api_params(kwargs)
        return eva.core.create_dump()

    @log_d
    @api_need_master
    @notify_plugins
    def list_plugins(self, **kwargs):
        """
        get list of loaded core plugins

        Args:
            k: .master

        Returns:
            list with plugin module information
        """
        return eva.core.serialize_plugins()

    @log_d
    @api_need_master
    @notify_plugins
    def get_cvar(self, **kwargs):
        """
        get the value of user-defined variable

        .. note::
        
            Even if different EVA controllers are working on the same
            server, they have different sets of variables To set the variables
            for each subsystem, use SYS API on the respective address/port.

        Args:
            k: .master

        Optional:
            .i: variable name

        Returns:
            Dict containing variable and its value. If no varible name was
            specified, all cvars are returned.
        """
        k, i = parse_function_params(kwargs, 'ki', '..')
        if i:
            val = eva.core.get_cvar(i)
            if val is None:
                raise ResourceNotFound
            return val
        else:
            return eva.core.get_cvar()

    @log_i
    @api_need_master
    @notify_plugins
    def set_cvar(self, **kwargs):
        """
        set the value of user-defined variable

        Args:
            k: .master
            .i: variable name

        Optional:
            v: variable value (if not specified, variable is deleted)
        """
        i, v = parse_api_params(kwargs, 'iv', 'S.')
        return eva.core.set_cvar(i, v)

    @log_d
    @api_need_master
    @notify_plugins
    def list_notifiers(self, **kwargs):
        """
        list notifiers

        Args:
            k: .master
        """
        parse_api_params(kwargs)
        result = []
        for n in eva.notify.get_notifiers(include_clients=True):
            result.append(n.serialize_info())
        return sorted(result, key=lambda k: k['id'])

    @log_d
    @api_need_master
    @notify_plugins
    def get_notifier(self, **kwargs):
        """
        get notifier configuration

        Args:
            k: .master
            .i: notifier ID
        """
        i = parse_api_params(kwargs, 'i', 'S')
        try:
            return eva.notify.get_notifier(
                i, get_default=False).serialize(info=True)
        except:
            raise ResourceNotFound

    @log_w
    @api_need_master
    @notify_plugins
    def enable_notifier(self, **kwargs):
        """
        enable notifier

        .. note::

            The notifier is enabled until controller restart. To enable
            notifier permanently, use notifier management CLI.

        Args:
            k: .master
            .i: notifier ID
        """
        i = parse_api_params(kwargs, 'i', 'S')
        try:
            eva.notify.get_notifier(i).enabled = True
        except:
            raise ResourceNotFound
        return True

    @log_w
    @api_need_master
    @notify_plugins
    def disable_notifier(self, **kwargs):
        """
        disable notifier

        .. note::

            The notifier is disabled until controller restart. To disable
            notifier permanently, use notifier management CLI.

        Args:
            k: .master
            .i: notifier ID
        """
        i = parse_api_params(kwargs, 'i', 'S')
        try:
            eva.notify.get_notifier(i).enabled = False
        except:
            raise ResourceNotFound
        return True

    @log_w
    @api_need_master
    @notify_plugins
    def set_debug(self, **kwargs):
        """
        switch debugging mode

        Enables and disables debugging mode while the controller is running.
        After the controller is restarted, this parameter is lost and
        controller switches back to the mode specified in the configuration
        file.

        Args:
            k: .master
            debug: true for enabling debug mode, false for disabling
        """
        debug = parse_api_params(kwargs, ('debug',), 'B')
        if debug:
            eva.core.debug_on()
        else:
            eva.core.debug_off()
        return True

    @log_w
    @api_need_master
    @notify_plugins
    def setup_mode(self, **kwargs):
        setup = parse_api_params(kwargs, ('setup',), 'B')
        if not config.api_setup_mode:
            return False
        if setup:
            eva.core.setup_on(config.api_setup_mode)
        else:
            eva.core.setup_off()
        return True

    @log_w
    @api_need_master
    @notify_plugins
    def shutdown_core(self, **kwargs):
        """
        shutdown the controller

        Controller process will be exited and then (should be) restarted by
        watchdog. This allows to restart controller remotely.

        For MQTT API calls a small shutdown delay usually should be specified
        to let the core send the correct API response.

        Returns:
            current boot id. This allows client to check is the controller
            restarted later, by comparing returned boot id and new boot id
            (obtained with "test" command)

        Args:
            k: .master
            t: shutdown delay (seconds)
        """

        def delayed_shutdown(delay):
            os.system('touch {}/{}_reload'.format(eva.core.dir_var,
                                                  eva.core.product.code))
            if delay:
                time.sleep(delay)
            eva.core.sighandler_term()

        t = parse_api_params(kwargs, 't', 'n')
        threading.Thread(target=delayed_shutdown, args=(t,)).start()
        return {'boot_id': eva.core._flags.boot_id}, api_result_accepted

    @log_w
    @api_need_master
    @notify_plugins
    def notify_leaving(self, **kwargs):
        """
        notify cloud about leaving. event will be sent at server restart

        Args:
            k: .master
            .i: notifier ID
        """
        i = parse_api_params(kwargs, 'i', 's')
        n = eva.notify.get_notifier(i)
        if not n:
            raise ResourceNotFound
        eva.notify.mark_leaving(n)
        return True

    @log_w
    @api_need_master
    @notify_plugins
    def install_plugin(self, **kwargs):
        prod = ['uc', 'lm', 'sfa']
        from eva.x import import_x
        i, m, c = parse_api_params(kwargs, 'imc', 'Ss.')
        if isinstance(c, str):
            try:
                c = dict_from_str(c)
            except:
                raise InvalidParameter('Unable to parse config')
        elif c is None:
            c = {}
        fname = f'{eva.core.dir_eva}/plugins/{i}.py'
        if m:
            with open(fname, 'w') as fh:
                fh.write(m)
        if i in eva.core.plugin_modules:
            raise ResourceAlreadyExists
        mod = import_x(fname)
        configs = eva.core.exec_plugin_func(i,
                                            mod,
                                            'install',
                                            c,
                                            raise_err=True)
        products = mod.flags.products
        for p in prod:
            if p in products:
                plugin_config = {
                    'enabled': True,
                }
                if configs:
                    if p in configs:
                        plugin_config['config'] = configs[p]
                eva.registry.key_set(f'config/{p}/plugins/{i}', plugin_config)
        return True

    @log_w
    @api_need_master
    @notify_plugins
    def uninstall_plugin(self, **kwargs):
        i = parse_api_params(kwargs, 'i', 'S')
        if not i in eva.core.plugin_modules:
            raise ResourceNotFound
        eva.core.exec_plugin_func(i,
                                  eva.core.plugin_modules[i],
                                  'uninstall',
                                  raise_err=True)
        products = eva.core.plugin_modules[i].flags.products
        for p in products:
            eva.registry.key_delete(f'config/{p}/plugins/{i}')
        return True

    @log_i
    @api_need_master
    @notify_plugins
    def clear_lang_cache(self, **kwargs):
        """
        Clear language cache
        """
        parse_api_params(kwargs, '', '')
        import eva.lang
        eva.lang.clear_cache()
        return True


class SysHTTP_API_abstract(SysAPI):

    def dump(self, **kwargs):
        fname = super().dump(**kwargs)
        if not fname:
            raise FunctionFailed
        return {'file': fname}

    def get_cvar(self, **kwargs):
        result = super().get_cvar(**kwargs)
        return {kwargs['i']: result} if 'i' in kwargs else result

    def file_get(self, **kwargs):
        i, b = parse_api_params(kwargs, 'ib', 'Sb')
        data, e = super().file_get(**kwargs)
        try:
            if b:
                raise Exception  # force binary
            data = data.decode()
            ct = 'text/plain'
        except:
            import base64
            data = base64.b64encode(data).decode()
            ct = 'application/octet-stream'
        return {
            'file': kwargs.get('i'),
            'data': data,
            'e': e,
            'content_type': ct
        }

    def regenerate_key(self, **kwargs):
        return {'key': super().regenerate_key(**kwargs)}


class SysHTTP_API(SysHTTP_API_abstract, GenericHTTP_API):

    def __init__(self):
        GenericHTTP_API.__init__(self)
        SysHTTP_API_abstract.__init__(self)
        self.expose_api_methods('sysapi')
        self._expose('test')
        self.wrap_exposed()


class SysHTTP_API_REST_abstract:

    def GET(self, rtp, k, ii, save, kind, method, for_dir, props):
        if rtp == 'core':
            return self.test(k=k)
        if rtp == 'plugin':
            return self.list_plugins(k=k)
        elif rtp == 'core@apilog':
            return self.api_log_get(k=k, **props)
        elif rtp == 'cvar':
            return self.get_cvar(k=k, i=ii)
        elif rtp == 'lock':
            if ii:
                return self.get_lock(k=k, l=ii)
        elif rtp == 'key':
            if ii:
                return self.list_key_props(k=k, i=ii)
            else:
                return self.list_keys(k=k)
        elif rtp == 'log':
            return self.log_get(k=k, l=ii, **props)
        elif rtp == 'notifier':
            if ii:
                return self.get_notifier(k=k, i=ii)
            else:
                return self.list_notifiers(k=k)
        elif rtp == 'runtime':
            return self.file_get(k=k, i=ii)
        elif rtp == 'corescript':
            if ii == 'mqtt-topics':
                return self.list_corescript_mqtt_topics(k=k)
        elif rtp == 'user':
            if ii:
                return self.get_user(k=k, u=ii)
            else:
                return self.list_users(k=k)
        raise MethodNotFound

    def POST(self, rtp, k, ii, save, kind, method, for_dir, props):
        if rtp == 'core':
            if method == 'dump':
                return self.dump(k=k)
            elif method == 'save':
                return self.save(k=k)
            elif method == 'log_rotate':
                return self.log_rotate(k=k)
            elif method == 'shutdown':
                return self.shutdown_core(k=k)
            else:
                raise MethodNotFound
        elif rtp == 'corescript':
            if method == 'reload':
                return self.reload_corescripts(k=k)
            elif method == 'mqtt-subscribe':
                return self.subscribe_corescripts_mqtt(k=k, **props)
            elif method == 'mqtt-unsubscribe':
                return self.unsubscribe_corescripts_mqtt(k=k, **props)
        elif rtp == 'cs' or rtp.startswith('cs/'):
            if ii is None:
                ii = ''
                uri_p = []
            else:
                uri_p = ii.split('/')
            eva.core.exec_corescripts(
                event=SimpleNamespace(type=eva.core.CS_EVENT_API,
                                      topic=ii,
                                      topic_p=uri_p,
                                      data=props,
                                      k=k))
            return True
        elif rtp == 'token':
            return self.login(k=k, **props)
        elif rtp == 'key':
            if method == 'regenerate' and ii:
                return self.regenerate_key(k=k, i=ii)
            else:
                raise MethodNotFound
        elif rtp == 'log':
            return self.log(k=k, l=ii, **props)
        elif rtp == 'cmd':
            if not ii:
                raise ResourceNotFound
            return self.cmd(k=k, c=ii, **props)
        raise MethodNotFound

    def PUT(self, rtp, k, ii, save, kind, method, for_dir, props):
        if rtp == 'cvar':
            self.set_cvar(k=k, i=ii, **props)
            return self.get_cvar(k=k, i=ii)
        elif rtp == 'key':
            if not SysAPI.create_key(self, k=k, i=ii, save=save):
                raise FunctionFailed
            for i, v in props.items():
                if not SysAPI.set_key_prop(self, k=k, i=ii, p=i, v=v,
                                           save=save):
                    raise FunctionFailed
            return self.list_key_props(k=k, i=ii)
        elif rtp == 'lock':
            self.lock(k=k, l=ii, **props)
            return self.get_lock(k=k, l=ii)
        elif rtp == 'runtime':
            m, e = parse_api_params(props, 'me', 'rb')
            SysAPI.file_put(self, k=k, i=ii, m=m)
            if e is not None:
                self.file_set_exec(k=k, i=ii, e=props['e'])
            return format_resource_id(rtp, ii)
        elif rtp == 'user':
            return self.create_user(k=k, u=ii, **props)
        raise MethodNotFound

    def PATCH(self, rtp, k, ii, save, kind, method, for_dir, props):
        if rtp == 'cvar':
            return self.set_cvar(k=k, i=ii, **props)
        elif rtp == 'core':
            success = False
            if 'debug' in props:
                if not self.set_debug(k=k, debug=props['debug']):
                    raise FunctionFailed
                success = True
            if 'setup' in props:
                if not self.setup_mode(k=k, setup=props['setup']):
                    raise FunctionFailed
                success = True
            if success:
                return True
            else:
                raise ResourceNotFound
        elif rtp == 'key':
            for i, v in props.items():
                if not SysAPI.set_key_prop(self, k=k, i=ii, p=i, v=v,
                                           save=save):
                    raise FunctionFailed
            return True
        elif rtp == 'notifier':
            if not 'enabled' in props:
                raise FunctionFailed
            return self.enable_notifier(k=k, i=ii) if val_to_boolean(
                props.get('enabled')) else self.disable_notifier(k=k, i=ii)
        elif rtp == 'runtime':
            m, e = parse_api_params(props, 'me', '.b')
            if m is not None:
                SysAPI.file_put(self, k=k, i=ii, m=m)
            if e is not None:
                self.file_set_exec(k=k, i=ii, e=e)
            return True
        elif rtp == 'user':
            for p, v in props.items():
                if not self.user_set(k=k, u=ii, p=p, v=v):
                    return False
            return True
        raise MethodNotFound

    def DELETE(self, rtp, k, ii, save, kind, method, for_dir, props):
        if rtp == 'key':
            return self.destroy_key(k=k, i=ii)
        if rtp == 'token':
            return self.logout(k=k)
        elif rtp == 'lock':
            return self.unlock(k=k, l=ii)
        elif rtp == 'runtime':
            return self.file_unlink(k=k, i=ii)
        elif rtp == 'user':
            return self.destroy_user(k=k, u=ii)
        raise MethodNotFound


def update_config(cfg):
    try:
        config.api_file_management_allowed = cfg.get('sysapi/file-management')
    except LookupError:
        pass
    try:
        config.api_rpvt_allowed = cfg.get('sysapi/rpvt')
    except LookupError:
        pass
    logging.debug(
        f'sysapi.file_management = {config.api_file_management_allowed}')
    try:
        s = cfg.get('sysapi/setup-mode')
        s = 60 if s is True else int(s)
        config.api_setup_mode = s
    except:
        pass
    logging.debug(f'sysapi.setup_mode = {config.api_setup_mode}')
    return True


def start():
    http_api = SysHTTP_API()
    cherrypy.tree.mount(http_api, http_api.api_uri)


api = SysAPI()

config = SimpleNamespace(api_file_management_allowed=False,
                         api_setup_mode=None,
                         api_rpvt_allowed=False)
