import base64
import hashlib
from Crypto.Cipher import AES
from Crypto import Random

BLOCK_SIZE = 16


def encrypt(raw, private_key):
    length = 16 - (len(raw) % 16)
    raw += bytes([length]) * length
    iv = Random.new().read(AES.block_size)
    cipher = AES.new(private_key, AES.MODE_CBC, iv)
    return iv + cipher.encrypt(raw)


def decrypt(enc, private_key):
    iv = enc[:16]
    cipher = AES.new(private_key, AES.MODE_CBC, iv)
    data = cipher.decrypt(enc[16:])
    return data[:-data[-1]]
