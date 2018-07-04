__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "EG-PM2-LAN smart PDU"
__api__ = 1

__id__ = 'eg_pm2_lan'
__equipment__ = 'EG-PM2-LAN'

__features__ = ['aao_get', 'port_set', 'cache']

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import handle_phi_event
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import get_timeout

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
        self.aao_get = True
        self.ip = self.phi_cfg.get('ip')
        self.pw = self.phi_cfg.get('pw')
        # set logout='skip' to speed up the operations
        # but keep device bound to UC ip address
        self.logout = self.phi_cfg.get('logout')
        self.re_ss = re.compile('sockstates = \[([01,]+)\]')
        if not self.ip or not self.pw:
            self.ready = False
        self.lock = threading.Lock()

    def _login(self, timeout):
        r = requests.post(
            'http://%s/login.html' % self.ip,
            data={'pw': self.pw},
            timeout=(timeout - 0.2))
        if r.status_code != 200:
            raise Exception('remote http code %s' % r.status_code)
        return r.text

    def _logout(self, timeout):
        return requests.get('http://%s/login.html' % self.ip, timeout=timeout)

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

    def get(self, port=None, timeout=None):
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
                if self.logout != 'skip':
                    self._logout(timeout=(t_start - time() + timeout))
            except:
                log_traceback()
                pass
            self.lock.release()
            return result
        except:
            try:
                if self.logout != 'skip':
                    self._logout(timeout=(t_start - time() + timeout))
            except:
                log_traceback()
                pass
            self.lock.release()
            log_traceback()
            return None

    def set(self, port, data, timeout):
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
                'http://%s/status.html?sn=%u' % (self.ip, socket),
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
                if self.logout != 'skip':
                    self._logout(timeout=(t_start - time() + timeout))
            except:
                log_traceback()
                pass
            self.lock.release()
            return True
        except:
            try:
                if self.logout != 'skip':
                    self._logout(timeout=(t_start - time() + timeout))
            except:
                log_traceback()
                pass
            self.lock.release()
            log_traceback()
            return False

    def serialize(self, full=False, config=False):
        d = super().serialize(full=full, config=config)
        return d

    def test(self, cmd=None):
        if cmd == 'get':
            return self.get(timeout=get_timeout())
        return None
