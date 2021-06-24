__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"

import platform
import logging

import eva.core

from eva.tools import parse_host_port

from eva.exceptions import FunctionFailed

from eva.tools import SimpleNamespace

from pyaltt2.mail import SMTP

import eva.registry

config = SimpleNamespace(sender='eva@' + platform.node(),
                         smtp_host='localhost',
                         smtp_port=25,
                         tls=False,
                         ssl=False,
                         login=None,
                         password=None,
                         default_rcp=['root'])

default_port = 25


def load():
    cfg = eva.registry.config_get('config/common/mailer', default={})
    try:
        config.smtp_host, config.smtp_port = parse_host_port(
            cfg.get('smtp'), default_port)
    except:
        config.smtp_host = 'localhost'
        config.smtp_port = default_port
    logging.debug('mailer.smtp = %s:%u' % (config.smtp_host, config.smtp_port))
    config.sender = cfg.get('from', default=f'eva@{platform.node()}')
    logging.debug(f'mailer.from = {config.sender}')
    try:
        config.default_rcp = cfg.get('default-rcp')
        if not isinstance(config.default_rcp, list):
            config.default_rcp = [config.default_rcp]
    except:
        config.default_rcp = ['root']
    logging.debug('mailer.default_rcp = %s' % ', '.join(config.default_rcp))
    config.ssl = cfg.get('ssl', default=False)
    logging.debug(f'mailer.ssl = {config.ssl}')
    config.tls = cfg.get('tls', default=False)
    logging.debug(f'mailer.tls = {config.tls}')
    config.login = cfg.get('login', default=None)
    logging.debug(f'mailer.login = {config.login}')
    config.password = cfg.get('password', default=None)
    logging.debug(f'mailer.password = {"*" if config.password else None}')
    return True


def send(subject=None, text=None, rcp=None):
    """
    send email message

    The function uses config/common/mailer :doc:`registry</registry>` key get
    sender address and list of the recipients (if not specified).

    Optional:
        subject: email subject
        text: email text
        rcp: recipient or array of the recipients

    Raises:
        FunctionFailed: mail is not sent
    """

    if subject is None:
        s = ''
    else:
        s = subject

    if text is None:
        t = s
    else:
        t = text

    if not rcp:
        if not config.default_rcp:
            raise FunctionFailed('Neither recipient nor default ' +
                                 'recipient in config not specified')
        else:
            _rcp = config.default_rcp
    else:
        _rcp = rcp
    if isinstance(_rcp, list) and len(_rcp) == 1:
        _rcp = _rcp[0]
    try:
        smtp = SMTP(host=config.smtp_host,
                    port=config.smtp_port,
                    tls=config.tls,
                    ssl=config.ssl,
                    login=config.login,
                    password=config.password)
        logging.debug(f'sending mail to {_rcp}')
        smtp.sendmail(config.sender, _rcp, subject=s, text=t)
        return True
    except Exception as e:
        eva.core.log_traceback()
        raise FunctionFailed(e)
