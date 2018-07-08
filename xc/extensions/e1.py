__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "Posts JSON data to the URL"
__api__ = 1

__id__ = 'e1'

__config_help__ = [{
    'name': 'url',
    'help': 'url to push JSON data to',
    'type': 'url',
    'required': True
}]

__functions__ = {'push(data)': 'push data to remote URL'}

__help__= """
This is test extension just to test how LM PLC extesions works. It sould be
removed before the final 3.1.0 release. If we forgot to do this, please remove
this mod manually."""

from eva.lm.extensions.generic import LMExt as GenericExt

from eva.lm.extapi import get_timeout
from eva.lm.extapi import log_traceback

import requests
import jsonpickle


class LMExt(GenericExt):

    def __init__(self, cfg=None):
        super().__init__(cfg)
        self.mod_id = __id__
        self.__author = __author__
        self.__license = __license__
        self.__description = __description__
        self.__version = __version__
        self.__api_version = __api__
        self.__config_help = __config_help__
        self.__functions = __functions__
        self.__help = __help__
        self.url = self.cfg.get('url')
        if not self.url: self.ready = False

    def push(self, data, timeout=None):
        _timeout = timeout if timeout else get_timeout()
        r = requests.post(self.url, json=data, timeout=_timeout)
        if r.status_code != 200:
            return None
        try:
            return jsonpickle.decode(r.text)
        except:
            return None
