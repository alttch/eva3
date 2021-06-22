from eva.features import InvalidParameter, dir_eva
from eva.features import cli_call, is_enabled, exec_shell, restart_controller
from eva.features import val_to_boolean

from textwrap import dedent


def setup(mqtt=None,
          id=None,
          ca=None,
          cert=None,
          key=None,
          retain=None,
          announce=None):
    check_cmd = dir_eva + '/sbin/check-mqtt'
    retain = True if retain is None else val_to_boolean(retain)
    announce = 30 if announce is None else float(announce)
    if not id:
        id = 'eva_1'
    if '/' in mqtt:
        _mqtt, space = mqtt.rsplit('/', 1)
    else:
        _mqtt = mqtt
        space = None
    batch = [f'create {id} mqtt:{_mqtt}{(" -s " + space) if space else ""}']
    if ca:
        batch.append(f'set {id} ca_certs {ca}')
        check_cmd += f' --cafile {ca}'
    if cert:
        batch.append(f'set {id} certfile {ca}')
        check_cmd += f' --cert {cert}'
    if key:
        batch.append(f'set {id} keyfile {ca}')
        check_cmd += f' --key {key}'
    check_cmd += f' {mqtt}'
    exec_shell(check_cmd, passthru=True)
    batch.append(f'set {id} retain_enabled {retain}')
    batch.append(f'test {id}')
    batch.append(f'subscribe state {id} -p "#" -g "#"')
    batch.append(f'subscribe log {id}')
    batch.append(f'subscribe server {id}')
    batch.append(f'set {id} api_enabled 1')
    batch.append(f'set {id} announce_interval {announce}')
    batch.append(f'enable {id}')
    for c in ['uc', 'lm']:
        if is_enabled(c):
            print(f'{c.upper()}...')
            for b in batch:
                cli_call(f'ns {c}', b, return_result=True)
            restart_controller(c)


def remove(id=None):
    if not id:
        id = 'eva_1'
    for c in ['uc', 'lm']:
        if is_enabled(c):
            print(f'{c.upper()}...')
            try:
                cli_call(f'ns {c}', f'destroy {id}', return_result=True)
                restart_controller(c)
            except:
                from eva.features import print_warn
                print_warn(f'unable to destroy {id} notifier for {c}')
