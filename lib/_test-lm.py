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

eva.apikey.allows = [ 'cmd', 'dm_rules' ]
eva.apikey.load()

print(eva.apikey.check('flagtest', pvt_dir = 'd5/dd'))
