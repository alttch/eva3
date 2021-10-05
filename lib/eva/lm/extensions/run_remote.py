__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.2"
__description__ = "Run macro on remote LM PLC"
__api__ = 7
__mods_required__ = []

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
    'type': 'ufloat',
    'required': False
}]

__functions__ = {
    'run(macro, args=None, kwargs=None, ' + \
            'wait=None, priority=None, q=None, _uuid=None)':
    'Launch macro on remote LM PLC'
}

__iec_functions__ = {
    'run': {
        'description':
            'run remote macro',
        'var_in': [{
            'var': 'macro',
            'description': 'macro id'
        }, {
            'var': 'args',
            'description': 'arguments'
        }, {
            'var': 'kwargs',
            'description': 'keyword arguments'
        }, {
            'var': 'wait',
            'description': 'wait (sec) until execution finish'
        }, {
            'var': 'priority'
        }],
        'var_out': [{
            'var': 'exitcode',
            'description': 'result code'
        }, {
            'var': 'out',
            'description': 'macro output'
        }, {
            'var': 'status',
            'description': 'execution status'
        }, {
            'var': 'uuid',
            'description': 'execution task uuid'
        }]
    }
}

__help__ = """
Allows to run macros on remote LM PLC
"""

from eva.lm.extensions.generic import LMExt as GenericExt

from eva.lm.extapi import get_timeout
from eva.lm.extapi import log_traceback

from eva.client.coreapiclient import CoreAPIClient

from eva.lm.extapi import ext_constructor


class LMExt(GenericExt):

    @ext_constructor
    def __init__(self, **kwargs):
        url = self.cfg.get('url')
        k = self.cfg.get('k')
        timeout = self.cfg.get('timeout')
        try:
            timeout = float(timeout)
        except:
            timeout = get_timeout()
        if not url:
            self.log_error('remote LM PLC API url not specified')
            self.ready = False
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
            kwargs=None,
            wait=None,
            priority=None,
            q=None,
            _uuid=None):
        params = {'i': macro_id}
        if args is not None:
            params['a'] = args
        if kwargs is not None:
            params['kw'] = kwargs
        if priority is not None:
            params['p'] = priority
        if wait is not None:
            params['w'] = wait
        if q is not None:
            params['q'] = q
        if _uuid is not None:
            params['u'] = _uuid
        code, result = self.apiclient.call('run', params)
        if code:
            self.log_error('Remote macro %s run failed, API code: %u' %
                           (macro_id, code))
            return None
        else:
            return result

    def validate_config(self, config={}, config_type='config', **kwargs):
        self.validate_config_whi(config=config,
                                 config_type=config_type,
                                 **kwargs)
