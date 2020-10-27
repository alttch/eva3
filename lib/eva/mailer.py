__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2020 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.3.2"

import platform
import logging

import eva.core

from eva.tools import parse_host_port

from eva.exceptions import FunctionFailed

from eva.tools import SimpleNamespace

from pyaltt2.mail import SMTP

config = SimpleNamespace(sender='eva@' + platform.node(),
                         smtp_host='localhost',
                         smtp_port=25,
                         tls=False,
                         ssl=False,
                         login=None,
                         password=None,
                         default_rcp=['root'])

default_port = 25


def update_config(cfg):
    try:
        config.smtp_host, config.smtp_port = parse_host_port(
            cfg.get('mailer', 'smtp'), default_port)
    except:
        config.smtp_host = 'localhost'
        config.smtp_port = default_port
    logging.debug('mailer.smtp = %s:%u' % (config.smtp_host, config.smtp_port))
    try:
        config.sender = cfg.get('mailer', 'from')
    except:
        config.sender = 'eva@' + platform.node()
    logging.debug('mailer.from = %s' % config.sender)
    try:
        config.default_rcp = list(
            filter(None, [
                x.strip() for x in cfg.get('mailer', 'default_rcp').split(',')
            ]))
    except:
        config.default_rcp = ['root']
    logging.debug('mailer.default_rcp = %s' % ', '.join(config.default_rcp))
    try:
        config.ssl = (cfg.get('mailer', 'ssl') == 'yes')
    except:
        config.ssl = False
    logging.debug(f'mailer.ssl = {config.ssl}')
    try:
        config.tls = (cfg.get('mailer', 'tls') == 'yes')
    except:
        config.tls = False
    logging.debug(f'mailer.tls = {config.tls}')
    try:
        config.login = cfg.get('mailer', 'login')
    except:
        config.login = None
    logging.debug(f'mailer.login = {config.login}')
    try:
        config.password = cfg.get('mailer', 'password')
    except:
        config.password = None
    logging.debug(f'mailer.password = {"*" if config.password else None}')
    return True


def send(subject=None, text=None, rcp=None):
    """
    send email message

    The function uses *[mailer]* section of the :ref:`LM PLC
    configuration<lm_ini>` to get sender address and list of the recipients (if
    not specified).

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
    return True
