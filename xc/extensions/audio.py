__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.0.0"
__description__ = "Play audio file"
__api__ = 1
__mods_required__ = ['soundfile', 'sounddevice']

__id__ = 'audio'

__config_help__ = [{
    'name': 'sdir',
    'help': 'Directory where audio files are stored',
    'type': 'str',
    'required': True
}, {
    'name': 'd',
    'help': 'Playback device (list: python3 -m sounddevice)',
    'type': 'int',
    'required': False
}, {
    'name': 'g',
    'help': 'Default gain (-10..inf)',
    'type': 'float',
    'required': False
}]

__functions__ = {'play(soundfile, gain=0, wait=True)': 'Play sound file'}

__help__ = """
Plays audio file inside the specified directory. The file path should be
relative to the directory root, witout a starting slash.
"""

import importlib
import json

from eva.lm.extensions.generic import LMExt as GenericExt
from eva.lm.extapi import log_traceback


class LMExt(GenericExt):

    def __init__(self, cfg=None, info_only=False):
        super().__init__(cfg)
        self.mod_id = __id__
        self.__author = __author__
        self.__license = __license__
        self.__description = __description__
        self.__version = __version__
        self.__mods_required = __mods_required__
        self.__api_version = __api__
        self.__config_help = __config_help__
        self.__functions = __functions__
        self.__help = __help__
        if info_only: return
        try:
            self.sdir = self.cfg.get('sdir')
            if not self.sdir:
                self.log_error('no audio files directory specified')
                raise Exception('no audio files directory specified')
            try:
                self.gain = float(self.cfg.get('g', 0))
            except:
                self.log_error('invalid gain value: %s' % self.cfg.get('g'))
                raise
            try:
                if 'd' in self.cfg: self.device = int(self.cfg.get('d'))
                else: self.device = None
            except:
                self.log_error('invalid device number: %s' % self.cfg.get('d'))
                raise
            try:
                self.sf = importlib.import_module('soundfile')
            except:
                self.log_error('soundfile Python module not installed')
                raise
            try:
                self.sd = importlib.import_module('sounddevice')
            except:
                self.log_error('sounddevice Python module not installed')
                raise
        except:
            log_traceback()
            self.ready = False

    def play(self, fname, gain=None, wait=True):
        if not isinstance(fname,
                          str) or fname[0] == '/' or fname.find('..') != -1:
            return False
        try:
            data, rate = self.sf.read(self.sdir + '/' + fname)
            if data is None or not rate:
                raise Exception('invalid audio file %s' % fname)
            gain = gain if gain is not None else self.gain
            if gain: data = data * self._gain_multiplier(gain)
            self.sd.play(data, rate, blocking=wait, device=self.device)
            return True
        except:
            self.log_error('file %s playback failed' % fname)
            log_traceback()
            return False

    def _gain_multiplier(self, gain):
        if not gain:
            g = 1.0
        elif gain > 0:
            g = 1 + gain / 10.0
        elif gain > -10:
            g = 1 - abs(gain) / 10.0
        else:
            g = 0.0
        return g
