__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.1.2"

import threading
import cherrypy
import logging
import threading
import time
import os
import sys
import shlex

import eva.core
import eva.runner
import eva.logs

from pyaltt import background_job

from functools import wraps

from eva.api import cp_forbidden_key
from eva.api import cp_api_error
from eva.api import cp_bad_request
from eva.api import cp_api_404
from eva.api import api_need_master
from eva.api import parse_api_params

from eva.api import NoAPIMethodException
from eva.api import GenericAPI

from eva.tools import format_json
from eva.tools import fname_remove_unsafe
from eva.tools import val_to_boolean

from eva.exceptions import FunctionFailed
from eva.exceptions import ResourceNotFound

from eva.tools import InvalidParameter

from eva.common import get_log_level_by_name
from eva.common import get_log_level_by_id

from pyaltt import background_worker

from types import SimpleNamespace

import eva.apikey

import eva.users

import eva.notify

locks = {}
lock_expire_time = {}


def api_need_file_management(f):

    @wraps(f)
    def do(*args, **kwargs):
        if not config.api_file_management_allowed:
            return None
        return f(*args, **kwargs)

    return do


def api_need_cmd(f):

    @wraps(f)
    def do(*args, **kwargs):
        if not eva.apikey.check(kwargs.get('k'), allow=['cmd']):
            return None
        return f(*args, **kwargs)

    return do


def api_need_sysfunc(f):

    @wraps(f)
    def do(*args, **kwargs):
        if not eva.apikey.check(kwargs.get('k'), sysfunc=True):
            return None
        return f(*args, **kwargs)

    return do


def api_need_lock(f):

    @wraps(f)
    def do(*args, **kwargs):
        if not eva.apikey.check(kwargs.get('k'), allow=['lock']):
            return None
        return f(*args, **kwargs)

    return do


class LockAPI(object):

    @api_need_lock
    def lock(self, **kwargs):
        """
        lock token request

        Lock tokens can be used similarly to file locking by the specific
        process. The difference is that SYS API tokens can be:
        
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
            t: maximum time (seconds) to get token
            e: time after which token is automatically unlocked (if absent,
                token may be unlocked only via unlock function)
        """
        l, t, e = parse_api_params('lte', 'S.n', kwargs,
                                  {'t': eva.core.timeout})
        if not l in locks:
            locks[l] = threading.Lock()
        logging.debug(
                'acquiring lock %s, timeout = %u, expires = %s' % \
                            (l, float(t), expires))
        if not locks[l].acquire(timeout=t):
            raise FunctionFailed('Unable to acquire lock')
        if result and e:
            lock_expire_time[l] = time.time() + e
        return True

    @api_need_lock
    def unlock(self, **kwargs):
        """
        release lock token

        Releases the previously obtained lock token.

        Args:
            k: .allow=lock
            .l: lock id

        apidoc_category: lock
        """
        l = parse_api_params('l', 'S')
        logging.debug('releasing lock %s' % l)
        try:
            locks[l].release()
            return True
        except:
            raise ResourceNotFound()


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
        self.timeout = timeout if timeout else eva.core.timeout
        self.xc = None
        self.status = cmd_status_created
        self.time = {'created': time.time()}

    def run(self):
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
        cmd, args, wait, timeout = parse_api_params('cawt', 'S.nn', kwargs)
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
        return _c


