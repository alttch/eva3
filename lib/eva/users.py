__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.1"

import hashlib
import eva.core
import logging
import rapidjson
import sqlalchemy as sa
import subprocess
import time
import dateutil
from datetime import datetime

from eva import apikey
from eva.core import userdb

from sqlalchemy import text as sql

from eva.exceptions import AccessDenied
from eva.exceptions import ResourceNotFound
from eva.exceptions import FunctionFailed
from eva.exceptions import ResourceAlreadyExists

from neotasker import background_worker

from pyaltt2.db import format_condition as format_sql_condition

from eva.tools import SimpleNamespace

from eva.tools import fmt_time

_d = SimpleNamespace(msad=None,
                     msad_ou='EVA',
                     msad_key_prefix='',
                     msad_cache_time=86400)

api_log_clean_delay = 60

msad_cache_clean_delay = 60


def msad_init(host,
              domain,
              ca=None,
              key_prefix=None,
              ou=None,
              cache_time=86400):
    try:
        from easyad import EasyAD
    except:
        logging.error('unable to import easyad module')
        return
    dbconn = userdb()
    meta = sa.MetaData()
    t_users = sa.Table(
        'msad_cache',
        meta,
        sa.Column('u', sa.String(64), primary_key=True),
        sa.Column('p', sa.String(64)),
        sa.Column('cn', sa.String(2048)),
        sa.Column('t', sa.Numeric(20, 8)),
    )
    try:
        meta.create_all(dbconn)
    except:
        eva.core.log_traceback()
        logging.critical('unable to create msad_cache table in db')
    ad_config = dict(AD_SERVER=host, AD_DOMAIN=domain, CA_CERT_FILE=ca)
    _d.msad = EasyAD(ad_config)
    _d.msad_key_prefix = key_prefix if key_prefix else ''
    _d.msad_cache_time = cache_time
    if ou is not None:
        _d.msad_ou = ou
    try:
        dbconn.close()
    except:
        pass


def msad_cache_credentials(username, password, cn):
    if _d.msad_cache_time <= 0:
        return
    dbconn = userdb()
    dbt = dbconn.begin()
    params = {
        'u': username,
        'p': crypt_password(password),
        'cn': cn,
        't': time.time()
    }
    try:
        if dbconn.execute(
                sql('update msad_cache set p=:p, cn=:cn, t=:t where u=:u'), **
                params).rowcount < 1:
            dbconn.execute(
                sql('insert into msad_cache(u, p, cn, t) '
                    'values (:u, :p, :cn, :t)'), **params)
        dbt.commit()
        logging.debug(f'MSAD credentials for {username} cached')
    except:
        dbt.rollback()
        raise


def msad_get_cached_credentials(username, password):
    if _d.msad_cache_time <= 0:
        return
    logging.debug(f'getting cached credentials for {username}')
    r = userdb().execute(
        sql('select cn from msad_cache where u=:u and p=:p and t>=:t'),
        u=username,
        p=crypt_password(password),
        t=time.time() - _d.msad_cache_time).fetchone()
    return r.cn if r else None


def msad_authenticate(username, password):
    try:
        if not _d.msad:
            return None

        try:
            user = _d.msad.authenticate_user(username, password, json_safe=True)
        except Exception as e:
            logging.warning(f'Unable to access active directory: {e}')
            eva.core.log_traceback()
            result = msad_get_cached_credentials(username, password)
            if result:
                d = []
                for r in result.split(','):
                    d.append(_d.msad_key_prefix + r)
                return d
            else:
                return None

        if not user:
            logging.warning(f'user {username} active directory access denied')
            return None

        result = []

        for grp in _d.msad.get_all_user_groups(user=user,
                                               credentials=dict(
                                                   username=username,
                                                   password=password)):
            cn = None
            ou = None
            for el in grp.split(','):
                try:
                    name, value = el.split('=')
                    if name == 'CN':
                        cn = value
                    elif name == 'OU':
                        ou = value
                    if cn and ou:
                        break
                except:
                    pass
            if ou == _d.msad_ou and cn:
                result.append(cn)

        if not result:
            return None
        # elif len(result) > 1:
        # raise RuntimeError(
        # f'User {username} has more than one {_d.msad_ou} '
        # f'OU group assigned: {", ".join(result)}')
        msad_cache_credentials(username, password, ','.join(result))
        d = []
        for r in result:
            d.append(_d.msad_key_prefix + r)
        return d
    except Exception as e:
        logging.error(f'Unable to authenticate via active directory: {e}')
        eva.core.log_traceback()
    return None


