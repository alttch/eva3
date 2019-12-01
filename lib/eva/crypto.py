import base64
import hashlib
from Crypto.Cipher import AES
from Crypto import Random


def _pad_key(key):
    l = len(key)
    if l == 16 or l == 24 or l == 32:
        return key
    elif l < 16:
        return key.ljust(16)
    elif l < 24:
        return key.ljust(24)
    elif l < 32:
        return key.ljust(32)
    else:
        return key[:32]


def encrypt(raw, private_key):
    length = 16 - (len(raw) % 16)
    raw += bytes([length]) * length
    iv = Random.new().read(AES.block_size)
    cipher = AES.new(_pad_key(private_key), AES.MODE_CBC, iv)
    return iv + cipher.encrypt(raw)


def decrypt(enc, private_key):
    iv = enc[:16]
    cipher = AES.new(_pad_key(private_key), AES.MODE_CBC, iv)
    data = cipher.decrypt(enc[16:])
    return data[:-data[-1]]
