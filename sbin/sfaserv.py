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
import eva.notify
import eva.lurp
import eva.api
import eva.tokens
import eva.apikey
import eva.users
import eva.sfa.controller
import eva.logs
import eva.sysapi
import eva.upnp
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
    print("""Usage: sfaserv.py [-d]

 -d                 run in background

for production use sfa-control only to start/stop SFA
""")


product_build = 2021062505

product_code = 'sfa'

eva.core.init()
eva.core.set_product(product_code, product_build)
eva.core.product.name = 'EVA SCADA Final Aggregator'

_fork = False

try:
    optlist, args = getopt.getopt(sys.argv[1:], 'f:dhV')
except:
    usage()
    sys.exit(4)

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

eva.lurp.update_config(cfg)
eva.api.update_config(cfg)
eva.sysapi.update_config(cfg)
eva.upnp.update_config(cfg)
eva.upnp._data.discover_ports = (1912, 1917)

eva.sysapi.cvars_public = True

eva.core.start()
eva.core.register_controller(eva.sfa.controller)
eva.core.load_cvars()
eva.core.load_corescripts()

eva.apikey.init()
eva.apikey.load()

eva.users.init()
eva.users.update_config(cfg)

eva.notify.mqtt_global_topics += ['lvar', 'lmacro', 'lcycle']

eva.notify.init()
eva.notify.load()
eva.notify.start()

eva.sfa.controller.init()
eva.sfa.controller.update_config(cfg)
eva.sfa.controller.load_remote_ucs()
eva.sfa.controller.load_remote_lms()

eva.api.init()
eva.sysapi.start()
eva.wsapi.start()
eva.lurp.start()
eva.upnp.start()
import eva.sfa.sfapi
eva.sfa.sfapi.start()

eva.sfa.controller.start()

eva.users.start()
eva.tokens.start()
eva.api.start()

eva.core.block()