def crypt_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def authenticate(user=None, password=None):

    def _format_key(key):
        try:
            if isinstance(key, list):
                kk = key
            else:
                kk = key.split(',')
            if len(kk) == 1:
                return kk[0]
            else:
                return apikey.create_combined_key(kk)
        except Exception as e:
            logging.error(e)
            raise

    if user is None or password is None:
        raise AccessDenied('No login/password provided')
    dbconn = userdb()
    try:
        r = dbconn.execute(sql('select k from users where u = :u and p = :p'),
                           u=user,
                           p=crypt_password(password)).fetchone()
    except:
        eva.core.report_userdb_error()
    if r:
        return _format_key(r.k), None
    else:
        k = msad_authenticate(user, password)
        if k is None:
            raise AccessDenied('Authentication failure')
        else:
            logging.debug(
                f'user {user} authenticated via active directory, key id: {k}')
            return _format_key(k), 'msad'


def api_log_insert(call_id,
                   gw=None,
                   ip=None,
                   auth=None,
                   u=None,
                   utp=None,
                   ki=None,
                   func=None,
                   params=None):
    dbconn = userdb()
    dbt = dbconn.begin()
    try:
        dbconn.execute(sql(
            'insert into api_log(id, t, gw, ip, auth, u, utp, ki, func, params)'
            ' values (:i, :t, :gw, :ip, :auth, :u, :utp, :ki, :func, :params)'),
                       i=call_id,
                       t=time.time(),
                       gw=gw,
                       ip=ip,
                       auth=auth,
                       u=u,
                       utp=utp,
                       ki=ki,
                       func=func,
                       params=rapidjson.dumps(params)[:512])
        dbt.commit()
    except:
        dbt.rollback()
        logging.error('Unable to insert API call info into DB')
        eva.core.log_traceback()


def api_log_set_status(call_id, status=None):
    dbconn = userdb()
    dbt = dbconn.begin()
    try:
        dbconn.execute(
            sql('update api_log set tf=:tf, status=:status where id=:i'),
            i=call_id,
            tf=time.time(),
            status=status)
        dbt.commit()
    except:
        dbt.rollback()
        logging.error('Unable to update API call info in DB')
        eva.core.log_traceback()


def api_log_update(call_id, **kwargs):
    # unsafe, make sure kwargs keys are not coming from outside
    cond = ''
    qkw = {'i': call_id}
    for k, v in kwargs.items():
        if cond:
            cond += ','
        cond += f'{k}=:{k}'
        qkw[k] = v
    if cond:
        dbconn = userdb()
        dbt = dbconn.begin()
        try:
            dbconn.execute(sql(f'update api_log set {cond} where id=:i'), **qkw)
            dbt.commit()
        except:
            dbt.rollback()
            logging.error('Unable to update API call info in DB')
            eva.core.log_traceback()


