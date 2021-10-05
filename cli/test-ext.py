__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.2"

import sys
import argparse

from pathlib import Path
sys.path.insert(0, (Path(__file__).absolute().parents[1] / 'lib').as_posix())

import eva.core
import eva.lm.extapi as ea
import logging

from eva.tools import dict_from_str

import time

_me = 'EVA ICS LM PLC extension tester version {}'.format(__version__)

ap = argparse.ArgumentParser(description=_me)

ap.add_argument('-D',
                '--debug',
                help='Enable debug messages',
                dest='debug',
                action='store_true',
                default=False)
ap.add_argument('e', metavar='EXTENSION', help='Extension to test')
ap.add_argument('fname',
                metavar='TEST_FILE',
                help='Test scenario file (call __FUNCTION)')
ap.add_argument('-c', metavar='PARAMS', help='Extension configuration params')

try:
    import argcomplete
    argcomplete.autocomplete(ap)
except:
    pass

a = ap.parse_args()

if a.debug:
    eva.core.debug_on()

if not ea.load_ext('_', a.e, cfg=dict_from_str(a.c)):
    sys.exit(2)

try:
    with open(a.fname) as fd:
        code = fd.read()
except:
    print('Unable to open file: ' + a.fname)
    ea.stop()
    sys.exit(5)

exec(code, ea.env)
ea.stop()
