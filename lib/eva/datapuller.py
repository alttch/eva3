__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"

import subprocess
import threading
import time
import logging
import psutil
import eva.core
import queue
import signal

import eva.registry

from eva.exceptions import ResourceNotFound
from eva.exceptions import MethodNotImplemented
from eva.exceptions import FunctionFailed
from eva.exceptions import InvalidParameter

datapullers = {}

dp_destroyed = set()

dp_lock = eva.core.RLocker('datapullers')


def preexec_function():
    signal.signal(signal.SIGINT, signal.SIG_IGN)


@dp_lock
def update_config(cfg):
    c = cfg.get('datapullers', default={})
    c.update(eva.registry.get_subkeys('config/uc/datapullers'))
    for i, v in c.items():
        try:
            if isinstance(v, dict):
                cmd = v['cmd']
                timeout = v.get('timeout')
                if timeout:
                    timeout = float(timeout)
                event_timeout = v.get('event-timeout')
                if event_timeout:
                    event_timeout = float(event_timeout)
            else:
                cmd = v
                timeout = None
                event_timeout = None
            logging.info(
                f'+ data puller {i}: {cmd} (timeout: {timeout}/{event_timeout})'
            )
            dp = DataPuller(i,
                            cmd,
                            polldelay=eva.core.config.polldelay,
                            timeout=timeout,
                            event_timeout=event_timeout)
            dp.saved = True
            datapullers[i] = dp
        except Exception as e:
            logging.error(f'Datapuller init error: {e}')
            eva.core.log_traceback()


@dp_lock
def create_data_puller(name, cmd, timeout=None, event_timeout=None, save=False):
    try:
        if datapullers[name].active:
            raise FunctionFailed('Data puller exists and is active')
    except KeyError:
        pass
    dp = DataPuller(name,
                    cmd,
                    polldelay=eva.core.config.polldelay,
                    timeout=timeout,
                    event_timeout=event_timeout)
    datapullers[name] = dp
    try:
        dp_destroyed.remove(name)
    except KeyError:
        pass
    if timeout is not None and timeout <= 0:
        raise InvalidParameter('timeout must be greater than zero')
    if event_timeout is not None and event_timeout <= 0:
        raise InvalidParameter('event timeout must be greater than zero')
    if save:
        if not eva.core.prepare_save():
            raise FunctionFailed('prepare save error')
        eva.registry.key_set(f'config/uc/datapullers/{name}', {
            'cmd': cmd,
            'timeout': timeout,
            'event-timeout': event_timeout
        })
        if not eva.core.finish_save():
            raise FunctionFailed('finish save error')
        dp.saved = True


@eva.core.save
@dp_lock
def save():
    for d in dp_destroyed:
        eva.registry.key_delete(f'config/uc/datapullers/{d}')
    for i, dp in datapullers:
        if not dp.saved:
            eva.registry.key_set(
                f'config/uc/datapullers/{i}', {
                    'cmd': dp.cmd,
                    'timeout': dp._timeout,
                    'event-timeout': dp.event_timeout
                })


@dp_lock
def destroy_data_puller(name):
    try:
        if datapullers[name].active:
            raise FunctionFailed('Data puller is active')
    except KeyError:
        raise ResourceNotFound
    del datapullers[name]
    if eva.core.config.auto_save:
        eva.registry.key_delete(f'config/uc/datapullers/{name}')
    else:
        dp_destroyed.add(name)


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

    def __init__(self,
                 name,
                 cmd,
                 polldelay=0.1,
                 tki=1,
                 timeout=None,
                 event_timeout=None):
        self.name = name
        self.cmd = cmd
        self.p = None
        self.active = False
        self.polldelay = polldelay
        self.tki = tki
        self.executor = None
        self.last_activity = None
        self.last_event = None
        self.timeout = timeout if timeout else eva.core.config.timeout
        self._timeout = timeout
        self.event_timeout = event_timeout
        self.state = ''
        self.saved = False

    def serialize(self):
        return {
            'name': self.name,
            'cmd': self.cmd,
            'active': self.active,
            'state': self.state,
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
                                          preexec_fn=preexec_function,
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
        elif cmd == '.state':
            self.state = args
        else:
            i = cmd
            x = args.split(maxsplit=2)
            self.last_event = time.perf_counter()
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
            if self.event_timeout and self.last_event and \
                    self.last_event + self.event_timeout < time.perf_counter(
            ):
                if not eva.core.is_shutdown_requested() and self.active:
                    logging.error(f'data puller {self.name} '
                                  f'timed out (no events). restarting')
                    self.restart(auto=True)
                break
            elif self.last_activity + self.timeout < time.perf_counter():
                if not eva.core.is_shutdown_requested() and self.active:
                    logging.error(f'data puller {self.name} timed '
                                  f'out (no output). restarting')
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
