import pyaltt2.crypto
import logging

from functools import partial

encrypt = partial(pyaltt2.crypto.encrypt, hmac_key=True, b64=False)
decrypt = partial(pyaltt2.crypto.decrypt, hmac_key=True, b64=False)
