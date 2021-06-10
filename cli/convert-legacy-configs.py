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

print(
    colored('{} CONFIGS'.format('CHECKING' if check else 'IMPORTING'),
            color='yellow'))
print()

eva_dir = a.dir

sys.path.insert(0, (Path(__file__).absolute().parents[1] / 'lib').as_posix())

if not check:
    import eva.registry

from eva.tools import ConfigFile, ShellConfigFile

SCHEMA = yaml.safe_load((Path(__file__).absolute().parents[1] /
                         'lib/eva/registry/schema.yml').open())

eva_servers = ShellConfigFile(f'{eva_dir}/etc/eva_servers')
eva_servers.open()


def load_json(f):
    with open(f) as fh:
        return json.load(fh)


def set(key, value, force_schema_key=None):
    schema_key = force_schema_key if force_schema_key else key
    if check:
        try:
            sch = SCHEMA[schema_key]
        except KeyError:
            try:
                sch = SCHEMA[schema_key[:schema_key.rfind('/')]]
            except KeyError:
                raise RuntimeError(f'No schema for {schema_key}')
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

# controller ini files

FLOATS = ['polldelay', 'timeout']
INTS = [
    'keep-action-history', 'action-cleaner-interval', 'keep-logmem',
    'keep-api-log', 'pool-min-size', 'pool-max-size', 'reactor-thread-pool',
    'cache-time', 'session-timeout', 'thread-pool', 'cache-remote-state',
    'buffer'
]
FORCE_ARRAY = [
    'hosts-allow', 'hosts-allow-encrypted', 'cdata', 'items', 'items-ro',
    'groups', 'groups-ro', 'items-deny', 'groups-deny', 'hosts-assign'
]
BOOLS = [
    'notify-on-start', 'show-traceback', 'debug', 'development',
    'dump-on-critical', 'file-management', 'setup-mode', 'rpvt',
    'session-no-prolong', 'x-real-ip', 'ssl', 'tls', 'use-core-pool',
    'cloud-manager', 'master', 'sysfunc'
]
TRY_BOOLS = ['syslog', 'stop-on-critical']

for c in prod:
    cu = c.upper()
    keyfile = dir_etc / f'{c}_apikeys.ini'
    if keyfile.exists():
        with ConfigFile(keyfile.as_posix()) as cf:
            for key_name in cf.cp.sections():
                d = dict(cf.get_section(key_name))
                kcfg = {}
                for k in [
                        'id', 'master', 'key', 'sysfunc', 'cdata', 'items',
                        'groups', 'items-ro', 'groups-ro', 'items-deny',
                        'groups-deny', 'hosts-allow', 'hosts-assign'
                ]:
                    try:
                        value = d[k.replace('-', '_')]
                    except KeyError:
                        continue
                    if k in FLOATS:
                        value = float(value)
                    elif k in INTS:
                        value = int(value)
                    elif k in FORCE_ARRAY:
                        if not isinstance(value, list):
                            value = [value]
                    elif k in BOOLS:
                        if value == 'yes':
                            value = True
                        elif value == 'no':
                            value = False
                        else:
                            raise ValueError('Invalid boolean value'
                                             ' (should be yes/no)')
                    elif k in TRY_BOOLS:
                        if value == 'yes':
                            value = True
                        elif value == 'no':
                            value = False
                    kcfg[k] = value
                for k in ['allow', 'pvt', 'rpvt']:
                    try:
                        value = list(
                            filter(None, [x.strip() for x in d[k].split(',')]))
                    except KeyError:
                        continue
                    kcfg[k] = value
                set(f'config/{c}/apikeys/{key_name}', kcfg)
    inifile = dir_etc / f'{c}.ini'
    if inifile.exists():
        service = {'setup': True}
        service['enabled'] = eva_servers.get(f'{cu}_ENABLED', 'no') == 'yes'
        try:
            service['user'] = eva_servers.get(f'{cu}_USER')
        except KeyError:
            pass
        try:
            service['supervisord-program'] = eva_servers.get(
                f'{cu}_SUPERVISORD')
        except KeyError:
            pass
        sch = SCHEMA[f'config/{c}/main']
        cfg = {}
        with ConfigFile(inifile.as_posix()) as cf:
            try:
                if cf.get('server', 'layout') == 'simple':
                    raise RuntimeError('Simple layout is no longer supported')
            except KeyError:
                pass
            for section, v in sch['properties'].items():
                if section not in ['modbus-slave', 'datapullers', 'plugins']:
                    try:
                        for name, vc in v['properties'].items():
                            try:
                                value = cf.get(section, name.replace('-', '_'))
                                if name == 'db-update':
                                    value = value.replace('_', '-')
                                elif name in FLOATS:
                                    value = float(value)
                                elif name in INTS:
                                    value = int(value)
                                elif name in FORCE_ARRAY:
                                    if not isinstance(value, list):
                                        value = [value]
                                elif name in BOOLS:
                                    if value == 'yes':
                                        value = True
                                    elif value == 'no':
                                        value = False
                                    else:
                                        raise ValueError('Invalid boolean value'
                                                         ' (should be yes/no)')
                                elif name in TRY_BOOLS:
                                    if value == 'yes':
                                        value = True
                                    elif value == 'no':
                                        value = False
                                cfg.setdefault(section, {})[name] = value
                            except KeyError:
                                pass
                    except:
                        print(f'Failed to convert {section}/{name}')
                        raise
            try:
                plugins_enabled = list(
                    filter(None, [
                        x.strip() for x in cf.get('server', 'plugins').split()
                    ]))
            except KeyError:
                plugins_enabled = []
            for section in cf.cp.sections():
                if section.startswith('plugin.'):
                    plugin_name = section[7:]
                    pcfg = {
                        'enabled': plugin_name in plugins_enabled,
                        'config': dict(cf.cp[section])
                    }
                    try:
                        plugins_enabled.remove(plugin_name)
                    except ValueError:
                        pass
                    set(f'config/{c}/plugins/{plugin_name}', pcfg)
            for p in plugins_enabled:
                set(f'config/{c}/plugins/{p}', {'enabled': True, 'config': {}})
            if c == 'uc':
                try:
                    for name, cmd in dict(
                            cf.get_section('datapullers')).items():
                        set(f'config/{c}/datapullers/{name}', {'cmd': cmd})
                except KeyError:
                    pass
                try:
                    for name, s in dict(cf.get_section('modbus')).items():
                        if name.startswith('tcp'):
                            proto = 'tcp'
                            unit, listen = s.split(',', 1)
                        elif name.startswith('udp'):
                            proto = 'tcp'
                            unit, listen = s.split(',', 1)
                        elif name.startswith('serial'):
                            unit, listen = s.split(',', 1)
                            proto, listen = listen.split(':', 1)
                        else:
                            continue
                        cfg.setdefault('modbus-slave', []).append({
                            'proto': proto,
                            'unit': unit,
                            'listen': listen
                        })
                except KeyError:
                    pass
        set(f'config/{c}/service', service)
        set(f'config/{c}/main', cfg)

