__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.1"

import sys
import getopt
import rapidjson
import yaml
import jinja2

try:
    yaml.warnings({'YAMLLoadWarning': False})
except:
    pass

from pathlib import Path
sys.path.insert(0, (Path(__file__).absolute().parents[1] / 'lib').as_posix())

from eva.client import apiclient

from eva.tools import print_json
from eva.tools import format_json


def usage():
    print()
    print('EVA UC device template tool version %s' % (apiclient.version))
    print("""
Usage: uc-tpl <command> [args] [-U API uri] [-K key] [-T sec] [-D] [-J]

    -U   specify API uri (http://host:port), if no uri specified, API will be
         called in the local mode
    -K   masterkey, if no key specified, local master key will be used (if
         local API)
    -T   API request timeout
    -D   Enable debug messages
    -J   JSON output (default: YML)

Template commands:

    validate <-t template_file> [-c config]        validate existing template,

                                                    config - config params,
                                                    comma separated name=value
                                                    pairs
                                                    
                                                    outputs formatted json if
                                                    success

    generate [-i items] [-g groups] [-v cvars] [-c config] [-t output_file]
                                                    generate new template

                                                    items - items to fetch,
                                                    comma separated.

                                                    groups - item groups, comma
                                                    separated (MQTT-style
                                                    wildcards are allowed)

                                                    cvars - cvars to fetch,
                                                    comma separated

                                                    config - config params,
                                                    comma separated name=value
                                                    pairs

Exit codes:

    0   everything is okay
    1   API error
    2   command failed

    99  if no command specified
    """)


def c_replace(s, rep):
    if isinstance(s, dict):
        result = {}
        for k, v in s.items():
            result[c_replace(k, rep)] = c_replace(v, rep)
        return result
    if isinstance(s, list):
        result = []
        for x in s:
            result.append(c_replace(x, rep))
        return result
    if not isinstance(s, str):
        return s
    result = s
    for i, v in rep.items():
        result = result.replace(i, '{{ %s }}' % v)
    return result


def print_debug(o1=None, o2=None, end='\n'):
    if not debug:
        return
    if o1:
        print(o1, end='')
    if o2:
        print('', o2, end='')
    print(end=end)


def dump_yaml(s):
    return yaml.dump(s, default_flow_style=False)


def print_yaml(s):
    print(dump_yaml(s))


timeout = None
apikey = None
apiuri = None

tpl_file = None

debug = False

encoder = dump_yaml
decoder = yaml.load
formatter = yaml.dump
printer = print_yaml

items = []
groups = []
cvars = []
c = []
config = {}
config_rev = {}
tpl_cvars = {}

try:
    func = sys.argv[1]
    o, a = getopt.getopt(sys.argv[2:], 'K:T:U:t:c:i:g:v:DJ')
except:
    usage()
    sys.exit(99)

for i, v in o:
    if i == '-t':
        tpl_file = v
    elif i == '-c':
        c = v.split(',')
    elif i == '-i':
        items = v.split(',')
    elif i == '-g':
        groups = v.split(',')
    elif i == '-v':
        cvars = v.split(',')
    elif i == '-J':
        encoder = rapidjson.dumps
        decoder = rapidjson.loads
        formatter = format_json
        printer = print_json
    elif i == '-T':
        try:
            timeout = float(v)
        except:
            usage()
            sys.exit(99)
    elif i == '-U':
        apiuri = v
        if apiuri[-1] == '/':
            apiuri = apiuri[:-1]
    elif i == '-K':
        apikey = v
    elif i == '-D':
        debug = True

for i in c:
    try:
        name, value = i.split('=')
        config[name] = value
        config_rev[value] = name
    except:
        usage()
        sys.exit(99)

if func == 'validate':
    try:
        with open(tpl_file) as fd:
            template = jinja2.Template(fd.read())
    except:
        print('No such template file: %s' % tpl_file)
        usage()
        sys.exit(99)
    raw = template.render(config)
    try:
        result = decoder(raw)
        printer(result)
    except:
        print('Invalid data')
        print_debug('-----------------------')
        print_debug(raw)
        raise
    sys.exit(0)

elif func == 'generate':
    tpl = {}
    if not apiuri:
        try:
            api = apiclient.APIClientLocal('uc')
        except:
            print('Can not init API')
            import traceback
            traceback.print_exc()
            sys.exit(98)
    else:
        api = apiclient.APIClient()
        api.set_uri(apiuri)
        api.set_product('uc')

    if apikey is not None:
        api.set_key(apikey)
    api.ssl_verify(False)
    print_debug('Generating new template')
    print_debug('items:', items)
    print_debug('groups:', groups)
    print_debug()
    for cvar in cvars:
        print_debug('cvar %s' % cvar, end='')
        c, r = api.call('get_cvar', {'i': cvar}, _debug=debug)
        if c:
            print('\nAPI call failed, code %u' % c)
            sys.exit(1)
        v = r[cvar]
        print_debug(' = %s' % v)
        tpl_cvars[c_replace(cvar, config_rev)] = c_replace(v, config_rev)
    c, r = api.call('test', _debug=debug)
    if c:
        print('\nAPI call failed, code %u' % c)
        sys.exit(1)
    controller_id = r['controller']
    for group in groups:
        c, r = api.call('list', {'g': group}, _debug=debug)
        if c:
            print('\nAPI call failed, code %u' % c)
            sys.exit(1)
        for i in r:
            items.append(i['oid'])
    for item in items:
        print_debug('item %s' % item, end='')
        c, r = api.call('get_config', {'i': item}, _debug=debug)
        if c:
            print('\nAPI call failed, code %u' % c)
            sys.exit(1)
        if r.get('type') not in ['unit', 'sensor']:
            print_debug(' - type not supported: %s' % r.get('type'))
        section = r.get('type')
        full_id = c_replace(r.get('full_id'), config_rev)
        for f in ['full_id', 'oid', 'id', 'group', 'type', 'value_condition']:
            try:
                del r[f]
            except:
                pass
        for p, v in r.items():
            r[p] = c_replace(v, config_rev)
        if not section in tpl:
            tpl[section] = {}
        update_exec = r.get('update_exec')
        if update_exec and update_exec.startswith('|'):
            if section == 'sensor' or \
                    (section == 'unit' and \
                        update_exec == r.get('action_exec') and \
                        r.get('update_driver_config') ==
                            r.get('action_driver_config')):
                driver_config = {'id': update_exec[1:]}
                driver_config['config'] = r.get('update_driver_config')
                for p in [
                        'update_exec', 'action_exec', 'action_driver_config',
                        'update_driver_config'
                ]:
                    try:
                        del r[p]
                    except KeyError:
                        pass
                r['driver'] = driver_config
        r['controller'] = controller_id
        tpl[section][full_id] = r
        print_debug(' - OK')
    if tpl_cvars:
        tpl.setdefault('controller',{})[controller_id] = { 'cvar': tpl_cvars }
    if (tpl_file):
        try:
            with open(tpl_file, 'w') as fd:
                fd.write(formatter(tpl))
            print('Template saved to %s' % tpl_file)
        except:
            print('Error: can not save template to %s' % tpl_file)
    else:
        print_debug('Template output:')
        print_debug('----------------')
        printer(tpl)
else:
    usage()
    sys.exit(99)
