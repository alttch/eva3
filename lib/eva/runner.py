__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.2"

import subprocess
import threading
import psutil
import logging
import time
import os
import traceback
import uuid

import eva.core
import eva.uc.driverapi

import concurrent.futures

default_tki_diff = 2


class GenericRunner(object):

    def __init__(self, timeout=None, tki=None):
        self.xc = None
        self.term = None
        self.out = None
        self.err = None
        self.exitcode = -15
        if tki:
            self.term_kill_interval = tki
        else:
            self.term_kill_interval = eva.core.config.timeout - default_tki_diff
        if self.term_kill_interval < 0:
            self.term_kill_interval = 0
        if timeout:
            self.timeout = timeout
        else:
            self.timeout = eva.core.config.timeout

    def get_cvars(self, item=None):
        cvars = eva.core.cvars.copy()
        result = {}
        for c in cvars.keys():
            if c.find('/') == -1:
                result[c] = cvars[c]
            elif item and item.group == '/'.join(c.split('/')[:-1]):
                result[c.split('/')[-1]] = cvars[c]
        return result

    def is_finished(self):
        return True

    def run(self):
        pass

    def terminate(self):
        pass


class DriverCommand(GenericRunner):

    def __init__(self,
                 item,
                 env=None,
                 update=False,
                 state=None,
                 timeout=None,
                 tki=None,
                 _uuid=None,
                 state_in=None):
        super().__init__(timeout=timeout, tki=tki)
        if env:
            cfg = env.copy()
        else:
            cfg = {}
        cfg.update(self.get_cvars(item))
        cfg.update(item.item_env(full=False))
        if update:
            if item.update_driver_config:
                cfg.update(item.update_driver_config)
        else:
            if item.action_driver_config:
                cfg.update(item.action_driver_config)
        self.result = None
        if env:
            cfg.update(env)
        self.finished = False
        if _uuid:
            self._uuid = _uuid
        else:
            self._uuid = str(uuid.uuid4())
        if update:
            self.driver_id = item.update_exec[1:]
        else:
            self.driver_id = item.action_exec[1:]
        self.driver = eva.uc.driverapi.get_driver(self.driver_id)
        self.update = update
        self.state = state
        self.state_in = state_in
        self.cfg = cfg

    def is_finished(self):
        return self.finished

    def run(self):
        if self.driver:
            if self.update:
                self.run_future = eva.core.spawn(self.driver.state, self._uuid,
                                                 self.cfg, self.timeout,
                                                 self.term_kill_interval,
                                                 self.state_in)
            else:
                self.run_future = eva.core.spawn(self.driver.action, self._uuid,
                                                 self.state[0], self.state[1],
                                                 self.cfg, self.timeout,
                                                 self.term_kill_interval)
            try:
                self.run_future.result(timeout=self.timeout)
            except concurrent.futures.TimeoutError:
                cmd = 'state' if self.update else 'action'
                logging.warning('driver ' + \
                    '%s %s command timeout, sending termination signal'
                    % (self.driver.driver_id, cmd))
                self.driver.terminate(self._uuid)
                try:
                    self.run_future.result(timeout=self.term_kill_interval)
                except concurrent.futures.TimeoutError:
                    logging.critical('driver %s %s command timeout (%s)' %
                                     (self.driver.driver_id, cmd, self.timeout))
                    eva.core.critical(from_driver=True)
                    self.run_future.result()
            except:
                eva.core.log_traceback()
        else:
            logging.error('driver %s not found' % self.driver_id)
        self.finish()

    def terminate(self):
        self.driver.terminate(self._uuid)

    def finish(self):
        self.finished = True
        if self.driver:
            result = self.driver.get_result(self._uuid)
            self.driver.clear_result(self._uuid)
            if self.update:
                if result is None:
                    self.exitcode = 1
                else:
                    self.out = result
                    self.exitcode = 0
            else:
                if result:
                    self.out = result.get('out')
                    self.err = result.get('err')
                    exitcode = result.get('exitcode')
                    if exitcode is None:
                        self.exitcode = -1
                    else:
                        self.exitcode = exitcode
                else:
                    self.exitcode = -3
                    self.out = ''
                    self.err = 'no result'
        else:
            self.exitcode = -2
            self.out = ''
            self.err = 'driver not found'


