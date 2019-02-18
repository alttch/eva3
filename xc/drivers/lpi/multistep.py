__author__ = 'Altertech Group, https://www.altertech.com/'
__copyright__ = 'Copyright (C) 2012-2018 Altertech Group'
__license__ = 'Apache License 2.0'
__version__ = '1.0.0'
__description__ = 'Multistep LPI (opener)'
__api__ = 1

__id__ = 'multistep'
__logic__ = 'multistep with delays'

__features__ = ['action', 'action_mp', 'port_set', 'aao_set']

__config_help__ = [{
    'name': 'bose',
    'help': 'allow action even if current status is error',
    'type': 'bool',
    'required': False
}]

__action_help__ = [{
    'name': 'port',
    'help': 'port(s) to use for power',
    'type': 'str',
    'required': True,
}, {
    'name': 'dport',
    'help': 'port(s) to use for direction',
    'type': 'str',
    'required': True,
}, {
    'name': 'steps',
    'help': 'delay steps',
    'type': 'list:float',
    'required': True
}, {
    'name': 'warmup',
    'help': 'warmup for middle status',
    'type': 'float',
    'required': False,
}, {
    'name': 'tuning',
    'help': 'tuning for start/end status',
    'type': 'float',
    'required': False
}, {
    'name': 'ts',
    'help': 'less and equal go to the start then to status',
    'type': 'uint',
    'required': False
}, {
    'name': 'te',
    'help': 'greater and equal go to the end then to status',
    'type': 'uint',
    'required': False
}]

__state_help__ = []

__help__ = """
Solves typical logic task: turning the motor direction and run the motor for
the specified number of seconds, to control i.e. window opening, door opening,
manipulators of the robots.

The duration of the motor work is specified in 'steps' unit driver
configuration param, each step corresponds to the next status.

Warmup is used to let the motor additional number of seconds for the starting
states between first and last.

Tuning is used to make sure the motor drivers the target to starting and
finishing position (i.e. completely opens/closes the door).

ts and te. Sometimes it's pretty hard to calculate the proper position for the
middle states. In this case LPI will ask motor to go all the way to the start
state (if target status <= ts) and then back to the target, or all the way to
the end and to the target (if target status >= te).

Unit driver config fields should have property 'port' with a
port label/number for PHI. 'io_label' prop allows to rename 'port', 'dport'
i.e. to 'socket', 'dsocket' for a more fancy unit configuration.  Each port and
dport may be specified as a single value or contain an array of values, in this
case multiple ports are used simultaneously.

You may set i: before the port label/number, i.e. i:2, to return/use inverted
port state. This works both for power and direction ports.
"""

from time import time
from eva.uc.drivers.lpi.basic import LPI as BasicLPI
from eva.uc.driverapi import log_traceback
from eva.tools import val_to_boolean


