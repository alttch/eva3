__author__ = "Altertech Group, http://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "See http://www.eva-ics.com/"
__version__ = "3.0.2"

import subprocess
import eva.core
import threading
import psutil
import logging
import time
import os
import traceback

default_tki_diff = 2


class ExternalProcess(object):

    def __init__(self,
                 fname,
                 item=None,
                 env=None,
                 update=False,
                 args=None,
                 timeout=None,
                 tki=None):
        if item:
            if item.virtual:
                self.xc_fname = eva.core.dir_xc + '/evirtual'
                self.args = (item.item_type,)
            else:
                self.xc_fname = eva.core.format_xc_fname(
                    item=item, xc_type='', update=update, fname=fname)
                self.args = ()
            self.env = item.item_env()
            self.args += (item.item_id,)
            if update:
                self.args += ('update',)
        else:
            self.env = {}
            self.xc_fname = fname
            self.args = ()
        if args: self.args += args
        if env: self.env.update(env)
        self.env.update(eva.core.env)
        cvars = eva.core.cvars.copy()
        for c in cvars.keys():
            if c.find('/') == -1:
                self.env[c] = cvars[c]
            elif item and item.group == '/'.join(c.split('/')[:-1]):
                self.env[c.split('/')[-1]] = cvars[c]
        self.xc = None
        self.termflag = threading.Event()
        self.term = None
        if tki: self.set_tki(tki)
        else: self.term_kill_interval = eva.core.timeout - default_tki_diff
        if timeout: self.timeout = timeout
        else: self.timeout = eva.core.timeout
        self.out = None
        self.err = None
        self.exitcode = -15
        self.finished = threading.Event()

    def set_tki(self, tki):
        if not tki: return
        if tki < eva.core.timeout - default_tki_diff:
            self.term_kill_interval = tki
        else:
            tki = eva.core.timeout - default_tki_diff
        if tki < 0: tki = 0

    def is_finished(self):
        return self.finished.is_set()

    def xc_finished(self):
        return self.xc.poll() is not None

    def wait(self, timeout=None):
        if timeout: t = timeout
        else: t = eva.core.timeout
        return self.finished.wait(t)

    def run(self):
        if self.launch():
            eva.core.wait_for(self.xc_finished, self.timeout)
            self.finish()

    def launch(self):
        try:
            self.term = threading.Thread(
                target=self._t_term, name='runner_t_term_%f' % time.time())
            self.xc = subprocess.Popen(
                args=(self.xc_fname,) + self.args,
                env=self.env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            self.term.start()
            return True
        except:
            self.terminate()
            logging.error('external process error %s' % self.xc_fname)
            eva.core.log_traceback()
            self.finished.set()
            return False

    def finish(self):
        self.terminate()
        out, err = self.xc.communicate()
        self.out = out.decode()
        self.err = err.decode()
        self.exitcode = self.xc.returncode
        self.finished.set()

    def terminate(self):
        self.termflag.set()

    def _t_term(self):
        self.termflag.wait()
        self.termflag.clear()
        if self.xc.poll() is not None: return
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

    def __init__(self, item=None, script=None, env_globals=None):
        if item:
            if item.action_exec:
                sfile = item.action_exec
            else:
                sfile = item.item_id + '.py'
        else:
            sfile = script
        self.script = sfile
        self.script_file = eva.core.format_xc_fname(fname=sfile)
        self.common_file = eva.core.format_xc_fname(fname='common.py')
        self.env_globals = env_globals
        self.code = None
        self.out = None
        self.err = None
        self.exitcode = -15

    def compile(self):
        if self.script_file in code_cache:
            omtime = code_cache_m[self.script_file]
        else:
            omtime = None
        try:
            mtime = os.path.getmtime(self.script_file)
            try:
                mtime_c = os.path.getmtime(self.common_file)
            except:
                mtime_c = 0
            if mtime_c > mtime:
                mtime = mtime_c
            if not omtime or mtime > omtime:
                raw = ''.join(open(self.script_file).readlines())
                try:
                    raw_c = ''.join(open(self.common_file).readlines())
                except:
                    raw_c = ''
                self.code = compile(raw_c + '\n\n' + raw, self.script, 'exec')
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

    def run(self):
        if not self.code:
            if not self.compile(): return False
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
            eva.core.log_traceback(force=True)
            self.err = traceback.format_exc()
            return False
