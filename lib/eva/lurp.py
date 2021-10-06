__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.2"

import logging
import threading
import socket
import base64
import hashlib
import msgpack

import eva.core

from eva.tools import parse_host_port

from types import SimpleNamespace

config = SimpleNamespace(host=None, port=None, buf=32768)

_flags = SimpleNamespace(dispatcher_active=False)


def update_config(cfg):
    try:
        config.host, config.port = parse_host_port(cfg.get('lurp/listen'))
        try:
            config.buf = int(cfg.get('lurp/buffer'))
        except:
            pass
        if config.port == 0:
            return False
        logging.debug('lurp.listen = %s:%u' % (config.host, config.port))
        logging.debug(f'lurp.buffer = {config.buf}')
        return True
    except:
        return False


def start():
    if not config.host:
        return False
    logging.info('Starting LURP, listening at %s:%u' %
                 (config.host, config.port))
    eva.core.stop.append(stop)
    _t = threading.Thread(target=_t_dispatcher,
                          name='lurp_t_dispatcher',
                          args=(config.host, config.port))
    _flags.dispatcher_active = True
    _t.setDaemon(True)
    _t.start()
    return True


def stop():
    _flags.dispatcher_active = False


def _t_dispatcher(host, port):
    chunk_buf = {}
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((host, port))
    logging.debug('LURP dispatcher started')
    controller = eva.core.controllers[0]

    def process_message(msg):
        if msg['s'] == 'state':
            state = msg['d']
            for s in [state] if isinstance(state, dict) else state:
                item = controller.get_item(s['oid'])
                if item:
                    if s['type'] == 'unit':
                        result = item.set_state_from_serialized(s, notify=False)
                        if result:
                            need_notify = item.update_nstate(
                                nstatus=s['nstatus'], nvalue=s['nvalue'])
                            if item.action_enabled != s['action_enabled']:
                                item.action_enabled = s['action_enabled']
                                need_notify = True
                            if result == 2 or need_notify:
                                item.notify()
                    else:
                        item.set_state_from_serialized(s)
                else:
                    logging.debug(f'LURP item not found: {s["oid"]}')

    while _flags.dispatcher_active:
        try:
            data, address = server_socket.recvfrom(config.buf)
            if not _flags.dispatcher_active:
                return
            if not data:
                continue
            logging.debug('LURP message from %s' % address[0])
            try:
                if data[0] == 0x01:  # first proto version
                    msg = msgpack.loads(data[2:], raw=False)
                    process_message(msg)
                elif data[2] == 0x00:  # single frame received
                    msg = msgpack.loads(data[3:], raw=False)
                    process_message(msg)
                elif data[2] == 0x01:  # first chunk received
                    chunk_buf[address] = data[3:]
                elif data[2] == 0x02:  # next chunk received
                    chunk_buf[address] += data[3:]
                elif data[2] == 0xff:  # last chunk received
                    frame = chunk_buf.pop(address) + data[3:]
                    msg = msgpack.loads(frame, raw=False)
                    process_message(msg)
            except Exception as e:
                logging.error(
                    f'LURP message from {address[0]} processing failed: {e}')
                eva.core.log_traceback()
        except:
            logging.critical('LURP dispatcher crashed, restarting')
            eva.core.log_traceback()
    logging.debug('LURP dispatcher stopped')
