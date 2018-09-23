__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "3.1.1"

import hashlib
import eva.core
import logging

from eva import apikey


def crypt_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def authenticate(user=None, password=None):
    if user is None or password is None:
        return None
    db = eva.core.get_user_db()
    c = db.cursor()
    try:
        c.execute('select k from users where u = ? and p = ?',
                  (user, crypt_password(password)))
        row = c.fetchone()
        db.commit()
        c.close()
        db.close()
        return None if not row else row[0]
    except:
        logging.critical('db error')
        eva.core.log_traceback()
        return None
    return None


def create_user_table():
    try:
        db = eva.core.get_user_db()
        c = db.cursor()
        c.execute('create table users(u primary key, p, k)')
        db.commit()
        c.close()
    except:
        logging.critical('unable to create state table in db')
    db.close()


def list_users():
    try:
        db = eva.core.get_user_db()
        c = db.cursor()
        result = []
        for row in c.execute('select u, k from users order by u'):
            u = {}
            u['user'] = row[0]
            u['key'] = row[1]
            result.append(u)
        db.commit()
        c.close()
        db.close()
        return sorted(result, key=lambda k: k['user'])
    except:
        return []


def create_user(user=None, password=None, key=None, create=True):
    if user is None or password is None or key is None or \
            key not in apikey.keys_by_id:
        return False
    try:
        db = eva.core.get_user_db()
        c = db.cursor()
        c.execute('select k from users where u = ?', (user,))
        row = c.fetchone()
        db.commit()
        c.close()
        db.close()
        if row:
            logging.info('Can not create user %s - already exist' % (user))
            return False
    except:
        if not create:
            logging.critical('db error')
            eva.core.log_traceback()
            return False
        else:
            logging.info('No user table in db, creating new')
            create_user_table()
            create_user(user=user, create=False)
    try:
        db = eva.core.get_user_db()
        c = db.cursor()
        c.execute('insert into users(u, p, k) values (?, ?, ?)',
                  (user, crypt_password(password), key))
        db.commit()
        c.close()
        db.close()
        logging.info('User %s created, key: %s' % (user, key))
        return True
    except:
        logging.critical('db error')
        eva.core.log_traceback()


def set_user_password(user=None, password=None):
    if user is None or password is None:
        return
    try:
        db = eva.core.get_user_db()
        c = db.cursor()
        c.execute('select k from users where u = ?', (user,))
        row = c.fetchone()
        db.commit()
        c.close()
        if not row:
            logging.info('Can not change password for %s - no such user' % \
                    (user))
            return False
        c = db.cursor()
        c.execute('update users set p = ? where u = ?',
                  (crypt_password(password), user))
        db.commit()
        c.close()
        db.close()
        logging.info('User %s new password set' % (user))
        return True
    except:
        logging.critical('db error')
        eva.core.log_traceback()


def set_user_key(user=None, key=None):
    if user is None or key is None or key not in apikey.keys_by_id:
        return
    try:
        db = eva.core.get_user_db()
        c = db.cursor()
        c.execute('select k from users where u = ?', (user,))
        row = c.fetchone()
        db.commit()
        c.close()
        if not row:
            logging.info('Can not change key for %s - no such user' % \
                    (user))
            return False
        c = db.cursor()
        c.execute('update users set k = ? where u = ?', (key, user))
        db.commit()
        c.close()
        db.close()
        logging.info('User %s key %s set' % (user, key))
        return True
    except:
        logging.critical('db error')
        eva.core.log_traceback()


def destroy_user(user=None):
    if user is None:
        return
    try:
        db = eva.core.get_user_db()
        c = db.cursor()
        c.execute('select k from users where u = ?', (user,))
        row = c.fetchone()
        db.commit()
        c.close()
        if not row:
            logging.info('Can not delete %s - no such user' % \
                    (user))
            return False
        c = db.cursor()
        c.execute('delete from users where u = ?', (user,))
        db.commit()
        c.close()
        db.close()
        logging.info('User %s deleted' % (user))
        return True
    except:
        logging.critical('db error')
        eva.core.log_traceback()
