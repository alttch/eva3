__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.6"

import sys
import os
import getopt

from pathlib import Path
sys.path.insert(0, (Path(__file__).absolute().parents[1] / 'lib').as_posix())

os.environ['EVA_DIR'] = Path(__file__).absolute().parents[1].as_posix()

import eva.core
import eva.notify
import eva.traphandler


def usage(version_only=False):
    if not version_only: print()
    print('%s version %s build %s ' % \
            (
                'EVA Layout Converter',
                eva.core.version,
                eva.core.product.build
            )
        )
    if version_only: return
    print("""Usage: layout-converter <uc|lm>

This tool converts simple item layout to enterprise.

Specify "uc" for Universal Controller or "lm" for Logic Manager PLC.
""")


product_build = -1

try:
    p = sys.argv[1]
    if p not in ['uc', 'lm']: raise Exception('wrong product selected')
except:
    usage()
    sys.exit(99)

product_code = p

eva.core.init()
eva.core.set_product(product_code, product_build)
eva.core.product.name = 'Layout Converter'

cfg = eva.core.load(initial=True, init_log=False)
if not cfg: sys.exit(2)

if eva.core.config.enterprise_layout:
    print('\nComponent already has enterprise layout set. Operation aborted')
    sys.exit(3)

print("""
Warning! This action can not be undone. Once enterprise layout is set,
conversion back to simple is not possible. Also make sure you've back up the
whole runtime folder.

""")

v = input('Type CONVERT (uppercase) to continue, Ctrl+C to abort: ')

if v != 'CONVERT':
    print('Operation aborted')
    sys.exit(4)

eva.core.start()

eva.notify.init()
eva.notify.load()

if p == 'uc':
    import eva.uc.controller
    eva.uc.controller.init()
    eva.uc.controller.load_units()
    eva.uc.controller.load_sensors()
    eva.uc.controller.load_mu()
    controller = eva.uc.controller
elif p == 'lm':
    import eva.lm.controller
    eva.lm.controller.init()
    eva.lm.controller.load_lvars()
    controller = eva.lm.controller

if not controller:
    eva.core.shutdown()
    raise Exception('No controller loaded')

print()

oc = []

for k, i in controller.items_by_id.items():
    oc.append(i.get_fname())
    i.config_changed = True

print("""
Now change layout to enterprise in etc/{}.ini""".format(p))

input('Press <ENTER> to continue...')

cfg = eva.core.load(initial=True, init_log=False)

if not eva.core.config.enterprise_layout:
    eva.core.shutdown()
    print('Layout is set to "simple". Operation aborted')
    sys.exit(4)

print("""
Starting layout conversion.
DON'T POWER OFF THE MACHINE, DON'T STOP THE PROGRAM, DON'T DISCONNECT!
""")

print('Removing old configuration files')
for o in oc:
    os.unlink(o)
    print('- ' + o)

if not controller.save():
    eva.core.shutdown()
    sys.exit(6)

eva.core.shutdown()
print()
print('Operation completed')
