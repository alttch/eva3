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


class MQTTAPIClient(APIClient):

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

    def set_uri(self, uri):
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

    def set_controller_id(self, controller_id):
        self.set_uri(controller_id)

    def set_notifier(self, notifier_id):
        self._notifier_id = notifier_id

    def set_key(self, key, key_id='default'):
        super().set_key(key)
        _k = base64.b64encode(hashlib.sha256(str(key).encode()).digest())
        self.ce = Fernet(_k)
        self._key_id = key_id

    def do_call(self, api_uri, api_type, func, p, t):
        n = eva.notify.get_notifier(self._notifier_id)
        request_id = str(uuid.uuid4())
        data = '{}|{}|{}|{}'.format(request_id, api_type, func,
                                    jsonpickle.encode(p))
        cb = self.MQTTCallback()
        n.send_api_request(
            request_id, self._product_code + '/' + self._uri, '|{}|{}'.format(
                self._key_id,
                self.ce.encrypt(data.encode()).decode()), cb.data_handler)
        if not eva.core.wait_for(cb.is_completed, self._timeout):
            n.cancel_api_request(request_id)
            raise requests.Timeout()
        r = self.Response()
        if cb.code:
            try:
                r.text = self.ce.decrypt(cb.body.encode()).decode()
                r.status_code = cb.code
            except:
                eva.core.log_traceback()
                r.status_code = 403
        return r
