__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "3.1.1"

version = __version__

import eva.notify
import base64
import hashlib
import uuid
import jsonpickle
from cryptography.fernet import Fernet

import eva.notify
import eva.core
import requests

from eva.client.apiclient import APIClient


class CoreAPIClient(APIClient):

    class MQTTCallback(object):

        def __init__(self):
            self._completed = False
            self.body = ''
            self.code = None

        def is_completed(self):
            return self._completed

        def data_handler(self, data):
            self._completed = True
            try:
                self.code, self.body = data.split('|', 1)
                self.code = int(self.code)
            except:
                self.code = 500

    class Response(object):
        status_code = 500
        text = ''

    def __init__(self):
        super().__init__()
        self._notifier_id = None
        self._key_id = ''
        # 0 - http
        # 1 - mqtt
        self.protocol_mode = 0

    def set_uri(self, uri):
        # mqtt uri format: mqtt:notifier_id:controller/group
        # or mqtt:controller/group or controller/group@notifier
        if uri.startswith('mqtt:'):
            n = uri[5:]
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
        if self._notifier_id == '': self._notifier_id = None

    def set_key(self, key, key_id='default'):
        if key.find(':') != -1:
            (_key_id, _key) = key.split(':', 1)
        else:
            _key_id, _key = key_id, key
        super().set_key(_key)
        _k = base64.b64encode(hashlib.sha256(str(_key).encode()).digest())
        self.ce = Fernet(_k)
        self._key_id = _key_id

    def do_call_mqtt(self, api_uri, api_type, func, p, t):
        n = eva.notify.get_notifier(self._notifier_id)
        r = self.Response()
        if not n: return r
        request_id = str(uuid.uuid4())
        data = '{}|{}|{}|{}'.format(request_id, api_type, func,
                                    jsonpickle.encode(p))
        print(self._key_id)
        cb = self.MQTTCallback()
        n.send_api_request(
            request_id, self._product_code + '/' + self._uri, '|{}|{}'.format(
                self._key_id,
                self.ce.encrypt(data.encode()).decode()), cb.data_handler)
        if not eva.core.wait_for(cb.is_completed, self._timeout):
            n.finish_api_request(request_id)
            raise requests.Timeout()
        if cb.code:
            try:
                r.text = self.ce.decrypt(cb.body.encode()).decode()
                r.status_code = cb.code
            except:
                eva.core.log_traceback()
                r.status_code = 403
        return r
