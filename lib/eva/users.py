__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.1.2"

import hashlib
import eva.core
import logging
import sqlalchemy as sa

from eva import apikey
from eva.core import userdb

from sqlalchemy import text as sql


def crypt_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def authenticate(user=None, password=None):
    if user is None or password is None:
        return None
    dbconn = userdb()
    try:
        r = dbconn.execute(
            sql('select k from users where u = :u and p = :p'),
            u=user,
            p=crypt_password(password)).fetchone()
        return None if not r else r.k
    except:
        logging.critical('db error')
        eva.core.log_traceback()
        return None
    return None


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
        eva.core.log_traceback()
        return []


def create_user(user=None, password=None, key=None):
    if user is None or password is None or key is None or \
            key not in apikey.keys_by_id:
        return False
    try:
        dbconn = userdb()
        row = dbconn.execute(
            sql('select k from users where u = :u'), u=user).fetchone()
        if row:
            logging.error('Can not create user {} - already exist'.format(user))
            return False
    except:
        logging.critical('db error')
        eva.core.log_traceback()
        return False
    try:
        dbconn.execute(
            sql('insert into users(u, p, k) values (:u, :p, :k)'),
            u=user,
            p=crypt_password(password),
            k=key)
        logging.info('User {} created, key: {}'.format(user, key))
        return True
    except:
        logging.critical('db error')
        eva.core.log_traceback()


def set_user_password(user=None, password=None):
    if user is None or password is None:
        return
    try:
        dbconn = userdb()
        if dbconn.execute(
                sql('update users set p = :p where u = :u'),
                p=crypt_password(password),
                u=user).rowcount:
            logging.info('user {} new password is set'.format(user))
            return True
        else:
            logging.error(
                'can not change password for {} - no such user'.format(user))
            return False
    except:
        logging.critical('db error')
        eva.core.log_traceback()
        return False


def set_user_key(user=None, key=None):
    if user is None or key is None or key not in apikey.keys_by_id:
        return
    try:
        dbconn = userdb()
        if dbconn.execute(
                sql('update users set k = :k where u = :u'), k=key,
                u=user).rowcount:
            logging.info('user {} key {} is set'.format(user, key))
            return True
        else:
            logging.error('can not set key for {} - no such user'.format(user))
            return False
    except:
        logging.critical('db error')
        eva.core.log_traceback()
        return False


def destroy_user(user=None):
    if user is None:
        return
    try:
        dbconn = userdb()
        if dbconn.execute(
                sql('delete from users where u = :u'), u=user).rowcount:
            logging.info('User {} deleted'.format(user))
            return True
        else:
            logging.error('Can not delete {} - no such user'.format(user))
            return False
    except:
        logging.critical('db error')
        eva.core.log_traceback()
        return False


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
        logging.critical('unable to create apikeys table in db')
