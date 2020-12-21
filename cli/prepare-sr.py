#!/usr/bin/env python3

import sys
from pathlib import Path
dir_eva = Path(__file__).absolute().parents[1]
sys.path.insert(0, (dir_eva / 'lib').as_posix())

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

from tqdm import tqdm
from textwrap import dedent

import eva.crypto

pubkey = serialization.load_pem_public_key(eva.crypto.eva_public_key,
                                           backend=default_backend())

import argparse
import neotermcolor

ap = argparse.ArgumentParser()

ap.add_argument('FILE')

a = ap.parse_args()

infile = Path(a.FILE)

if infile.suffix not in ('gz', 'tgz', 'zip',
                         'rar') and infile.stat().st_size > 256000:
    print('Please compress or tail the file < 256K before processing')
    sys.exit(1)

CHSIZE = 900

outfile = Path(Path(a.FILE + '.sr').name)

try:
    with outfile.open('wb') as of:
        with infile.open('rb') as fh:
            pbar = tqdm(total=infile.stat().st_size, unit='b')
            while True:
                buf = fh.read(CHSIZE)
                if buf:
                    ebuf = pubkey.encrypt(
                        buf,
                        padding.OAEP(
                            mgf=padding.MGF1(algorithm=hashes.SHA256()),
                            algorithm=hashes.SHA256(),
                            label=None))
                    of.write(ebuf)
                    pbar.update(CHSIZE)
                else:
                    pbar.close()
                    break
except:
    outfile.unlink()
    raise

print()
print(f'Support request file created: ' +
      neotermcolor.colored(outfile, color='green', attrs='bold'))
print()
print('Please send the above file to your support engineer.')
if pubkey.key_size >= 4096:
    print(
        dedent("""
    The file is encrypted with 8192-bit RSA key, so any public communcation
    channel can be used.
    """))
