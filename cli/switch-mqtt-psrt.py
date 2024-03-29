#!/usr/bin/env python3

from pathlib import Path
from argparse import ArgumentParser

ap = ArgumentParser()

ap.add_argument('NOTIFIER_ID')
ap.add_argument('TYPE', choices=['mqtt', 'psrt'])
ap.add_argument('HOST')

a = ap.parse_args()

h = a.HOST

if ':' in h:
    host, port = h.rsplit(':', 1)
    port = int(port)
else:
    host = h
    port = 2873 if a.TYPE == 'psrt' else 1883

eva_dir = Path(__file__).absolute().parents[1].as_posix()

import sys, os

sys.path.insert(0, f'{eva_dir}/lib')

import eva.registry

os.system(f'{eva_dir}/bin/eva server stop')

for p in ['uc', 'lm', 'sfa']:
    try:
        k = f'config/{p}/notifiers/{a.NOTIFIER_ID}'
        data = eva.registry.key_get(k)
        data_bak = data.copy()
        print(f'{p.upper()} - ', end='', flush=True)
        data['host'] = host
        data['port'] = port
        data['type'] = a.TYPE
        eva.registry.key_set(k, data)
        if os.system(
                f'{eva_dir}/bin/eva ns {p} test {a.NOTIFIER_ID} > /dev/null'):
            print('FAILED')
            eva.registry.key_set(k, data_bak)
        else:
            print(f'{a.NOTIFIER_ID} switched to {a.TYPE}')
    except KeyError:
        print(f'no notifier {a.NOTIFIER_ID} for {p.upper()}')

os.system(f'{eva_dir}/bin/eva server start')
