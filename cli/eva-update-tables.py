__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"

import sys
import os
import sqlalchemy

from pathlib import Path
sys.path.insert(0, (Path(__file__).absolute().parents[1] / 'lib').as_posix())

os.environ['EVA_DIR'] = Path(__file__).absolute().parents[1].as_posix()

import eva.core


def usage(version_only=False):
    if not version_only:
        print()
    print('%s version %s build %s ' % \
            (
                'EVA table update',
                eva.core.version,
                eva.core.product.build
            )
        )
    if version_only:
        return
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
        exc = str(e).lower()
        if 'duplicate' in exc:
            print('Already exists')
        elif 'no such table' in exc:
            print('table not present')
        else:
            raise


product_build = -1

try:
    p = sys.argv[1]
    if p not in ['uc', 'lm', 'sfa']:
        raise Exception('wrong product selected')
except:
    usage()
    sys.exit(99)

product_code = p

eva.core.init()
eva.core.set_product(product_code, product_build)
eva.core.product.name = 'table update'

cfg = eva.core.load(initial=True, init_log=False, omit_plugins=True)
if not cfg:
    sys.exit(2)
eva.core.start()
dbconn = eva.core.userdb()

print('Creating missing table columns')

append_db_column('apikeys', 'i_ro', 'VARCHAR(8192)', dbconn)
append_db_column('apikeys', 'g_ro', 'VARCHAR(8192)', dbconn)
append_db_column('apikeys', 'i_deny', 'VARCHAR(8192)', dbconn)
append_db_column('apikeys', 'g_deny', 'VARCHAR(8192)', dbconn)
append_db_column('apikeys', 'cdata', 'VARCHAR(16384)', dbconn)

if product_code == 'uc':
    append_db_column('state', 'set_time', 'NUMERIC(20,8)', dbconn)

if product_code in ['uc', 'lm']:
    tbl = 'state' if product_code == 'uc' else 'lvar_state'
    append_db_column(tbl, 'ieid_b', 'NUMERIC(38,0)', dbconn)
    append_db_column(tbl, 'ieid_i', 'NUMERIC(38,0)', dbconn)

try:
    dbconn.execute('update apikeys set i_ro = "" where i_ro is null')
    dbconn.execute('update apikeys set g_ro = "" where g_ro is null')
    dbconn.execute('update apikeys set i_deny = "" where i_deny is null')
    dbconn.execute('update apikeys set g_deny = "" where g_deny is null')
    dbconn.execute('update apikeys set cdata = "" where cdata is null')
except sqlalchemy.exc.OperationalError as e:
    exc = str(e).lower()
    if 'no such table' in exc:
        print('table not present')
    else:
        raise

eva.core.shutdown()
print()
print('Operation completed')
