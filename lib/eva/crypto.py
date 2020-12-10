import pyaltt2.crypto
import os

from functools import partial

encrypt = partial(pyaltt2.crypto.encrypt, hmac_key=True, b64=False)
decrypt = partial(pyaltt2.crypto.decrypt, hmac_key=True, b64=False)
sign = pyaltt2.crypto.sign
verify_signature = pyaltt2.crypto.verify_signature

with open(
        os.path.abspath(os.path.dirname(__file__)) + '/keys/eva.pub',
        'rb') as fh:
    eva_public_key = fh.read()
    pyaltt2.crypto.default_public_key = eva_public_key


def safe_download(url, manifest=None, public_key=None, **kwargs):
    import requests
    r = requests.get(url, **kwargs)
    if not r.ok:
        raise RuntimeError(f'HTTP error {r.status_code} for {url}')
    if isinstance(manifest, str):
        r_m = requests.get(manifest, **kwargs)
        if not r_m.ok:
            raise RuntimeError(f'HTTP error {r.status_code} for {manifest}')
        manifest = r_m.json()
    if manifest:
        try:
            data = manifest['content'][url.rsplit('/', 1)[-1]]
            size = data['size']
            sha256 = data['sha256']
            signature = data['signature']
        except KeyError:
            raise RuntimeError(f'Info for {url} not found in manifest')
        if len(r.content) != size:
            raise RuntimeError(f'Size check error for {url}')
        import hashlib
        if hashlib.sha256(r.content).hexdigest() != sha256:
            raise RuntimeError(f'Checksum error for {url}')
        try:
            verify_signature(r.content, signature, public_key)
        except:
            raise RuntimeError(f'Signature error for {url}')
    return r.content
