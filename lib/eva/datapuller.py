__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.3.2"

import subprocess
import select
import threading
import time
import logging
import psutil
import eva.core
import queue

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
        return {
            'name': self.name,
            'cmd': self.cmd,
            'active': self.active,
            'pid': self.p.pid if self.p and self.active else None
        }

    def start(self, auto=False):

        def _start(delay=True):
            try:
                logging.info(f'data puller {self.name} is starting')
                if delay:
                    time.sleep(1)
                if eva.core.is_shutdown_requested():
                    return
                env = {}
                env.update(eva.core.env)
                env.update(eva.core.cvars)
                self.p = subprocess.Popen([
                    self.cmd if self.cmd.startswith('/') else
                    f'{eva.core.dir_eva}/{self.cmd}'
                ],
                                          shell=True,
                                          env=env,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)
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
                logging.debug(
                    f'data puller {self.name} skipping item {i} - not found')
                return
            if x[0] != 'u':
                raise MethodNotImplemented(cmd[1])
            status = x[1]
            status = None if status in ('N', 'None') else int(status)
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

        def decode_line(line):
            self.last_activity = time.perf_counter()
            try:
                return line.decode().strip()
            except Exception as e:
                logging.error(
                    f'data puller {self.name} unable to decode data: {e}')
                eva.core.log_traceback()
                return None

        def _t_collect_stream(pipe, q):
            for i in iter(pipe.readline, b''):
                q.put(i)

        stdout_q = queue.Queue()
        stderr_q = queue.Queue()

        self.last_activity = time.perf_counter()

        stdout_processor = threading.Thread(name=f'datapuller_{self.name}_sout',
                                            args=(self.p.stdout, stdout_q),
                                            target=_t_collect_stream)
        stdout_processor.start()

        stderr_processor = threading.Thread(name=f'datapuller_{self.name}_serr',
                                            args=(self.p.stderr, stderr_q),
                                            target=_t_collect_stream)
        stderr_processor.start()

        while self.active:
            ns = True
            try:
                d = stdout_q.get_nowait()
                ns = False
                line = decode_line(d)
                if line is not None:
                    process_stdout(line)
            except queue.Empty:
                pass
            try:
                d = stderr_q.get_nowait()
                ns = False
                line = decode_line(d)
                if line is not None:
                    process_stderr(line)
            except queue.Empty:
                pass
            if ns:
                time.sleep(eva.core.config.polldelay)
            else:
                continue
            if self.p.poll() is not None:
                if not eva.core.is_shutdown_requested() and self.active:
                    stdout_processor.join()
                    stderr_processor.join()
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
            except psutil.NoSuchProcess:
                pass
            except:
                eva.core.log_traceback()
        if self.executor:
            try:
                self.executor.join()
            except RuntimeError:
                pass
            finally:
                self.executor = None
