__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.1"
__description__ = "Text-to-speech via ttsbroker"
__api__ = 7
__mods_required__ = ['ttsbroker']

__config_help__ = [{
    'name': 'p',
    'help': 'TTS provider',
    'type': 'str',
    'required': True
}, {
    'name': 'k',
    'help': 'provider key file (JSON)',
    'type': 'str',
    'required': False
}, {
    'name': 'sdir',
    'help': 'Directory where audio files are permanently stored',
    'type': 'str',
    'required': False
}, {
    'name': 'cdir',
    'help': 'Directory where audio files are cached',
    'type': 'str',
    'required': False
}, {
    'name': 'cf',
    'help': 'Cache format (default: wav)',
    'type': 'str',
    'required': False
}, {
    'name': 'o',
    'help': 'JSON file with default provider options',
    'type': 'str',
    'required': False
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

__functions__ = {
    'say(text, **kwargs)': 'Say text (calls ttsbroker.TTSEngine.say)'
}

__iec_functions__ = {
    'say': {
        'description':
            'say text',
        'var_in': [{
            'var': 'text',
            'description': 'text to say'
        }, {
            'var': 'gain',
            'description': 'volume gain'
        }, {
            'var': 'cache',
            'description': 'use cache'
        }, {
            'var': 'wait',
            'description': 'wait until playback finish'
        }]
    }
}

__help__ = """
Text-to-speech engine via ttsbroker Python module. Refer to module
documentation for more info: https://pypi.org/project/ttsbroker/

Params for external command: %f - file, if no %f is specified, file name is
automatically added to the end.
"""

import importlib
import rapidjson

from eva.lm.extensions.generic import LMExt as GenericExt
from eva.lm.extapi import log_traceback

from eva.lm.extapi import ext_constructor


class LMExt(GenericExt):

    @ext_constructor
    def __init__(self, **kwargs):
        try:
            provider = self.cfg.get('p')
            if not provider:
                self.log_error('no provider specified')
                raise Exception('no provider specified')
            try:
                gain = float(self.cfg.get('g', 0))
            except:
                self.log_error('invalid gain value: %s' % self.cfg.get('g'))
                raise
            try:
                if 'd' in self.cfg:
                    device = int(self.cfg.get('d'))
                else:
                    device = None
            except:
                self.log_error('invalid device number: %s' % self.cfg.get('d'))
                raise
            try:
                mod = importlib.import_module('ttsbroker')
            except:
                self.log_error('ttsbroker Python module not installed')
                raise
            try:
                if 'o' in self.cfg:
                    with open(self.cfg.get('o')) as fd:
                        opts = rapidjson.loads(fd.read())
                else:
                    opts = {}
            except:
                self.log_error('invalid options file: %s' % self.cfg.get('o'))
                raise
            try:
                self.tts = mod.TTSEngine(storage_dir=self.cfg.get('sdir'),
                                         cache_dir=self.cfg.get('cdir'),
                                         cache_format=self.cfg.get('cf', 'wav'),
                                         device=device,
                                         gain=gain,
                                         provider=self.cfg.get('p'),
                                         provider_options=opts,
                                         cmd=self.cfg.get('cmd'))
            except:
                self.log_error('unable to init TTS broker')
                raise
            try:
                k = self.cfg.get('k')
                if k:
                    self.tts.set_key(k)
            except:
                self.log_error('unable to set TTS key')
                raise
        except:
            log_traceback()
            self.ready = False

    def say(self, text, **kwargs):
        if text is None:
            return False
        try:
            return self.tts.say(text, **kwargs)
        except:
            log_traceback()
            return False

    def validate_config(self, config={}, config_type='config', **kwargs):
        self.validate_config_whi(config=config,
                                 config_type=config_type,
                                 **kwargs)
