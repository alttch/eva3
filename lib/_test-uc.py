import sys
import getopt
import eva.core
import eva.traphandler
import eva.udpapi
import eva.notify
import eva.api
import eva.apikey
import eva.uc.controller
import eva.uc.ucapi
import eva.logs
import time

import json 
import jsonpickle

import eva.runner
import eva.sysapi
import eva.wsapi


def usage():
    print ("""
Usage: ucserv.py [-f config_file ] [-d]

 -f config_file - start with an alternative config file
 -d - run in background
""")


product_build = 20170629

product_code = 'uc'

eva.core.init()
eva.core.set_product(product_code, product_build)
eva.core.product_name = 'EVA Universal Controller'

_fork = False
_eva_ini = None

try:
    optlist, args = getopt.getopt(sys.argv[1:], 'f:d')
except:
    usage()
    sys.exit(4)

for o, a in optlist:
    if o == '-d': _fork = True
    if o == '-f': _eva_ini = a

cfg = eva.core.load(fname = _eva_ini, initial = True)
if not cfg: sys.exit(2)

if _fork: eva.core.fork()
eva.core.write_pid_file()

eva.logs.mute()
eva.logs.start()

eva.traphandler.update_config(cfg)
eva.udpapi.update_config(cfg)
eva.api.update_config(cfg)
eva.sysapi.update_config(cfg)

eva.core.load_cvars()

eva.apikey.allows = [ 'cmd' ]
eva.apikey.load()

eva.notify.init()
eva.notify.load()
eva.notify.start()
eva.uc.controller.init()
eva.uc.controller.load_units()
eva.uc.controller.load_sensors()
eva.uc.controller.load_mu()

eva.sysapi.start()
eva.wsapi.start()
eva.traphandler.start()
eva.udpapi.start()
eva.uc.ucapi.start()

if eva.core.notify_on_start: eva.uc.controller.notify_all()

eva.uc.controller.start()

eva.api.start()

eva.core.block()

