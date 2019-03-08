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
import jsonpickle
import shlex

import eva.core
import eva.runner
import eva.logs

from eva.api import cp_json_handler
from eva.api import log_api_request
from eva.api import http_remote_info
from eva.api import cp_forbidden_key
from eva.api import cp_api_error
from eva.api import cp_api_404
from eva.api import cp_need_master
from eva.api import cp_session_pre
from eva.api import cp_json_pre
from eva.api import cp_api_pre
from eva.api import http_api_result_ok
from eva.api import http_api_result_error
from eva.api import session_timeout

from eva.api import http_real_ip
from eva.api import cp_client_key

from eva.api import GenericAPI
from eva.api import JSON_RPC_API

from eva.tools import format_json
from eva.tools import fname_remove_unsafe
from eva.tools import val_to_boolean

import eva.apikey

import eva.users

import eva.notify

locks = {}
lock_expire_time = {}

_lock_processor_active = False

_lock_processor = None

api = None

api_file_management_allowed = False
api_setup_mode_allowed = False

cvars_public = False


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

    def dev_locks(self, k=None):
        return {'locks': list(locks.keys()), 'expire': lock_expire_time}


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

    def notifiers(self, k=None):
        result = []
        for n in eva.notify.get_notifiers():
            result.append(n.serialize())
        return sorted(result, key=lambda k: k['id'])

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
        if debug:
            eva.core.debug_on()
        else:
            eva.core.debug_off()
        return True

    def setup_mode(self, k=None, setup=False):
        if not eva.apikey.check(k, master=True) or not api_setup_mode_allowed:
            return False
        if setup:
            eva.core.setup_on()
        else:
            eva.core.setup_off()
        return True


