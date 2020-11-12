#!/usr/bin/env python3

import argparse
import os

ap = argparse.ArgumentParser()


def gsutil(params):
    cmd = f'gsutil -m {params}'
    print(cmd)
    if os.system(cmd):
        raise RuntimeError


ap.add_argument('version')
ap.add_argument('build')
ap.add_argument('--test',
                help='Update update_info.json for test only',
                action='store_true')
ap.add_argument('-u',
                '--update-info',
                help='Update update_info',
                action='store_true')

a = ap.parse_args()

import random
if not a.test:

    gsutil(
        f'cp -a public-read '
        f'gs://get.eva-ics.com/{a.version}/nightly/eva-{a.version}-{a.build}.tgz'
        f' gs://get.eva-ics.com/{a.version}/stable/eva-{a.version}-{a.build}.tgz'
    )

    fname = '/tmp/update{}.sh'.format(random.randint(1, 1000000))
    gsutil(f'cp '
           f'gs://get.eva-ics.com/{a.version}/nightly/update-{a.build}.sh '
           f' {fname}')
    gsutil(f'-h "Cache-Control:no-cache" cp -a public-read '
           f'{fname} '
           f' gs://get.eva-ics.com/{a.version}/stable/update.sh')
    os.unlink(fname)

    gsutil(f'cp -a public-read '
           f'gs://get.eva-ics.com/{a.version}/nightly/CHANGELOG.html'
           f' gs://get.eva-ics.com/{a.version}/stable/CHANGELOG.html')

    gsutil(f'-h "Content-Type:text/x-rst" cp -a public-read '
           f'gs://get.eva-ics.com/{a.version}/nightly/UPDATE.rst '
           f'gs://get.eva-ics.com/{a.version}/stable/UPDATE.rst')

if a.update_info or a.test:
    import json
    fname = '/tmp/update_info_{}.json'.format(random.randint(1, 1000000))
    ftarget = 'update_info{}.json'.format('_test' if a.test else '')
    with open(fname, 'w') as fh:
        fh.write(json.dumps({'version': a.version, 'build': a.build}))
    gsutil(f'-h "Cache-Control:no-cache" cp -a public-read '
           f'{fname} gs://get.eva-ics.com/{ftarget}')
    os.unlink(fname)
