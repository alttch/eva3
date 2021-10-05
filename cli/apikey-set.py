__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.2"

import sys
import os
import argparse

from pathlib import Path
sys.path.insert(0, (Path(__file__).absolute().parents[1] / 'lib').as_posix())

os.environ['EVA_DIR'] = Path(__file__).absolute().parents[1].as_posix()

import eva.core
import eva.apikey

product_build = -1

ap = argparse.ArgumentParser()

ap.add_argument('CONTROLLER', choices=['uc', 'lm', 'sfa'])
ap.add_argument('KEY_ID')
ap.add_argument('NEW_KEY')

a = ap.parse_args()

product_code = a.CONTROLLER

eva.core.init()
eva.core.set_product(product_code, product_build)
eva.core.product.name = 'API key manager'
cfg = eva.core.load(initial=True)
if not cfg:
    raise RuntimeError('Unable to load config')
eva.core.start(init_db_only=True)

eva.apikey.init()
eva.apikey.load()

key = eva.apikey.keys_by_id.get(a.KEY_ID)

if not key:
    raise KeyError

key.set_prop('key', a.NEW_KEY, save=True)
print(f'Key "{a.KEY_ID}" set')
