__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "Emulates 16-port relay"

__id__ = 'vrtrelay'
__equipment__ = 'virtual'
__api__ = 1
__required__ = ['port_get', 'port_set']
__features__ = ['port_get', 'port_set', 'aao_set']
__config_help__ = {'default_status': 'ports status on load (default: -1)'}

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import handle_phi_event
from eva.uc.driverapi import log_traceback


class PHI(GenericPHI):

    def __init__(self, phi_cfg=None):
        super().__init__(phi_cfg=phi_cfg)
        d = self.phi_cfg.get('default_status')
        if d is None: d = -1
        else:
            try:
                d = int(d)
            except:
                d = -1
        self.data = {}
        for i in range(1, 16):
            self.data[str(i)] = d
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

    def get(self, port=None, cfg=None, timeout=0):
        # if self.aao_get: return self.data
        try:
            return self.data.get(str(port))
        except:
            return None

    def set(self, port=None, data=None, cfg=None, timeout=0):
        if isinstance(port, list):
            ports = port
            multi = True
        else:
            ports = [port]
            multi = False
        for i in range(0, len(ports)):
            p = ports[i]
            _port = str(p)
            if multi:
                d = data[i]
            else:
                d = data
            try:
                _data = int(d)
            except:
                return False
            if not _port in self.data:
                return False
            self.data[_port] = _data
        if self.phi_cfg.get('event_on_set'):
            handle_phi_event(self.phi_id, port, self.data)
        return True

    def test(self, cmd=None):
        if cmd == 'self':
            return 'OK'
        if cmd == 'get':
            return self.data
        if cmd == 'critical':
            self.log_critical('test')
            return True
        try:
            port, val = cmd.split('=')
            port = int(port)
            val = int(val)
            if port < 1 or port > 16 or val < -1 or val > 1: return None
            self.data[str(port)] = val
            self.log_debug('test set port %s=%s' % (port, val))
            if self.phi_cfg.get('event_on_test_set'):
                handle_phi_event(self, port, self.data)
            return self.data
        except:
            return {'get': 'get relay ports status', 'X=S': 'set port X to S'}
