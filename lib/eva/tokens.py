import time
import logging
import eva.core
from eva.tools import gen_random_str
from functools import wraps
from neotasker import background_worker
"""
token (dict) fields:
    u: user login
    utp: user type
    ki: API key ID
    t: token creation or refresh time
    m: token mode (NORMAL, RO)
"""

TOKEN_MODE_NORMAL = 1
TOKEN_MODE_RO = 2

TOKEN_MODE_NAMES = {1: 'normal', 2: 'readonly'}

tokens = {}

tokens_lock = eva.core.RLocker('tokens')

expire = 0

prolong_disabled = False


def is_enabled():
    return expire > 0


def need_tokens_enabled(f):

    @wraps(f)
    def do(*args, **kwargs):
        if not is_enabled():
            return False
        return f(*args, **kwargs)

    return do


@need_tokens_enabled
@tokens_lock
def list_tokens():
    result = []
    for token, info in tokens.items():
        data = info.copy()
        data['token'] = token
        result.append(data)
    return sorted(result, key=lambda k: k['u'])


@need_tokens_enabled
@tokens_lock
def append_token(key_id, user=None, utp=None):
    i = 0
    while True:
        token = 'token:' + gen_random_str()
        if token not in tokens:
            break
        i += 1
        if i > 3:
            return False
    tokens[token] = {
        'u': user,
        'ki': key_id,
        'utp': utp,
        't': time.time(),
        'm': TOKEN_MODE_NORMAL
    }
    logging.debug('{} added. user: {}, key id: {}'.format(
        token[:12], user, key_id))
    return token


@need_tokens_enabled
@tokens_lock
def remove_token(token=None, user=None, key_id=None):
    try:
        if token:
            t = tokens[token]
            del tokens[token]
            logging.debug('{} removed. user: {}, key id: {}'.format(
                token[:12], t['u'], t['ki']))
        elif user:
            for token in list(tokens):
                if tokens[token]['u'] == user:
                    remove_token(token)
        elif key_id:
            for token in list(tokens):
                if tokens[token]['ki'] == key_id:
                    remove_token(token)
        return True
    except:
        eva.core.log_traceback()
        return False


@need_tokens_enabled
@tokens_lock
def refresh_token(token):
    try:
        if not prolong_disabled:
            tokens[token]['t'] = time.time()
        return True
    except:
        return False


@need_tokens_enabled
@tokens_lock
def get_token_mode(token):
    return tokens[token]['m']


@need_tokens_enabled
@tokens_lock
def set_token_mode(token, mode):
    tokens[token]['m'] = mode


@need_tokens_enabled
@tokens_lock
def get_token(token):
    refresh_token(token)
    return tokens.get(token)


@need_tokens_enabled
@tokens_lock
def is_token_alive(token):
    return token in tokens


@background_worker(delay=60, loop='cleaners', on_error=eva.core.log_traceback)
async def token_cleaner(**kwargs):

    @tokens_lock
    def clean_tokens():
        for token in list(tokens):
            if tokens[token]['t'] + expire < time.time():
                remove_token(token)

    clean_tokens()


def start():
    if is_enabled():
        token_cleaner.start()


@eva.core.stop
def stop():
    if is_enabled():
        token_cleaner.stop()
