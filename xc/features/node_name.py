from eva.features import InvalidParameter, FunctionFailed
from eva.features import is_enabled, ShellConfigFile, ConfigFile
from eva.features import stop_controller, start_controller, print_warn

import eva.registry


def setup(name=None):
    if not name:
        raise InvalidParameter
    current_name = eva.registry.SYSTEM_NAME
    try:
        eva.registry.db.key_get(key=f'eva3/{current_name}/config/venv')
    except Exception as e:
        raise FunctionFailed(f'Unable to setup registry config: {e}')
    print('Stopping controllers...')
    for c in ['sfa', 'lm', 'uc']:
        if is_enabled(c):
            stop_controller(c)
    if name != current_name:
        print('Setting local inter-connection for UC...')
        for c in ['lm', 'sfa']:
            if is_enabled(c):
                try:
                    with eva.registry.key_as_dict(
                            f'data/{c}/remote_uc/{current_name}') as k:
                        k.set('id', name)
                        k.set('full_id', f'uc/{name}')
                        k.set('oid', f'remote_uc:uc/{name}')
                    eva.registry.db.key_rename(
                        key=f'eva3/{current_name}'
                        f'/data/{c}/remote_uc/{current_name}',
                        dst_key=f'eva3/{current_name}/data/{c}/remote_uc/{name}'
                    )
                except KeyError:
                    pass
        print('Setting local inter-connection for LM PLC...')
        if is_enabled('sfa'):
            try:
                with eva.registry.key_as_dict(
                        f'data/sfa/remote_lm/{current_name}') as k:
                    k.set('id', name)
                    k.set('full_id', f'lm/{name}')
                    k.set('oid', f'remote_lm:lm/{name}')
                eva.registry.db.key_rename(
                    key=f'eva3/{current_name}/data'
                    f'/sfa/remote_lm/{current_name}',
                    dst_key=f'eva3/{current_name}/data/sfa/remote_lm/{name}')
            except KeyError:
                pass
        print('Renaming schema keys...')
        eva.registry.db.key_rename(key=f'.schema/eva3/{current_name}',
                                   dst_key=f'.schema/eva3/{name}')
        print('Renaming node keys...')
        eva.registry.db.key_rename(key=f'eva3/{current_name}',
                                   dst_key=f'eva3/{name}')
    print('Setting new name in etc/eva_config ...')
    with ShellConfigFile('eva_config', init_if_missing=True) as cf:
        cf.set('SYSTEM_NAME', name)
    print('Setting new name in etc/eva_shell.ini ...')
    with ConfigFile('eva_shell.ini', init_if_missing=True) as cf:
        cf.set('shell', 'nodename', name)
    eva.registry.SYSTEM_NAME = current_name
    print('Starting controllers back')
    for c in ['uc', 'lm', 'sfa']:
        if is_enabled(c):
            start_controller(c)
    print()
    print_warn(f'Local node renamed to "{name}"')
    print_warn('If eva-shell is running in the interactive mode, '
               'it is recommended to restart the session')