class SysHTTP_API(SysAPI, JSON_RPC_API):

    _cp_config = {
        'tools.session_pre.on': True,
        'tools.json_pre.on': True,
        'tools.log_pre.on': True,
        'tools.json_out.on': True,
        'tools.json_out.handler': cp_json_handler,
        'tools.auth_sysfunc.on': True,
        'tools.sessions.on': True,
        'tools.sessions.timeout': session_timeout,
        'tools.trailing_slash.on': False
    }

    def cp_check_perm(self, api_key=None, path_info=None):
        k = api_key if api_key else cp_client_key()
        path = path_info if path_info is not None else \
                cherrypy.serving.request.path_info
        if k is not None: cherrypy.serving.request.params['k'] = k
        if path in ['', '/']: return
        if path[:6] == '/login': return
        if path[:4] == '/dev': dev = True
        else: dev = False
        if dev and not eva.core.development: raise cp_forbidden_key()
        p = cherrypy.serving.request.params.copy()
        if not eva.core.development:
            if 'k' in p: del p['k']
            if path[:12] == '/create_user' or \
              path[:18] == '/set_user_password':
                if 'p' in p: del p['p']
        if path[:6] == '/file_' and \
                not api_file_management_allowed:
            raise cp_forbidden_key()
        if path[:9] == '/file_put' and \
                'm' in p:
            del p['m']
        log_api_request(path[1:], http_remote_info(k), p, False)
        if path[:4] == '/cmd':
            allow = ['cmd']
            sysfunc = False
        else:
            allow = []
            sysfunc = True
        if not eva.apikey.check(
                k, allow=allow, ip=http_real_ip(), sysfunc=sysfunc, master=dev):
            raise cp_forbidden_key()
        return

    def __init__(self):
        cherrypy.tools.session_pre = cherrypy.Tool(
            'on_start_resource', cp_session_pre, priority=1)
        cherrypy.tools.json_pre = cherrypy.Tool(
            'before_handler', cp_json_pre, priority=10)
        cherrypy.tools.log_pre = cherrypy.Tool(
            'before_handler', cp_api_pre, priority=20)
        cherrypy.tools.auth_sysfunc = cherrypy.Tool(
            'before_handler', self.cp_check_perm, priority=60)
        super().__init__()
        SysHTTP_API.lock.exposed = True
        SysHTTP_API.unlock.exposed = True
        SysHTTP_API.cmd.exposed = True
        SysHTTP_API.save.exposed = True
        SysHTTP_API.dump.exposed = True
        SysHTTP_API.get_cvar.exposed = True
        SysHTTP_API.set_cvar.exposed = True
        SysHTTP_API.notifiers.exposed = True
        SysHTTP_API.log_rotate.exposed = True
        SysHTTP_API.set_debug.exposed = True
        SysHTTP_API.setup_mode.exposed = True

        if eva.core.development:
            GenericAPI.dev_env.exposed = True
            GenericAPI.dev_cvars.exposed = True
            GenericAPI.dev_k.exposed = True
            GenericAPI.dev_n.exposed = True
            GenericAPI.dev_t.exposed = True
            GenericAPI.dev_test_critical.exposed = True
            LockAPI.dev_locks.exposed = True

        GenericAPI.test.exposed = True
        SysHTTP_API.index.exposed = True

        SysHTTP_API.log_debug.exposed = True
        SysHTTP_API.log_info.exposed = True
        SysHTTP_API.log_warning.exposed = True
        SysHTTP_API.log_error.exposed = True
        SysHTTP_API.log_critical.exposed = True
        SysHTTP_API.log_get.exposed = True

        SysHTTP_API.file_unlink.exposed = True
        SysHTTP_API.file_get.exposed = True
        SysHTTP_API.file_put.exposed = True
        SysHTTP_API.file_set_exec.exposed = True

        SysHTTP_API.create_user.exposed = True
        SysHTTP_API.set_user_password.exposed = True
        SysHTTP_API.set_user_key.exposed = True
        SysHTTP_API.destroy_user.exposed = True

        SysHTTP_API.list_keys.exposed = True
        SysHTTP_API.list_users.exposed = True

        SysHTTP_API.enable_notifier.exposed = True
        SysHTTP_API.disable_notifier.exposed = True

        SysHTTP_API.create_key.exposed = True
        SysHTTP_API.list_key_props.exposed = True
        SysHTTP_API.set_key_prop.exposed = True
        SysHTTP_API.regenerate_key.exposed = True
        SysHTTP_API.destroy_key.exposed = True

    def lock(self, k=None, l=None, t=None, e=None):
        if not l:
            raise cp_api_error('No lock provided')
        result = super().lock(k, l, t, e)
        if result is None: raise cp_forbidden_key()
        return http_api_result_ok() \
                if result else http_api_result_error()

    def unlock(self, k=None, l=None):
        if not l:
            raise cp_api_error('No lock provided')
        if not l in locks:
            raise cp_api_404('Lock not found')
        result = super().unlock(k, l)
        if result is None: raise cp_forbidden_key()
        return http_api_result_ok() if result else \
                http_api_result_ok({ 'remark': 'notlocked' })

    def cmd(self, k, c, a=None, w=None, t=None):
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

    def save(self, k=None):
        return http_api_result_ok() \
                if super().save(k) else http_api_result_error()

    def dump(self, k=None):
        cp_need_master(k)
        fname = super().dump(k)
        return http_api_result_ok( {'file': fname } ) if fname \
                else http_api_result_error()

    def set_cvar(self, k=None, i=None, v=None):
        cp_need_master(k)
        result = super().set_cvar(k, i, v)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    def get_cvar(self, k=None, i=None):
        result = super().get_cvar(k, i)
        if result is False: raise cp_forbidden_key()
        if result is None: raise cp_api_404()
        return {i: result} if i is not None else result

    def notifiers(self, k=None):
        cp_need_master(k)
        return super().notifiers(k)

    def log_rotate(self, k=None):
        return http_api_result_ok() if super().log_rotate(k) \
                else http_api_result_error()

    def log_debug(self, k=None, m=None):
        super().log_debug(k, m)
        return http_api_result_ok()

    def log_info(self, k=None, m=None):
        super().log_info(k, m)
        return http_api_result_ok()

    def log_warning(self, k=None, m=None):
        super().log_warning(k, m)
        return http_api_result_ok()

    def log_error(self, k=None, m=None):
        super().log_error(k, m)
        return http_api_result_ok()

    def log_critical(self, k=None, m=None):
        super().log_critical(k, m)
        return http_api_result_ok()

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

    def set_debug(self, k=None, debug=None):
        cp_need_master(k)
        val = val_to_boolean(debug)
        if val is None: raise cp_api_error()
        return http_api_result_ok() if super().set_debug(k, val) \
                else http_api_result_error()

    def setup_mode(self, k=None, setup=None):
        cp_need_master(k)
        val = val_to_boolean(setup)
        if val is None: raise cp_api_error()
        return http_api_result_ok() if super().setup_mode(k, val) \
                else http_api_result_error()

    def enable_notifier(self, k=None, i=None):
        cp_need_master(k)
        return http_api_result_ok() if super().enable_notifier(k, i) \
                else http_api_result_error()

    def disable_notifier(self, k=None, i=None):
        cp_need_master(k)
        return http_api_result_ok() if super().disable_notifier(k, i) \
                else http_api_result_error()

    def file_unlink(self, k=None, i=None):
        cp_need_master(k)
        result = super().file_unlink(k, i)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    def file_get(self, k=None, i=None):
        cp_need_master(k)
        data = super().file_get(k, i)
        if not data: raise cp_api_404()
        return http_api_result_ok({'file': i, 'data': data})

    def file_put(self, k=None, i=None, m=None):
        cp_need_master(k)
        return http_api_result_ok() if super().file_put(k, i, m) \
                else http_api_result_error()

    def file_set_exec(self, k=None, i=None, e=None):
        cp_need_master(k)
        try:
            _e = val_to_boolean(e)
        except:
            raise cp_api_error()
        result = super().file_set_exec(k, i, _e)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    def create_user(self, k=None, u=None, p=None, a=None):
        cp_need_master(k)
        return http_api_result_ok() if super().create_user(k, u, p, a) \
                else http_api_result_error()

    def set_user_password(self, k=None, u=None, p=None):
        cp_need_master(k)
        result = super().set_user_password(k, u, p)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    def set_user_key(self, k=None, u=None, a=None):
        cp_need_master(k)
        result = super().set_user_key(k, u, a)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    def destroy_user(self, k=None, u=None, p=None):
        cp_need_master(k)
        result = super().destroy_user(k, u)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    def list_keys(self, k=None):
        cp_need_master(k)
        return super().list_keys(k)

    def list_users(self, k=None):
        cp_need_master(k)
        return super().list_users(k)

    def create_key(self, k=None, i=None, save=None):
        cp_need_master(k)
        result = super().create_key(k, i, save)
        return result if result else http_api_result_error()

    def list_key_props(self, k=None, i=None):
        cp_need_master(k)
        result = super().list_key_props(k, i)
        if result is None: raise cp_api_404()
        return result if result else http_api_result_error()

    def set_key_prop(self, k=None, i=None, p=None, v=None, save=None):
        cp_need_master(k)
        result = super().set_key_prop(k, i, p, v, save)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    def destroy_key(self, k=None, i=None):
        cp_need_master(k)
        result = super().destroy_key(k, i)
        if result is None: raise cp_api_404()
        return http_api_result_ok() if result else http_api_result_error()

    def regenerate_key(self, k=None, i=None, save=None):
        cp_need_master(k)
        result = super().regenerate_key(k, i, save)
        if result is None: raise cp_api_404()
        return http_api_result_ok({'key':result}) if \
                result else http_api_result_error()


def update_config(cfg):
    global api_file_management_allowed, api_setup_mode_allowed
    try:
        api_file_management_allowed = (cfg.get('sysapi',
                                               'file_management') == 'yes')
    except:
        pass
    logging.debug('sysapi.file_management = %s' % ('yes' \
            if api_file_management_allowed else 'no'))
    try:
        api_setup_mode_allowed = (cfg.get('sysapi', 'setup_mode') == 'yes')
    except:
        pass
    logging.debug('sysapi.setup_mode = %s' % ('yes' \
            if api_setup_mode_allowed else 'no'))
    return True


def start():
    global _lock_processor
    global _lock_processor_active
    global api
    api = SysAPI()
    cherrypy.tree.mount(SysHTTP_API(), '/sys-api')
    _lock_processor = threading.Thread(
        target=_t_lock_processor, name='_t_lock_processor')
    _lock_processor_active = True
    _lock_processor.start()


@eva.core.stop
def stop():
    global _lock_processor_active
    if _lock_processor_active:
        _lock_processor_active = False
        _lock_processor.join()


def _t_lock_processor():
    logging.debug('LockAPI processor started')
    while _lock_processor_active:
        time.sleep(eva.core.polldelay)
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
    logging.debug('LockAPI processor stopped')
