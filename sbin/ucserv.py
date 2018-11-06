__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "3.1.2"

import sys
import os
import getopt

dir_lib = os.path.dirname(os.path.realpath(__file__)) + '/../lib'
sys.path.append(dir_lib)

import eva.sysapi
import eva.core
import eva.traphandler
import eva.udpapi
import eva.notify
import eva.api
import eva.apikey
import eva.uc.controller
import eva.uc.ucapi
import eva.logs

import eva.runner
import eva.wsapi


def usage(version_only=False):
    if not version_only: print()
    print('%s version %s build %s ' % \
            (
                eva.core.product_name,
                eva.core.version,
                eva.core.product_build
            )
        )
    if version_only: return
    print("""Usage: ucserv.py [-f config_file ] [-d]

 -f config_file     start with an alternative config file
 -d                 run in background

for production use uc-control only to start/stop UC
""")


product_build = 2018110701

product_code = 'uc'

eva.core.init()
eva.core.set_product(product_code, product_build)
eva.core.product_name = 'EVA Universal Controller'

_fork = False
_eva_ini = None

try:
    optlist, args = getopt.getopt(sys.argv[1:], 'f:dhV')
except:
    usage()
    sys.exit(99)

for o, a in optlist:
    if o == '-d': _fork = True
    if o == '-f': _eva_ini = a
    if o == '-V':
        usage(version_only=True)
        sys.exit()
    if o == '-h':
        usage()
        sys.exit()

cfg = eva.core.load(fname=_eva_ini, initial=True)
if not cfg: sys.exit(2)

if _fork: eva.core.fork()
eva.core.write_pid_file()

eva.logs.start()

eva.traphandler.update_config(cfg)
eva.udpapi.update_config(cfg)
eva.api.update_config(cfg)
eva.sysapi.update_config(cfg)

eva.core.load_cvars()

eva.apikey.allows = ['cmd', 'lock', 'device']
eva.apikey.init()
eva.apikey.load()

eva.notify.init()
eva.notify.load()
eva.notify.start()
eva.uc.controller.init()
eva.uc.controller.load_drivers()
eva.uc.controller.load_units()
eva.uc.controller.load_sensors()
eva.uc.controller.load_mu()

eva.sysapi.start()
eva.wsapi.start()
eva.traphandler.start()
eva.udpapi.start()
eva.uc.ucapi.start()
eva.uc.controller.start()

if eva.core.notify_on_start: eva.uc.controller.notify_all()

eva.api.start()
eva.core.block()
