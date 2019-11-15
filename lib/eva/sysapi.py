__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.6"

import threading
import cherrypy
import logging
import threading
import time
import os
import sys
import shlex

import eva.core

from pyaltt import background_job

from functools import wraps

from eva.api import api_need_master
from eva.api import parse_api_params

from eva.api import format_resource_id

from eva.api import MethodNotFound
from eva.api import GenericAPI
from eva.api import GenericHTTP_API

from eva.api import log_d
from eva.api import log_i
from eva.api import log_w

from eva.api import api_result_accepted

from eva.tools import format_json
from eva.tools import fname_remove_unsafe
from eva.tools import val_to_boolean

from eva.exceptions import FunctionFailed
from eva.exceptions import ResourceNotFound
from eva.exceptions import AccessDenied

from eva.exceptions import InvalidParameter
from eva.tools import parse_function_params

from pyaltt import background_worker
from pyaltt import background_job

from types import SimpleNamespace

import eva.apikey

import eva.tokens as tokens

import eva.users

import eva.notify

locks = {}
lock_expire_time = {}


def api_need_file_management(f):

    @wraps(f)
    def do(*args, **kwargs):
        if not config.api_file_management_allowed:
            raise AccessDenied
        return f(*args, **kwargs)

    return do


def api_need_rpvt(f):

    @wraps(f)
    def do(*args, **kwargs):
        if not config.api_rpvt_allowed:
            raise AccessDenied
        return f(*args, **kwargs)

    return do


def api_need_cmd(f):

    @wraps(f)
    def do(*args, **kwargs):
        if not eva.apikey.check(kwargs.get('k'), allow=['cmd']):
            raise AccessDenied
        return f(*args, **kwargs)

    return do


def api_need_sysfunc(f):

    @wraps(f)
    def do(*args, **kwargs):
        if not eva.apikey.check(kwargs.get('k'), sysfunc=True):
            raise AccessDenied
        return f(*args, **kwargs)

    return do


def api_need_lock(f):

    @wraps(f)
    def do(*args, **kwargs):
        if not eva.apikey.check(kwargs.get('k'), allow=['lock']):
            raise AccessDenied
        return f(*args, **kwargs)

    return do


class LockAPI(object):

    @log_i
    @api_need_lock
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
        if not l in locks:
            locks[l] = threading.Lock()
        logging.debug(
                'acquiring lock %s, timeout = %s, expires = %s' % \
                            (l, t, e))
        if not locks[l].acquire(timeout=t):
            raise FunctionFailed('Unable to acquire lock')
        if e:
            lock_expire_time[l] = time.time() + e
        return True

    @log_i
    @api_need_lock
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
            result['locked'] = locks[l].locked()
            return result
        except KeyError:
            raise ResourceNotFound
        except Exception as e:
            raise
            raise FunctionFailed(e)

    @log_i
    @api_need_lock
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

    def run(self):
        import eva.runner
        self.xc = eva.runner.ExternalProcess(
            eva.core.dir_xc + '/cmd/' + self.cmd,
            args=self.args,
            timeout=self.timeout,
        )
        self.status = cmd_status_running
        self.time['running'] = time.time()
        self.xc.run()

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
                script)
            w: wait (in seconds) before API call sends a response. This allows
                to try waiting until command finish
            t: maximum time of command execution. If the command fails to finish
                within the specified time (in sec), it will be terminated
        """
        cmd, args, wait, timeout = parse_api_params(kwargs, 'cawt', 'S.nn')
        if cmd[0] == '/' or cmd.find('..') != -1:
            return None
        if args is not None:
            try:
                _args = tuple(shlex.split(str(args)))
            except:
                _args = tuple(str(args).split(' '))
        else:
            _args = ()
        _c = CMD(cmd, _args, timeout)
        logging.info('executing "%s %s", timeout = %s' % \
                (cmd, ''.join(list(_args)), timeout))
        t = threading.Thread(
            target=_c.run, name='sysapi_c_run_%f' % time.time())
        t.start()
        if wait:
            eva.core.wait_for(_c.xc.is_finished, wait)
        return _c.serialize()


class LogAPI(object):

    @log_i
    @api_need_sysfunc
    def log_rotate(self, **kwargs):
        """
        rotate log file
        
        Equal to kill -HUP <controller_process_pid>.

        Args:
            k: .sysfunc=yes
        """
        parse_api_params(kwargs)
        try:
            eva.core.reset_log()
        except:
            eva.core.log_traceback()
            raise FunctionFailed
        return True

    @log_d
    @api_need_sysfunc
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
        if m: logging.debug(m)
        return True

    @log_d
    @api_need_sysfunc
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
        if m: logging.info(m)
        return True

    @log_d
    @api_need_sysfunc
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
        if m: logging.warning(m)
        return True

    @log_d
    @api_need_sysfunc
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
        if m: logging.error(m)
        return True

    @log_d
    @api_need_sysfunc
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
        if m: logging.critical(m)
        return True

    @log_d
    @api_need_sysfunc
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
        """
        import eva.logs
        l, t, n = parse_api_params(kwargs, 'ltn', '.ii')
        if not l: l = 'i'
        try:
            l = int(l)
        except:
            l = eva.logs.get_log_level_by_name(l)
        return eva.logs.log_get(logLevel=l, t=t, n=n)

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

    @log_i
    @api_need_file_management
    @api_need_master
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
    def file_get(self, **kwargs):
        """
        get file contents from runtime folder

        Args:
            k: .master
            .i: relative path (without first slash)
        """
        i = parse_api_params(kwargs, 'i', 'S')
        self._check_file_name(i)
        if not os.path.isfile(eva.core.dir_runtime + '/' + i):
            raise self._file_not_found(i)
        try:
            i = eva.core.dir_runtime + '/' + i
            with open(i) as fd:
                data = fd.read()
            return data, os.access(i, os.X_OK)
        except:
            eva.core.log_traceback()
            raise FunctionFailed

    @log_i
    @api_need_file_management
    @api_need_master
    def file_put(self, **kwargs):
        """
        put file to runtime folder

        Puts a new file into runtime folder. If the file with such name exists,
        it will be overwritten. As all files in runtime are text, binary data
        can not be put.

        Args:
            k: .master
            .i: relative path (without first slash)
            m: file content
        """
        i, m = parse_api_params(kwargs, 'im', 'Ss')
        self._check_file_name(i)
        try:
            raw = '' if m is None else m
            eva.core.prepare_save()
            try:
                with open(eva.core.dir_runtime + '/' + i, 'w') as fd:
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
            if e: perm = 0o755
            else: perm = 0o644
            eva.core.prepare_save()
            try:
                os.chmod(eva.core.dir_runtime + '/' + i, perm)
            finally:
                eva.core.finish_save()
            return True
        except:
            eva.core.log_traceback()
            raise FunctionFailed


