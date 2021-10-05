__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.2"
__description__ = "Play audio file"
__api__ = 7
__mods_required__ = []

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
}, {
    'name': 'cmd',
    'help': 'External playback command',
    'type': 'str',
    'required': False
}]

__functions__ = {'play(soundfile, gain=0, wait=True)': 'Play audio file'}

__iec_functions__ = {
    'play': {
        'description':
            'play audio file',
        'var_in': [{
            'var': 'soundfile',
            'description': 'audio file to play'
        }, {
            'var': 'gain',
            'description': 'volume gain'
        }, {
            'var': 'wait',
            'description': 'wait until playback finish'
        }]
    }
}

__help__ = """
Plays audio file inside the specified directory. The file path should be
relative to the directory root, witout a starting slash.

If external playback command is not specified, "sounddevice" and "soundfile"
python modules must be present in system.

Params for external command: %f - file, %g - gain, e.g. "play %f gain %g", if
no %f is specified, file name is automatically added to the end.
"""

import importlib

from eva.lm.extensions.generic import LMExt as GenericExt
from eva.lm.extapi import log_traceback

from eva.lm.extapi import ext_constructor


class LMExt(GenericExt):

    @ext_constructor
    def __init__(self, **kwargs):
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
                if 'd' in self.cfg:
                    self.device = int(self.cfg.get('d'))
                else:
                    self.device = None
            except:
                self.log_error('invalid device number: %s' % self.cfg.get('d'))
                raise
            self.cmd = self.cfg.get('cmd')
            if not self.cmd:
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
            f = self.sdir + '/' + fname
            if self.cmd:
                cmd = self.cmd.replace(
                    '%g',
                    str(gain) if gain is not None else str(self.gain)).replace(
                        '%f', f)
                if self.cmd.find('%f') == -1:
                    cmd += ' ' + f
                if not wait:
                    cmd += ' &'
                import os
                ec = os.system(cmd)
                if ec:
                    raise Exception('Command "{}" exit code: {}'.format(
                        cmd, ec))
            else:
                data, rate = self.sf.read(f)
                if data is None or not rate:
                    raise Exception('invalid audio file %s' % fname)
                gain = gain if gain is not None else self.gain
                if gain:
                    data = data * self._gain_multiplier(gain)
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

    def validate_config(self, config={}, config_type='config', **kwargs):
        self.validate_config_whi(config=config,
                                 config_type=config_type,
                                 **kwargs)
