from eva.features import restart_controller

from eva.features import InvalidParameter
from eva.features import ConfigFile


def setup(ttl=None):
    if ttl:
        try:
            ttl = float(ttl)
        except:
            raise InvalidParameter('ttl is not a number')
    with ConfigFile('lm.ini') as fh:
        fh.set('plc', 'cache_remote_state', ttl)
    restart_controller('lm')


def remove():
    with ConfigFile('lm.ini') as fh:
        fh.delete('plc', 'cache_remote_state')
    restart_controller('lm')