class UserAPI(object):

    @log_w
    @api_need_master
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
        u, p, a = parse_api_params(kwargs, 'upa', 'SSS')
        return eva.users.create_user(u, p, a)

    @log_w
    @api_need_master
    def user_set(self, **kwargs):
        """
        .set user property

        Args:
            k: .master
            .u: user login
            p: property (password or key)
            v: value
        """
        u, p, v = parse_api_params(kwargs, 'upv', 'SSS')
        tokens.remove_token(user=u)
        if p == 'password':
            return eva.users.set_user_password(u, v)
        elif p == 'key':
            return eva.users.set_user_key(u, v)
        else:
            raise InvalidParameter('Property unknown: {}'.format(p))

    @log_w
    @api_need_master
    def set_user_password(self, **kwargs):
        """
        set user password

        Args:
            k: .master
            .u: user login
            p: new password
        """
        u, p = parse_api_params(kwargs, 'up', 'SS')
        tokens.remove_token(user=u)
        return eva.users.set_user_password(u, p)

    @log_w
    @api_need_master
    def set_user_key(self, **kwargs):
        """
        assign API key to user

        Args:
            k: .master
            .u: user login
            a: API key to assign (key id, not a key itself)
        """
        u, a = parse_api_params(kwargs, 'ua', 'SS')
        tokens.remove_token(user=u)
        return eva.users.set_user_key(u, a)

    @log_w
    @api_need_master
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
    def list_keys(self, **kwargs):
        """
        list API keys

        Args:
            k: .master
        """
        parse_api_params(kwargs)
        result = []
        for _k in eva.apikey.keys:
            r = eva.apikey.serialized_acl(_k)
            r['dynamic'] = eva.apikey.keys[_k].dynamic
            result.append(r)
        return sorted(
            sorted(result, key=lambda k: k['key_id']),
            key=lambda k: k['master'],
            reverse=True)

    @log_w
    @api_need_master
    def create_key(self, **kwargs):
        """
        create API key

        API keys are defined statically in etc/<controller>_apikeys.ini file as
        well as can be created with API and stored in user database.

        Keys with master permission can not be created.

        Args:
            k: .master
            .i: API key ID
            save: save configuration immediately
        
        Returns:
            JSON with serialized key object
        """
        i, save = parse_api_params(kwargs, 'iS', 'Sb')
        return eva.apikey.add_api_key(i, save)

    @log_w
    @api_need_master
    def list_key_props(self, **kwargs):
        """
        list API key permissions

        Lists API key permissons (including a key itself)

        .. note::

            API keys, defined in etc/<controller>_apikeys.ini file can not be
            managed with API.

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
        tokens.remove_token(key_id=i)
        key = eva.apikey.keys_by_id.get(i)
        if not key: raise ResourceNotFound
        return key.set_prop(p, v, save)

    @log_w
    @api_need_master
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
        tokens.remove_token(key_id=i)
        return eva.apikey.regenerate_key(i, save)

    @log_w
    @api_need_master
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


class SysAPI(LockAPI, CMDAPI, LogAPI, FileAPI, UserAPI, GenericAPI):

    def __init__(self):
        super().__init__()
        self._nofp_log('create_user', 'p')
        self._nofp_log('set_user_password', 'p')
        self._nofp_log('file_put', 'm')

    @log_d
    @api_need_rpvt
    def rpvt(self, **kwargs):
        k, f, ic, nocache = parse_function_params(
            kwargs, ['k', 'f', 'ic', 'nocache'], '.S..')
        if not eva.apikey.check(k, rpvt_uri=f):
            logging.warning('rpvt uri %s access forbidden' % (f))
            eva.core.log_traceback()
            raise AccessDenied
        try:
            import requests
            if f.find('//') == -1: _f = 'http://' + f
            else: _f = f
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
    @api_need_master
    def dump(self, **kwargs):
        parse_api_params(kwargs)
        return eva.core.create_dump()

    @log_d
    @api_need_master
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
            if eva.apikey.check_master(k):
                return eva.core.get_cvar()
            else:
                raise AccessDenied

    @log_i
    @api_need_master
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
    def list_notifiers(self, **kwargs):
        """
        list notifiers

        Args:
            k: .master
        """
        parse_api_params(kwargs)
        result = []
        for n in eva.notify.get_notifiers():
            result.append(n.serialize())
        return sorted(result, key=lambda k: k['id'])

    @log_d
    @api_need_master
    def get_notifier(self, **kwargs):
        """
        get notifier configuration

        Args:
            k: .master
            .i: notifier ID
        """
        i = parse_api_params(kwargs, 'i', 'S')
        try:
            return eva.notify.get_notifier(i, get_default=False).serialize()
        except:
            raise ResourceNotFound

    @log_w
    @api_need_master
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
    def shutdown_core(self, **kwargs):
        """
        shutdown the controller

        Controller process will be exited and then (should be) restarted by
        watchdog. This allows to restart controller remotely.

        Args:
            k: .master
        """
        parse_api_params(kwargs)
        os.system('touch {}/{}_reload'.format(eva.core.dir_var,
                                              eva.core.product.code))
        background_job(eva.core.sighandler_term)()
        return True, api_result_accepted

    @log_w
    @api_need_master
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


class SysHTTP_API_abstract(SysAPI):

    def dump(self, **kwargs):
        fname = super().dump(**kwargs)
        if not fname: raise FunctionFailed
        return {'file': fname}

    def get_cvar(self, **kwargs):
        result = super().get_cvar(**kwargs)
        return {kwargs['i']: result} if 'i' in kwargs else result

    def file_get(self, **kwargs):
        data, e = super().file_get(**kwargs)
        return {
            'file': kwargs.get('i'),
            'data': data,
            'e': e,
            'content_type': 'text/plain'
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
            if not ii: raise ResourceNotFound
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
                if not SysAPI.set_key_prop(
                        self, k=k, i=ii, p=i, v=v, save=save):
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
            if success: return True
            else: raise ResourceNotFound
        elif rtp == 'key':
            for i, v in props.items():
                if not SysAPI.set_key_prop(
                        self, k=k, i=ii, p=i, v=v, save=save):
                    raise FunctionFailed
            return True
        elif rtp == 'notifier':
            if not 'enabled' in props:
                raise FunctionFailed
            return self.enable_notifier(
                k=k, i=ii) if val_to_boolean(
                    props.get('enabled')) else self.disable_notifier(
                        k=k, i=ii)
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
        config.api_file_management_allowed = (cfg.get(
            'sysapi', 'file_management') == 'yes')
    except:
        pass
    try:
        config.api_rpvt_allowed = (cfg.get('sysapi', 'rpvt') == 'yes')
    except:
        pass
    logging.debug('sysapi.file_management = %s' % ('yes' \
            if config.api_file_management_allowed else 'no'))
    try:
        s = cfg.get('sysapi', 'setup_mode')
        s = 60 if s == 'yes' else int(s)
        config.api_setup_mode = s
    except:
        pass
    logging.debug('sysapi.setup_mode = %s' % config.api_setup_mode)
    return True


def start():
    http_api = SysHTTP_API()
    cherrypy.tree.mount(http_api, http_api.api_uri)
    lock_processor.start(_interval=eva.core.config.polldelay)


@eva.core.stop
def stop():
    lock_processor.stop()


@background_worker
def lock_processor(**kwargs):
    for i, v in lock_expire_time.copy().items():
        if time.time() > v:
            logging.debug('lock %s expired, releasing' % i)
            try:
                del lock_expire_time[i]
            except:
                logging.critical('Lock API broken')
            try:
                locks[i].release()
            except:
                pass


api = SysAPI()

config = SimpleNamespace(
    api_file_management_allowed=False,
    api_setup_mode=None,
    api_rpvt_allowed=False)