class ExternalProcess(GenericRunner):

    def __init__(self,
                 fname,
                 item=None,
                 env=None,
                 update=False,
                 args=None,
                 timeout=None,
                 tki=None):
        super().__init__(timeout=timeout, tki=tki)
        if item:
            self.xc_fname = eva.core.format_xc_fname(item=item,
                                                     xc_type='',
                                                     update=update,
                                                     fname=fname)
            self.args = ()
            self.env = item.item_env()
            self.args += (item.item_id,)
            if update:
                self.args += ('update',)
        else:
            self.env = {}
            self.xc_fname = fname
            self.args = ()
        if args:
            self.args += args
        if env:
            self.env.update(env)
        self.env.update(eva.core.env)
        self.env.update(self.get_cvars(item))
        self.termflag = threading.Event()
        self.finished = threading.Event()

    def is_finished(self):
        return self.finished.is_set()

    def xc_finished(self):
        return self.xc.poll() is not None

    def wait(self, timeout=None):
        if timeout:
            t = timeout
        else:
            t = eva.core.config.timeout
        return self.finished.wait(t)

    def run(self, input_data=None):
        if self.launch(input_data=input_data):
            eva.core.wait_for(self.xc_finished, self.timeout)
            self.finish()

    def write_input(self, pipe, data, close=True):
        try:
            pipe.write(data if isinstance(data, bytes) else str(data).encode())
            pipe.flush()
            if close:
                pipe.close()
        except:
            logging.error(f'external process data input error {self.xc_name}')
            eva.core.log_traceback()

    def launch(self, input_data=None):
        try:
            self.term = eva.core.spawn(self._t_term)
            self.xc = subprocess.Popen(
                args=(self.xc_fname,) + self.args,
                env=self.env,
                stdin=subprocess.PIPE if input_data else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            if input_data:
                eva.core.spawn(self.write_input, self.xc.stdin, input_data)
            return True
        except:
            self.terminate()
            logging.error('external process error %s' % self.xc_fname)
            eva.core.log_traceback()
            self.finished.set()
            return False

    def finish(self):
        self.terminate()
        try:
            self.out = self.xc.stdout.read().decode()
        except:
            self.out = None
            eva.core.log_traceback()
        try:
            self.err = self.xc.stderr.read().decode()
        except:
            self.err = None
            eva.core.log_traceback()
        self.exitcode = self.xc.returncode
        if self.exitcode is None:
            self.exitcode = -15
        self.finished.set()

    def terminate(self):
        self.termflag.set()

    def _t_term(self):
        self.termflag.wait()
        self.termflag.clear()
        if self.xc.poll() is not None:
            return
        try:
            pp = psutil.Process(self.xc.pid)
        except:
            return
        childs = []
        try:
            for child in pp.children(recursive=True):
                childs.append(child)
        except:
            pass
        try:
            self.xc.terminate()
        except:
            pass
        for child in childs:
            try:
                child.terminate()
            except:
                pass
        eva.core.wait_for(self.xc_finished, self.term_kill_interval)
        try:
            self.xc.kill()
        except:
            pass
        for child in childs:
            try:
                child.kill()
            except:
                pass
        return


code_cache = {}
code_cache_m = {}


class PyThread(object):

    def __init__(self,
                 item=None,
                 script=None,
                 env_globals=None,
                 bcode=None,
                 mfcode=None,
                 subdir=None):
        self.pfcode = None
        if item:
            if item.action_exec:
                sfile = item.action_exec
            else:
                sfile = item.item_id + '.py'
            try:
                self.pfcode = item.pfcode
            except:
                pass
        else:
            sfile = script
        self.script = sfile
        self.script_file = eva.core.format_xc_fname(fname=sfile, subdir=subdir)
        self.common_file = eva.core.format_xc_fname(fname='common.py',
                                                    subdir=subdir)
        self.env_globals = env_globals
        self.code = None
        self.out = None
        self.err = None
        self.bcode = bcode if bcode else ''
        self.mfcode = mfcode
        self.exitcode = -15
        self.compile_lock = threading.RLock()

    def compile(self):
        if not self.compile_lock.acquire(timeout=eva.core.config.timeout):
            logging.critical('PyThread::compile locking broken')
            eva.core.critical()
            return False
        try:
            omtime = code_cache_m.get(self.script_file)
            if not self.pfcode:
                mtime = os.path.getmtime(self.script_file)
            else:
                mtime = 0
            try:
                mtime_c = os.path.getmtime(self.common_file)
            except:
                mtime_c = 0
            if mtime_c > mtime:
                mtime = mtime_c
            if self.mfcode and self.mfcode.build_time > mtime:
                mtime = self.mfcode.build_time
            if not omtime or mtime > omtime:
                if self.pfcode:
                    raw = self.pfcode
                else:
                    with open(self.script_file) as fd:
                        raw = fd.read()
                try:
                    with open(self.common_file) as fd:
                        raw_c = fd.read()
                except:
                    raw_c = ''
                self.code = compile((self.mfcode.code if self.mfcode else '') +
                                    self.bcode + raw_c + '\n' + raw,
                                    self.script, 'exec')
                code_cache[self.script_file] = self.code
                code_cache_m[self.script_file] = mtime
                logging.debug('File %s compiled successfully' % \
                        self.script_file)
            else:
                self.code = code_cache[self.script_file]
                logging.debug('File %s not modified, using cached code' % \
                        self.script_file)
            return True
        except:
            logging.error('Failed to compile file %s' % self.script_file)
            eva.core.log_traceback(force=True)
            self.err = traceback.format_exc()
            return False
        finally:
            self.compile_lock.release()

    def run(self):
        if not self.code:
            if not self.compile():
                return False
        try:
            exec(self.code, self.env_globals)
            self.exitcode = 0
            if 'out' in self.env_globals:
                self.out = self.env_globals['out']
            return True
        except SystemExit as value:
            self.exitcode = value.code
            if 'out' in self.env_globals:
                self.out = self.env_globals['out']
            return True if not value.code else False
        except:
            logging.error('Error while running "%s"' % self.script)
            if 'out' in self.env_globals:
                self.out = self.env_globals['out']
            eva.core.log_traceback(force=True)
            self.err = traceback.format_exc()
            return False
