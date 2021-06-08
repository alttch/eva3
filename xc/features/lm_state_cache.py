from eva.features import restart_controller, is_enabled

from eva.features import InvalidParameter, FunctionFailed

import eva.registry


def setup(ttl=None):
    if not is_enabled('lm'):
        raise FunctionFailed('LM PLC is not enabled')
    if ttl:
        try:
            ttl = float(ttl)
        except:
            raise InvalidParameter('ttl is not a number')
    eva.registry.key_set_field('config/lm/main', 'plc/cache-remote-state', ttl)
    restart_controller('lm')


def remove():
    if not is_enabled('lm'):
        raise FunctionFailed('LM PLC is not enabled')
    eva.registry.key_delete_field('config/lm/main', 'plc/cache-remote-state')
    restart_controller('lm')
