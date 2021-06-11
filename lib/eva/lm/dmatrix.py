__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"

import logging
import uuid
import eva.item
import eva.core
import time
import shlex
import threading
import re

from eva.tools import val_to_boolean
from eva.tools import dict_from_str
from eva.tools import parse_func_str

from eva.exceptions import FunctionFailed


class DecisionMatrix:

    def __init__(self):
        self.rules = []
        self.rules_locker = threading.Lock()

    def process(self, item, ns=False):
        if not ns and item.prv_status == item.status and \
                item.prv_value == item.value:
            return False
        elif ns and item.prv_nstatus == item.nstatus and \
                item.prv_nvalue == item.nvalue:
            return False
        event_code = '%s/dme-%f' % (item.full_id, time.time())
        if not ns:
            logging.debug('Decision matrix event %s %s, ' % \
                (item.item_type, item.full_id) + \
                'status = %s -> %s, ' % (item.prv_status, item.status) + \
                'value = "%s" -> "%s" ' % (item.prv_value, item.value) + \
                'assigned code = %s' % event_code)
        else:
            logging.debug('Decision matrix event %s %s, ' % \
                (item.item_type, item.full_id) + \
                'nstatus = %s -> %s, ' % (item.prv_nstatus, item.nstatus) + \
                'nvalue = "%s" -> "%s" ' % (item.prv_nvalue, item.nvalue) + \
                'assigned code = %s' % event_code)
        with self.rules_locker:
            rules = self.rules.copy()
        for rule in rules:
            if not rule.enabled:
                continue
            with rule.processing_lock:
                if rule.for_item_type and rule.for_item_type != '#' and \
                        rule.for_item_type != item.item_type:
                    continue
                if rule.for_item_id and rule.for_item_id != '#' and \
                    rule.for_item_id != item.item_id and \
                    not (rule.for_item_id[0] == '*' and \
                        rule.for_item_id[1:] == \
                            item.item_id[-len(rule.for_item_id)+1:]) and \
                    not (rule.for_item_id[-1] == '*' and \
                        rule.for_item_id[:-1] == \
                            item.item_id[:len(rule.for_item_id)-1]) and \
                    not (rule.for_item_id[0] == '*' and \
                        rule.for_item_id[-1] == '*' and \
                        item.item_id.find(rule.for_item_id[1:-1]) > -1
                        ):
                    continue
                if rule.for_item_group is not \
                        None and not \
                        eva.item.item_match(item, [], [ rule.for_item_group ]):
                    continue
                pv = None
                v = None
                if rule.for_prop == 'status' and not ns:
                    try:
                        pv = float(item.prv_status)
                    except:
                        pv = None
                    try:
                        v = float(item.status)
                    except:
                        v = None
                elif rule.for_prop == 'value' and not ns:
                    if item.prv_value is not None:
                        try:
                            pv = float(item.prv_value)
                        except:
                            pv = item.prv_value
                    try:
                        v = float(item.value)
                    except:
                        v = item.value
                elif rule.for_prop == 'nstatus' and ns:
                    try:
                        pv = float(item.prv_nstatus)
                    except:
                        pv = None
                    try:
                        v = float(item.nstatus)
                    except:
                        v = None
                elif rule.for_prop == 'nvalue' and ns:
                    if item.prv_nvalue is not None:
                        try:
                            pv = float(item.prv_nvalue)
                        except:
                            pv = item.prv_nvalue
                    try:
                        v = float(item.nvalue)
                    except:
                        v = item.value
                else:
                    continue
                rule.chillout_event = None
                if rule.for_prop_bit is not None:
                    if isinstance(pv, float):
                        pv = float(int(pv) >> rule.for_prop_bit & 1)
                    if isinstance(v, float):
                        v = float(int(v) >> rule.for_prop_bit & 1)
                    if pv == v:
                        continue
                if (pv is None and rule.for_initial == 'skip') or \
                        (pv is not None and \
                            rule.for_initial == 'only') or \
                        v is None or \
                        pv == v:
                    continue
                if pv is not None:
                    if not isinstance(pv, float):
                        if rule.in_range_min is not None and \
                                pv == rule.in_range_min:
                            continue
                    else:
                        if (rule.in_range_min is not None and \
                                not isinstance(rule.in_range_min, float)) or \
                            (rule.in_range_max is not None and \
                                not isinstance(rule.in_range_max, float)):
                            continue
                        if rule.in_range_min is not None and \
                                rule.in_range_max is not None:
                            if ((rule.in_range_min_eq and \
                                        pv >= rule.in_range_min) or \
                                (not rule.in_range_min_eq and \
                                        pv > rule.in_range_min)) and \
                                ((rule.in_range_max_eq and \
                                        pv <= rule.in_range_max) or \
                                (not rule.in_range_max_eq and \
                                    pv < rule.in_range_max)):
                                continue
                        elif rule.in_range_min is not None:
                            if (rule.in_range_min_eq and \
                                        pv >= rule.in_range_min) or \
                                (not rule.in_range_min_eq and \
                                    pv > rule.in_range_min):
                                continue
                        elif rule.in_range_max is not None:
                            if ((rule.in_range_max_eq and \
                                    pv <= rule.in_range_max) or \
                            (not rule.in_range_max_eq and \
                                pv < rule.in_range_max)):
                                continue
                if not isinstance(v, float):
                    if rule.in_range_min is not None and \
                            v != rule.in_range_min:
                        continue
                else:
                    if (rule.in_range_min is not None and \
                            not isinstance(rule.in_range_min, float)) or \
                        (rule.in_range_max is not None and \
                            not isinstance(rule.in_range_max, float)):
                        continue
                    if rule.in_range_min is not None:
                        if rule.in_range_min_eq:
                            if v < rule.in_range_min:
                                continue
                        else:
                            if v <= rule.in_range_min:
                                continue
                    if rule.in_range_max is not None:
                        if rule.in_range_max_eq:
                            if v > rule.in_range_max:
                                continue
                        else:
                            if v >= rule.in_range_max:
                                continue
                if eva.core.config.development:
                    rule_id = rule.item_id
                else:
                    rule_id = rule.item_id[:14] + '...'
                logging.debug('Decision matrix rule %s match event %s' % \
                        (rule_id, event_code))
                if rule.chillout_active:
                    logging.debug(
                        'Decision matrix rule ' + \
                                '%s event %s skipped due to chillout time' % \
                                (rule_id, event_code) + \
                                ', chillot ending in %f sec' % \
                                (rule.chillout_time + rule.last_matched - \
                                    time.time()))
                    rule.chillout_event = event_code
                    continue
                self.exec_rule_action(event_code, rule, item)
                if rule.break_after_exec:
                    logging.debug('Decision matrix rule ' + \
                            '%s is an event %s breaker, stopping event' % \
                            (rule_id, event_code))
                    break
        return True

    def process_chillout(self, rule, item):
        # don't use Timer - chillout_time can be changed during wait
        while rule.last_matched + rule.chillout_time > time.time():
            time.sleep(eva.core.config.polldelay)
            if eva.core.is_shutdown_requested():
                return
        with rule.processing_lock:
            rule.chillout_active = False
            if rule.chillout_event:
                if eva.core.config.development:
                    rule_id = rule.item_id
                else:
                    rule_id = rule.item_id[:14] + '...'
                logging.debug(
                    'Decision matrix rule {} matched event {} during chillout'.
                    format(rule_id, rule.chillout_event))
                self.exec_rule_action(rule.chillout_event, rule, item)
                rule.chillout_event = None

    def exec_rule_action(self, event_code, rule, item):
        rule.last_matched = time.time()
        if rule.macro:
            eva.core.spawn(self.run_macro, event_code, rule, item)
        if rule.chillout_time:
            rule.chillout_active = True
            eva.core.spawn(self.process_chillout, rule, item)

    def run_macro(self, event_code, rule, item):
        if not eva.lm.controller.exec_macro(macro=rule.macro,
                                            argv=rule.macro_args,
                                            kwargs=rule.macro_kwargs,
                                            source=item):
            logging.error('Decision matrix can not exec macro' + \
                    ' %s for event %s' % (rule.macro, event_code))

    def append_rule(self, d_rule, do_sort=True):
        if d_rule in self.rules:
            return False
        r = self.rules.copy()
        r.append(d_rule)
        if do_sort:
            r = self.sort_rule_array(r)
        self.rules = r
        return True

    def sort(self):
        self.rules = self.sort_rule_array(self.rules.copy())

    def sort_rule_array(self, rule_array):
        r = sorted(rule_array, key=lambda v: v.item_id)
        r = sorted(rule_array, key=lambda v: v.description)
        r = sorted(r, key=lambda v: v.priority)
        return r

    def remove_rule(self, d_rule):
        if not d_rule in self.rules:
            return False
        self.rules.remove(d_rule)


