__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.2"

import hashlib
import eva.core
import logging
import sqlalchemy as sa
import subprocess

from eva import apikey
from eva.core import userdb

from sqlalchemy import text as sql

from eva.exceptions import AccessDenied
from eva.exceptions import ResourceNotFound
from eva.exceptions import FunctionFailed
from eva.exceptions import ResourceAlreadyExists


def crypt_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def authenticate(user=None, password=None):
    if user is None or password is None:
        raise AccessDenied('No login/password provided')
    dbconn = userdb()
    try:
        r = dbconn.execute(
            sql('select k from users where u = :u and p = :p'),
            u=user,
            p=crypt_password(password)).fetchone()
    except:
        eva.core.report_userdb_error()
    if not r:
        raise AccessDenied('Authentication failure')
    return r.k


def list_users():
    try:
        dbconn = userdb()
        result = []
        r = dbconn.execute(sql('select u, k from users order by u'))
        while 1:
            row = r.fetchone()
            if not row: break
            u = {}
            u['user'] = row.u
            u['key'] = row.k
            result.append(u)
        return sorted(result, key=lambda k: k['user'])
    except:
        eva.core.report_userdb_error()


def get_user(user=None):
    if not user: return None
    try:
        dbconn = userdb()
        result = []
        row = dbconn.execute(
            sql('select u, k from users where u=:u'), u=user).fetchone()
    except:
        eva.core.report_userdb_error()
    if not row: raise ResourceNotFound
    return {'user': row.u, 'key': row.k}


def create_user(user=None, password=None, key=None):
    if user is None or password is None or key is None: return False
    if key not in apikey.keys_by_id:
        raise ResourceNotFound('API key')
    try:
        dbconn = userdb()
        row = dbconn.execute(
            sql('select k from users where u = :u'), u=user).fetchone()
    except:
        eva.core.report_userdb_error()
    if row:
        raise ResourceAlreadyExists
    try:
        dbconn.execute(
            sql('insert into users(u, p, k) values (:u, :p, :k)'),
            u=user,
            p=crypt_password(password),
            k=key)
        logging.info('User {} created, key: {}'.format(user, key))
    except:
        eva.core.report_userdb_error()
        return None
    run_hook('create', user, password)
    return {'user': user, 'key': key}


def set_user_password(user=None, password=None):
    if user is None or password is None:
        return None
    try:
        dbconn = userdb()
        if dbconn.execute(
                sql('update users set p = :p where u = :u'),
                p=crypt_password(password),
                u=user).rowcount:
            logging.info('user {} new password is set'.format(user))
        else:
            raise ResourceNotFound
    except ResourceNotFound:
        raise
    except:
        eva.core.report_userdb_error()
        return False
    run_hook('set_password', user, password)
    return True


def set_user_key(user=None, key=None):
    if user is None or key is None or key not in apikey.keys_by_id:
        return None
    try:
        dbconn = userdb()
        if dbconn.execute(
                sql('update users set k = :k where u = :u'), k=key,
                u=user).rowcount:
            logging.info('user {} key {} is set'.format(user, key))
            return True
    except:
        eva.core.report_userdb_error()
    raise ResourceNotFound


def destroy_user(user=None):
    if user is None:
        raise FunctionFailed
    try:
        dbconn = userdb()
        if dbconn.execute(
                sql('delete from users where u = :u'), u=user).rowcount:
            logging.info('User {} deleted'.format(user))
        else:
            raise ResourceNotFound
    except ResourceNotFound:
        raise
    except:
        eva.core.report_userdb_error()
        return False
    run_hook('destroy', user)
    return True


def init():
    dbconn = userdb()
    meta = sa.MetaData()
    t_users = sa.Table('users', meta,
                       sa.Column('u', sa.String(64), primary_key=True),
                       sa.Column('p', sa.String(64)),
                       sa.Column('k', sa.String(64)))
    try:
        meta.create_all(dbconn)
    except:
        eva.core.log_traceback()
        logging.critical('unable to create apikeys table in db')


def run_hook(cmd, u, password=None):
    if not eva.core.config.user_hook:
        return True
    p = subprocess.Popen(
        eva.core.config.user_hook + [cmd, u],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE)
    if password is not None:
        p.stdin.write(password.encode())
    p.communicate()
    exitcode = p.returncode
    if exitcode:
        raise FunctionFailed('user hook exited with code {}'.format(exitcode))
    return True
