_author__ = "Altertech Group, https://www.altertech.com/"
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
from eva.api import cp_api_404
from eva.api import http_api_result_ok
from eva.api import http_api_result_error

from eva.api import http_real_ip
from eva.api import cp_client_key
from eva.api import cp_need_master

from eva.api import expose_api_methods
from eva.api import NoAPIMethodException

from eva.api import GenericAPI

from eva.tools import format_json
from eva.tools import fname_remove_unsafe
from eva.tools import val_to_boolean

from eva.common import log_levels_by_name

from pyaltt import background_worker

from types import SimpleNamespace

import eva.apikey

import eva.users

import eva.notify

locks = {}
lock_expire_time = {}

cvars_public = False


def cp_need_file_management(f):

    @wraps(f)
    def do(*args, **kwargs):
        if not config.api_file_management_allowed:
            raise cp_forbidden_key()
        return f(*args, **kwargs)

    return do


def cp_need_cmd(f):

    @wraps(f)
    def do(*args, **kwargs):
        if not eva.apikey.check(kwargs.get('k'), allow=['cmd']):
            raise cp_forbidden_key()
        return f(*args, **kwargs)

    return do


def cp_need_sysfunc(f):

    @wraps(f)
    def do(*args, **kwargs):
        if not eva.apikey.check(kwargs.get('k'), sysfunc=True):
            raise cp_forbidden_key()
        return f(*args, **kwargs)

    return do


class LockAPI(object):

    def lock(self, k=None, l=None, timeout=None, expires=None):
        if not eva.apikey.check(k, allow=['lock']):
            return None
        if timeout: t = timeout
        else: t = eva.core.timeout
        if not l in locks:
            locks[l] = threading.Lock()
        logging.debug(
                'acquiring lock %s, timeout = %u, expires = %s' % \
                            (l, float(t), expires))
        result = locks[l].acquire(timeout=float(t))
        if result and expires:
            lock_expire_time[l] = time.time() + float(expires)
        return result

    def unlock(self, k=None, l=None):
        if not eva.apikey.check(k, allow=['lock']):
            return None
        logging.debug('releasing lock %s' % l)
        try:
            locks[l].release()
            return True
        except:
            return False


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

    def cmd(self, k, cmd, args=None, wait=None, timeout=None):
        if not eva.apikey.check(k, allow = [ 'cmd' ]) or \
            cmd[0] == '/' or \
            cmd.find('..') != -1:
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

    def log_rotate(self, k=None):
        try:
            eva.core.reset_log()
        except:
            eva.core.log_traceback()
            return False
        return True

    def log_debug(self, k=None, m=None):
        if m: logging.debug(m)

    def log_info(self, k=None, m=None):
        if m: logging.info(m)

    def log_warning(self, k=None, m=None):
        if m: logging.warning(m)

    def log_error(self, k=None, m=None):
        if m: logging.error(m)

    def log_critical(self, k=None, m=None):
        if m: logging.critical(m)

    def log_get(self, k=None, l=0, t=0, n=None):
        return eva.logs.log_get(logLevel=l, t=t, n=n)