class LogAPI(object):

    @api_need_sysfunc
    def log_rotate(self, k=None):
        """
        rotate log file
        
        Equal to kill -HUP <controller_process_pid>.

        Args:
            k: .sysfunc=yes
        """
        try:
            eva.core.reset_log()
        except:
            eva.core.log_traceback()
            raise FunctionFailed()
        return True

    @api_need_sysfunc
    def log_debug(self, k=None, m=None):
        """
        put debug message to log file
        
        An external application can put a message in the logs on behalf of the
        controller.

        Args:
            k: .sysfunc=yes
            m: message text
        """
        if m: logging.debug(m)
        return True

    @api_need_sysfunc
    def log_info(self, k=None, m=None):
        """
        put info message to log file
        
        An external application can put a message in the logs on behalf of the
        controller.

        Args:
            k: .sysfunc=yes
            m: message text
        """
        if m: logging.info(m)
        return True

    @api_need_sysfunc
    def log_warning(self, k=None, m=None):
        """
        put warning message to log file
        
        An external application can put a message in the logs on behalf of the
        controller.

        Args:
            k: .sysfunc=yes
            m: message text
        """
        if m: logging.warning(m)
        return True

    @api_need_sysfunc
    def log_error(self, k=None, m=None):
        """
        put error message to log file
        
        An external application can put a message in the logs on behalf of the
        controller.

        Args:
            k: .sysfunc=yes
            m: message text
        """
        if m: logging.error(m)
        return True

    @api_need_sysfunc
    def log_critical(self, k=None, m=None):
        """
        put critical message to log file
        
        An external application can put a message in the logs on behalf of the
        controller.

        Args:
            k: .sysfunc=yes
            m: message text
        """
        if m: logging.critical(m)
        return True

    @api_need_sysfunc
    def log_get(self, *kwargs):
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
        l, t, n = parse_api_params('ltn', '.ii')
        return eva.logs.log_get(logLevel=log_level_by_name(l), t=t, n=n)

    def log(self, *kwargs):
        """
        put message to log file
        
        An external application can put a message in the logs on behalf of the
        controller.

        Args:
            k: .sysfunc=yes
            l: log level
            m: message text
        """
        l, m = parse_api_params(kwargs, 'lm', 'R.', {'l': 'info'})
        log_level = get_log_level_by_id(l)
        f = getattr(self, 'log_' + log_level)
        f(k=k, m=m)
        return True

class FileAPI(object):

    @staticmethod
    def _file_name_correct(fname):
        if fname is None or \
                fname[0] == '/' or \
                fname.find('..') != -1:
            return False
        return True

    @api_need_file_management
    @api_need_master
    def file_unlink(self, k, fname=None):
        if not self._file_name_correct(fname): return None
        try:
            if not eva.core.prepare_save(): return False
            if not os.path.isfile(eva.core.dir_runtime + '/' + fname):
                return None
            os.unlink(eva.core.dir_runtime + '/' + fname)
            if not eva.core.finish_save(): return False
            return True
        except:
            eva.core.log_traceback()
            return False

    @api_need_file_management
    @api_need_master
    def file_get(self, k, fname=None):
        if not self._file_name_correct(fname): return None, 0
        try:
            if not os.path.isfile(eva.core.dir_runtime + '/' + fname):
                return None, 0
            fname = eva.core.dir_runtime + '/' + fname
            data = ''.join(open(fname).readlines())
            return data, os.access(fname, os.X_OK)
        except:
            eva.core.log_traceback()
            return False, 0

    @api_need_file_management
    @api_need_master
    def file_put(self, k, fname=None, data=None):
        if not self._file_name_correct(fname): return None
        try:
            if not data: raw = ''
            else: raw = data
            if not eva.core.prepare_save(): return False
            open(eva.core.dir_runtime + '/' + fname, 'w').write(raw)
            if not eva.core.finish_save(): return False
            return True
        except:
            eva.core.log_traceback()
            return False

    @api_need_file_management
    @api_need_master
    def file_set_exec(self, k, fname=None, e=False):
        if not self._file_name_correct(fname): return None
        try:
            if val_to_boolean(e): perm = 0o755
            else: perm = 0o644
            if not eva.core.prepare_save(): return False
            if not os.path.isfile(eva.core.dir_runtime + '/' + fname):
                return None
            os.chmod(eva.core.dir_runtime + '/' + fname, perm)
            if not eva.core.finish_save(): return False
            return True
        except:
            eva.core.log_traceback()
            return False


