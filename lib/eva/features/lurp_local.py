from eva.features import InvalidParameter, dir_eva, print_warn
from eva.features import cli_call, is_enabled, exec_shell, restart_controller
from eva.features import eva_jcmd

import eva.registry


def setup(buffer=None):
    if is_enabled('uc'):
        if is_enabled('lm'):
            nid = 'lurp_local_lm'
            cli_call(f'ns uc',
                     f'create {nid} udp:127.0.0.1:8911',
                     return_result=True)
            cli_call(f'ns uc',
                     f'set {nid} max_frame_size 65000',
                     return_result=True)
            cli_call(f'ns uc',
                     f'subscribe state {nid} -p "#" -g "#"',
                     return_result=True)
            cli_call(f'ns uc',
                     f'enable {nid} -p "#" -g "#"',
                     return_result=True)
        if is_enabled('sfa'):
            nid = 'lurp_local_sfa'
            cli_call(f'ns uc',
                     f'create {nid} udp:127.0.0.1:8921',
                     return_result=True)
            cli_call(f'ns uc',
                     f'set {nid} max_frame_size 65000',
                     return_result=True)
            cli_call(f'ns uc',
                     f'subscribe state {nid} -p "#" -g "#"',
                     return_result=True)
            cli_call(f'ns uc',
                     f'enable {nid} -p "#" -g "#"',
                     return_result=True)
        restart_controller('uc')
    if buffer:
        buf = int(buffer)
        if buf <= 1024:
            raise ValueError('Buffer too small')
        buf_cfg = {'buffer': buf}
    else:
        buf_cfg = {}
    if is_enabled('lm'):
        cfg = {'listen': '127.0.0.1:8911'}
        cfg.update(buf_cfg)
        eva.registry.key_set_field('config/lm/main', 'lurp', cfg)
        if is_enabled('sfa'):
            nid = 'lurp_local_sfa'
            cli_call(f'ns lm',
                     f'create {nid} udp:127.0.0.1:8921',
                     return_result=True)
            cli_call(f'ns lm',
                     f'set {nid} max_frame_size 65000',
                     return_result=True)
            cli_call(f'ns lm',
                     f'subscribe state {nid} -p "#" -g "#"',
                     return_result=True)
            cli_call(f'ns lm',
                     f'enable {nid} -p "#" -g "#"',
                     return_result=True)
        restart_controller('lm')
        if is_enabled('uc'):
            sysname = eva_jcmd('uc', 'test')['system']
            cli_call('lm',
                     f'controller set uc/{sysname} ws_state_events 0 -y',
                     return_result=True)
    if is_enabled('sfa'):
        cfg = {'listen': '127.0.0.1:8921'}
        cfg.update(buf_cfg)
        eva.registry.key_set_field('config/sfa/main', 'lurp', cfg)
        restart_controller('sfa')
        for c in ['uc', 'lm']:
            if is_enabled(c):
                sysname = eva_jcmd(c, 'test')['system']
                cli_call('sfa',
                         f'controller set {c}/{sysname} ws_state_events 0 -y',
                         return_result=True)


def remove():
    need_restart = False
    try:
        cli_call(f'ns uc', f'destroy lurp_local_lm', return_result=True)
        need_restart = True
    except:
        print_warn('UC notifier lurp_local_lm was not setup')
    try:
        cli_call(f'ns uc', f'destroy lurp_local_sfa', return_result=True)
        need_restart = True
    except:
        print_warn('UC notifier lurp_local_sfa was not setup')
    if need_restart and is_enabled('uc'):
        restart_controller('uc')
    try:
        cli_call(f'ns lm', f'destroy lurp_local_sfa', return_result=True)
    except:
        print_warn('LM notifier lurp_local_sfa was not setup')
    if is_enabled('lm'):
        eva.registry.key_delete_field('config/lm/main', 'lurp')
        restart_controller('lm')
        if is_enabled('uc'):
            sysname = eva_jcmd('uc', 'test')['system']
            cli_call('lm',
                     f'controller set uc/{sysname} ws_state_events 1 -y',
                     return_result=True)
    if is_enabled('sfa'):
        eva.registry.key_delete_field('config/sfa/main', 'lurp')
        restart_controller('sfa')
        for c in ['uc', 'lm']:
            if is_enabled(c):
                sysname = eva_jcmd(c, 'test')['system']
                cli_call('sfa',
                         f'controller set {c}/{sysname} ws_state_events 1 -y',
                         return_result=True)
