__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.6"

import sys
import os
import getopt
import sqlalchemy

dir_lib = os.path.dirname(os.path.realpath(__file__)) + '/../lib'
sys.path.append(dir_lib)

os.environ['EVA_DIR'] = os.path.normpath(
    os.path.dirname(os.path.realpath(__file__)) + '/..')

import eva.core
import eva.notify
import eva.traphandler


def usage(version_only=False):
    if not version_only: print()
    print('%s version %s build %s ' % \
            (
                'EVA table update',
                eva.core.version,
                eva.core.product.build
            )
        )
    if version_only: return
    print("""Usage: update-tables <uc|lm>

Updates EVA ICS database tables.

Specify uc|lm|sfa
""")


def append_db_column(table, column, coltype, dbconn):
    print('{} -> {}: '.format(table, column), end='')
    try:
        dbconn.execute('alter table {} add {} {}'.format(
            table, column, coltype))
        print('OK')
    except sqlalchemy.exc.OperationalError as e:
        if str(e).lower().find('duplicate') == -1:
            raise
        print('Already exists')


product_build = -1

try:
    p = sys.argv[1]
    if p not in ['uc', 'lm', 'sfa']: raise Exception('wrong product selected')
except:
    usage()
    sys.exit(99)

product_code = p

eva.core.init()
eva.core.set_product(product_code, product_build)
eva.core.product.name = 'table update'

cfg = eva.core.load(initial=True, init_log=False)
if not cfg: sys.exit(2)
eva.core.start()
dbconn = eva.core.userdb()

print('Creating missing table columns')

append_db_column('apikeys', 'i_ro', 'VARCHAR(1024)', dbconn)
append_db_column('apikeys', 'g_ro', 'VARCHAR(1024)', dbconn)

dbconn.execute('update apikeys set i_ro = "" where i_ro is null')
dbconn.execute('update apikeys set g_ro = "" where g_ro is null')

eva.core.shutdown()
print()
print('Operation completed')
