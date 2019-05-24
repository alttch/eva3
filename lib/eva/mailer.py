__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.3"

import smtplib
import platform
import logging

from email.mime.text import MIMEText
import eva.core

from eva.tools import parse_host_port

from eva.exceptions import FunctionFailed

from types import SimpleNamespace

config = SimpleNamespace(
    sender='eva@' + platform.node(),
    smtp_host='localhost',
    smtp_port=25,
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

    if subject is None: s = ''
    else: s = subject

    if text is None: t = s
    else: t = text

    if not rcp:
        if not config.default_rcp:
            raise FunctionFailed('Neither recipient nor default ' +
                                 'recipient in config not specified')
        else:
            _rcp = config.default_rcp
    else:
        if isinstance(_rcp, str): _rcp = [rcp]
        else: _rcp = rcp

    try:
        msg = MIMEText(t)

        msg['Subject'] = s
        msg['From'] = config.sender

        if len(_rcp) == 1:
            msg['To'] = _rcp[0]
        sm = smtplib.SMTP(config.smtp_host, config.smtp_port)
        sm.sendmail(config.sender, _rcp, msg.as_string())
        logging.debug('sending mail to %s, subject "%s"' % (', '.join(_rcp), s))
        sm.quit()
        return True
    except Exception as e:
        eva.core.log_traceback()
        raise FunctionFailed(e)
