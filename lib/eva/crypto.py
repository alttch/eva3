import pyaltt2.crypto
import os

from functools import partial

encrypt = partial(pyaltt2.crypto.encrypt, hmac_key=True, b64=False)
decrypt = partial(pyaltt2.crypto.decrypt, hmac_key=True, b64=False)

with open(
        os.path.abspath(os.path.dirname(__file__)) + '/../eva/keys/eva.pub',
        'rb') as fh:
    eva_public_key = fh.read()


def sign(content, private_key, key_password=None):
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.backends import default_backend
    import hashlib
    import base64

    if not isinstance(content, bytes):
        content = str(content).encode()
    if not isinstance(private_key, bytes):
        private_key = str(private_key).encode()

    privkey = serialization.load_pem_private_key(private_key,
                                                 password=key_password,
                                                 backend=default_backend())

    prehashed = hashlib.sha256(content).digest()

    sig = privkey.sign(
        prehashed,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())

    return base64.b64encode(sig).decode()


def verify_signature(content, signature, public_key=None):
    import hashlib
    import base64
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.backends import default_backend

    if not isinstance(content, bytes):
        content = str(content).encode()
    if public_key is None:
        public_key = eva_public_key
    elif not isinstance(public_key, bytes):
        public_key = str(public_key).encode()

    pubkey = serialization.load_pem_public_key(public_key,
                                               backend=default_backend())
    prehashed_msg = hashlib.sha256(content).digest()
    decoded_sig = base64.b64decode(signature)
    pubkey.verify(
        decoded_sig, prehashed_msg,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
    return True


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
