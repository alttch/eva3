import logging
import sys
import eva
from eva.uc.unit import Unit
from eva import apikey

import eva.notify

import json 
import jsonpickle

from eva.tools import print_json

eva.product_code = 'uc'
eva.product_build = 20170629

eva.load()

apikey.allows = [ 'cmd' ]
apikey.load()

if not eva.load(initial = True): sys.exit(2)

eva.load_cvars()

            
u = Unit('LAMP2')
u.group = 'hall/lamps'
u.description = 'lamp 2'

u.status = 1
u.nstatus = 1

eva.notify.load()

# n = eva.notify.MQTTNotifier('local', 'localhost', space = 'lab',
        # username='eva', password='test', keepalive=10, qos= {'status' : 1,
        # 'log': 1})

data = u

print(u.serialize(config = True))

# sys.exit(0)

# print (data.serialize())

# n.subscribe('status', '*', '*', '*')
# n.subscribe('log', log_level = 10)

# eva.notify.notifiers['local'] = n
# print(eva.notify.notifiers['local'].test())

eva.notify.notify('status', data, notifier_id='local')
# eva.notify.notify_all()


# print(n.serialize())

# eva.notify.notify('status', data )

# eva.notify.notify('status', [ data, data, data ] )

# data = {
        # 'msg': 'test test',
        # 'level': 30
        # }

# eva.notify.notify('log', [ data, data ] )
# eva.notify.notify('log', [ data, data, data ], notifier_id = 'local')

print_json(eva.notify.serialize())

# eva.notify.save()
import time
time.sleep(1)
