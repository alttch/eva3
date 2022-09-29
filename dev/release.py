#!/usr/bin/env python3

import argparse
import os
import hashlib
import requests
import sys
import json
import random

dir_eva = os.path.dirname(os.path.abspath(__file__)) + '/..'

sys.path.insert(0, dir_eva + '/lib')

import eva.crypto

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

fname_manifest = '/tmp/manifest-{}.json'.format(random.randint(1, 1000000))
content = {}
priv_key = open(f'{dir_eva}/.keys/private.key', 'rb').read()
for f in [f'eva-{a.version}-{a.build}.tgz', f'update-{a.build}.sh']:
    uri = f'https://pub.bma.ai/eva3/{a.version}/nightly/{f}'
    r = requests.get(uri)
    if not r.ok:
        raise RuntimeError(f'http response: {r.status_code} for {uri}')
    s = hashlib.sha256()
    s.update(r.content)
    signature = eva.crypto.sign(r.content, priv_key)
    eva.crypto.verify_signature(r.content, signature)
    content[f] = dict(size=len(r.content),
                      sha256=s.hexdigest(),
                      signature=signature)

try:
    with open(fname_manifest, 'w') as fh:
        fh.write(
            json.dumps({
                'version': a.version,
                'build': a.build,
                'content': content
            }))
    gsutil(f'cp -a public-read {fname_manifest}'
           f' gs://pub.bma.ai/eva3/{a.version}/nightly/manifest-{a.build}.json')
finally:
    try:
        os.unlink(fname_manifest)
    except FileNotFoundError:
        pass

if not a.test:
    gsutil(
        f'cp -a public-read '
        f'gs://pub.bma.ai/eva3/{a.version}/nightly/eva-{a.version}-{a.build}.tgz'
        f' gs://pub.bma.ai/eva3/{a.version}/stable/eva-{a.version}-{a.build}.tgz'
    )

    fname = '/tmp/update{}.sh'.format(random.randint(1, 1000000))
    gsutil(f'cp '
           f'gs://pub.bma.ai/eva3/{a.version}/nightly/update-{a.build}.sh '
           f' {fname}')
    gsutil(f'-h "Cache-Control:no-cache" cp -a public-read '
           f'{fname} '
           f' gs://pub.bma.ai/eva3/{a.version}/stable/update.sh')
    os.unlink(fname)

    gsutil(f'cp -a public-read '
           f'gs://pub.bma.ai/eva3/{a.version}/nightly/CHANGELOG.html'
           f' gs://pub.bma.ai/eva3/{a.version}/stable/CHANGELOG.html')

    gsutil(f'-h "Content-Type:text/x-rst" cp -a public-read '
           f'gs://pub.bma.ai/eva3/{a.version}/nightly/UPDATE.rst '
           f'gs://pub.bma.ai/eva3/{a.version}/stable/UPDATE.rst')

    gsutil(
        f'cp -a public-read '
        f'gs://pub.bma.ai/eva3/{a.version}/nightly/manifest-{a.build}.json'
        f' gs://pub.bma.ai/eva3/{a.version}/stable/manifest-{a.build}.json'
    )

if a.update_info or a.test:
    fname = '/tmp/update_info_{}.json'.format(random.randint(1, 1000000))
    try:
        ftarget = 'update_info{}.json'.format('_test' if a.test else '')
        with open(fname, 'w') as fh:
            fh.write(json.dumps({
                'version': a.version,
                'build': a.build,
            }))
        gsutil(f'-h "Cache-Control:no-cache" cp -a public-read '
               f'{fname} gs://pub.bma.ai/eva3/{ftarget}')
    finally:
        try:
            os.unlink(fname)
        except FileNotFoundError:
            pass