def api_log_get(t_start=None, t_end=None, limit=None, time_format=None, f=None):
    t_start = fmt_time(t_start)
    t_end = fmt_time(t_end)
    qkw = {}
    if t_start or t_end:
        cond = 'where ('
        if t_start is not None:
            try:
                t_start = float(t_start)
            except:
                try:
                    t_start = dateutil.parser.parse(t_start).timestamp()
                except:
                    raise ValueError('start time format is uknown')
            cond += 't >= :t_start'
            qkw['t_start'] = t_start
        if t_end is not None:
            try:
                t_end = float(t_end)
            except:
                try:
                    t_end = dateutil.parser.parse(t_end).timestamp()
                except:
                    raise ValueError('end time format is uknown')
            if t_start is not None:
                cond += ' and '
            cond += 't <= :t_end'
            qkw['t_end'] = t_end
        cond += ')'
    else:
        cond = ''
    if f:
        # make sure some empty fields are null
        for z in ('u', 'utp', 'status'):
            if z in f and f[z] == '':
                f[z] = None
    if 'params' in f:
        condp = 'params like :params'
        qkw['params'] = f'%{f["params"]}%'
        del f['params']
    else:
        condp = None
    try:
        cond, qkw = format_sql_condition(f,
                                         qkw,
                                         fields=('gw', 'ip', 'auth', 'u', 'utp',
                                                 'ki', 'func', 'status'),
                                         cond=cond)
    except ValueError as e:
        raise ValueError(f'Invalid filter: {e}')
    if condp:
        if cond:
            cond += ' and '
        else:
            cond = 'where '
        cond += condp
    if limit is None:
        cond += ' order by t asc'
    else:
        cond += f' order by t desc limit {limit}'
    result = [
        dict(r) for r in userdb().execute(
            sql('select id, t, tf, gw, ip, auth, u, utp, ki,'
                f' func, params, status from api_log {cond}'), **
            qkw).fetchall()
    ]
    if limit is not None:
        result = sorted(result, key=lambda k: k['t'])
    if time_format == 'iso':
        import pytz
        tz = pytz.timezone(time.tzname[0])
        for r in result:
            r['t'] = datetime.fromtimestamp(r['t'], tz).isoformat()
            r['tf'] = datetime.fromtimestamp(r['tf'], tz).isoformat()
    return result


def list_users():
    try:
        dbconn = userdb()
        result = []
        r = dbconn.execute(sql('select u, k from users order by u'))
        while 1:
            row = r.fetchone()
            if not row:
                break
            u = {}
            u['user'] = row.u
            u['key_id'] = row.k
            result.append(u)
        return sorted(result, key=lambda k: k['user'])
    except:
        eva.core.report_userdb_error()


def get_user(user=None):
    if not user:
        return None
    try:
        dbconn = userdb()
        result = []
        row = dbconn.execute(sql('select u, k from users where u=:u'),
                             u=user).fetchone()
    except:
        eva.core.report_userdb_error()
    if not row:
        raise ResourceNotFound
    return {'user': row.u, 'key_id': row.k}


def create_user(user=None, password=None, key=None):
    if user is None or password is None or key is None:
        return False
    kk = key if isinstance(key, list) else key.split(',')
    for k in kk:
        if k not in apikey.keys_by_id:
            raise ResourceNotFound(f'API key {k}')
    try:
        dbconn = userdb()
        row = dbconn.execute(sql('select k from users where u = :u'),
                             u=user).fetchone()
    except:
        eva.core.report_userdb_error()
    if row:
        raise ResourceAlreadyExists
    try:
        dbconn.execute(sql('insert into users(u, p, k) values (:u, :p, :k)'),
                       u=user,
                       p=crypt_password(password),
                       k=','.join(kk))
        logging.info('User {} created, key: {}'.format(user, ','.join(kk)))
    except:
        eva.core.report_userdb_error()
        return None
    run_hook('create', user, password)
    return {'user': user, 'key_id': key}


