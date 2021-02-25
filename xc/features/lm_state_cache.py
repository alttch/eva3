from eva.features import restart_controller, is_enabled

from eva.features import InvalidParameter, FunctionFailed
from eva.features import ConfigFile


def setup(ttl=None):
    if not is_enabled('lm'):
        raise FunctionFailed('LM PLC is not enabled')
    if ttl:
        try:
            ttl = float(ttl)
        except:
            raise InvalidParameter('ttl is not a number')
    with ConfigFile('lm.ini') as fh:
        fh.set('plc', 'cache_remote_state', ttl)
    restart_controller('lm')


def remove():
    if not is_enabled('lm'):
        raise FunctionFailed('LM PLC is not enabled')
    with ConfigFile('lm.ini') as fh:
        fh.delete('plc', 'cache_remote_state')
    restart_controller('lm')
