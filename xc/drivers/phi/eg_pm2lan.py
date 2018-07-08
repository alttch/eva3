__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "EG-PM2-LAN smart PDU"

__id__ = 'eg_pm2lan'
__equipment__ = 'EG-PM2-LAN'
__api__ = 1
__required__ = ['aao_get', 'port_set', 'status', 'action']
__features__ = ['aao_get', 'port_set', 'cache']

__config_help__ = [{
    'name': 'host',
    'help': 'device ip/host[:port]',
    'type': 'str',
    'required': True
}, {
    'name': 'pw',
    'help': 'device password',
    'type': 'str',
    'required': True,
}, {
    'name': 'skip_logout',
    'help': 'skip logout after command',
    'type': 'bool',
    'required': False
}]
__get_help__ = []
__set_help__ = []

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import handle_phi_event
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import get_timeout

from eva.tools import val_to_boolean

import requests
import re
import threading

from time import time


class PHI(GenericPHI):

    def __init__(self, phi_cfg=None):
        super().__init__(phi_cfg=phi_cfg)
        self.phi_mod_id = __id__
        self.__author = __author__
        self.__license = __license__
        self.__description = __description__
        self.__version = __version__
        self.__api_version = __api__
        self.__equipment = __equipment__
        self.__features = __features__
        self.__required = __required__
        self.__config_help = __config_help__
        self.__get_help = __get_help__
        self.__set_help = __set_help__
        self.aao_get = True
        self.host = self.phi_cfg.get('host')
        self.pw = self.phi_cfg.get('pw')
        # set logout='skip' to speed up the operations
        # but keep device bound to UC ip address
        self.skip_logout = val_to_boolean(self.phi_cfg.get('skip_logout'))
        self.re_ss = re.compile('sockstates = \[([01,]+)\]')
        if not self.host or not self.pw:
            self.ready = False
        self.lock = threading.Lock()

    def _login(self, timeout):
        r = requests.post(
            'http://%s/login.html' % self.host,
            data={'pw': self.pw},
            timeout=(timeout - 0.2))
        if r.status_code != 200:
            raise Exception('remote http code %s' % r.status_code)
        return r.text

    def _logout(self, timeout):
        return requests.get('http://%s/login.html' % self.host, timeout=timeout)

    def _parse_response(self, data):
        m = re.search(self.re_ss, data)
        if not m:
            raise Exception('sockstats not found')
        data = m.group(1).split(',')
        result = {}
        if len(data) != 4:
            raise Exception('bad sockstats data')
        for i in range(0, 4):
            result[str(i + 1)] = int(data[i])
        self.set_cached_state(result)
        return result

    def get(self, port=None, cfg=None, timeout=0):
        # trying to get cached state before
        state = self.get_cached_state()
        if state is not None:
            return state
        t_start = time()
        if not self.lock.acquire(int(timeout - 1)):
            return None
        logged_in = False
        try:
            res = self._login(timeout=(t_start - time() + timeout))
            result = self._parse_response(res)
            try:
                if not self.skip_logout:
                    self._logout(timeout=(t_start - time() + timeout))
            except:
                log_traceback()
                pass
            self.lock.release()
            return result
        except:
            try:
                if not self.skip_logout:
                    self._logout(timeout=(t_start - time() + timeout))
            except:
                log_traceback()
            self.lock.release()
            log_traceback()
            return None

    def set(self, port=None, data=None, cfg=None, timeout=0):
        if not port or not data: return False
        t_start = time()
        if not isinstance(port, str):
            return False
        try:
            socket = int(port)
        except:
            return False
        if not self.lock.acquire(int(timeout - 2)):
            return False
        try:
            self._login(timeout=(t_start - time() + timeout))
            self.clear_cache()
            r = requests.post(
                'http://%s/status.html?sn=%u' % (self.host, socket),
                data={"cte%u" % socket: data},
                timeout=(t_start - time() + timeout - 1))
            if r.status_code != 200:
                raise Exception(
                    'remote http code %s on port set' % r.status_code)
            # the remote doesn't return any errors, so just check the socket
            result = self._parse_response(r.text)
            if result.get(port) != data:
                raise Exception('port %s set failed' % port)
            try:
                if not self.skip_logout:
                    self._logout(timeout=(t_start - time() + timeout))
            except:
                log_traceback()
                pass
            self.lock.release()
            return True
        except:
            try:
                if not self.skip_logout:
                    self._logout(timeout=(t_start - time() + timeout))
            except:
                log_traceback()
                pass
            self.lock.release()
            log_traceback()
            return False

    def test(self, cmd=None):
        if cmd == 'get' or cmd == 'self':
            result = self.get(timeout=get_timeout())
            if cmd == 'self':
                return 'OK' if result else 'FAILED'
            return result
        return {'get': 'get socket status'}