def set_user_password(user=None, password=None):
    if user is None or password is None:
        return None
    try:
        dbconn = userdb()
        if dbconn.execute(sql('update users set p = :p where u = :u'),
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
    if user is None or key is None:
        return None
    kk = key if isinstance(key, list) else key.split(',')
    for k in kk:
        if k not in apikey.keys_by_id:
            raise ResourceNotFound(f'API key {k}')
    try:
        dbconn = userdb()
        if dbconn.execute(sql('update users set k = :k where u = :u'),
                          k=','.join(kk),
                          u=user).rowcount:
            logging.info('user {} key {} is set'.format(user, ','.join(kk)))
            return True
    except:
        eva.core.report_userdb_error()
    raise ResourceNotFound


def destroy_user(user=None):
    if user is None:
        raise FunctionFailed
    try:
        dbconn = userdb()
        if dbconn.execute(sql('delete from users where u = :u'),
                          u=user).rowcount:
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
                       sa.Column('k', sa.String(2048)))
    t_api_log = sa.Table('api_log', meta,
                         sa.Column('id', sa.String(36), primary_key=True),
                         sa.Column('t', sa.Numeric(20, 8), nullable=False),
                         sa.Column('tf', sa.Numeric(20, 8)),
                         sa.Column('gw', sa.String(128)),
                         sa.Column('ip', sa.String(45)),
                         sa.Column('auth', sa.String(128)),
                         sa.Column('u', sa.String(128)),
                         sa.Column('utp', sa.String(32)),
                         sa.Column('ki', sa.String(2048)),
                         sa.Column('func', sa.String(128)),
                         sa.Column('params', sa.String(512)),
                         sa.Column('status', sa.String(32)))
    try:
        meta.create_all(dbconn)
    except:
        eva.core.log_traceback()
        logging.critical('unable to create users table in db')
    try:
        dbconn.close()
    except:
        pass


def update_config(cfg):
    try:
        host = cfg.get('msad/host')
    except LookupError:
        return
    logging.debug(f'msad.host = {host}')
    domain = cfg.get('msad/domain', default='')
    logging.debug(f'msad.domain = {domain}')
    ca = cfg.get('msad/ca', default=None)
    logging.debug(f'msad.ca = {ca}')
    key_prefix = cfg.get('msad/key-prefix', default=None)
    logging.debug(f'msad.key_prefix = {key_prefix}')
    ou = cfg.get('msad/ou', default=_d.msad_ou)
    logging.debug(f'msad.ou = {ou}')
    try:
        cache_time = float(cfg.get('msad/cache-time'))
    except:
        cache_time = 86400
    logging.debug(f'msad.cache_time = {cache_time}')
    msad_init(host, domain, ca, key_prefix, ou, cache_time)


def run_hook(cmd, u, password=None):
    if not eva.core.config.user_hook:
        return True
    p = subprocess.Popen(eva.core.config.user_hook + [cmd, u],
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


def start():
    if eva.core.config.keep_api_log:
        api_log_cleaner.start()
    if _d.msad and _d.msad_cache_time > 0:
        msad_cache_cleaner.start()


@eva.core.stop
def stop():
    if eva.core.config.keep_api_log:
        api_log_cleaner.stop()


@background_worker(delay=api_log_clean_delay,
                   name='users:api_log_cleaner',
                   loop='cleaners',
                   on_error=eva.core.log_traceback)
def api_log_cleaner(**kwargs):
    logging.debug('cleaning API log')
    dbconn = userdb()
    dbt = dbconn.begin()
    try:
        dbconn.execute(sql('delete from api_log where t < :t'),
                       t=time.time() - eva.core.config.keep_api_log)
        dbt.commit()
    except:
        dbt.rollback()
        raise
    try:
        dbconn.close()
    except:
        pass


@background_worker(delay=msad_cache_clean_delay,
                   name='users:msad_cache_cleaner',
                   loop='cleaners',
                   on_error=eva.core.log_traceback)
def msad_cache_cleaner(**kwargs):
    logging.debug('cleaning MSAD cache')
    dbconn = userdb()
    dbt = dbconn.begin()
    try:
        dbconn.execute(sql('delete from msad_cache where t < :t'),
                       t=time.time() - _d.msad_cache_time)
        dbt.commit()
    except:
        dbt.rollback()
        raise
