__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.1.0"
__description__ = "Push client for Roboger"
__api__ = 4
__mods_required__ = ['pyrpush']

__config_help__ = [{
    'name':
    'cf',
    'help':
    'Config file (default: /usr/local/etc/roboger_push.ini)',
    'type':
    'str',
    'required':
    False
}]

__functions__ = {
    'push(media_file=None, **kwargs)':
    'Push message (calls pyrpush.Client.push)'
}

__help__ = """
Push client for Roboger event pager (https://www.roboger.com,
https://github.com/alttch/roboger). Refer to pyrpush module documentation for
more info: https://pypi.org/project/pyrpush/
"""

import importlib

from eva.lm.extensions.generic import LMExt as GenericExt
from eva.lm.extapi import log_traceback

from eva.lm.extapi import ext_constructor


class LMExt(GenericExt):

    @ext_constructor
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        try:
            try:
                mod = importlib.import_module('pyrpush')
            except:
                self.log_error('pyrpush Python module not installed')
                raise
            try:
                self.rpush = mod.Client(ini_file=self.cfg.get('cf'))
            except:
                self.log_error('unable to init pyrpush client')
                raise
        except:
            log_traceback()
            self.ready = False

    def push(self, media_file=None, **kwargs):
        try:
            return self.rpush.push(media_file, **kwargs)
        except:
            log_traceback()
            return False
