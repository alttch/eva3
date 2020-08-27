__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2020 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.3.1"

import subprocess
import select
import threading
import time
import logging
import psutil
import eva.core

from eva.exceptions import ResourceNotFound
from eva.exceptions import MethodNotImplemented

datapullers = {}


def update_config(cfg):
    try:
        c = dict(dict(cfg)['datapullers'])
    except KeyError:
        return
    for i, v in c.items():
        logging.info(f'+ data puller {i}: {v}')
        append_data_puller(i, v)


def append_data_puller(name, cmd):
    datapullers[name] = DataPuller(name,
                                   cmd,
                                   polldelay=eva.core.config.polldelay)


def start():
    for i, v in datapullers.items():
        v.start()


def stop():
    for i, v in datapullers.items():
        v.stop()


def serialize():
    return sorted([v.serialize() for i, v in datapullers.items()],
                  key=lambda k: k['name'])


class DataPuller:

    def __init__(self, name, cmd, polldelay=0.1, tki=1):
        self.name = name
        self.cmd = cmd
        self.p = None
        self.active = False
        self.polldelay = polldelay
        self.tki = tki
        self.executor = None
        self.last_activity = None
        self.timeout = eva.core.config.timeout

    def serialize(self):
        return {'name': self.name, 'cmd': self.cmd, 'active': self.active}

    def start(self, auto=False):

        def _start(delay=True):
            try:
                logging.info(f'data puller {self.name} is starting')
                if delay:
                    time.sleep(1)
                if eva.core.is_shutdown_requested():
                    return
                self.p = subprocess.Popen([self.cmd],
                                          shell=True,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)
                self.sout = select.poll()
                self.serr = select.poll()
                self.sout.register(self.p.stdout, select.POLLIN)
                self.serr.register(self.p.stderr, select.POLLIN)
                self.executor = threading.Thread(target=self._t_run,
                                                 daemon=False,
                                                 name=f'datapuller_{self.name}')
                self.executor.start()
            except:
                eva.core.log_traceback()

        if not self.active:
            self.active = True
            eva.core.spawn(_start, delay=auto)
        else:
            logging.warning(
                f'data puller {self.name} is already active, skipping start')

    def process_data(self, data):
        if eva.core.is_shutdown_requested():
            return
        if not data:
            logging.debug(f'data puller {self.name} <empty line>')
            return
        logging.debug(f'data puller {self.name} {data}')
        z = data.split(maxsplit=1)
        if len(z) > 1:
            cmd = z[0]
            args = z[1]
        else:
            cmd = z[0]
            args = ''
        if cmd == '.ping':
            pass
        elif cmd == '.log':
            level, msg = args.split(maxsplit=1)
            level = level.lower()[0]
            msg = f'data puller {self.name} {msg}'
            if level == 'd':
                logging.debug(msg)
            elif level == 'w':
                logging.warning(msg)
            elif level == 'e':
                logging.error(msg)
            elif level == 'c':
                logging.critical(msg)
            else:
                logging.info(msg)
        else:
            i = cmd
            x = args.split(maxsplit=2)
            item = eva.core.controllers[0].get_item(i)
            if item is None:
                raise ResourceNotFound(i)
            if x[0] != 'u':
                raise MethodNotImplemented(cmd[1])
            status = x[1]
            status = None if status == 'None' else int(status)
            try:
                value = x[2]
                for q in ['\'', '"']:
                    if value.startswith(q) and value.endswith(q):
                        value = value[1:-1]
                        break
            except:
                value = None
            logging.debug(f'data puller {self.name} item {i} '
                          f'update status: {status}, value: {value}')
            if value == 'None':
                value = None
            item.update_set_state(status, value)

    def restart(self, auto=False):
        self.stop()
        self.start(auto=auto)

    def _t_run(self):

        def get_line(pipe):
            self.last_activity = time.perf_counter()
            try:
                return pipe.readline().decode().strip()
            except Exception as e:
                logging.error(
                    f'data puller {self.name} unable to decode data: {e}')
                eva.core.log_traceback()

        def process_stdout(data):
            try:
                self.process_data(data)
            except:
                logging.error(f'data puller {self.name} unable '
                              f'to process data: {data}')
                eva.core.log_traceback()

        def process_stderr(data):
            if data:
                logging.error(f'data puller {self.name} {data}')

        self.last_activity = time.perf_counter()
        while self.active:
            ns = True
            if self.sout.poll(self.polldelay):
                process_stdout(get_line(self.p.stdout))
                ns = False
            if self.serr.poll(self.polldelay):
                process_stderr(get_line(self.p.stderr))
                ns = False
            if ns:
                time.sleep(self.polldelay)
            if self.p.poll() is not None:
                if not eva.core.is_shutdown_requested() and self.active:
                    out, err = self.p.communicate()
                    for d in out.decode().strip().split('\n'):
                        d = d.strip()
                        if d:
                            process_stdout(d)
                    for d in err.decode().strip().split('\n'):
                        d = d.strip()
                        if d:
                            process_stderr(d)
                    logging.error(f'data puller {self.name} exited with '
                                  f'code {self.p.returncode}. restarting')
                    self.restart(auto=True)
                break
            if self.last_activity + self.timeout < time.perf_counter():
                if not eva.core.is_shutdown_requested() and self.active:
                    logging.error(
                        f'data puller {self.name} timed out. restarting')
                    self.restart(auto=True)
                break

    def stop(self):
        logging.info(f'data puller {self.name} is stopping')
        self.active = False
        if self.p:
            try:
                pp = psutil.Process(self.p.pid)
                childs = []
                for c in pp.children(recursive=True):
                    childs.append(c)
                try:
                    self.p.terminate()
                    for c in childs:
                        try:
                            c.terminate()
                        except:
                            pass
                    self.p.terminate()
                    try:
                        if self.p.poll() is None:
                            time.sleep(self.tki)
                    except:
                        pass
                except:
                    pass
                self.p.kill()
                for c in childs:
                    try:
                        c.kill()
                    except:
                        pass
            except:
                pass
        if self.executor:
            try:
                self.executor.join()
            except RuntimeError:
                pass
            finally:
                self.executor = None
