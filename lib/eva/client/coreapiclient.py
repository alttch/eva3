__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"

version = __version__

import eva.notify
import hashlib
import uuid
import threading
import msgpack
import logging

import eva.crypto

import eva.notify
import eva.core
import requests

from eva.client.apiclient import APIClient, pack_msgpack


class CoreAPIClient(APIClient):

    class MQTTCallback(object):

        def __init__(self):
            self.completed = threading.Event()
            self.body = ''
            self.code = None

        def data_handler(self, data):
            self.completed.set()
            try:
                if data[0] != 0:
                    raise ValueError
                self.code = data[1]
                self.body = data[2:]
            except:
                self.code = 500

    class Response(object):
        status_code = 500
        text = ''
        content = ''
        ok = False

    def __init__(self):
        super().__init__()
        self._notifier_id = None
        self._key_id = ''
        # 0 - http
        # 1 - mqtt
        self.protocol_mode = 0

    def set_uri(self, uri):
        # mqtt uri format: mqtt://notifier_id:type/controller
        # or mqtt:type/controller or type/controller@notifier
        if uri.startswith('mqtt:'):
            n = uri[5:]
            if n.startswith('//'):
                n = n[2:]
            if n.find(':') != -1:
                notifier_id, controller_id = n.split(':')
            else:
                notifier_id, controller_id = None, n
            self.set_notifier(notifier_id)
            self.set_controller_id(controller_id)
            self.set_protocol_mode(1)
        elif not uri.startswith('http://') and \
                not uri.startswith('https://') and uri.find('/') != -1:
            if uri.find('@') != -1:
                notifier_id, controller_id = uri.split('@')
            else:
                notifier_id, controller_id = None, uri
            self.set_notifier(notifier_id)
            self.set_controller_id(controller_id)
            self.set_protocol_mode(1)
        else:
            super().set_uri(uri)
            self.set_protocol_mode(0)

    def set_protocol_mode(self, protocol_mode):
        if not protocol_mode:
            self.do_call = self.do_call_http
        elif protocol_mode == 1:
            self.do_call = self.do_call_mqtt
        else:
            raise Exception('protocol_mode unknown')
        self.protocol_mode = protocol_mode

    def set_controller_id(self, uri):
        _u = uri
        if _u.find('/') != -1:
            try:
                self._product_code, self._uri = _u.split('/')
            except:
                self._product_code = None
                self._uri = None
            return
        else:
            self._uri = _u

    def set_notifier(self, notifier_id):
        self._notifier_id = notifier_id
        if self._notifier_id == '':
            self._notifier_id = None

    def set_key(self, key, key_id=None):
        if key is None:
            return
        if key_id is None:
            key_id = eva.core.config.default_cloud_key
        if key.find(':') != -1:
            (_key_id, _key) = key.split(':', 1)
        else:
            _key_id, _key = key_id, key
        super().set_key(_key)
        self._key_id = _key_id
        self._private_key = hashlib.sha512(str(_key).encode()).digest()

    def do_call_mqtt(self, payload, t, rid=None):
        """
        Protocol description:

        API request is sent to controller MQTT API topic

        Request format:

        0 - 0x00, binary packet
        1 - 0x02, protocol version
        2 - API key ID and binary request frame (RF), combined with 0x00

        RF format:

        0-15    Binary hexadecimal request ID, padded
        16-end  MessagePack request payload

        API response will be sent to response_topic/{request_ID_in_hex}
        """
        n = eva.notify.get_notifier(self._notifier_id)
        r = self.Response()
        if not n:
            return r
        if rid is None:
            rid = uuid.uuid4().bytes
        else:
            if len(rid) > 16:
                logging.error('request ID is longer than 16 bytes, aborting')
                return r
            rid.ljust(16, b'\x00')
        request_id = rid.hex()
        data = rid + pack_msgpack(payload)
        cb = self.MQTTCallback()
        n.send_api_request(
            request_id, self._product_code + '/' + self._uri,
            b'\x00\x02' + self._key_id.encode() + b'\x00' +
            eva.crypto.encrypt(data, self._private_key, key_is_hash=True),
            cb.data_handler)
        if not cb.completed.wait(self._timeout):
            n.finish_api_request(request_id)
            raise requests.Timeout()
        if cb.code:
            try:
                r.content = eva.crypto.decrypt(cb.body,
                                               self._private_key,
                                               key_is_hash=True)
                if cb.code == 200:
                    r.ok = True
                r.status_code = cb.code
            except:
                eva.core.log_traceback()
                r.status_code = 403
        return r