class DecisionRule(eva.item.Item):

    def __init__(self, rule_uuid=None, **kwargs):
        self.priority = 100
        if not rule_uuid:
            _uuid = str(uuid.uuid4())
        else:
            _uuid = rule_uuid
        self.enabled = False
        self.for_item_type = None
        self.for_item_id = None
        self.for_item_group = None
        self.for_prop = 'status'
        self.for_initial = 'skip'
        self.in_range_min = None
        self.in_range_max = None
        self.in_range_min_eq = False
        self.in_range_max_eq = False
        self.for_prop_bit = None
        self.macro = None
        self.macro_args = []
        self.macro_kwargs = {}
        self.break_after_exec = False
        self.chillout_time = 0
        self.chillout_event = None
        self.chillout_active = False
        self.last_matched = 0
        self.processing_lock = threading.Lock()
        super().__init__(_uuid, 'dmatrix_rule', **kwargs)
        super().update_config({'group': 'dm_rules'})

    def get_rkn(self):
        return f'inventory/{self.item_type}/{self.item_id}'

    def serialize(self,
                  full=False,
                  config=False,
                  info=False,
                  props=False,
                  notify=False):
        d = {}
        if info or full:
            c = self.chillout_time + self.last_matched - time.time()
            if c < 0:
                c = 0
            d['chillout_ends_in'] = c
        d['enabled'] = self.enabled
        d['priority'] = self.priority
        d['for_item_type'] = self.for_item_type
        d['for_item_id'] = self.for_item_id
        d['for_item_group'] = self.for_item_group
        d['for_prop'] = self.for_prop
        d['for_initial'] = self.for_initial
        d['in_range_min'] = self.in_range_min
        d['in_range_max'] = self.in_range_max
        d['in_range_min_eq'] = self.in_range_min_eq
        d['in_range_max_eq'] = self.in_range_max_eq
        d['for_prop_bit'] = self.for_prop_bit
        d['macro'] = self.macro
        d['macro_args'] = self.macro_args
        d['macro_kwargs'] = self.macro_kwargs
        d['break_after_exec'] = self.break_after_exec
        d['chillout_time'] = self.chillout_time
        if not config:
            for_oid = self.for_item_type if self.for_item_type else '#'
            for_oid += ':'
            for_oid += self.for_item_group if self.for_item_group else '#'
            for_oid += '/'
            for_oid += self.for_item_id if self.for_item_id else '#'
            for_oid += '.'
            for_oid += self.for_prop if self.for_prop else '#'
            if self.for_prop_bit is not None:
                for_oid += f'.b{self.for_prop_bit}'
            d['for_oid'] = for_oid
            condition = ''
            cond_eq = False
            if self.in_range_min is not None:
                if isinstance(self.in_range_min, float):
                    try:
                        if self.for_prop == 'status':
                            m = int(self.in_range_min)
                        else:
                            m = self.in_range_min
                    except:
                        m = self.in_range_min
                    if self.in_range_min == self.in_range_max and \
                            self.in_range_min_eq and \
                            self.in_range_max_eq:
                        cond_eq = True
                        condition = 'x == %s' % m
                    else:
                        condition = str(m) + ' <'
                        if self.in_range_min_eq:
                            condition += '='
                        condition += ' x'
                else:
                    condition = 'x == \'%s\'' % self.in_range_min
                    cond_eq = True
            if (self.in_range_min is not None and \
                    isinstance(self.in_range_min, float) or \
                    self.in_range_min is None) and \
                    not cond_eq and \
                    self.in_range_max is not None and \
                    isinstance(self.in_range_max, float):
                if not condition:
                    condition = 'x'
                condition += ' <'
                if self.in_range_max_eq:
                    condition += '='
                if self.for_prop == 'status':
                    m = int(self.in_range_max)
                else:
                    m = self.in_range_max
                condition += ' ' + str(m)
            d['condition'] = condition
        d.update(super().serialize(full=full,
                                   config=config,
                                   info=info,
                                   props=props,
                                   notify=notify))
        if 'group' in d:
            del d['group']
        if 'full_id' in d:
            del d['full_id']
        if 'notify_events' in d:
            del d['notify_events']
        return d

    def update_config(self, data):
        if 'enabled' in data:
            self.enabled = data['enabled']
        if 'priority' in data:
            self.priority = data['priority']
        if 'for_item_type' in data:
            self.for_item_type = data['for_item_type']
        if 'for_item_id' in data:
            self.for_item_id = data['for_item_id']
        if 'for_item_group' in data:
            self.for_item_group = data['for_item_group']
        if 'for_prop' in data:
            self.for_prop = data['for_prop']
        if 'for_initial' in data:
            self.for_initial = data['for_initial']
        if 'in_range_min' in data:
            self.in_range_min = data['in_range_min']
        if 'in_range_max' in data:
            self.in_range_max = data['in_range_max']
        if 'in_range_min_eq' in data:
            self.in_range_min_eq = data['in_range_min_eq']
        if 'in_range_max_eq' in data:
            self.in_range_max_eq = data['in_range_max_eq']
        if 'for_prop_bit' in data:
            self.for_prop_bit = data['for_prop_bit']
        if 'macro' in data:
            self.macro = data['macro']
        if 'macro_args' in data:
            m = data['macro_args']
            if isinstance(m, str):
                try:
                    m = shlex.split(m)
                except:
                    m = m.split(' ')
            elif not m:
                m = []
            self.macro_args = m
        if 'macro_kwargs' in data:
            self.macro_kwargs = dict_from_str(data['macro_kwargs'])
        if 'break_after_exec' in data:
            self.break_after_exec = data['break_after_exec']
        if 'chillout_time' in data:
            self.chillout_time = data['chillout_time']
        super().update_config(data)

    def set_hri(self, v, save=False):

        def parse_str(s):
            item_oids = ['unit', 'sensor', 'lvar']
            if isinstance(s, str):
                d = s.strip().split()
            else:
                d = s.copy()
            if len(d) < 2 or d[0] != 'if':
                raise ValueError('Invalid string')
            c_oid = None
            condition = None
            run = None
            for a, z in enumerate(d[1:]):
                if z == 'then':
                    condition = ' '.join(d[1:a + 1])
                    run = ' '.join(d[a + 2:])
                    break
                else:
                    for i in item_oids:
                        if z.startswith(i + ':'):
                            c_oid = z
                            d[a + 1] = 'x'
                            break
            if not c_oid:
                raise ValueError('Condition not found')
            if not condition:
                condition = ' '.join(d[1:])
            return c_oid, condition, run

        try:
            o, c, r = parse_str(v)
        except Exception as e:
            raise FunctionFailed(e)
        if not self.set_prop('oid', o):
            raise FunctionFailed('Unable to set rule oid')
        if not self.set_prop('condition', c):
            raise FunctionFailed('Unable to set rule condition')
        if r:
            try:
                name, args, kwargs = parse_func_str(r)
            except Exception as e:
                raise FunctionFailed(e)
            if not self.set_prop('macro', name):
                raise FunctionFailed('Unable to set rule macro')
            if not self.set_prop('macro_args', args):
                raise FunctionFailed('Unable to set rule macro args')
            if not self.set_prop('macro_kwargs', kwargs):
                raise FunctionFailed('Unable to set rule macro kwargs')
        if save:
            self.save()
        return True

    def set_prop(self, prop, val=None, save=False):
        if prop == 'enabled':
            v = val_to_boolean(val)
            if v is not None:
                if self.enabled != v:
                    self.enabled = v
                    self.log_set(prop, v)
                    self.set_modified(save)
                return True
            else:
                return False
        elif prop in ['c', 'cond', 'condition']:
            try:
                d = self.parse_rule_condition(val)
                for k, v in d.items():
                    try:
                        if not self.set_prop(k, v):
                            return False
                    except:
                        eva.core.log_traceback()
                        return False
                return True
            except Exception as e:
                logging.error('Unable to parse condition: {}'.format(e))
                eva.core.log_traceback()
                return False
        elif prop in ['o', 'oid', 'for_oid', 'for']:
            try:
                d = self.parse_rule_for_oid(val)
                for k, v in d.items():
                    try:
                        if not self.set_prop(k, v):
                            return False
                    except:
                        eva.core.log_traceback()
                        return False
                return True
            except Exception as e:
                logging.error('Unable to parse for_oid: {}'.format(e))
                eva.core.log_traceback()
                return False
        elif prop == 'for_expire':
            if not self.in_range_max_eq or \
                    self.in_range_min_eq or \
                    self.in_range_min is not None or \
                    self.in_range_max != -1 or \
                    self.for_prop != 'status' or \
                    not isinstance(self.in_range_max, float):
                self.in_range_min_eq = False
                self.in_range_max_eq = True
                self.in_range_min = None
                self.in_range_max = -1.0
                self.for_prop = 'status'
                self.log_set(prop, val)
                self.set_modified(save)
            return True
        elif prop == 'for_set':
            if not self.in_range_max_eq or \
                    not self.in_range_min_eq or \
                    self.in_range_min != 1 or \
                    self.in_range_max != 1 or \
                    self.for_prop != 'status' or \
                    not isinstance(self.in_range_min, float) or \
                    not isinstance(self.in_range_max, float):
                self.in_range_min_eq = True
                self.in_range_max_eq = True
                self.in_range_min = 1.0
                self.in_range_max = 1.0
                self.for_prop = 'status'
                self.log_set(prop, val)
                self.set_modified(save)
            return True
        elif prop == 'priority':
            try:
                v = int(val)
                if v <= 0:
                    return False
            except:
                return False
            if self.priority != v:
                self.priority = v
                self.log_set(prop, v)
                self.set_modified(save)
            return True
        elif prop == 'for_item_type':
            if val is not None:
                if val == 'U':
                    v = 'unit'
                elif val == 'S':
                    v = 'sensor'
                elif val == 'LV':
                    v = 'lvar'
                else:
                    v = val
                if not v in ['#', 'unit', 'sensor', 'lvar']:
                    return False
            else:
                v = None
            if self.for_item_type != v:
                self.for_item_type = v
                self.log_set(prop, v)
                self.set_modified(save)
            return True
        elif prop == 'for_item_id':
            if self.for_item_id != val:
                self.for_item_id = val
                self.log_set(prop, val)
                self.set_modified(save)
            return True
        elif prop == 'for_item_group':
            if self.for_item_group != val:
                self.for_item_group = val
                self.log_set(prop, val)
                self.set_modified(save)
            return True
        elif prop == 'for_prop':
            if val not in ['status', 'value', 'nstatus', 'nvalue']:
                return False
            if self.for_prop != val:
                self.for_prop = val
                self.log_set(prop, val)
                self.set_modified(save)
            return True
        elif prop == 'for_initial':
            if val is not None and \
                    val not in [ 'only', 'skip', 'any', 'none', 'None' ]:
                return False
            v = val
            if v in ['any', 'none', 'None']:
                v = None
            if self.for_initial != v:
                self.for_initial = v
                self.log_set(prop, v)
                self.set_modified(save)
            return True
        elif prop == 'in_range_min':
            if val is not None and val != '':
                try:
                    v = float(val)
                except:
                    if self.for_prop == 'status':
                        return False
                    v = val
            else:
                v = None
            if self.in_range_min != v:
                self.in_range_min = v
                self.log_set(prop, v)
                self.set_modified(save)
            return True
        elif prop == 'in_range_max':
            if val is not None and val != '':
                try:
                    v = float(val)
                except:
                    if self.for_prop == 'status':
                        return False
                    v = val
            else:
                v = None
            if self.in_range_max != v:
                self.in_range_max = v
                self.log_set(prop, v)
                self.set_modified(save)
            return True
        elif prop == 'in_range_min_eq':
            v = val_to_boolean(val)
            if v is not None:
                if self.in_range_min_eq != v:
                    self.in_range_min_eq = v
                    self.log_set(prop, v)
                    self.set_modified(save)
                return True
            else:
                return False
        elif prop == 'in_range_max_eq':
            v = val_to_boolean(val)
            if v is not None:
                if self.in_range_max_eq != v:
                    self.in_range_max_eq = v
                    self.log_set(prop, v)
                    self.set_modified(save)
                return True
            else:
                return False
        elif prop == 'for_prop_bit':
            try:
                if val is None or val == '':
                    v = None
                else:
                    v = int(val)
                    if v < 0:
                        raise ValueError('bit number can not be negative')
                if self.for_prop_bit != v:
                    self.for_prop_bit = v
                    self.log_set(prop, v)
                    self.set_modified(save)
                return True
            except:
                eva.core.log_traceback()
                return False
        elif prop == 'macro':
            if self.macro != val:
                self.macro = val
                self.log_set(prop, val)
                self.set_modified(save)
            return True
        elif prop == 'macro_args':
            if val is not None:
                if isinstance(val, list):
                    v = val
                elif isinstance(val, tuple):
                    v = list(val)
                else:
                    try:
                        v = shlex.split(val)
                    except:
                        v = val.split(' ')
            else:
                v = []
            self.macro_args = v
            self.log_set(prop, val)
            self.set_modified(save)
            return True
        elif prop == 'macro_kwargs':
            if val is None:
                self.macro_kwargs = {}
            else:
                try:
                    self.macro_kwargs = dict_from_str(val)
                except:
                    return False
            self.log_set(prop, val)
            self.set_modified(save)
            return True
        elif prop == 'break_after_exec':
            v = val_to_boolean(val)
            if v is not None:
                if self.break_after_exec != v:
                    self.break_after_exec = v
                    self.log_set(prop, v)
                    self.set_modified(save)
                return True
            else:
                return False
        elif prop == 'chillout_time':
            try:
                v = float(val)
            except:
                return False
            if self.chillout_time != v:
                self.chillout_time = v
                self.log_set(prop, v)
                self.set_modified(save)
            return True
        return super().set_prop(prop, val, save)

    @staticmethod
    def parse_rule_condition(condition=None):
        r_imi = None
        r_ixi = None
        r_imiq = False
        r_ixiq = False
        if condition:
            c = condition.replace(' ', '').replace('>=', '}').replace(
                '=>',
                '}').replace('<=',
                             '{').replace('=<',
                                          '{').replace('===',
                                                       '=').replace('==', '=')
            vals = re.split('[<>}{=]', c)
            if len(vals) > 1:
                if len(vals) > 3:
                    raise Exception('invalid condition length')
                for i in range(0, len(vals)):
                    v = vals[i]
                    if v == 'x':
                        if len(vals) == 2:
                            s = c[len(vals[0])]
                            if s == '=':
                                r_imi = vals[1 - i]
                                r_ixi = r_imi
                                r_imiq = True
                                r_ixiq = True
                            elif (s in ['}', '>'] and
                                  i == 0) or (s in ['{', '<'] and i == 1):
                                r_imi = vals[1 - i]
                                r_imiq = s in ['}', '{']
                            elif (s in ['}', '>'] and
                                  i == 1) or (s in ['{', '<'] and i == 0):
                                r_ixi = vals[1 - i]
                                r_ixiq = s in ['}', '{']
                        elif len(vals) == 3:
                            if i != 1:
                                raise Exception('invalid condition')
                            s1 = c[len(vals[0])]
                            s2 = c[len(vals[0]) + 2]
                            if s1 and s2 in ['}', '>']:
                                r_ixi = vals[i - 1]
                                r_ixiq = s1 == '}'
                                r_imi = vals[i + 1]
                                r_imiq = s2 == '}'
                            elif s1 and s2 in ['{', '<']:
                                r_imi = vals[i - 1]
                                r_imiq = s1 == '{'
                                r_ixi = vals[i + 1]
                                r_ixiq = s2 == '{'
                            if float(r_ixi) <= float(r_imi):
                                raise Exception('invalid condition')
                        break
        return {
            'in_range_min': r_imi,
            'in_range_min_eq': r_imiq,
            'in_range_max': r_ixi,
            'in_range_max_eq': r_ixiq
        }

    @staticmethod
    def parse_rule_for_oid(param):
        if not param:
            tp, prop, item_id, group = ('#', 'status', '#', '#')
        else:
            tp, full_id_v = param.split(':')
            i = full_id_v.split('/')
            prop = i[-1]
            item_id = i[-2]
            group = '/'.join(i[:-2])
        if tp not in ['unit', 'U', 'sensor', 'S', 'lvar', 'LV', '#']:
            raise Exception('invalid type')
        if '.status.b' in prop or '.value.b' in prop:
            prop, prop_bit = prop.rsplit('.b', 1)
            prop_bit = int(prop_bit)
        else:
            prop_bit = None
        if prop not in ['status', 'value', 'nstatus', 'nvalue']:
            if prop.find('.') == -1:
                raise Exception('invalid state prop')
            else:
                group = group + ('/' if group else '') + item_id
                item_id, prop = prop.rsplit('.', 1)
                if prop not in ['status', 'value', 'nstatus', 'nvalue']:
                    raise Exception('invalid state prop')
        return {
            'for_item_group': group,
            'for_item_type': tp,
            'for_prop': prop,
            'for_prop_bit': prop_bit,
            'for_item_id': item_id
        }
