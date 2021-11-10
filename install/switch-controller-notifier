#!/usr/bin/env python3

from pathlib import Path
from argparse import ArgumentParser

ap = ArgumentParser()

ap.add_argument('CONTROLLER')
ap.add_argument('NOTIFIER_ID')

a = ap.parse_args()

eva_dir = Path(__file__).absolute().parents[1].as_posix()

import sys, os

sys.path.insert(0, f'{eva_dir}/lib')

import eva.registry

os.system(f'{eva_dir}/bin/eva server stop')

for p in ['lm', 'sfa']:
    for remote in ['uc', 'lm']:
        for k, data in eva.registry.key_get_recursive(
                f'data/{p}/remote_{remote}'):
            if k == a.CONTROLLER:
                uri = data['uri']
                if uri[:5] in ['mqtt:', 'psrt:']:
                    proto, notifier_id, path = uri.split(':', 2)
                    uri = f'{proto}:{a.NOTIFIER_ID}:{path}'
                    data['uri'] = uri
                    data['mqtt_update'] = a.NOTIFIER_ID
                    print(f'{p.upper()} {a.CONTROLLER} '
                          f'switched to {a.NOTIFIER_ID}')
                    eva.registry.key_set(f'data/{p}/remote_{remote}/{k}', data)

os.system(f'{eva_dir}/bin/eva server start')