class UserAPI(object):

    @api_need_master
    def create_user(self, k, user=None, password=None, key=None):
        return eva.users.create_user(user, password, key)

    @api_need_master
    def set_user_password(self, k, user=None, password=None):
        return eva.users.set_user_password(user, password)

    @api_need_master
    def set_user_key(self, k, user=None, key=None):
        return eva.users.set_user_key(user, key)

    @api_need_master
    def destroy_user(self, k, user=None):
        return eva.users.destroy_user(user)

    @api_need_master
    def list_keys(self, k):
        result = []
        for _k in eva.apikey.keys:
            r = eva.apikey.serialized_acl(_k)
            r['dynamic'] = eva.apikey.keys[_k].dynamic
            result.append(r)
        return sorted(
            sorted(result, key=lambda k: k['key_id']),
            key=lambda k: k['master'],
            reverse=True)

    @api_need_master
    def list_users(self, k):
        return eva.users.list_users()

    @api_need_master
    def get_user(self, k, u):
        return eva.users.get_user(u)

    @api_need_master
    def create_key(self, k, i=None, save=False):
        return eva.apikey.add_api_key(i, save)

    @api_need_master
    def list_key_props(self, k=None, i=None):
        key = eva.apikey.keys_by_id.get(i)
        return None if not key or not key.dynamic else key.serialize()

    @api_need_master
    def set_key_prop(self, k=None, i=None, prop=None, value=None, save=False):
        key = eva.apikey.keys_by_id.get(i)
        return None if not key else key.set_prop(prop, value, save)

    @api_need_master
    def regenerate_key(self, key=None, i=None, save=False):
        return eva.apikey.regenerate_key(i, save)

    @api_need_master
    def destroy_key(self, k=None, i=None):
        return eva.apikey.delete_api_key(i)


class SysAPI(LockAPI, CMDAPI, LogAPI, FileAPI, UserAPI, GenericAPI):

    @api_need_sysfunc
    def save(self, k=None):
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
        return eva.core.do_save()

    @api_need_master
    def dump(self, k=None):
        return eva.core.create_dump()

    @api_need_master
    def get_cvar(self, k=None, var=None):
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
        if var:
            return eva.core.get_cvar(var)
        else:
            return eva.core.cvars.copy()

    @api_need_master
    def set_cvar(self, k=None, var=None, val=None):
        """
        set the value of user-defined variable

        Args:
            k: .master
            .i: variable name
            v: variable value
        """
        return eva.core.set_cvar(var, val)

    @api_need_master
    def list_notifiers(self, k=None):
        """
        list notifiers

        Args:
            k: .master
        """
        result = []
        for n in eva.notify.get_notifiers():
            result.append(n.serialize())
        return sorted(result, key=lambda k: k['id'])

    @api_need_master
    def get_notifier(self, k=None, i=None):
        try:
            return eva.notify.get_notifier(i).serialize()
        except:
            raise ResourceNotFound()

    @api_need_master
    def enable_notifier(self, k=None, i=None):
        n = eva.notify.get_notifier(i)
        if not n: return None
        n.enabled = True
        return True

    @api_need_master
    def disable_notifier(self, k=None, i=None):
        n = eva.notify.get_notifier(i)
        if not n: return None
        n.enabled = False
        return True

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

    @api_need_master
    def setup_mode(self, k=None, setup=False):
        if not config.api_setup_mode_allowed:
            return False
        if val_to_boolean(setup):
            eva.core.setup_on()
        else:
            eva.core.setup_off()
        return True

    @api_need_master
    def shutdown_core(self, k=None):
        background_job(eva.core.sighandler_term)()
        return True


