__author__ = "Altertech Group, http://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2017 Altertech Group"
__license__ = "See http://www.eva-ics.com/"
__version__ = "3.0.0"

import smtplib
import platform
import logging

from email.mime.text import MIMEText
from eva.tools import parse_host_port

_from = 'eva@' + platform.node()

_smtp_host = 'localhost'
_smtp_port = 25
_default_rcp = [ 'root' ]

default_port = 25

def update_config(cfg):
    global _smtp_host, _smtp_port, _from, _default_rcp
    try:
        _smtp_host, _smtp_port = parse_host_port(cfg.get('mailer', 'smtp'))
        if not _smtp_port:
            _smtp_port = default_port
    except:
        _smtp_host = 'localhost'
        _smtp_port = default_port
    logging.debug('mailer.smtp = %s:%u' % (_smtp_host, _smtp_port))
    try:
        _from = cfg.get('mailer', 'from')
    except:
        _from = 'eva@' + platform.node()
    logging.debug('mailer.from = %s' % _from)
    try:
        _default_rcp = list(filter(None,
            [x.strip() for x in cfg.get('mailer', 'default_rcp').split(',')]))
    except:
        _default_rcp = [ 'root' ]
    logging.debug('mailer.default_rcp = %s' % ', '.join(_default_rcp))
    return True

def send(subject = None, text = None, rcp = None):

    if subject is None: s = ''
    else: s = subject

    if text is None: t = s
    else: t = text

    msg = MIMEText(t)

    msg['Subject'] = s
    msg['From'] = _from

    if not rcp:
        if not _default_rcp: return False
        else: _rcp = _default_rcp
    else:
        if isinstance(_rcp, str): _rcp = [ rcp ]
        else: _rcp = rcp

    if len(_rcp) == 1:
        msg['To'] = _rcp[0]
    sm = smtplib.SMTP(_smtp_host, _smtp_port)
    sm.sendmail(_from, _rcp, msg.as_string())
    logging.debug('sending mail to %s, subject "%s"' % (', '.join(_rcp), s))
    sm.quit()
    return True