# import inventory and notifiers

INVENTORY = [
    ('uc_unit.d', 'inventory/unit'),
    ('uc_sensor.d', 'inventory/sensor'),
    ('uc_mu.d', 'inventory/mu'),
    ('uc_notify.d', 'config/uc/notifiers'),
    ('lm_notify.d', 'config/lm/notifiers'),
    ('sfa_notify.d', 'config/sfa/notifiers'),
    ('lm_lvar.d', 'inventory/lvar'),
    ('lm_lmacro.d', 'inventory/lmacro'),
    ('lm_lcycle.d', 'inventory/lcycle'),
    ('lm_job.d', 'inventory/job'),
    ('lm_dmatrix_rule.d', 'inventory/dmatrix_rule'),
    ('lm_remote_uc.d', 'data/lm/remote_uc'),
    ('sfa_remote_uc.d', 'data/sfa/remote_uc'),
    ('sfa_remote_lm.d', 'data/sfa/remote_lm'),
]

INVENTORY_RESPECT_LAYOUT = ['unit', 'sensor', 'mu', 'lvar', 'lmacro', 'lcycle']

for d, k in INVENTORY:
    for f in (dir_runtime / d).glob('*.json'):
        tp = k.rsplit('/')[-1]
        data = load_json(f.as_posix())
        if tp in INVENTORY_RESPECT_LAYOUT:
            if 'full_id' not in data:
                data['full_id'] = data['group'] + '/' + data['id']
            try:
                oid = data['oid']
            except KeyError:
                oid = f'{data["type"]}:{data["group"]}/{data["id"]}'
                data['oid'] = oid
            key = f'{k}/{oid[oid.find(":")+1:]}'
        else:
            key = f'{k}/{data["id"]}'
        if 'macro_args' in data:
            d = data['macro_args']
            if d is None:
                d = []
            elif isinstance(d, str):
                d = d.split()
            data['macro_args'] = d
        if 'macro_kwargs' in data:
            d = data['macro_kwargs']
            if not isinstance(d, dict):
                d = {}
            data['macro_kwargs'] = d
        if 'set_time' in data:
            del data['set_time']
        if tp in ['lmacro', 'job', 'dmatrix_rule', 'remote_uc', 'remote_lm']:
            if 'notify_events' in data:
                del data['notify_events']
        if tp == 'dmatrix_rule':
            if 'condition' in data:
                del data['condition']
        if tp == 'dmatrix_rule':
            data['oid'] = 'dmatrix_rule:dm_rules/' + data['id']
        if tp == 'job':
            data['oid'] = 'job:jobs/' + data['id']
        set(key, data, force_schema_key=k)

print()

if check:
    print(colored('CHECK PASSED', color='cyan'))
else:
    print(colored('IMPORT COMPLETED', color='green'))
    # TODO cleanup

print()
