__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.1"

import sys
import argparse

from pathlib import Path
sys.path.insert(0, (Path(__file__).absolute().parents[1] / 'lib').as_posix())

import eva.core
import eva.uc.driverapi as da
import logging

import rapidjson
import jsonpickle
import termcolor
import time
from pygments import lexers, highlight, formatters

from eva.tools import print_json, dict_from_str

suppress_colors = False


def colored(text, color=None, on_color=None, attrs=None):
    if suppress_colors or \
            not sys.stdout.isatty():
        return text
    return termcolor.colored(text, color=color, on_color=on_color, attrs=attrs)


def format_json(obj, minimal=False, unpicklable=False):
    if unpicklable:
        return rapidjson.dumps(rapidjson.loads(jsonpickle.encode(obj,
                unpicklable = unpicklable)), indent=4, sort_keys=True) \
                    if not minimal else \
                    jsonpickle.encode(obj, unpicklable = unpicklable)
    else:
        return rapidjson.dumps(obj, indent=4, sort_keys=True) \
            if not minimal else rapidjson.dumps(obj)


def print_result(result):
    if isinstance(result, dict):
        j = format_json(result)
        if not suppress_colors and \
                sys.stdout.isatty():
            j = highlight(j, lexers.JsonLexer(), formatters.TerminalFormatter())
        print(j)
    else:
        if result == 'OK' or result is True:
            print(colored(result, color='green', attrs=['bold']))
        elif result == 'FAILED' or result is False:
            print(colored(result, color='red'))
        else:
            print(result)
    print(colored('-' * 50, color='grey'))
    return result


def print_command(cmd):
    print('{} {}'.format(colored('> ', color='white'),
                         colored(cmd, color='yellow', attrs=['bold'])))


class PHITester(object):

    def __init__(self):
        self.phi = None

    def load(self, phi_mod, phi_cfg=None):
        if isinstance(phi_cfg, str):
            _c = dict_from_str(phi_cfg)
        elif isinstance(phi_cfg, dict):
            _c = phi_cfg
        else:
            _c = None
        da.load_phi('t1', phi_mod, _c)
        self.phi = da.get_phi('t1')

    def get(self, port=None, cfg=None, timeout=None):
        if self.phi is None:
            raise Exception('no PHI module loaded')
        if isinstance(cfg, str):
            _c = dict_from_str(cfg)
        elif isinstance(cfg, dict):
            _c = cfg
        else:
            _c = None
        _timeout = default_timeout if timeout is None else timeout
        print_command('get(port={}, cfg={}, timeout={})'.format(
            port, _c, _timeout))
        return print_result(self.phi.get(port=port, cfg=_c, timeout=_timeout))

    def set(self, port=None, data=None, cfg=None, timeout=None):
        if self.phi is None:
            raise Exception('no PHI module loaded')
        if isinstance(cfg, str):
            _c = dict_from_str(cfg)
        elif isinstance(cfg, dict):
            _c = cfg
        else:
            _c = None
        _timeout = default_timeout if timeout is None else timeout
        print_command('set(port={}, data={}, cfg={}, timeout={})'.format(
            port, data, _c, _timeout))
        return print_result(
            self.phi.set(port=port, data=data, cfg=_c, timeout=_timeout))

    def test(self, cmd=None):
        if self.phi is None:
            raise Exception('no PHI module loaded')
        print_command('test({})'.format(cmd))
        return print_result(self.phi.test(cmd))

    def exec(self, cmd=None, args=None):
        if self.phi is None:
            raise Exception('no PHI module loaded')
        print_command('exec(cmd={}, args={})'.format(cmd, args))
        return print_result(self.phi.exec(cmd))

    def modbus(self, params, **kwargs):
        import eva.uc.modbus
        ka = ''
        for k, v in kwargs.items():
            ka += ', {}='.format(k)
            if isinstance(v, str):
                ka += '\'{}\''.format(v)
            else:
                ka += str(v)
        print_command('modbus({}{})'.format(params, ka))
        eva.uc.modbus.create_modbus_port('default', params, **kwargs)

    def debug(self):
        print_command('debug')
        eva.core.debug_on()

    def nodebug(self):
        print_command('nodebug')
        eva.core.debug_off()


_me = 'EVA ICS PHI tester version {}'.format(__version__)

ap = argparse.ArgumentParser(description=_me)

ap.add_argument('-T',
                '--timeout',
                help='default PHI timeout (default: 10 sec)',
                dest='timeout',
                type=float,
                metavar='TIMEOUT',
                default=10)
ap.add_argument('-D',
                '--debug',
                help='Enable debug messages',
                dest='debug',
                action='store_true',
                default=False)
ap.add_argument('-R',
                '--raw-output',
                help='Print raw result (no colors)',
                dest='raw',
                action='store_true',
                default=False)
ap.add_argument('fname', metavar='TEST_FILE', help='Test scenario file')

try:
    import argcomplete
    argcomplete.autocomplete(ap)
except:
    pass

a = ap.parse_args()
suppress_colors = a.raw
default_timeout = a.timeout

if a.debug:
    eva.core.debug_on()

d = {}

tester = PHITester()

d['load'] = tester.load
d['get'] = tester.get
d['set'] = tester.set
d['test'] = tester.test
d['exec'] = tester.exec
d['modbus'] = tester.modbus
d['debug'] = tester.debug
d['nodebug'] = tester.nodebug
d['sleep'] = time.sleep

try:
    with open(a.fname) as fd:
        code = fd.readlines()
except:
    print('Unable to open file: ' + a.fname)
    da.stop()
    sys.exit(5)

for i in range(len(code)):
    if code[i] == 'debug\n':
        code[i] = 'debug()\n'
    elif code[i] == 'nodebug\n':
        code[i] = 'nodebug()\n'

exec(''.join(code), d)
da.stop()
