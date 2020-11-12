import argparse
import sys
import time
import neotermcolor

neotermcolor.set_style('debug', color='grey', attrs='bold')
neotermcolor.set_style('error', color='red', attrs='bold')
neotermcolor.set_style('warning', color='yellow')
neotermcolor.set_style('counter', color='yellow', attrs='bold')

cprint = neotermcolor.cprint

from pathlib import Path
sys.path.insert(0, (Path(__file__).absolute().parents[1] / 'lib').as_posix())

from eva.client.apiclient import APIClientLocal
from eva.client.apiclient import result_ok

c = APIClientLocal('uc')

ap = argparse.ArgumentParser()

ap.add_argument('-n',
                '--iterations',
                help='Iterations to execute',
                type=int,
                default=10000)

a = ap.parse_args()

iterations = a.iterations

turn_debug = False


def api_call(func, params=None, eoe=True):
    code, result = c.call(func, params)
    if eoe and code != result_ok:
        cprint(
            'Function {}({}) failed, API code: {}'.format(func, params, code),
            '@error')
        sys.exit(1)
    return code, result


print('EVA ICS UC Core Reaction Time (CRT) benchmark')

print()
cprint('Preparing environment...', '@debug')

code, result = api_call('test')

if result.get('db_update') == 1:
    cprint(
        'WARNING: db_update is set to "instant"'
        ', this may slow down core benchmark', '@warning')

if result.get('debug'):
    print('Disabling debug mode')
    api_call('set_debug', {'debug': False})
    turn_debug = True

if result.get('log_level') < 30:
    print(
        'Warning: log level lower than "warning" may cause perfomance slow down'
    )
api_call('destroy', {'i': 'sensor:eva_benchmarks/eva_benchmark_sensor'},
         eoe=False)
api_call('destroy', {'i': 'unit:eva_benchmarks/eva_benchmark_unit'}, eoe=False)

api_call('create', {'i': 'sensor:eva_benchmarks/eva_benchmark_sensor'})
api_call('create', {'i': 'unit:eva_benchmarks/eva_benchmark_unit'})
api_call(
    'set_prop', {
        'i': 'unit:eva_benchmarks/eva_benchmark_unit',
        'p': 'action_always_exec',
        'v': 1
    })
api_call('set_prop', {
    'i': 'unit:eva_benchmarks/eva_benchmark_unit',
    'p': 'action_queue',
    'v': 1
})
api_call('enable_actions', {'i': 'unit:eva_benchmarks/eva_benchmark_unit'})

api_call('load_phi', {'i': 'eva_benchmark_vr', 'm': 'vrtrelay'})
api_call('load_phi', {
    'i': 'eva_benchmark_vs',
    'm': 'vrtsensors',
    'c': 'event_on_test_set=1'
})

api_call(
    'assign_driver', {
        'i': 'unit:eva_benchmarks/eva_benchmark_unit',
        'd': 'eva_benchmark_vr.default',
        'c': 'port=1'
    })
api_call(
    'assign_driver', {
        'i': 'sensor:eva_benchmarks/eva_benchmark_sensor',
        'd': 'eva_benchmark_vs.default',
        'c': 'port=1000'
    })

params = {}

cprint('Starting. Please do not perform any API calls during core benchmark',
       '@warning')

code, result = api_call('test_phi', {
    'i': 'eva_benchmark_vr',
    'c': 'start_benchmark'
})

if result.get('output') != 'OK':
    print('Unable to register benchmark core handlers')
    sys.exit(2)

params['i'] = 'eva_benchmark_vs'

print('Executing {} iterations...'.format(
    neotermcolor.colored(iterations, color='cyan', attrs='bold')))

for a in range(0, iterations):
    params['c'] = '1000=' + str(a + 101)
    p = a / iterations * 100
    if p and p == int(p):
        cprint(f'\r{p:.0f}%', '@counter', end=' ' * 2, flush=True)
    code, result = api_call('test_phi', params)
    if code != 0:
        cprint('FAILED', '@error')
        sys.exit(4)

cprint('\r100%', '@counter', end=' ', flush=True)

time.sleep(1)

cprint('\rBenchmark completed', color='green', end=' ' * 20 + '\n')

code, result = api_call('test')

api_call('test_phi', {'i': 'eva_benchmark_vr', 'c': 'stop_benchmark'})

print('Cleaning up...')

api_call('destroy', {'i': 'sensor:eva_benchmarks/eva_benchmark_sensor'})
api_call('destroy', {'i': 'unit:eva_benchmarks/eva_benchmark_unit'})
api_call('unload_phi', {'i': 'eva_benchmark_vr'})
api_call('unload_phi', {'i': 'eva_benchmark_vs'})

if turn_debug:
    print('Enabling debug mode back')
    api_call('set_debug', {'debug': True})

print()
avg = result.get('benchmark_crt')
if avg > 0:
    print('CRT: ', end='')
    cprint('{:.3f}'.format(avg * 1000), end='', attrs='normal', color='white')
    print(' ms')
else:
    cprint('FAILED TO OBTAIN CRT', '@error')
    sys.exit(5)

sys.exit(0)
