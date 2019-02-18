__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.0.0"
__description__ = "Run macro on remote LM PLC"
__api__ = 1
__mods_required__ = []

__id__ = 'run_remote'

__config_help__ = [{
    'name': 'url',
    'help': 'LM API URL (http://host:port)',
    'type': 'url',
    'required': True
}, {
    'name': 'k',
    'help': 'API key',
    'type': 'str',
    'required': False
}, {
    'name': 'timeout',
    'help': 'API timeout',
    'type': 'int',
    'required': False
}]

__functions__ = {
    'run(macro, args=None, wait=None, priority=None, q=None, _uuid=None)':
    'Launch macro on remote LM PLC'
}

__help__ = """
Allows to run macros on remote LM PLC
"""

from eva.lm.extensions.generic import LMExt as GenericExt

from eva.lm.extapi import get_timeout
from eva.lm.extapi import log_traceback

from eva.client.coreapiclient import CoreAPIClient


class LMExt(GenericExt):

    def __init__(self, cfg=None, info_only=False):
        super().__init__(cfg)
        self.mod_id = __id__
        self.__author = __author__
        self.__license = __license__
        self.__description = __description__
        self.__version = __version__
        self.__mods_required = __mods_required__
        self.__api_version = __api__
        self.__config_help = __config_help__
        self.__functions = __functions__
        self.__help = __help__
        if info_only: return
        url = self.cfg.get('url')
        k = self.cfg.get('k')
        timeout = self.cfg.get('timeout')
        try:
            timeout = float(timeout)
        except:
            timeout = get_timeout()
        if not url: self.ready = False
        else:
            apiclient = CoreAPIClient()
            apiclient.set_uri(url)
            apiclient.set_key(k)
            apiclient.set_product('lm')
            apiclient.set_timeout(timeout)
            self.apiclient = apiclient

    def run(self,
            macro_id,
            args=None,
            wait=None,
            priority=None,
            q=None,
            _uuid=None):
        params = {'i': macro_id}
        if args is not None: params['a'] = args
        if priority is not None: params['p'] = priority
        if wait is not None: params['w'] = wait
        if q is not None: params['q'] = q
        if _uuid is not None: params['u'] = _uuid
        code, result = self.apiclient.call('run', params)
        if code:
            self.log_error(
                'Remote macro %s run failed, API code: %u' % (macro_id, code))
            return None
        else:
            return result
