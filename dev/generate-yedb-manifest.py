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

ap.add_argument('version')
ap.add_argument('out')

a = ap.parse_args()

content = {}
priv_key = open(f'{dir_eva}/.keys/private.key', 'rb').read()
for arch in ['arm-musleabihf', 'i686-musl', 'x86_64-musl']:
    f = f'yedb-{a.version}-{arch}.tar.gz'
    with open(f'/tmp/{f}', 'rb') as fh:
        c = fh.read()
    s = hashlib.sha256()
    s.update(c)
    signature = eva.crypto.sign(c, priv_key)
    eva.crypto.verify_signature(c, signature)
    content[f] = dict(size=len(c),
                      sha256=s.hexdigest(),
                      signature=signature)

with open(a.out, 'w') as fh:
    fh.write(
        json.dumps({
            'version': a.version,
            'content': content
        }))
