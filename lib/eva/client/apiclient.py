__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.3.3"

import requests
import uuid
from pathlib import Path

from functools import partial


def pack_msgpack(data):
    p = msgpack.Packer(use_bin_type=True)
    return p.pack(data)


try:
    import msgpack
    CONTENT_TYPE = 'application/msgpack'
    pack = pack_msgpack
    unpack = partial(msgpack.loads, raw=False)
except:
    CONTENT_TYPE = 'application/json'
    try:
        import rapidjson as json
    except:
        import json
    pack = json.dumps
    unpack = json.loads

version = __version__

result_ok = 0
result_not_found = 1
result_forbidden = 2
result_api_error = 3
result_unknown_error = 4
result_not_ready = 5
result_func_unknown = 6
result_server_error = 7
result_server_timeout = 8
result_bad_data = 9
result_func_failed = 10
result_invalid_params = 11
result_already_exists = 12  # returned by JSON RPC only, 409
result_busy = 13  # 409
result_not_implemented = 14  # 400
result_token_restricted = 15


# copy of eva.tools.parse_host_port to avoid unnecesseary imports
def parse_host_port(hp, default_port):
    if hp.find(':') == -1:
        return (hp, default_port)
    try:
        host, port = hp.split(':')
        port = int(port)
        return (host, port)
    except:
        return (None, None)


class APIClient(object):

    def __init__(self):
        self._key = None
        self._uri = None
        self._timeout = 5
        self._product_code = 'sfa'
        self._ssl_verify = True
        self.do_call = self.do_call_http

    def set_key(self, key):
        self._key = key

    def set_uri(self, uri):
        self._uri = uri
        if self._uri:
            if not self._uri.startswith('http://') and \
                    not self._uri.startswith('https://'):
                self._uri = 'http://' + self._uri

    def set_timeout(self, timeout):
        self._timeout = timeout

    def set_product(self, product):
        self._product_code = product

    def ssl_verify(self, v):
        self._ssl_verify = v

    def do_call_http(self, payload, t, rid=None):
        return requests.post(self._uri + '/jrpc',
                             data=pack(payload),
                             timeout=t,
                             verify=self._ssl_verify,
                             headers={'Content-Type': CONTENT_TYPE})

    def login(self, login, password):
        self._key = None
        code, data = self.call('login', {'u': login, 'p': password})
        if code == result_ok:
            self._key = data.get('token')
        return code, data

    def logout(self):
        code, data = self.call('logout')
        if code == result_ok:
            self._key = None
        return code, data

    def call(self,
             func,
             params=None,
             timeout=None,
             call_id=None,
             _return_raw=False,
             _debug=False):
        if not self._uri or not self._product_code:
            return result_not_ready, {}
        if timeout:
            t = timeout
        else:
            t = self._timeout
        if params:
            p = params.copy()
        else:
            p = {}
        if self._key is not None and 'k' not in p:
            p['k'] = self._key
        if call_id is not None:
            cid = call_id
            rid = str(call_id).encode()
        else:
            u = uuid.uuid4()
            cid = str(u)
            rid = u.bytes
        payload = {'jsonrpc': '2.0', 'method': func, 'params': p, 'id': cid}
        try:
            r = self.do_call(payload, t, rid=rid)
        except requests.Timeout:
            return (result_server_timeout, {}) if \
                    not _return_raw else (-1, {})
        except:
            if _debug:
                import traceback
                print(traceback.format_exc())
            return (result_server_error, {}) if \
                    not _return_raw else (-2, {})
        if _return_raw:
            return r.status_code, r.content
        if not r.ok:
            try:
                result = unpack(r.content)
            except:
                result = {}
            if r.status_code in [400, 403, 404, 405, 409, 500]:
                return result_api_error, {}
            else:
                return result_unknown_error, {}
        try:
            result = unpack(r.content)
            if not isinstance(result, dict) or \
                result.get('jsonrpc' != '2.0') or \
                result.get('id') != cid:
                raise Exception
            if 'error' in result:
                return result['error']['code'], {
                    'error': result['error']['message']
                }
            return result_ok, result['result']
        except:
            if _debug:
                import traceback
                print('Result:')
                print('-' * 80)
                print(r.content)
                print('-' * 80)
                print(traceback.format_exc())
            return (result_bad_data, r.text)


class APIClientLocal(APIClient):

    def __init__(self, product, dir_eva=None):
        import configparser
        super().__init__()
        if dir_eva is not None:
            import sys
            sys.path.insert(0, f'{dir_eva}/lib')
        import eva.registry
        self._product_code = product
        for key_name, key in eva.registry.get_subkeys(
                f'config/{product}/apikeys').items():
            if key.get('master'):
                self._key = key.get('key')
                break
        cfg = eva.registry.config_get(f'config/{product}/main')
        try:
            self._timeout = float(cfg.get('server/timeout'))
        except LookupError:
            pass
        try:
            h = cfg.get('webapi/listen')
            pfx = 'http://'
            default_port = 80
        except LookupError:
            try:
                h = cfg.get('webapi/ssl_listen')
                pfx = 'https://'
                default_port = 443
            except LookupError:
                h = None
        if h:
            try:
                host, port = parse_host_port(h, default_port)
                if host == '0.0.0.0':
                    host = '127.0.0.1'
                self._uri = pfx + host + ':' + str(port)
            except:
                pass
