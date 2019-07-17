import sys
import os
import time

dir_lib = os.path.dirname(os.path.realpath(__file__)) + '/../lib'
sys.path.append(dir_lib)

from eva.client.apiclient import APIClientLocal
from eva.client.apiclient import result_ok

c = APIClientLocal('uc')

iterations = 10000

turn_debug = False


def api_call(func, params=None, eoe=True):
    code, result = c.call(func, params)
    if eoe and code != result_ok:
        print('Function {}({}) failed, API code: {}'.format(func, params, code))
        sys.exit(1)
    return code, result


print('EVA ICS UC Core Reaction Time (CRT) benchmark')

print()
print('Preparing environment...')

code, result = api_call('test')

if result.get('db_update') == 1:
    print(
        'WARNING: db_update is set to "instant"' + \
                ', this may slow down core benchmark'
    )

if result.get('debug'):
    print('Disabling debug mode')
    api_call('set_debug', {'debug': False})
    turn_debug = True

if result.get('log_level') < 30:
    print(
        'Warning: log level lower than "warning" may cause perfomance slow down'
    )
api_call(
    'destroy', {'i': 'sensor:eva_benchmarks/eva_benchmark_sensor'}, eoe=False)
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

print('Starting. Please do not perform any API calls during core benchmark')

code, result = api_call('test_phi', {
    'i': 'eva_benchmark_vr',
    'c': 'start_benchmark'
})

if result.get('output') != 'OK':
    print('Unable to register benchmark core handlers')
    sys.exit(2)

params['i'] = 'eva_benchmark_vs'

print('Executing {} iterations...'.format(iterations))

for a in range(0, iterations):
    params['c'] = '1000=' + str(a + 101)
    p = a / iterations * 100
    if p and p / 10 == int(p / 10):
        print('%u%%' % p)
    code, result = api_call('test_phi', params)
    if code != 0:
        print('FAILED')
        sys.exit(4)
    # time.sleep(0.03)

print('100%')

print('Benchmark completed')

time.sleep(1)

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
    print('CRT: {:.3f} ms'.format(avg * 1000))
else:
    print('FAILED TO OBTAIN CRT')
    sys.exit(5)

sys.exit(0)
