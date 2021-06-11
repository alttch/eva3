__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.3.3"

import yaml
import sys
import argparse

from neotermcolor import colored

ap = argparse.ArgumentParser()
ap.add_argument('KEYS_FILE',
                metavar='FILE',
                help='key-value file (keys as relative paths), "-" for stdin')
ap.add_argument('-c',
                '--config',
                metavar='VARS',
                help='Template vars, comma separated')

a = ap.parse_args()

from pathlib import Path
sys.path.insert(0, (Path(__file__).absolute().parents[1] / 'lib').as_posix())

import eva.registry

from eva.tools import dict_from_str, render_template

try:
    yaml.warnings({'YAMLLoadWarning': False})
except:
    pass

if a.KEYS_FILE == '-':
    tplc = sys.stdin.read()
else:
    with open(a.KEYS_FILE) as fh:
        tplc = fh.read()

keys = render_template(tplc, a.config)

for key, value in keys.items():
    eva.registry.key_set(key, value)
    print(f' [{colored("+", color="green")}] {key}')
