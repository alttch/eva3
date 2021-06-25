__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"

from pyaltt2.console import redirect
redirect()

import sys
import os
import getopt

from pathlib import Path
sys.path.insert(0, (Path(__file__).parent.parent / 'lib').as_posix())

import eva.core
import eva.sysapi
import eva.traphandler
import eva.udpapi
import eva.upnp
import eva.notify
import eva.api
import eva.apikey
import eva.users
import eva.uc.controller
import eva.logs
import eva.uc.modbus
import eva.wsapi
import eva.mailer


def usage(version_only=False):
    if not version_only:
        print()
    print('%s version %s build %s ' % \
            (
                eva.core.product.name,
                eva.core.version,
                eva.core.product.build
            )
        )
    if version_only:
        return
    print("""Usage: ucserv.py [-d]

 -d                 run in background

for production use eva-control only to start/stop UC
""")


product_build = 2021062505

product_code = 'uc'

eva.core.init()

eva.core.set_product(product_code, product_build)
eva.core.product.name = 'EVA Universal Controller'

eva.core._flags.use_reactor = True

_fork = False

try:
    optlist, args = getopt.getopt(sys.argv[1:], 'f:dhV')
except:
    usage()
    sys.exit(99)

for o, a in optlist:
    if o == '-d':
        _fork = True
    if o == '-V':
        usage(version_only=True)
        sys.exit()
    if o == '-h':
        usage()
        sys.exit()

cfg = eva.core.load(initial=True)
if not cfg:
    sys.exit(2)

if _fork:
    eva.core.fork()
eva.core.write_pid_file()

eva.core.start_supervisor()
eva.logs.start()

eva.mailer.load()

eva.traphandler.update_config(cfg)
eva.udpapi.update_config(cfg)
eva.api.update_config(cfg)
eva.upnp.update_config(cfg)
eva.upnp.port = 1912
eva.sysapi.update_config(cfg)
eva.uc.modbus.update_config(cfg)
eva.datapuller.update_config(cfg)

eva.core.start()
eva.core.register_controller(eva.uc.controller)
eva.core.load_cvars()
eva.core.load_corescripts()

eva.apikey.init()
eva.apikey.load()

eva.users.init()
eva.users.update_config(cfg)

eva.notify.init()
eva.notify.load()
eva.notify.start()

eva.uc.controller.init()
eva.uc.controller.load_drivers()
eva.uc.controller.load_units()
eva.uc.controller.load_sensors()
eva.uc.controller.load_mu()

eva.api.init()
eva.sysapi.start()
eva.wsapi.start()
eva.traphandler.start()
eva.udpapi.start()
eva.upnp.start()
import eva.uc.ucapi
eva.uc.ucapi.start()
eva.uc.controller.start()

if eva.core.config.notify_on_start:
    eva.uc.controller.notify_all()

eva.users.start()
eva.tokens.start()
eva.api.start()
eva.core.block()
