from eva.features import InvalidParameter, dir_eva
from eva.features import cli_call, is_enabled, exec_shell, restart_controller
from eva.features import val_to_boolean
from eva.features import print_warn

from textwrap import dedent


def setup(host=None,
          id=None,
          ca=None,
          cert=None,
          key=None,
          retain=None,
          announce=None,
          proto=None,
          socket_buf_size=None):
    if proto is None:
        proto = 'mqtt'
    elif proto not in ['mqtt', 'psrt']:
        raise InvalidParameter(f'Invalid protocol: {proto}')
    check_cmd = dir_eva + f'/sbin/check-{proto}'
    if proto == 'psrt':
        retain = False if retain is None else val_to_boolean(retain)
    else:
        retain = True if retain is None else val_to_boolean(retain)
    announce = 30 if announce is None else float(announce)
    if not id:
        id = 'eva_1'
    if '/' in host:
        _host, space = host.rsplit('/', 1)
    else:
        _host = host
        space = None
    batch = [f'create {id} {proto}:{_host}{(" -s " + space) if space else ""}']
    if ca:
        batch.append(f'set {id} ca_certs {ca}')
        check_cmd += f' --cafile {ca}'
    if cert:
        if proto == 'psrt':
            print_warn('cert/key auth no supported by psrt')
        else:
            batch.append(f'set {id} certfile {ca}')
            check_cmd += f' --cert {cert}'
    if key and proto != 'psrt':
        if proto == 'psrt':
            print_warn('cert/key auth no supported by psrt')
        else:
            batch.append(f'set {id} keyfile {ca}')
            check_cmd += f' --key {key}'
    check_cmd += f' {host}'
    exec_shell(check_cmd, passthru=True)
    if retain and proto == 'psrt':
        print_warn('retain not supported by psrt')
    if proto == 'mqtt':
        batch.append(f'set {id} retain_enabled {retain}')
    if socket_buf_size:
        if proto == 'psrt':
            batch.append(f'set {id} socket_buf_size {socket_buf_size}')
        else:
            print_warn('socket_buf_size supported by psrt only')
    if proto == 'mqtt':
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
                print_warn(f'unable to destroy {id} notifier for {c}')
