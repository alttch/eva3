from eva.features import InvalidParameter
from eva.features import cli_call, restart_controller


def setup(key=None):
    if not key:
        raise InvalidParameter
    data = cli_call('', 'server status', return_result=True)
    changed = False
    for c, v in data.items():
        if v:
            print(f'Changing default key for {c}')
            cli_call(c, f'key set default key {key} -y', return_result=True)
            changed = True
    if changed:
        restart_controller()
