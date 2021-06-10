#!/usr/bin/env python3

import argparse
import sys
import yaml
import jsonschema
import json

from neotermcolor import colored

ap = argparse.ArgumentParser()

ap.add_argument('MODE', choices=['import', 'check'])
ap.add_argument('--dir', help='EVA ICS dir', default='.')
ap.add_argument('--clear', action='store_true')

a = ap.parse_args()

prod = ['uc', 'lm', 'sfa']

from pathlib import Path

dir_runtime = Path(a.dir) / 'runtime'
dir_etc = Path(a.dir) / 'etc'

if not dir_runtime.is_dir():
    raise RuntimeError(f'{dir_runtime} is not a directory!')

if not dir_etc.is_dir():
    raise RuntimeError(f'{dir_etc} is not a directory!')

check = a.MODE == 'check'

eva_dir = a.dir

sys.path.insert(0, (Path(__file__).absolute().parents[1] / 'lib').as_posix())

if not check:
    import eva.registry

from eva.tools import ConfigFile, ShellConfigFile

SCHEMA = yaml.safe_load((Path(__file__).absolute().parents[1] /
                         'lib/eva/registry/schema.yml').open())


def load_json(f):
    with open(f) as fh:
        return json.load(fh)


def set(key, value):
    if check:
        try:
            sch = SCHEMA[key]
        except KeyError:
            try:
                sch = SCHEMA[key[:key.rfind('/')]]
            except KeyError:
                raise RuntimeError(f'No schema for {key}')
        try:
            jsonschema.validate(value, schema=sch)
            print(f'[{colored("✓", color="cyan")}] {key}')
        except:
            print(f'[{colored("!", color="red")}] {key}')
            raise
    else:
        try:
            eva.registry.key_set(key, value)
            print(f'[{colored("+", color="green")}] {key}')
        except:
            print(f'[{colored("!", color="red")}] {key}')
            raise


# etc/venv

with ShellConfigFile(f'{dir_etc}/venv') as f:
    data = {
        'use-system-pip': f.get('USE_SYSTEM_PIP', '0') == '1',
        'system-site-packages': f.get('SYSTEM_SITE_PACKAGES', '0') == '1',
        'python': f.get('PYTHON', 'python3'),
    }
    try:
        data['pip-extra-options'] = f.get('PIP_EXTRA_OPTIONS')
    except KeyError:
        pass
    for k in ['skip', 'extra']:
        try:
            d = f.get(k.upper())
        except KeyError:
            continue
        data[k] = list(filter(None, [z.strip() for z in d.split()]))
    set('config/venv', data)

# etc/watchdog

with ShellConfigFile(f'{dir_etc}/watchdog') as f:
    data = {
        'dump': f.get('WATCHDOG_DUMP', 'no') == 'yes',
        'max-timeout': int(f.get('WATCHDOG_TIMEOUT', 5)),
        'interval': int(f.get('WATCHDOG_INTERVAL', 60))
    }
    set('config/watchdog', data)

# etc/easy_setup
try:
    with ShellConfigFile(f'{dir_etc}/easy_setup') as f:
        data = {
            'mqtt-discovery-enabled':
                f.get('MQTT_DISCOVERY_ENABLED', '0') == '1',
            'link':
                f.get('LINK', '0') == '1',
        }
        set('data/easy_setup', data)
except FileNotFoundError:
    pass

# cvars

for c in prod:
    try:
        cvars = load_json(f'{dir_runtime}/{c}_cvars.json')
        for k, v in cvars.items():
            set(f'config/{c}/cvars/{k}', v)
    except FileNotFoundError:
        pass

# cs
for c in prod:
    try:
        data = load_json(f'{dir_runtime}/{c}_cs.json')
        if not data:
            data = {'mqtt-topics': []}
        set(f'config/{c}/cs', data)
    except FileNotFoundError:
        pass

# iote.domains
try:
    clouds = {}
    with open(f'{dir_etc}/iote.domains') as fh:
        for s in fh.readlines():
            if s:
                domain, cloud, ctp = s.split(maxsplit=2)
                clouds.setdefault(f'{domain}.{cloud}', {})['account'] = domain
    if clouds:
        set('config/clouds/iote', clouds)
except FileNotFoundError:
    pass

print()

if check:
    print(colored('CHECK PASSED', color='cyan'))
else:
    print(colored('IMPORT COMPLETED', color='green'))
    # TODO cleanup

print()