class FileAPI(object):

    def file_unlink(self, k, fname=None):
        if not eva.apikey.check(k, master=True): return None
        if fname is None or \
                not eva.apikey.check(k, master = True) or \
                fname[0] == '/' or \
                fname.find('..') != -1:
            return None
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

    def file_get(self, k, fname=None):
        if not eva.apikey.check(k, master=True): return None
        if fname is None or \
                not eva.apikey.check(k, master = True) or \
                fname[0] == '/' or \
                fname.find('..') != -1:
            return None
        try:
            if not os.path.isfile(eva.core.dir_runtime + '/' + fname):
                return None
            data = ''.join(open(eva.core.dir_runtime + '/' + fname).readlines())
            return data
        except:
            eva.core.log_traceback()
            return False

    def file_put(self, k, fname=None, data=None):
        if not eva.apikey.check(k, master=True): return None
        if fname is None or \
                not eva.apikey.check(k, master = True) or \
                fname[0] == '/' or \
                fname.find('..') != -1:
            return False
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

    def file_set_exec(self, k, fname=None, e=False):
        if not eva.apikey.check(k, master=True): return None
        if fname is None or \
                not eva.apikey.check(k, master = True) or \
                fname[0] == '/' or \
                fname.find('..') != -1:
            return None
        try:
            if e: perm = 0o755
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

    def create_user(self, k, user=None, password=None, key=None):
        if not eva.apikey.check(k, master=True): return False
        return eva.users.create_user(user, password, key)

    def set_user_password(self, k, user=None, password=None):
        if not eva.apikey.check(k, master=True): return False
        return eva.users.set_user_password(user, password)

    def set_user_key(self, k, user=None, key=None):
        if not eva.apikey.check(k, master=True): return False
        return eva.users.set_user_key(user, key)

    def destroy_user(self, k, user=None):
        if not eva.apikey.check(k, master=True): return False
        return eva.users.destroy_user(user)

    def list_keys(self, k):
        if not eva.apikey.check(k, master=True): return False
        result = []
        for _k in eva.apikey.keys:
            r = eva.apikey.serialized_acl(_k)
            r['dynamic'] = eva.apikey.keys[_k].dynamic
            result.append(r)
        return sorted(
            sorted(result, key=lambda k: k['key_id']),
            key=lambda k: k['master'],
            reverse=True)

    def list_users(self, k):
        if not eva.apikey.check(k, master=True): return False
        return eva.users.list_users()

    def get_user(self, k, u):
        if not eva.apikey.check(k, master=True): return False
        return eva.users.get_user(u)

    def create_key(self, k, i=None, save=False):
        if not eva.apikey.check(k, master=True): return False
        return eva.apikey.add_api_key(i, save)

    def list_key_props(self, k=None, i=None):
        if not eva.apikey.check(k, master=True): return False
        key = eva.apikey.keys_by_id.get(i)
        return None if not key or not key.dynamic else key.serialize()

    def set_key_prop(self, k=None, i=None, prop=None, value=None, save=False):
        if not eva.apikey.check(k, master=True): return False
        key = eva.apikey.keys_by_id.get(i)
        return None if not key else key.set_prop(prop, value, save)

    def regenerate_key(self, key=None, i=None, save=False):
        if not eva.apikey.check(key, master=True): return False
        return eva.apikey.regenerate_key(i, save)

    def destroy_key(self, k=None, i=None):
        if not eva.apikey.check(k, master=True): return False
        return eva.apikey.delete_api_key(i)


class SysAPI(LockAPI, CMDAPI, LogAPI, FileAPI, UserAPI, GenericAPI):

    def save(self, k=None):
        return eva.core.do_save()

    def dump(self, k=None):
        return eva.core.create_dump()

    def get_cvar(self, k=None, var=None):
        if not eva.apikey.check(k, master=not cvars_public):
            return False
        if var:
            return eva.core.get_cvar(var)
        else:
            return eva.core.cvars.copy()

    def set_cvar(self, k=None, var=None, val=None):
        if not eva.apikey.check(k, master=True): return None
        return eva.core.set_cvar(var, val)

    def list_notifiers(self, k=None):
        result = []
        for n in eva.notify.get_notifiers():
            result.append(n.serialize())
        return sorted(result, key=lambda k: k['id'])

    def get_notifier(self, k=None, i=None):
        try:
            return eva.notify.get_notifier(i).serialize()
        except:
            return None

    def enable_notifier(self, k=None, i=None):
        n = eva.notify.get_notifier(i)
        if not n: return False
        n.enabled = True
        return True

    def disable_notifier(self, k=None, i=None):
        n = eva.notify.get_notifier(i)
        if not n: return False
        n.enabled = False
        return True

    def set_debug(self, k=None, debug=False):
        if not eva.apikey.check(k, master=True):
            return False
        if val_to_boolean(debug):
            eva.core.debug_on()
        else:
            eva.core.debug_off()
        return True

    def setup_mode(self, k=None, setup=False):
        if not eva.apikey.check(
                k, master=True) or not config.api_setup_mode_allowed:
            return False
        if val_to_boolean(setup):
            eva.core.setup_on()
        else:
            eva.core.setup_off()
        return True

    def shutdown_core(self, k=None):
        if not eva.apikey.check(k, master=True):
            return False
        background_job(eva.core.sighandler_term)()
        return True


