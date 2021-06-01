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
                help='key-value file (keys as relative paths)')

a = ap.parse_args()

from pathlib import Path
sys.path.insert(0, (Path(__file__).absolute().parents[1] / 'lib').as_posix())

import eva.registry

try:
    yaml.warnings({'YAMLLoadWarning': False})
except:
    pass

with open(a.KEYS_FILE) as fh:
    keys = yaml.load(fh)

for key, value in keys.items():
    eva.registry.key_set(key, value)
    print(f' [{colored("+", color="green")}] {key}')
