import sys
import getopt
import eva.core
import eva.notify
import eva.api
import eva.apikey
import eva.sfa.controller
import eva.sfa.sfapi
import eva.logs

import eva.runner
import eva.sysapi
import eva.wsapi


def usage():
    print()
    print('%s version %s build %s ' % \
            (   
                eva.core.product_name,
                eva.core.version,
                eva.core.product_build
            )   
        )   
    print ("""
Usage: sfaserv.py [-f config_file ] [-d]

 -f config_file     start with an alternative config file
 -d                 run in background

for production use sfa-control only to start/stop SFA
""")


product_build = 20170629

product_code = 'sfa'

eva.core.init()
eva.core.set_product(product_code, product_build)
eva.core.product_name = 'EVA SCADA Final Aggregator'

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

eva.api.update_config(cfg)
eva.sysapi.update_config(cfg)

eva.core.load_cvars()

eva.apikey.allows = [ 'cmd', 'dm_rules' ]
eva.apikey.load()

eva.notify.init()
eva.notify.load()
eva.notify.start()

eva.sfa.controller.init()
eva.sfa.controller.load_remote_ucs()
eva.sfa.controller.load_remote_lms()

eva.sysapi.start()
eva.wsapi.start()
eva.sfa.sfapi.start()

eva.sfa.controller.start()

eva.api.start()

eva.core.block()
