__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.0.3"
__description__ = "Nanoleaf LEDs"

__equipment__ = 'Nanoleaf LEDs'
__api__ = 5
__required__ = ['port_get', 'port_set', 'value', 'status', 'action']
__mods_required__ = []
__lpi_default__ = 'usp'
__features__ = []
__config_help__ = [{
    'name': 'host',
    'help': 'nanoleaf host/ip[:port]',
    'type': 'str',
    'required': True
}, {
    'name': 'token',
    'help': 'Authentication token',
    'type': 'str',
    'required': False
}]
__get_help__ = []
__set_help__ = []
__help__ = """
Nanoleaf (https://nanoleaf.me/) LEDs control.

If token is not specified, Nanoleaf power button must be pressed for 7 seconds
before loading PHI.

If unit value is specified as RGB hex, PHI sets its color, otherwise chosen
effect is applied.
"""
__discover__ = 'net'
__discover_help__ = 'Set timeout at least to 3 seconds'

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import phi_constructor
from eva.uc.driverapi import get_timeout

import requests
import math
from time import time


class PHI(GenericPHI):

    @phi_constructor
    def __init__(self, **kwargs):
        self.host = self.phi_cfg.get('host')
        if not self.host:
            self.ready = False
            self.log_error('host is not specified')
            return
        self.api_uri = 'http://{}:16021/api/v1'.format(self.host)
        self.token = self.phi_cfg.get('token')
        if not self.token:
            try:
                result = requests.post(
                    '{}/new'.format(self.api_uri),
                    timeout=get_timeout()).json()
                self.token = result['auth_token']
                self.phi_cfg['token'] = self.token
            except:
                self.log_error('unable to create token')
                log_traceback()
                self.ready = False
        self.api_uri += '/{}'.format(self.token)

    @staticmethod
    def discover(interface=None, timeout=0):
        import eva.uc.drivers.tools.ssdp as ssdp
        result = []
        data = ssdp.discover(
            'nanoleaf_aurora:light',
            interface=interface,
            timeout=timeout,
            discard_headers=[
                'Cache-control', 'Ext', 'Location', 'Host', 'Nl-deviceid',
                'Usn', 'S', 'St'
            ])
        if data:
            for r in data:
                if 'Nl-devicename' in r:
                    try:
                        r['Name'] = r['Nl-devicename']
                        del r['Nl-devicename']
                    except:
                        pass
                    r['!load'] = {'host': r['IP']}
                    result.append(r)
            if result:
                result = [{'!opt': 'cols', 'value': ['IP', 'Name']}] + result
        return result

    def get(self, port=None, cfg=None, timeout=0):
        try:
            result = requests.get(self.api_uri, timeout=timeout).json()
            status = 1 if result['state']['on']['value'] else 0
            value = result['effects']['select']
            if value == '*Solid*':
                h = result['state']['hue']['value']
                s = result['state']['sat']['value']
                v = result['state']['brightness']['value']
                value = self.hsv2rgb(h, s, v)
            else:
                value += ',{}'.format(result['state']['brightness']['value'])
            return status, value
        except:
            self.log_error('unable to get state')
            log_traceback()
            return None

    def set(self, port=None, data=None, cfg=None, timeout=0):
        t_start = time()
        status, value = data
        try:
            if value:
                try:
                    s_in = value[1:] if value.startswith('#') else value
                    red = int(s_in[:2], 16)
                    green = int(s_in[2:4], 16)
                    blue = int(s_in[4:], 16)
                    # we have hex
                    h, s, v = self.rgb2hsv(red, green, blue)
                    params = {
                        'hue': {
                            'value': h
                        },
                        'sat': {
                            'value': s
                        },
                        'brightness': {
                            'value': v
                        }
                    }
                    result = requests.put(
                        '{}/state'.format(self.api_uri),
                        json=params,
                        timeout=timeout)
                    if not result.ok:
                        raise Exception(
                            'set value (color) http code: {}'.format(
                                result.status_code))
                except ValueError:
                    # we have a string, probably effect
                    try:
                        p = value.split(',', 1)
                    except:
                        return False
                    result = requests.put(
                        '{}/effects'.format(self.api_uri),
                        json={'select': p[0]},
                        timeout=timeout)
                    if not result.ok:
                        raise Exception(
                            'set value (effect) http code: {}'.format(
                                result.status_code))
                    if len(p) > 1:
                        t2 = timeout - time() + t_start
                        if t2 <= 0: raise Exception('PHI timeout')
                        try:
                            params = {'brightness': {'value': int(p[1])}}
                        except:
                            raise Exception('Invalid brightness value')
                        result = requests.put(
                            '{}/state'.format(self.api_uri),
                            json=params,
                            timeout=timeout)
                        if not result.ok:
                            raise Exception(
                                'set value (brightness) http code: {}'.format(
                                    result.status_code))
            t2 = timeout - time() + t_start
            if t2 <= 0: raise Exception('PHI timeout')
            params = {'on': {'value': True if status else False}}
            result = requests.put(
                '{}/state/on'.format(self.api_uri), json=params, timeout=t2)
            if not result.ok:
                raise Exception('set status http code: {}'.format(
                    result.status_code))
            return True
        except Exception as e:
            self.log_error('unable to set state: {}'.format(e))
            log_traceback()
            return False

    def test(self, cmd=None):
        if cmd in ['self', 'get']:
            try:
                u = self.api_uri
                result = requests.get(u, timeout=get_timeout()).json()
                if 'manufacturer' not in result:
                    raise Exception
                return 'OK' if cmd == 'self' else result
            except:
                log_traceback()
                return 'FAILED' if cmd == 'self' else None
        else:
            return {'get': 'get panel info'}

    def unload(self):
        try:
            result = requests.delete(self.api_uri, timeout=get_timeout())
            if not result.ok:
                raise Exception
        except:
            self.log_warning('unable to delete token')
            log_traceback()

    @staticmethod
    def hsv2rgb(h, s, v):
        h = float(h)
        s = float(s) / 100
        v = float(v) / 100
        h60 = h / 60.0
        h60f = math.floor(h60)
        hi = int(h60f) % 6
        f = h60 - h60f
        p = v * (1 - s)
        q = v * (1 - f * s)
        t = v * (1 - (1 - f) * s)
        r, g, b = 0, 0, 0
        if hi == 0: r, g, b = v, t, p
        elif hi == 1: r, g, b = q, v, p
        elif hi == 2: r, g, b = p, v, t
        elif hi == 3: r, g, b = p, q, v
        elif hi == 4: r, g, b = t, p, v
        elif hi == 5: r, g, b = v, p, q
        r, g, b = int(r * 255), int(g * 255), int(b * 255)
        return '#{:02x}{:02x}{:02x}'.format(r, g, b)

    @staticmethod
    def rgb2hsv(r, g, b):
        r, g, b = r / 255.0, g / 255.0, b / 255.0
        mx = max(r, g, b)
        mn = min(r, g, b)
        df = mx - mn
        if mx == mn:
            h = 0
        elif mx == r:
            h = (60 * ((g - b) / df) + 360) % 360
        elif mx == g:
            h = (60 * ((b - r) / df) + 120) % 360
        elif mx == b:
            h = (60 * ((r - g) / df) + 240) % 360
        if mx == 0:
            s = 0
        else:
            s = df / mx
        v = mx
        return round(h), round(s * 100), round(v * 100)