class SysHTTP_API_abstract(SysAPI):

    @cp_need_sysfunc
    def lock(self, k=None, l=None, t=None, e=None):
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

        apidoc_category: lock
        """
        if not l:
            raise cp_api_error('No lock provided')
        result = super().lock(k, l, t, e)
        if result is None: raise cp_forbidden_key()
        return http_api_result_ok() \
                if result else http_api_result_error()

    @cp_need_sysfunc
    def unlock(self, k=None, l=None):
        """
        release lock token

        Releases the previously obtained lock token.

        Args:
            k: .allow=lock
            .l: lock id

        Returns:
            In case token is already unlocked, *remark = "notlocked"* note will
            be present in the result.
        
        apidoc_category: lock
        """
        if not l:
            raise cp_api_error('No lock provided')
        if not l in locks:
            raise cp_api_404('Lock not found')
        result = super().unlock(k, l)
        if result is None: raise cp_forbidden_key()
        return http_api_result_ok() if result else \
                http_api_result_ok({ 'remark': 'notlocked' })

    @cp_need_cmd
    def cmd(self, k, c, a=None, w=None, t=None):
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

        apidoc_category: general
        """
        if t:
            try:
                _t = float(t)
            except:
                raise cp_api_error()
        else:
            _t = None
        if w:
            try:
                _w = float(w)
            except:
                raise cp_api_error()
        else:
            _w = None
        result = super().cmd(k, cmd=c, args=a, wait=_w, timeout=_t)
        if result: return result.serialize()
        else: raise cp_api_404()

    @cp_need_sysfunc
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

        apidoc_priority: 2
        apidoc_category: general
        """
        return http_api_result_ok() \
                if super().save(k) else http_api_result_error()

    @cp_need_master
    def dump(self, k=None):
        fname = super().dump(k)
        return http_api_result_ok( {'file': fname } ) if fname \
                else http_api_result_error()

    @cp_need_master
    def set_cvar(self, k=None, i=None, v=None):
        result = super().set_cvar(k, i, v)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @cp_need_sysfunc
    def get_cvar(self, k=None, i=None):
        result = super().get_cvar(k, i)
        if result is False: raise cp_forbidden_key()
        if result is None: raise cp_api_404()
        return {i: result} if i else result

    @cp_need_master
    def list_notifiers(self, k=None):
        return super().list_notifiers(k)

    @cp_need_sysfunc
    def log_rotate(self, k=None):
        return http_api_result_ok() if super().log_rotate(k) \
                else http_api_result_error()

    @cp_need_sysfunc
    def log_debug(self, k=None, m=None):
        super().log_debug(k, m)
        return http_api_result_ok()

    @cp_need_sysfunc
    def log_info(self, k=None, m=None):
        super().log_info(k, m)
        return http_api_result_ok()

    @cp_need_sysfunc
    def log_warning(self, k=None, m=None):
        super().log_warning(k, m)
        return http_api_result_ok()

    @cp_need_sysfunc
    def log_error(self, k=None, m=None):
        super().log_error(k, m)
        return http_api_result_ok()

    @cp_need_sysfunc
    def log_critical(self, k=None, m=None):
        super().log_critical(k, m)
        return http_api_result_ok()

    @cp_need_sysfunc
    def log_get(self, k=None, l=0, t=0, n=None):
        try:
            _l = int(l)
        except:
            _l = None
        try:
            _t = int(t)
        except:
            _t = None
        try:
            _n = int(n)
        except:
            _n = None
        return super().log_get(k, _l, _t, _n)

    @cp_need_master
    def set_debug(self, k=None, debug=None):
        """
        switch debugging mode

        Enables and disables debugging mode while the controller is running.
        After the controller is restarted, this parameter is lost and
        controller switches back to the mode specified in the configuration
        file.

        Args:
            k: .master
            debug: 1 for enabling debug mode, 0 for disabling

        apidoc_category: general
        """
        val = val_to_boolean(debug)
        if val is None: raise cp_api_error()
        return http_api_result_ok() if super().set_debug(k, val) \
                else http_api_result_error()

    @cp_need_master
    def shutdown_core(self, k):
        return http_api_result_ok() if super().shutdown_core(k) \
                else http_api_result_error()

    @cp_need_master
    def setup_mode(self, k=None, setup=None):
        val = val_to_boolean(setup)
        if val is None: raise cp_api_error()
        return http_api_result_ok() if super().setup_mode(k, val) \
                else http_api_result_error()

    @cp_need_master
    def enable_notifier(self, k=None, i=None):
        return http_api_result_ok() if super().enable_notifier(k, i) \
                else http_api_result_error()

    @cp_need_master
    def disable_notifier(self, k=None, i=None):
        return http_api_result_ok() if super().disable_notifier(k, i) \
                else http_api_result_error()

    @cp_need_master
    def get_notifier(self, k=None, i=None):
        result = super().get_notifier(k=k, i=i)
        if result is None: raise cp_api_404()
        return result

    @cp_need_file_management
    @cp_need_master
    def file_unlink(self, k=None, i=None):
        result = super().file_unlink(k, i)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @cp_need_file_management
    @cp_need_master
    def file_get(self, k=None, i=None):
        data = super().file_get(k, i)
        if not data: raise cp_api_404()
        return http_api_result_ok({'file': i, 'data': data})

    @cp_need_file_management
    @cp_need_master
    def file_put(self, k=None, i=None, m=None):
        return http_api_result_ok() if super().file_put(k, i, m) \
                else http_api_result_error()

    @cp_need_file_management
    @cp_need_master
    def file_set_exec(self, k=None, i=None, e=None):
        try:
            _e = val_to_boolean(e)
        except:
            raise cp_api_error()
        result = super().file_set_exec(k, i, _e)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @cp_need_master
    def create_user(self, k=None, u=None, p=None, a=None):
        return http_api_result_ok() if super().create_user(k, u, p, a) \
                else http_api_result_error()

    @cp_need_master
    def set_user_password(self, k=None, u=None, p=None):
        result = super().set_user_password(k, u, p)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @cp_need_master
    def set_user_key(self, k=None, u=None, a=None):
        result = super().set_user_key(k, u, a)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @cp_need_master
    def destroy_user(self, k=None, u=None):
        result = super().destroy_user(k, u)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @cp_need_master
    def list_keys(self, k=None):
        return super().list_keys(k)

    @cp_need_master
    def list_users(self, k=None):
        return super().list_users(k)

    @cp_need_master
    def get_user(self, k=None, u=None):
        result = super().get_user(k=k, u=u)
        if result is None: raise cp_api_404()
        return result

    @cp_need_master
    def create_key(self, k=None, i=None, save=None):
        result = super().create_key(k, i, save)
        return result if result else http_api_result_error()

    @cp_need_master
    def list_key_props(self, k=None, i=None):
        result = super().list_key_props(k, i)
        if result is None: raise cp_api_404()
        return result if result else http_api_result_error()

    @cp_need_master
    def set_key_prop(self, k=None, i=None, p=None, v=None, save=None):
        result = super().set_key_prop(k, i, p, v, save)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @cp_need_master
    def destroy_key(self, k=None, i=None):
        result = super().destroy_key(k, i)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    @cp_need_master
    def regenerate_key(self, k=None, i=None, save=None):
        result = super().regenerate_key(k, i, save)
        if result is None: raise cp_api_404()
        return http_api_result_ok({'key':result}) if \
                result else http_api_result_error()


class SysHTTP_API(SysHTTP_API_abstract, eva.api.GenericHTTP_API):

    def __init__(self):
        super().__init__()
        self.api_uri = expose_api_methods(self.__class__, 'sysapi')


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
            if not ii: ii = 'info'
            level = ii.lower()
            f = getattr(self, 'log_' + level, None)
            if not f: raise cp_api_404()
            return f(k=k, m=props.get('m', ''))
        elif rtp == 'cmd':
            if not ii: raise cp_api_404()
            return self.cmd(
                k=k, c=ii, a=props.get('a'), w=props.get('w'), t=props.get('t'))
        raise NoAPIMethodException

    def PUT(self, rtp, k, ii, full, kind, save, for_dir, props):
        if rtp == 'cvar':
            return self.set_cvar(k=k, i=ii, v=props.get('v'))
        elif rtp == 'key':
            if not super().create_key(k=k, i=ii, save=save):
                return http_api_result_error()
            for i, v in props.items():
                if not super().set_key_prop(
                        k=k, i=ii, prop=i, value=v, save=save):
                    return http_api_result_error()
            return http_api_result_ok()
        elif rtp == 'lock':
            return self.lock(k=k, l=ii, t=props.get('t'), e=props.get('e'))
        elif rtp == 'runtime':
            if not super().file_put(k, ii, props.get('m')):
                return http_api_result_error()
            if props.get('e'):
                return self.file_set_exec(k=k, i=ii, e=1)
            return http_api_result_ok()
        elif rtp == 'user':
            return self.create_user(
                k=k, u=ii, p=props.get('p'), a=props.get('a'))
        raise NoAPIMethodException

    def PATCH(self, rtp, k, ii, full, kind, save, for_dir, props):
        if rtp == 'cvar':
            return self.set_cvar(k=k, i=ii, v=props.get('v'))
        elif rtp == 'core':
            if 'debug' in props:
                if self.set_debug(
                        k=k, debug=props['debug']).get('result') != 'OK':
                    return http_api_result_error()
            if 'setup' in props:
                if self.setup_mode(
                        k=k, setup=props['setup']).get('result') != 'OK':
                    return http_api_result_error()
            return http_api_result_ok()
        elif rtp == 'key':
            for i, v in props.items():
                if not super().set_key_prop(
                        k=k, i=ii, prop=i, value=v, save=save):
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
            if not super().file_put(k, ii, props.get('m')):
                return http_api_result_error()
            if props.get('e'):
                return self.file_set_exec(k=k, i=ii, e=1)
            return http_api_result_ok()
        elif rtp == 'user':
            if 'p' in props:
                if not super().set_user_password(
                        k=k, user=ii, password=props['p']):
                    return http_api_result_error()
            if 'a' in props:
                if not super().set_user_key(k=k, user=ii, key=props['a']):
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