class SysHTTP_API_abstract(SysAPI):

    def dump(self, k=None):
        fname = super().dump(k=k)
        return http_api_result_ok( {'file': fname } ) if fname \
                else False

    def get_cvar(self, k=None, i=None):
        result = super().get_cvar(k=k, i=i)
        return {i: result} if i else result

    @cp_need_sysfunc

    @cp_need_sysfunc
    def log_debug(self, k=None, m=None):
        super().log_debug(k=k, m=m)
        return http_api_result_ok()

    @cp_need_sysfunc
    def log_info(self, k=None, m=None):
        super().log_info(k=k, m=m)
        return http_api_result_ok()

    @cp_need_sysfunc
    def log_warning(self, k=None, m=None):
        super().log_warning(k=k, m=m)
        return http_api_result_ok()

    @cp_need_sysfunc
    def log_error(self, k=None, m=None):
        super().log_error(k=k, m=m)
        return http_api_result_ok()

    @cp_need_sysfunc
    def log_critical(self, k=None, m=None):
        super().log_critical(k=k, m=m)
        return http_api_result_ok()

    @cp_need_master
    def set_debug(self, k=None, debug=None):
        val = val_to_boolean(debug)
        if val is None: raise cp_bad_request('Invalid value of "debug"')
        return http_api_result_ok() if super().set_debug(k=k, debug=val) \
                else http_api_result_error()

    @cp_need_master
    def shutdown_core(self, k):
        """
        shutdown the controller

        Controller process will be exited and then (should be) restarted by
        watchdog. This allows to restart controller remotely.

        Args:
            k: .master
        """
        return http_api_result_ok() if super().shutdown_core(k) \
                else http_api_result_error()

    @cp_need_master
    def setup_mode(self, k=None, setup=None):
        val = val_to_boolean(setup)
        if val is None: raise cp_bad_request('Invalid value of "setup"')
        return http_api_result_ok() if super().setup_mode(k, val) \
                else http_api_result_error()

    @cp_need_master
    def enable_notifier(self, k=None, i=None):
        """
        enable notifier

        .. note::

            The notifier is enabled until controller restart. To enable
            notifier permanently, use notifier management CLI.

        Args:
            k: .master
            .i: notifier ID
        """
        result = super().enable_notifier(k, i)
        if not result: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @cp_need_master
    def disable_notifier(self, k=None, i=None):
        """
        disable notifier

        .. note::

            The notifier is disabled until controller restart. To disable
            notifier permanently, use notifier management CLI.

        Args:
            k: .master
            .i: notifier ID
        """
        result = super().disable_notifier(k, i)
        if not result: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @cp_need_master
    def get_notifier(self, k=None, i=None):
        """
        get notifier configuration

        Args:
            k: .master
            .i: notifier ID
        """
        result = super().get_notifier(k=k, i=i)
        if result is None: raise cp_api_404()
        return result

    @cp_need_file_management
    @cp_need_master
    def file_unlink(self, k=None, i=None):
        """
        delete file from runtime folder

        Args:
            k: .master
            .i: relative path (without first slash)
        """
        result = super().file_unlink(k, i)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @cp_need_file_management
    @cp_need_master
    def file_get(self, k=None, i=None):
        """
        get file contents from runtime folder

        Args:
            k: .master
            .i: relative path (without first slash)
        """
        d = super().file_get(k, i)
        if d is None: raise cp_api_404()
        return http_api_result_ok({'file': i, 'data': d[0], 'e': d[1]})

    @cp_need_file_management
    @cp_need_master
    def file_put(self, k=None, i=None, m=None):
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
        return http_api_result_ok() if super().file_put(k, i, m) \
                else http_api_result_error()

    @cp_need_file_management
    @cp_need_master
    def file_set_exec(self, k=None, i=None, e=None):
        """
        set file exec permission

        Args:
            k: .master
            .i: relative path (without first slash)
            e: *false* for 0x644, *true* for 0x755 (executable)
        """
        try:
            _e = val_to_boolean(e)
        except:
            raise cp_bad_request('Invalid value of "e"')
        result = super().file_set_exec(k, i, _e)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @cp_need_master
    def create_user(self, k=None, u=None, p=None, a=None):
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
        return http_api_result_ok() if super().create_user(k, u, p, a) \
                else http_api_result_error()

    @cp_need_master
    def set_user_password(self, k=None, u=None, p=None):
        """
        set user password

        Args:
            k: .master
            .u: user login
            p: new password
        """
        result = super().set_user_password(k, u, p)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @cp_need_master
    def set_user_key(self, k=None, u=None, a=None):
        """
        assign API key to user

        Args:
            k: .master
            .u: user login
            a: API key to assign (key id, not a key itself)
        """
        result = super().set_user_key(k, u, a)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @cp_need_master
    def destroy_user(self, k=None, u=None):
        """
        delete user account

        Args:
            k: .master
            .u: user login
        """
        result = super().destroy_user(k, u)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @cp_need_master
    def list_keys(self, k=None):
        """
        list API keys

        Args:
            k: .master
        """
        return super().list_keys(k)

    @cp_need_master
    def list_users(self, k=None):
        """
        list user accounts

        Args:
            k: .master
        """
        return super().list_users(k)

    @cp_need_master
    def get_user(self, k=None, u=None):
        """
        get user account info

        Args:
            k: .master
            .u: user login
        """
        result = super().get_user(k=k, u=u)
        if result is None: raise cp_api_404()
        return result

    @cp_need_master
    def create_key(self, k=None, i=None, save=None):
        """
        create API key

        API keys are defined statically in etc/<controller>_apikeys.ini file as
        well as can be created with API and stored in user database.

        Keys with master permission can not be created.

        Args:
            k: .master
            .i: API key ID
            save: save configuration immediately
        """
        result = super().create_key(k, i, save)
        return result if result else http_api_result_error()

    @cp_need_master
    def list_key_props(self, k=None, i=None):
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
        result = super().list_key_props(k, i)
        if result is None: raise cp_api_404()
        return result if result else http_api_result_error()

    @cp_need_master
    def set_key_prop(self, k=None, i=None, p=None, v=None, save=None):
        """
        set API key permissions

        Args:
            k: .master
            .i: API key ID
            p: property
            v: value (if none, permission will be revoked)
            save: save configuration immediately
        """
        result = super().set_key_prop(k, i, p, v, save)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @cp_need_master
    def destroy_key(self, k=None, i=None):
        """
        delete API key

        Args:
            k: .master
            .i: API key ID
        """
        result = super().destroy_key(k, i)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @cp_need_master
    def regenerate_key(self, k=None, i=None, save=None):
        """
        regenerate API key

        Args:
            k: .master
            .i: API key ID

        Returns:
            JSON dict with new key value in "key" field
        """
        result = super().regenerate_key(k, i, save)
        if result is None: raise cp_api_404()
        return http_api_result_ok({'key':result}) if \
                result else http_api_result_error()