class LPI(BasicLPI):

    def __init__(self, lpi_cfg=None, phi_id=None, info_only=False):
        super().__init__(lpi_cfg, phi_id, info_only)
        self.lpi_mod_id = __id__
        self.__author = __author__
        self.__license = __license__
        self.__description = __description__
        self.__version = __version__
        self.__api_version = __api__
        self.__lpi_mod_id = __id__
        self.__logic = __logic__
        self.__features = __features__
        self.__config_help = __config_help__
        self.__action_help = __action_help__
        self.__state_help = __state_help__
        self.__help = __help__
        self.connections = {'port': 'power', 'dport': 'destination'}
        if info_only: return
        self.bose = val_to_boolean(self.lpi_cfg.get('bose'))

    def get_item_cmap(self, cfg):
        result = super().get_item_cmap(cfg)
        dport = cfg.get('d' + self.io_label)
        if not isinstance(dport, list): dport = [dport]
        result['dport'] = dport
        return result

    def do_state(self, _uuid, cfg, timeout, tki, state_in):
        self.log_error('state function not implemented')
        return self.state_result_error(_uuid)

    def _calc_delay(self, s, ns, steps, warmup=0, tuning=0):
        _delay = 0
        if s == ns: return 0
        if ns > s:
            _delay = sum(steps[s:ns])
            if s > 0:
                _delay += warmup
            if ns == len(steps):
                _delay += tuning
        else:
            _delay = sum(steps[ns:s])
            if s < len(steps):
                _delay += warmup
            if ns == 0:
                _delay += tuning
        return _delay

    def do_action(self, _uuid, status, value, cfg, timeout, tki):
        time_start = time()
        if cfg is None:
            return self.action_result_error(_uuid, 1, 'no config provided')
        phi_cfg = self.prepare_phi_cfg(cfg)
        if cfg.get('bose'):
            bose = cfg.get('bose')
        else:
            bose = self.bose
        if status is None:
            return self.action_result_error(_uuid, 1, 'no status provided')
        port = cfg.get(self.io_label)
        if port is None:
            return self.action_result_error(
                _uuid, 1, 'no ' + self.io_label + ' in config')
        dport = cfg.get('d' + self.io_label)
        if dport is None:
            return self.action_result_error(
                _uuid, 2, 'no d' + self.io_label + ' in config')
        try:
            nstatus = int(status)
        except:
            return self.action_result_error(_uuid, msg='status is not integer')
        _steps = cfg.get('steps')
        if not _steps or not isinstance(_steps, list):
            return self.action_result_error(_uuid, msg='no steps provided')
        steps = []
        for i in _steps:
            try:
                steps.append(float(i))
            except:
                return self.action_result_error(
                    _uuid, msg='steps should be float numbers')
        if nstatus < 0 or nstatus > len(steps):
            return self.action_result_error(
                _uuid, msg='status is not in range 0..%u' % len(steps))
        pstatus = cfg.get('EVA_ITEM_STATUS')
        try:
            pstatus = int(pstatus)
        except:
            pstatus = 0
        if pstatus is None or pstatus < 0:
            if bose:
                return self.action_result_error(
                    _uuid, msg='current status is an error')
            pstatus = 0
        if pstatus > len(steps):
            self.log_warning('current status is %s while only %s steps are set'
                             % (pstatus, len(steps)))
        if pstatus == nstatus:
            return self.action_result_ok(_uuid)
        warmup = cfg.get('warmup')
        if warmup is not None:
            try:
                warmup = float(warmup)
            except:
                return self.action_result_error(_uuid, 1,
                                                'warmup is not a number')
        else:
            warmup = 0
        tuning = cfg.get('tuning')
        if tuning is not None:
            try:
                tuning = float(tuning)
            except:
                return self.action_result_error(_uuid, 1,
                                                'tuning is not a number')
        else:
            tuning = 0
        ts = cfg.get('ts')
        if ts:
            try:
                ts = int(ts)
            except:
                return self.action_result_error(_uuid, 1, 'ts is not a number')
        te = cfg.get('te')
        if te:
            try:
                te = int(te)
            except:
                return self.action_result_error(_uuid, 1, 'te is not a number')
        if nstatus < pstatus and ts and ts <= nstatus:
            # we need to go to start then to nstatus
            _delay = self._calc_delay(pstatus, 0, steps, warmup, tuning)
            _delay += self._calc_delay(0, nstatus, steps, warmup, tuning)
            if _delay > time_start - time() + timeout:
                return self.action_result_error(
                    _uuid, 4,
                    'can not perform action. requires: %s sec, timeout: %s sec'
                    % (_delay, timeout))
            _pstatus = [pstatus, 0]
            _nstatus = [0, nstatus]
        elif nstatus > pstatus and te and te <= nstatus:
            # we need to go to the end then to nstatus
            _delay = self._calc_delay(pstatus, len(steps), steps, warmup,
                                      tuning)
            _delay += self._calc_delay(
                len(steps), nstatus, steps, warmup, tuning)
            if _delay > time_start - time() + timeout:
                return self.action_result_error(
                    _uuid, 4,
                    'can not perform action. requires: %s sec, timeout: %s sec'
                    % (_delay, timeout))
            _pstatus = [pstatus, len(steps)]
            _nstatus = [len(steps), nstatus]
        else:
            _pstatus = [pstatus]
            _nstatus = [nstatus]
        for i in range(0, len(_pstatus)):
            pstatus = _pstatus[i]
            nstatus = _nstatus[i]
            if nstatus > pstatus:
                direction = 1
            else:
                direction = 0
            try:
                _delay = self._calc_delay(pstatus, nstatus, steps, warmup,
                                          tuning)
            except:
                log_traceback()
                return self.action_result_error(_uuid, 3, '_delay calc error')
            # no delay - nothing to do
            if not _delay:
                continue
            if _delay > time_start - time() + timeout:
                return self.action_result_error(
                    _uuid, 4,
                    'can not perform action. requires: %s sec, timeout: %s sec'
                    % (_delay, time_start - time() + timeout))
            _c = {self.io_label: port}
            _cd = {self.io_label: dport}
            # direction
            r = self.exec_super_subaction(direction, _cd,
                                          time_start - time() + timeout, tki)
            if not r or r.get('exitcode') != 0:
                if not r:
                    r = {}
                return self.action_result_error(
                    _uuid, 4,
                    'direction set error: %s, %s' % (r.get('exitcode'),
                                                     r.get('err')))
            # power on
            r = self.exec_super_subaction(1, _c, time_start - time() + timeout,
                                          tki)
            if not r or r.get('exitcode') != 0:
                if not r:
                    r = {}
                return self.action_result_error(
                    _uuid, 4, 'power on error: %s, %s' % (r.get('exitcode'),
                                                          r.get('err')))
            dr = self.delay(_uuid, _delay)
            # power off
            r = self.exec_super_subaction(0, _c, time_start - time() + timeout,
                                          tki)
            if not r or r.get('exitcode') != 0:
                if not r:
                    r = {}
                self.critical('power off error!')
                return self.action_result_error(
                    _uuid, 4, 'power off error: %s, %s' % (r.get('exitcode'),
                                                           r.get('err')))
            if not dr:
                # we are terminated
                return self.action_result_terminated(_uuid)
        return self.action_result_ok(_uuid)

    def exec_super_subaction(self, status, cfg, timeout, tki):
        _u = self.gen_uuid()
        self.prepare_action(_u)
        super().do_action(_u, status, None, cfg, timeout, tki)
        result = self.get_result(_u)
        self.clear_result(_u)
        return result