class SysHTTP_API(SysHTTP_API_abstract, eva.api.GenericHTTP_API):

    def __init__(self):
        super().__init__()
        self.expose_api_methods('sysapi')


class SysHTTP_API_REST_abstract:

    def GET(self, rtp, k, ii, full, kind, save, for_dir, props):
        if rtp == 'core':
            return self.test(k=k)
        elif rtp == 'cvar':
            return self.get_cvar(k=k, i=ii)
        elif rtp == 'key':
            if ii:
                return self.list_key_props(k=k, i=ii)
            else:
                return self.list_keys(k=k)
        elif rtp == 'log':
            return self.log_get(
                k=k,
                l=log_levels_by_name.get(ii.lower()
                                         if ii is not None else None, ''),
                t=props.get('t'),
                n=props.get('n'))
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
        raise NoAPIMethodException

    def POST(self, rtp, k, ii, full, kind, save, for_dir, props):
        if rtp == 'core':
            cmd = props.get('cmd')
            if cmd == 'dump':
                return self.dump(k=k)
            elif cmd == 'save':
                return self.save(k=k)
            elif cmd == 'log_rotate':
                return self.log_rotate(k=k)
            elif cmd == 'shutdown':
                return self.shutdown_core(k=k)
        elif rtp == 'log':
            return self.log(k=k, l=ii, m=props.get('m'))
        elif rtp == 'cmd':
            if not ii: raise cp_api_404()
            return self.cmd(
                k=k, c=ii, a=props.get('a'), w=props.get('w'), t=props.get('t'))
        raise NoAPIMethodException

    def PUT(self, rtp, k, ii, full, kind, save, for_dir, props):
        if rtp == 'cvar':
            return self.set_cvar(k=k, i=ii, v=props.get('v'))
        elif rtp == 'key':
            if not SysAPI.create_key(self, k=k, i=ii, save=save):
                return http_api_result_error()
            for i, v in props.items():
                if not SysAPI.set_key_prop(
                        self, k=k, i=ii, prop=i, value=v, save=save):
                    return http_api_result_error()
            return http_api_result_ok()
        elif rtp == 'lock':
            return self.lock(k=k, l=ii, t=props.get('t'), e=props.get('e'))
        elif rtp == 'runtime':
            if not config.api_file_management_allowed:
                raise cp_forbidden_key('File management is disabled')
            if not SysAPI.file_put(self, k=k, fname=ii, data=props.get('m')):
                return http_api_result_error()
            if 'e' in props:
                return self.file_set_exec(k=k, i=ii, e=props['e'])
            return http_api_result_ok()
        elif rtp == 'user':
            return self.create_user(
                k=k, u=ii, p=props.get('p'), a=props.get('a'))
        raise NoAPIMethodException

    def PATCH(self, rtp, k, ii, full, kind, save, for_dir, props):
        if rtp == 'cvar':
            return self.set_cvar(k=k, i=ii, v=props.get('v'))
        elif rtp == 'core':
            success = False
            if 'debug' in props:
                if self.set_debug(
                        k=k, debug=props['debug']).get('result') != 'OK':
                    return http_api_result_error()
                success = True
            if 'setup' in props:
                if self.setup_mode(
                        k=k, setup=props['setup']).get('result') != 'OK':
                    return http_api_result_error()
                success = True
            if success: return http_api_result_ok()
            else: raise cp_api_404()
        elif rtp == 'key':
            for i, v in props.items():
                if not SysAPI.set_key_prop(
                        self, k=k, i=ii, prop=i, value=v, save=save):
                    return http_api_result_error()
            return http_api_result_ok()
        elif rtp == 'notifier':
            if not 'enabled' in props:
                return http_api_result_error()
            return self.enable_notifier(
                k=k, i=ii) if val_to_boolean(
                    props.get('enabled')) else self.disable_notifier(
                        k=k, i=ii)
        elif rtp == 'runtime':
            if not config.api_file_management_allowed:
                raise cp_forbidden_key('File management is disabled')
            if 'm' in props:
                if not SysAPI.file_put(self, k=k, fname=ii, data=props['m']):
                    return http_api_result_error()
            if 'e' in props:
                return self.file_set_exec(k=k, i=ii, e=props['e'])
            return http_api_result_ok()
        elif rtp == 'user':
            if 'p' in props:
                if not SysAPI.set_user_password(
                        self, k=k, user=ii, password=props['p']):
                    return http_api_result_error()
            if 'a' in props:
                if not SysAPI.set_user_key(self, k=k, user=ii, key=props['a']):
                    return http_api_result_error()
            return http_api_result_ok()
        raise NoAPIMethodException

    def DELETE(self, rtp, k, ii, full, kind, save, for_dir, props):
        if rtp == 'key':
            return self.destroy_key(k=k, i=ii)
        elif rtp == 'lock':
            return self.unlock(k=k, l=ii)
        elif rtp == 'runtime':
            return self.file_unlink(k=k, i=ii)
        elif rtp == 'user':
            return self.destroy_user(k=k, u=ii)
        raise NoAPIMethodException


def update_config(cfg):
    try:
        config.api_file_management_allowed = (cfg.get(
            'sysapi', 'file_management') == 'yes')
    except:
        pass
    logging.debug('sysapi.file_management = %s' % ('yes' \
            if config.api_file_management_allowed else 'no'))
    try:
        config.api_setup_mode_allowed = (cfg.get('sysapi',
                                                 'setup_mode') == 'yes')
    except:
        pass
    logging.debug('sysapi.setup_mode = %s' % ('yes' \
            if config.api_setup_mode_allowed else 'no'))
    return True


def start():
    http_api = SysHTTP_API()
    cherrypy.tree.mount(http_api, http_api.api_uri)
    lock_processor.start(_interval=eva.core.polldelay)


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
    api_file_management_allowed=False, api_setup_mode_allowed=False)

