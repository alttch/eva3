__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"

import cherrypy
import shlex
import eva.core

import eva.api
import eva.sysapi

from eva.api import GenericHTTP_API
from eva.api import JSON_RPC_API_abstract
from eva.api import GenericAPI
from eva.api import GenericCloudAPI

from eva.api import parse_api_params
from eva.api import format_resource_id

from eva.api import api_need_master

from eva.api import api_result_accepted

from eva.api import generic_web_api_method
from eva.api import restful_api_method
from eva.api import set_restful_response_location

from eva.api import MethodNotFound

from eva.api import log_d
from eva.api import log_i
from eva.api import log_w
from eva.api import notify_plugins

from eva.api import key_check
from eva.api import key_check_master

from eva.tools import dict_from_str
from eva.tools import oid_to_id
from eva.tools import parse_oid
from eva.tools import is_oid
from eva.tools import val_to_boolean

from eva.exceptions import FunctionFailed
from eva.exceptions import ResourceNotFound
from eva.exceptions import ResourceBusy
from eva.exceptions import AccessDenied
from eva.exceptions import InvalidParameter

from eva.tools import parse_function_params

from eva import apikey

from functools import wraps

import eva.lm.controller
import eva.lm.extapi
import eva.ei
import jinja2
import logging


class LM_API(GenericAPI, GenericCloudAPI):

    def __init__(self):
        self.controller = eva.lm.controller
        super().__init__()

    @log_d
    @notify_plugins
    def groups(self, **kwargs):
        """
        get item group list

        Get the list of item groups. Useful e.g. for custom interfaces.

        Args:
            k:
            .p: item type (must be set to lvar [LV])
        """
        k, tp = parse_function_params(kwargs,
                                      'kp',
                                      '.S',
                                      defaults={'p': 'lvar'})
        if key_check_master(k, ro_op=True):
            if tp == 'LV' or tp == 'lvar':
                return sorted(eva.lm.controller.lvars_by_group.keys())
            else:
                return []
        else:
            groups = []
            m = None
            if tp == 'LV' or tp == 'lvar':
                m = eva.lm.controller.lvars_by_full_id
            if m:
                for i, v in m.copy().items():
                    if key_check(k, v, ro_op=True) and not v.group in groups:
                        groups.append(v.group)
                return sorted(groups)
            else:
                return []

    @log_d
    @notify_plugins
    def state(self, **kwargs):
        """
        get lvar state

        State of lvar or all lvars can be obtained using state command.

        Args:
            k:

        Optional:
            .p: item type (none or lvar [LV])
            .i: item id
            .g: item group
            .full: return full state
        """
        k, i, group, tp, full = parse_function_params(kwargs,
                                                      'kigpY',
                                                      '.sssb',
                                                      defaults={'p': 'lvar'})
        if tp is None:
            tp = 'lvar'
        elif tp not in ['LV', 'lvar']:
            raise ResourceNotFound
        if i:
            item = eva.lm.controller.get_lvar(i)
            if not item or not key_check(k, item, ro_op=True):
                raise ResourceNotFound
            if is_oid(i):
                t, iid = parse_oid(i)
                if not item or item.item_type != t:
                    raise ResourceNotFound
            return item.serialize(full=full)
        else:
            gi = eva.lm.controller.lvars_by_full_id
            result = []
            for i, v in gi.copy().items():
                if key_check(k, v, ro_op=True) and \
                        (not group or \
                            eva.item.item_match(v, [], [group])):
                    r = v.serialize(full=full)
                    result.append(r)
            return sorted(result, key=lambda k: k['oid'])

    @log_i
    @notify_plugins
    def set(self, **kwargs):
        """
        set lvar state

        Set status and value of a :ref:`logic variable<lvar>`.

        Args:
            k:
            .i: lvar id
        
        Optional:
            s: lvar status
            v: lvar value
        """
        k, i, s, v = parse_function_params(kwargs, 'kisv', '.si.')
        item = eva.lm.controller.get_lvar(i)
        if not item:
            raise ResourceNotFound
        elif not key_check(k, item):
            raise AccessDenied
        from eva.lm.lvar import LOGIC_SIMPLE
        if s and not -1 <= s <= 1 and item.logic != LOGIC_SIMPLE:
            raise InvalidParameter('status should be -1, 0 or 1')
        # if v is None:
        # v = ''
        # else:
        if v is not None:
            v = str(v)
        item.update_set_state(status=s, value=v)
        return True

    @log_i
    @notify_plugins
    def reset(self, **kwargs):
        """
        reset lvar state

        Set status and value of a :ref:`logic variable<lvar>` to *1*. Useful
        when lvar is being used as a timer to reset it, or as a flag to set it
        *True*.

        Args:
            k:
            .i: lvar id
        """
        k, i = parse_function_params(kwargs, 'ki', '.s')
        return self.set(k=k, i=i, s=1, v='1')

    @log_i
    @notify_plugins
    def clear(self, **kwargs):
        """
        clear lvar state

        set status (if **expires** lvar param > 0) or value (if **expires**
        isn't set) of a :ref:`logic variable<lvar>` to *0*. Useful when lvar is
        used as a timer to stop it, or as a flag to set it *False*.

        Args:
            k:
            .i: lvar id
        """
        k, i = parse_function_params(kwargs, 'ki', '.s')
        item = eva.lm.controller.get_lvar(i)
        if not item:
            raise ResourceNotFound
        elif not key_check(k, item):
            raise AccessDenied
        return self.set(k=k, i=i, s=0 if item.expires > 0 else 1, v='0')

    @log_i
    @notify_plugins
    def toggle(self, **kwargs):
        """
        toggle lvar state

        switch value of a :ref:`logic variable<lvar>` between *0* and *1*.
        Useful when lvar is being used as a flag to switch it between
        *True*/*False*.

        Args:
            k:
            .i: lvar id
        """
        k, i = parse_function_params(kwargs, 'ki', '.s')
        item = eva.lm.controller.get_lvar(i)
        if not item:
            raise ResourceNotFound
        elif not key_check(k, item):
            raise AccessDenied
        v = item.value
        if v != '0':
            return self.clear(k=k, i=i)
        else:
            return self.reset(k=k, i=i)

    @log_i
    @notify_plugins
    def increment(self, **kwargs):
        """
        increment lvar value

        Increment value of a :ref:`logic variable<lvar>`. Initial value should
        be number

        Args:
            k:
            .i: lvar id
        """
        k, i, = parse_function_params(kwargs, 'ki', '.s')
        item = eva.lm.controller.get_lvar(i)
        if not item:
            raise ResourceNotFound
        elif not key_check(k, item):
            raise AccessDenied
        return item.increment()

    @log_i
    @notify_plugins
    def decrement(self, **kwargs):
        """
        decrement lvar value

        Decrement value of a :ref:`logic variable<lvar>`. Initial value should
        be number

        Args:
            k:
            .i: lvar id
        """
        k, i, = parse_function_params(kwargs, 'ki', '.s')
        item = eva.lm.controller.get_lvar(i)
        if not item:
            raise ResourceNotFound
        elif not key_check(k, item):
            raise AccessDenied
        return item.decrement()

    @log_i
    @notify_plugins
    def run(self, **kwargs):
        """
        execute macro

        Execute a :doc:`macro<macros>` with the specified arguments.

        Args:
            k:
            .i: macro id

        Optional:
            a: macro arguments, array or space separated
            kw: macro keyword arguments, name=value, comma separated or dict
            w: wait for the completion for the specified number of seconds
            .u: action UUID (will be auto generated if none specified)
            p: queue priority (default is 100, lower is better)
            q: global queue timeout, if expires, action is marked as "dead"
        """
        k, i, a, kw, w, u, p, q = parse_function_params(kwargs, 'kiaKwupq',
                                                        '.s..nsin')
        macro = eva.lm.controller.get_macro(i, pfm=True)
        if not macro:
            raise ResourceNotFound
        elif not key_check(k, macro):
            raise AccessDenied
        if a is None:
            a = []
        else:
            if isinstance(a, list):
                pass
            elif isinstance(a, str):
                try:
                    a = shlex.split(a)
                except:
                    a = a.split(' ')
            else:
                a = [a]
        if isinstance(kw, str):
            try:
                kw = dict_from_str(kw)
            except:
                raise InvalidParameter('Unable to parse kw args')
        elif isinstance(kw, dict):
            pass
        else:
            kw = {}
        return self._process_action_result(
            eva.lm.controller.exec_macro(macro=macro,
                                         argv=a,
                                         kwargs=kw,
                                         priority=p,
                                         q_timeout=q,
                                         wait=w,
                                         action_uuid=u))

    @log_i
    @notify_plugins
    def result(self, **kwargs):
        """
        macro execution result

        Get :doc:`macro<macros>` execution results either by action uuid or by
        macro id.

        Args:
            k:

        Optional:
            .u: action uuid or
            .i: macro id
            g: filter by unit group
            s: filter by action status: Q for queued, R for running, F for
               finished

        Returns:
            list or single serialized action object
        """
        k, u, i, g, s = parse_function_params(kwargs, 'kuigs', '.ssss')
        return self._result(k, u, i, g, s, rtp='lmacro')

# dm rules functions

    @log_i
    @api_need_master
    @notify_plugins
    def create_rule(self, **kwargs):
        """
        create new rule

        Creates new :doc:`decision rule<decision_matrix>`. Rule id (UUID) is
        generated automatically unless specified.

        Args:
            k: .master

        Optional:
            .u: rule UUID to set
            .v: rule properties (dict) or human-readable input
            .e: enable rule after creation
            save: save rule configuration immediately
        """
        u, v, e, save = parse_api_params(kwargs, 'uveS', 's.bb')
        rule = eva.lm.controller.create_dm_rule(save=False, rule_uuid=u)
        if e:
            rule.set_prop('enabled', True)
        if save:
            rule.save()
        try:
            if v:
                if isinstance(v, dict):
                    self._set_prop(rule, v=v, save=save)
                else:
                    rule.set_hri(v, save=save)
        except:
            eva.core.log_traceback()
            eva.lm.controller.destroy_dm_rule(rule.item_id)
            raise
        return rule.serialize(info=True)

    @log_w
    @api_need_master
    @notify_plugins
    def destroy_rule(self, k=None, i=None):
        """
        delete rule

        Deletes :doc:`decision rule<decision_matrix>`.

        Args:
            k: .master
            .i: rule id
        """
        return eva.lm.controller.destroy_dm_rule(i)

    @log_d
    @notify_plugins
    def list_rule_props(self, **kwargs):
        """
        list rule properties

        Get all editable parameters of the :doc:`decision
        rule</lm/decision_matrix>`.

        Args:
            k:
            .i: rule id
        """
        k, i = parse_function_params(kwargs, 'ki', '.s')
        if is_oid(i):
            t, i = parse_oid(i)
        item = eva.lm.controller.get_dm_rule(i)
        if not item or (is_oid(i) and item and item.item_type != t):
            raise ResourceNotFound
        if not key_check(k, item, ro_op=True):
            raise ResourceNotFound
        result = item.serialize(props=True)
        if not key_check_master(k):
            for i in result:
                if i[:9] != 'in_range_' and \
                        i not in [ 'enabled', 'chillout_time', 'condition' ]:
                    del result[i]
        return result

    @log_i
    @notify_plugins
    def set_rule_prop(self, **kwargs):
        """
        set rule parameters

        Set configuration parameters of the :doc:`decision
        rule</lm/decision_matrix>`.

        .. note::

            Master key is required for batch set.

        Args:
        
            k:
            .i: rule id
            .p: property name (or empty for batch set)
        
        Optional:
            .v: propery value (or dict for batch set)
            save: save configuration after successful call
        """
        k, i, p, v, save = parse_function_params(kwargs, 'kipvS', '.s..b')
        item = eva.lm.controller.get_dm_rule(i)
        if not p and (not isinstance(v, dict) or not key_check_master(k)):
            raise InvalidParameter('property not specified')
        if not item:
            raise ResourceNotFound
        if p:
            if p[:9] == 'in_range_' or p in ['enabled', 'chillout_time']:
                if not key_check(k, item):
                    raise ResourceNotFound
        else:
            if not key_check_master(k):
                raise ResourceNotFound
        if not self._set_prop(item, p, v, save):
            raise FunctionFailed
        if (p and p in ['priority', 'description']) or \
                (isinstance(v, dict) and \
                    ('property' in v or 'description' in v)):
            eva.lm.controller.DM.sort()
        return True

    @log_i
    @notify_plugins
    def list_rules(self, **kwargs):
        """
        get rules list

        Get the list of all available :doc:`decision rules<decision_matrix>`.

        Args:
            k:
        """
        k = parse_function_params(kwargs, 'k', '.')
        result = []
        for i in eva.lm.controller.DM.rules.copy():
            if key_check(k, i, ro_op=True):
                d = i.serialize(info=True)
                if not key_check_master(k):
                    for x in d.copy():
                        if x[:9] != 'in_range_' and \
                                x not in [
                                        'id',
                                        'condition',
                                        'description',
                                        'chillout_ends_in',
                                        'enabled',
                                        'chillout_time'
                                        ]:
                            del d[x]
                result.append(d)
        return result

    @log_i
    @notify_plugins
    def get_rule(self, **kwargs):
        """
        get rule information

        Args:
            k:
            .i: rule id
        """
        k, i = parse_function_params(kwargs, 'ki', '.s')
        item = eva.lm.controller.get_dm_rule(i)
        if not item or not key_check(k, item, ro_op=True):
            raise ResourceNotFound
        d = item.serialize(info=True)
        if not key_check_master(k):
            for x in d.copy():
                if x[:9] != 'in_range_' and x not in [
                        'id', 'condition', 'description', 'chillout_ends_in',
                        'enabled', 'chillout_time'
                ]:
                    del d[x]
        return d

# jobs functions

    @log_i
    @api_need_master
    @notify_plugins
    def create_job(self, **kwargs):
        """
        create new job

        Creates new :doc:`scheduled job<jobs>`. Job id (UUID) is
        generated automatically unless specified.

        Args:
            k: .master

        Optional:
            .u: job UUID to set
            .v: job properties (dict) or human-readable input
            .e: enable job after creation
            save: save job configuration immediately
        """
        u, v, e, save = parse_api_params(kwargs, 'uveS', 's.bb')
        job = eva.lm.controller.create_job(save=False, job_uuid=u)
        if e:
            job.set_prop('enabled', True)
        if save:
            job.save()
        try:
            if v:
                if isinstance(v, dict):
                    self._set_prop(job, v=v, save=save)
                else:
                    job.set_hri(v, save=save)
        except:
            eva.core.log_traceback()
            eva.lm.controller.destroy_job(job.item_id)
            raise
        return job.serialize(info=True)

    @log_w
    @api_need_master
    @notify_plugins
    def destroy_job(self, k=None, i=None):
        """
        delete job

        Deletes :doc:`scheduled job<jobs>`.

        Args:
            k: .master
            .i: job id
        """
        return eva.lm.controller.destroy_job(i)

    @log_d
    @api_need_master
    @notify_plugins
    def list_job_props(self, **kwargs):
        """
        list job properties

        Get all editable parameters of the :doc:`scheduled job</lm/jobs>`.

        Args:
            k: .master
            .i: job id
        """
        k, i = parse_function_params(kwargs, 'ki', '.s')
        if is_oid(i):
            t, i = parse_oid(i)
        item = eva.lm.controller.get_job(i)
        if not item or (is_oid(i) and item and item.item_type != t):
            raise ResourceNotFound
        result = item.serialize(props=True)
        return result

    @log_i
    @api_need_master
    @notify_plugins
    def set_job_prop(self, **kwargs):
        """
        set job parameters

        Set configuration parameters of the :doc:`scheduled job</lm/jobs>`.

        Args:
        
            k: .master
            .i: job id
            .p: property name (or empty for batch set)
        
        Optional:
            .v: propery value (or dict for batch set)
            save: save configuration after successful call
        """
        k, i, p, v, save = parse_function_params(kwargs, 'kipvS', '.s..b')
        item = eva.lm.controller.get_job(i)
        if not p and not isinstance(v, dict):
            raise InvalidParameter('property not specified')
        if not item:
            raise ResourceNotFound
        if not self._set_prop(item, p, v, save):
            raise FunctionFailed
        if (p and p in ['every']) or \
                (isinstance(v, dict) and \
                ('every' in v)):
            item.reschedule()
        return True

    @log_i
    @api_need_master
    @notify_plugins
    def list_jobs(self, **kwargs):
        """
        get jobs list

        Get the list of all available :doc:`scheduled jobs<jobs>`.

        Args:
            k: .master
        """
        k = parse_function_params(kwargs, 'k', '.')
        result = []
        for i, v in eva.lm.controller.jobs.copy().items():
            d = v.serialize(info=True)
            result.append(d)
        return result

    @log_i
    @api_need_master
    @notify_plugins
    def get_job(self, **kwargs):
        """
        get job information

        Args:
            k: .master
            .i: job id
        """
        k, i = parse_function_params(kwargs, 'ki', '.s')
        item = eva.lm.controller.get_job(i)
        if not item:
            raise ResourceNotFound
        d = item.serialize(info=True)
        return d
# macro functions

    @log_d
    @api_need_master
    @notify_plugins
    def get_macro_function(self, **kwargs):
        i = parse_api_params(kwargs, 'i', 'S')
        f = eva.lm.controller.get_macro_function(i)
        if not f:
            raise ResourceNotFound
        return f

    @log_d
    @api_need_master
    @notify_plugins
    def list_macro_functions(self, **kwargs):
        fn = eva.lm.controller.get_macro_function()
        result = []
        for f, v in fn.items():
            v = v.copy()
            del v['src']
            result.append(v)
        return sorted(result, key=lambda k: k['name'])

    @log_w
    @api_need_master
    @notify_plugins
    def put_macro_function(self, **kwargs):
        name, description, i, o, code = parse_api_params(
            kwargs, ['function', 'description', 'input', 'output', 'src'],
            'ss...')
        fname = eva.lm.controller.put_macro_function(fname=name,
                                                     fdescr=description,
                                                     i=i,
                                                     o=o,
                                                     fcode=code)
        if not fname:
            raise FunctionFailed
        return eva.lm.controller.get_macro_function(fname)

    @log_i
    @api_need_master
    @notify_plugins
    def reload_macro_function(self, **kwargs):
        i, tp = parse_api_params(kwargs, 'ip', 'ss')
        if not eva.lm.controller.reload_macro_function(fname=i, tp=tp):
            raise FunctionFailed
        else:
            return True

    @log_w
    @api_need_master
    @notify_plugins
    def destroy_macro_function(self, **kwargs):
        i = parse_api_params(kwargs, 'i', 'S')
        return eva.lm.controller.destroy_macro_function(i)

# macros

    @log_d
    @notify_plugins
    def groups_macro(self, **kwargs):
        """
        get macro groups list


        Get the list of macros. Useful e.g. for custom interfaces.

        Args:
            k:
        """
        k = parse_function_params(kwargs, 'k', '.')
        result = []
        for i, v in eva.lm.controller.macros_by_id.copy().items():
            if key_check(k, v) and \
                    v.group not in result:
                result.append(v.group)
        return sorted(result)

    @log_d
    @notify_plugins
    def list_macros(self, **kwargs):
        """
        get macro list

        Get the list of all available :doc:`macros<macros>`.

        Args:
            k:

        Optional:
            .g: filter by group
        """
        k, group = parse_function_params(kwargs, 'kg', '.s')
        result = []
        for i, v in eva.lm.controller.macros_by_id.copy().items():
            if key_check(k, v) and \
                    (not group or eva.item.item_match(v, [], [ group ])):
                result.append(v.serialize(info=True))
        return sorted(result, key=lambda k: k['full_id'])

    @log_i
    @api_need_master
    @notify_plugins
    def create_macro(self, **kwargs):
        """
        create new macro

        Creates new :doc:`macro<macros>`. Macro code should be put in **xc/lm**
        manually.

        Args:
            k: .master
            .i: macro id

        Optional:
            .g: macro group
        """
        k, i, g, save = parse_function_params(kwargs, 'kigS', '.Ssb')
        return eva.lm.controller.create_macro(i, g, save).serialize()

    @log_w
    @api_need_master
    @notify_plugins
    def destroy_macro(self, **kwargs):
        """
        delete macro

        Deletes :doc:`macro<macros>`.

        Args:
            k: .master
            .i: macro id
        """
        i = parse_api_params(kwargs, 'i', 'S')
        return eva.lm.controller.destroy_macro(i)

    @log_i
    @api_need_master
    @notify_plugins
    def list_macro_props(self, **kwargs):
        """
        get macro configuration properties

        Args:
            k: .master
            .i: macro id
        """
        i = parse_api_params(kwargs, 'i', 'S')
        item = eva.lm.controller.get_macro(i)
        if not item:
            raise ResourceNotFound
        return item.serialize(props=True)

    @log_i
    @api_need_master
    @notify_plugins
    def set_macro_prop(self, **kwargs):
        """
        set macro configuration property

        Set configuration parameters of the :doc:`macro<macros>`.

        Args:
            k: .master
            .i: item id
            .p: property name (or empty for batch set)
        
        Optional:
            .v: propery value (or dict for batch set)
            save: save configuration after successful call
        """
        i, p, v, save = parse_api_params(kwargs, 'ipvS', 's..b')
        if not p and not isinstance(v, dict):
            raise InvalidParameter('property not specified')
        if is_oid(i):
            t, i = parse_oid(i)
        macro = eva.lm.controller.get_macro(i)
        if not macro or (is_oid(i) and macro and macro.macro_type != t):
            raise ResourceNotFound
        return self._set_prop(macro, p, v, save)

    @log_d
    @notify_plugins
    def get_macro(self, **kwargs):
        """
        get macro information

        Args:
            k:
            .i: macro id
        """
        k, i = parse_function_params(kwargs, 'ki', '.S')
        item = eva.lm.controller.get_macro(i)
        if not item or not key_check(k, item):
            raise ResourceNotFound
        result = item.serialize(info=True)
        if key_check_master(k):
            t, s = eva.lm.controller.get_macro_source(item)
            result['src'] = s
            if t:
                result['type'] += ':' + t
        return result

# cycle functions

    @log_d
    @notify_plugins
    def groups_cycle(self, **kwargs):
        """
        get cycle groups list


        Get the list of cycles. Useful e.g. for custom interfaces.

        Args:
            k:
        """
        k = parse_function_params(kwargs, 'k', '.')
        result = []
        for i, v in eva.lm.controller.cycles_by_id.copy().items():
            if key_check(k, v, ro_op=True) and \
                    v.group not in result:
                result.append(v.group)
        return sorted(result)

    @log_d
    @notify_plugins
    def list_cycles(self, **kwargs):
        """
        get cycle list

        Get the list of all available :doc:`cycles<cycles>`.

        Args:
            k:

        Optional:
            .g: filter by group
        """
        k, group = parse_function_params(kwargs, 'kg', '.s')
        result = []
        for i, v in eva.lm.controller.cycles_by_id.copy().items():
            if key_check(k, v, ro_op=True) and \
                    (not group or eva.item.item_match(v, [], [ group ])):
                result.append(v.serialize(info=True))
        return sorted(result, key=lambda k: k['full_id'])

    @log_i
    @api_need_master
    @notify_plugins
    def create_cycle(self, **kwargs):
        """
        create new cycle

        Creates new :doc:`cycle<cycles>`.

        Args:
            k: .master
            .i: cycle id

        Optional:
            .g: cycle group
            .v: cycle properties (dict) or human-readable input
        """
        k, i, g, v, save = parse_function_params(kwargs, 'kigvS', '.Ss.b')
        cycle = eva.lm.controller.create_cycle(i, g, save)
        try:
            if v:
                if isinstance(v, dict):
                    self._set_prop(cycle, v=v, save=save)
                else:
                    cycle.set_hri(v, save=save)
        except:
            eva.core.log_traceback()
            eva.lm.controller.destroy_cycle(cycle.item_id)
            raise
        return cycle.serialize(info=True)

    @log_w
    @api_need_master
    @notify_plugins
    def destroy_cycle(self, **kwargs):
        """
        delete cycle

        Deletes :doc:`cycle<cycles>`. If cycle is running, it is stopped before
        deletion.

        Args:
            k: .master
            .i: cycle id
        """
        i = parse_api_params(kwargs, 'i', 'S')
        return eva.lm.controller.destroy_cycle(i)

    @log_i
    @api_need_master
    @notify_plugins
    def list_cycle_props(self, **kwargs):
        """
        get cycle configuration properties

        Args:
            k: .master
            .i: cycle id
        """
        i = parse_api_params(kwargs, 'i', 'S')
        item = eva.lm.controller.get_cycle(i)
        if not item:
            raise ResourceNotFound
        return item.serialize(props=True)

    @log_i
    @api_need_master
    @notify_plugins
    def set_cycle_prop(self, **kwargs):
        """
        set cycle property

        Set configuration parameters of the :doc:`cycle<cycles>`.

        Args:
            k: .master
            .i: item id
            .p: property name (or empty for batch set)
        
        Optional:
            .v: propery value (or dict for batch set)
            save: save configuration after successful call
        """
        i, p, v, save = parse_api_params(kwargs, 'ipvS', 's..b')
        if not p and not isinstance(v, dict):
            raise InvalidParameter('property not specified')
        if is_oid(i):
            t, i = parse_oid(i)
        cycle = eva.lm.controller.get_cycle(i)
        if not cycle or (is_oid(i) and cycle and cycle.cycle_type != t):
            raise ResourceNotFound
        return self._set_prop(cycle, p, v, save)

    @log_d
    @notify_plugins
    def get_cycle(self, **kwargs):
        """
        get cycle information

        Args:
            k:
            .i: cycle id

        Returns:
            field "value" contains real average cycle interval
        """
        k, i = parse_function_params(kwargs, 'ki', '.S')
        item = eva.lm.controller.get_cycle(i)
        if not item or not key_check(k, item, ro_op=True):
            raise ResourceNotFound
        return item.serialize(info=True)

    @log_i
    @notify_plugins
    def start_cycle(self, **kwargs):
        """
        start cycle

        Args:
            k:
            .i: cycle id
        """
        k, i = parse_function_params(kwargs, 'ki', '.S')
        cycle = eva.lm.controller.get_cycle(i)
        if not cycle:
            raise ResourceNotFound
        elif not key_check(k, cycle):
            raise AccessDenied
        if cycle.cycle_status:
            raise ResourceBusy('cycle is already started')
        return cycle.start()

    @log_i
    @notify_plugins
    def stop_cycle(self, **kwargs):
        """
        stop cycle

        Args:
            k:
            .i: cycle id

        Optional:
            wait: wait until cycle is stopped
        """
        k, i, wait = parse_function_params(kwargs, 'kiW', '.Sb')
        cycle = eva.lm.controller.get_cycle(i)
        if not cycle:
            raise ResourceNotFound
        elif not key_check(k, cycle):
            raise AccessDenied
        cycle.stop(wait=wait)
        return (True, api_result_accepted) if not wait else True

    @log_i
    @notify_plugins
    def reset_cycle_stats(self, **kwargs):
        """
        reset cycle statistic

        Args:
            k:
            .i: cycle id
        """
        k, i = parse_function_params(kwargs, 'ki', '.S')
        cycle = eva.lm.controller.get_cycle(i)
        if not cycle:
            raise ResourceNotFound
        elif not key_check(k, cycle):
            raise AccessDenied
        cycle.reset_stats()
        return True

# lvars

    @log_i
    @api_need_master
    @notify_plugins
    def get_config(self, **kwargs):
        """
        get lvar configuration

        Args:
            k: .master
            .i: lvaar id

        Returns:
            complete :ref:`lvar<lvar>` configuration.
        """
        i = parse_api_params(kwargs, 'i', 's')
        if is_oid(i):
            t, i = parse_oid(i)
        item = eva.lm.controller.get_item(i)
        if not item or (is_oid(i) and item and item.item_type != t):
            raise ResourceNotFound
        return item.serialize(config=True)

    @log_i
    @api_need_master
    @notify_plugins
    def save_config(self, **kwargs):
        """
        save lvar configuration

        Saves :ref:`lvar<lvar>`. configuration on disk (even if it hasn't been
        changed)

        Args:
            k: .master
            .i: lvar id
        """
        i = parse_api_params(kwargs, 'i', 's')
        if is_oid(i):
            t, i = parse_oid(i)
        item = eva.lm.controller.get_item(i)
        if not item or (is_oid(i) and item and item.item_type != t):
            raise ResourceNotFound
        item = eva.lm.controller.get_item(i)
        return item.save()

    @log_i
    @api_need_master
    @notify_plugins
    def list(self, **kwargs):
        """
        list lvars

        Args:
            k: .master

        Optional:
            .g: filter by item group
            x: serialize specified item prop(s)

        Returns:
            the list of all :ref:`lvars<lvar>` available
        """
        tp, group, prop = parse_api_params(kwargs, 'pgx', 'ss.', {'p': 'lvar'})
        if prop:
            if isinstance(prop, list):
                pass
            elif isinstance(prop, str):
                prop = prop.split(',')
            else:
                raise InvalidParameter('"x" must be list or string')
        result = []
        if tp == 'LV' or tp == 'lvar':
            items = eva.lm.controller.lvars_by_full_id
        else:
            items = eva.lm.controller.items_by_full_id
        for i, v in items.copy().items():
            if not group or eva.item.item_match(v, [], [group]):
                if not prop:
                    result.append(v.serialize(info=True))
                else:
                    r = {'oid': v.oid}
                    s = v.serialize(props=True)
                    for p in prop:
                        try:
                            r[p] = s[p]
                        except:
                            raise ResourceNotFound('{}: config prop {}'.format(
                                v.oid, p))
                    result.append(r)
        result = sorted(result, key=lambda k: k['oid'])
        if prop:
            for s in reversed(prop):
                try:
                    result = sorted(result, key=lambda k: k[s])
                except:
                    pass
        return result

    @log_i
    @api_need_master
    @notify_plugins
    def list_props(self, **kwargs):
        """
        list lvar properties

        Get all editable parameters of the :ref:`lvar<lvar>` confiugration.

        Args:
            k: .master
            .i: item id
        """
        i = parse_api_params(kwargs, 'i', 's')
        if is_oid(i):
            t, i = parse_oid(i)
        item = eva.lm.controller.get_item(i)
        if not item or (is_oid(i) and item and item.item_type != t):
            raise ResourceNotFound
        return item.serialize(props=True)

    @log_i
    @api_need_master
    @notify_plugins
    def set_prop(self, **kwargs):
        """
        set lvar property

        Set configuration parameters of the :ref:`lvar<lvar>`.

        Args:
            k: .master
            .i: item id
            .p: property name (or empty for batch set)
        
        Optional:
            .v: propery value (or dict for batch set)
            save: save configuration after successful call
        """
        i, p, v, save = parse_api_params(kwargs, 'ipvS', 's..b')
        if not p and not isinstance(v, dict):
            raise InvalidParameter('property not specified')
        if is_oid(i):
            t, i = parse_oid(i)
        item = eva.lm.controller.get_item(i)
        if not item or (is_oid(i) and item and item.item_type != t):
            raise ResourceNotFound
        return self._set_prop(item, p, v, save)

    @log_i
    @api_need_master
    @notify_plugins
    def create_lvar(self, **kwargs):
        """
        create lvar

        Create new :ref:`lvar<lvar>`

        Args:
            k: .master
            .i: lvar id

        Optional:
            .g: lvar group
            save: save lvar configuration immediately
        """
        i, g, save = parse_api_params(kwargs, 'igS', 'Ssb')
        return eva.lm.controller.create_lvar(lvar_id=oid_to_id(i, 'lvar'),
                                             group=g,
                                             save=save).serialize()

    @log_i
    @api_need_master
    @notify_plugins
    def create(self, **kwargs):
        """
        alias for create_lvar
        """
        return self.create_lvar(**kwargs)

    @log_w
    @api_need_master
    @notify_plugins
    def destroy_lvar(self, **kwargs):
        """
        delete lvar

        Args:
            k: .master
            .i: lvar id
        """
        i, g = parse_api_params(kwargs, 'ig', 'ss')
        if not i and not g:
            raise InvalidParameter('either lvar id or group must be specified')
        return eva.lm.controller.destroy_item(i) if i \
                else eva.lm.controller.destroy_group(g)

    @log_w
    @api_need_master
    @notify_plugins
    def destroy(self, **kwargs):
        """
        alias for destroy_lvar
        """
        return self.destroy_lvar(**kwargs)

# controller management

    @log_i
    @api_need_master
    @notify_plugins
    def list_remote(self, **kwargs):
        """
        get a list of items from connected UCs

        Get a list of the items loaded from the connected :ref:`UC
        controllers<lm_remote_uc>`. Useful to debug the controller
        connections.

        Args:
            k: .master

        Optional:
            .i: controller id
            g: filter by item group
            p: filter by item type
        """
        i, group, tp = parse_api_params(kwargs, 'igp', 'sss')
        result = []
        items = []
        if i:
            controller = eva.lm.controller.get_controller(i)
            if not controller:
                raise ResourceNotFound('controller {}'.format(i))
            c_id = controller.item_id
        if tp is None or tp in ['U', 'unit', '#']:
            if i:
                if not c_id in eva.lm.controller.uc_pool.units_by_controller:
                    return []
                items.append(
                    eva.lm.controller.uc_pool.units_by_controller[c_id])
            else:
                items.append(eva.lm.controller.uc_pool.units_by_controller)
        if tp is None or tp in ['S', 'sensor', '#']:
            if i:
                if not c_id in eva.lm.controller.uc_pool.sensors_by_controller:
                    return []
                items.append(
                    eva.lm.controller.uc_pool.sensors_by_controller[c_id])
            else:
                items.append(eva.lm.controller.uc_pool.sensors_by_controller)
        if not items:
            return []
        if i:
            for x in items:
                for a, v in x.copy().items():
                    if not group or eva.item.item_match(v, [], [group]):
                        result.append(v.serialize(full=True))
        else:
            for x in items:
                for c, d in x.copy().items():
                    for a, v in d.copy().items():
                        if not group or eva.item.item_match(v, [], [group]):
                            result.append(v.serialize(full=True))
        return sorted(sorted(result, key=lambda k: k['oid']),
                      key=lambda k: ['controller_id'])

    @log_i
    @api_need_master
    @notify_plugins
    def list_controllers(self, **kwargs):
        """
        get controllers list

        Get the list of all connected :ref:`UC controllers<lm_remote_uc>`.

        Args:
            k: .master
        """
        result = []
        for i, v in eva.lm.controller.remote_ucs.copy().items():
            result.append(v.serialize(info=True))
        return sorted(result, key=lambda k: k['full_id'])

    @log_i
    @api_need_master
    @notify_plugins
    def append_controller(self, **kwargs):
        """
        connect remote UC via HTTP

        Connects remote :ref:`UC controller<lm_remote_uc>` to the local.

        Args:
            k: .master
            u: :doc:`/uc/uc_api` uri (*proto://host:port*, port not required
                if default)
            a: remote controller API key (\$key to use local key)

        Optional:
            m: ref:`MQTT notifier<mqtt_>` to exchange item states in real time
                (default: *eva_1*)
            s: verify remote SSL certificate or pass invalid
            t: timeout (seconds) for the remote controller API calls
            save: save connected controller configuration on the disk
                immediately after creation
        """
        uri, key, mqtt_update, ssl_verify, timeout, save = parse_api_params(
            kwargs, 'uamstS', 'Sssbnb')
        c = eva.lm.controller.append_controller(uri=uri,
                                                key=key,
                                                mqtt_update=mqtt_update,
                                                ssl_verify=ssl_verify,
                                                timeout=timeout,
                                                save=save)
        if not c:
            raise FunctionFailed
        return c.serialize(info=True)

    @log_i
    @api_need_master
    @notify_plugins
    def reload_controller(self, **kwargs):
        """
        reload controller

        Reloads items from connected UC

        Args:
            k: .master
            .i: controller id
        """
        i = parse_api_params(kwargs, 'i', 'S')
        controller = eva.lm.controller.get_controller(i)
        return eva.lm.controller.uc_pool.manually_reload_controller(
            controller.item_id)

    @log_i
    @api_need_master
    @notify_plugins
    def upnp_rescan_controllers(self, **kwargs):
        """
        rescan controllers via UPnP

        Args:
            k: .master
        """
        parse_api_params(kwargs, '', '')
        import eva.upnp
        if eva.upnp.discovery_worker.is_active():
            eva.upnp.discovery_worker.trigger_threadsafe()
            return True
        else:
            return False


# master functions for lmacro extension management

    @log_i
    @api_need_master
    @notify_plugins
    def load_ext(self, **kwargs):
        """
        load extension module

        Loads:doc:`macro extension</lm/ext>`.

        Args:
            k: .master
            .i: extension ID
            m: extension module

        Optional:
            c: extension configuration
            save: save extension configuration after successful call
        """
        i, m, c, save = parse_api_params(kwargs, 'imcS', 'SS.b')
        if isinstance(c, str):
            try:
                c = dict_from_str(c)
            except:
                raise InvalidParameter('Unable to parse config')
        if eva.lm.extapi.load_ext(i, m, c):
            if save:
                eva.lm.extapi.save()
            return eva.lm.extapi.get_ext(i).serialize(full=True, config=True)

    @log_w
    @api_need_master
    @notify_plugins
    def unload_ext(self, **kwargs):
        """
        unload macro extension

        Args:
            k: .master
            .i: extension ID
        """
        i = parse_api_params(kwargs, 'i', 'S')
        eva.lm.extapi.unload_ext(i, remove_data=True)
        if eva.core.config.db_update == 1:
            eva.lm.extapi.save()
        return True

    @log_d
    @api_need_master
    @notify_plugins
    def list_ext(self, **kwargs):
        """
        get list of available macro extensions

        Args:
            k: .master

        Optional:
            .full: get full information
        """
        full = parse_api_params(kwargs, 'Y', 'b')
        return sorted(eva.lm.extapi.serialize(full=full, config=full),
                      key=lambda k: k['id'])

    @log_d
    @api_need_master
    @notify_plugins
    def get_ext(self, **kwargs):
        """
        get loaded extension information

        Args:
            k: .master
            .i: extension ID
        """
        i = parse_api_params(kwargs, 'i', 'S')
        ext = eva.lm.extapi.get_ext(i)
        if ext:
            return ext.serialize(full=True, config=True)
        else:
            raise ResourceNotFound

    @log_d
    @api_need_master
    @notify_plugins
    def list_ext_mods(self, **kwargs):
        """
        get list of available extension modules

        Args:
            k: .master
        """
        return eva.lm.extapi.list_mods()

    @log_d
    @api_need_master
    @notify_plugins
    def modinfo_ext(self, **kwargs):
        """
        get extension module info

        Args:
            k: .master
            .m: extension module name (without *.py* extension)
        """
        m = parse_api_params(kwargs, 'm', 'S')
        return eva.lm.extapi.modinfo(m)

    @log_d
    @api_need_master
    @notify_plugins
    def modhelp_ext(self, **kwargs):
        """
        get extension usage help

        Args:
            k: .master
            .m: extension name (without *.py* extension)
            .c: help context (*cfg* or *functions*)
        """
        m, c = parse_api_params(kwargs, 'mc', 'SS')
        return eva.lm.extapi.modhelp(m, c)

    @log_i
    @api_need_master
    @notify_plugins
    def set_ext_prop(self, **kwargs):
        """
        set extension configuration property

        appends property to extension configuration and reloads module

        Args:
            k: .master
            .i: extension id
            .p: property name (or empty for batch set)

        Optional:
            .v: propery value (or dict for batch set)
            save: save configuration after successful call
        """
        i, p, v, save = parse_api_params(kwargs, 'ipvS', 'S.Rb')
        eva.lm.extapi.set_ext_prop(i, p, v)
        if save:
            eva.lm.extapi.save()
        return True


class LM_HTTP_API_abstract(LM_API, GenericHTTP_API):

    def __init__(self):
        super().__init__()
        self._nofp_log('put_macro_function', 'src')
        self._nofp_log('put_macro_function', 'input')
        self._nofp_log('put_macro_function', 'output')
        self._nofp_log('set_macro_prop', 'v')


class LM_HTTP_API(LM_HTTP_API_abstract, GenericHTTP_API):

    def __init__(self):
        super().__init__()
        self.expose_api_methods('lmapi')
        self.wrap_exposed()


class LM_JSONRPC_API(eva.sysapi.SysHTTP_API_abstract,
                     eva.api.JSON_RPC_API_abstract, LM_HTTP_API_abstract):

    def __init__(self):
        super().__init__()
        self.expose_api_methods('lmapi', set_api_uri=False)
        self.expose_api_methods('sysapi', set_api_uri=False)


class LM_REST_API(eva.sysapi.SysHTTP_API_abstract,
                  eva.sysapi.SysHTTP_API_REST_abstract,
                  eva.api.GenericHTTP_API_REST_abstract, LM_HTTP_API_abstract,
                  GenericHTTP_API):

    @generic_web_api_method
    @restful_api_method
    def GET(self, rtp, k, ii, save, kind, method, for_dir, props):
        try:
            return super().GET(rtp, k, ii, save, kind, method, for_dir, props)
        except MethodNotFound:
            pass
        if rtp == 'lvar':
            if kind == 'groups':
                return self.groups(k=k, p=rtp)
            elif kind == 'history':
                return self.state_history(k=k, i=ii, **props)
            elif kind == 'log':
                return self.state_log(k=k, i='{}:{}'.format(rtp, ii), **props)
            elif kind == 'props':
                return self.list_props(k=k, i=ii)
            elif kind == 'config':
                return self.get_config(k=k, i=ii)
            elif for_dir:
                return self.state(k=k, p=rtp, g=ii, **props)
            else:
                return self.state(k=k, p=rtp, i=ii, **props)
        elif rtp == 'controller':
            if kind == 'items':
                return self.list_remote(k=k, i=ii, **props)
            elif kind == 'props' and ii and ii.find('/') != -1:
                return self.list_controller_props(k=k, i=ii)
            else:
                if ii and ii.find('/') != -1:
                    return self.get_controller(k=k, i=ii)
                else:
                    return self.list_controllers(k=k, g=ii)
        elif rtp == 'action':
            return self.result(k=k, u=ii, **props)
        elif rtp == 'dmatrix_rule':
            if ii:
                if kind == 'props':
                    return self.list_rule_props(k=k, i=ii)
                else:
                    return self.get_rule(k=k, i=ii)
            else:
                return self.list_rules(k=k)
        elif rtp == 'job':
            if ii:
                if kind == 'props':
                    return self.list_job_props(k=k, i=ii)
                else:
                    return self.get_job(k=k, i=ii)
            else:
                return self.list_jobs(k=k)
        elif rtp == 'lmacro':
            if ii:
                if kind == 'props':
                    return self.list_macro_props(k=k, i=ii)
                else:
                    if for_dir:
                        return self.list_macros(k=k, g=ii)
                    else:
                        return self.get_macro(k=k, i=ii)
            else:
                if kind == 'groups':
                    return self.groups_macro(k=k)
                else:
                    return self.list_macros(k=k)
        elif rtp == 'lmacro-function':
            if ii:
                return self.get_macro_function(k=k, i=ii)
            else:
                return self.list_macro_functions(k=k)
        elif rtp == 'lcycle':
            if ii:
                if kind == 'props':
                    return self.list_cycle_props(k=k, i=ii)
                else:
                    if for_dir:
                        return self.list_cycles(k=k, g=ii)
                    else:
                        return self.get_cycle(k=k, i=ii)
            else:
                if kind == 'groups':
                    return self.groups_cycle(k=k)
                else:
                    return self.list_cycles(k=k)
        elif rtp == 'ext':
            if ii:
                return self.get_ext(k=k, i=ii)
            else:
                return self.list_ext(k=k)
        elif rtp == 'ext-module':
            if ii:
                if 'help' in props:
                    return self.modhelp_ext(k=k, m=ii, c=props['help'])
                else:
                    return self.modinfo_ext(k=k, m=ii)
            else:
                return self.list_ext_mods(k=k)
        raise MethodNotFound

    @generic_web_api_method
    @restful_api_method
    def POST(self, rtp, k, ii, save, kind, method, for_dir, props):
        try:
            return super().POST(rtp, k, ii, save, kind, method, for_dir, props)
        except MethodNotFound:
            pass
        if rtp == 'lvar':
            if ii:
                v = props.get('v')
                if v == '!increment':
                    return self.increment(k=k, i=ii)
                if v == '!decrement':
                    return self.decrement(k=k, i=ii)
                s = props.get('s')
                if s == 'reset':
                    return self.reset(k=k, i=ii)
                elif s == 'clear':
                    return self.clear(k=k, i=ii)
                elif s == 'toggle':
                    return self.toggle(k=k, i=ii)
                else:
                    return self.set(k=k, i=ii, **props)
        elif rtp == 'lmacro':
            if method == "run":
                a = self.run(k=k, i=ii, **props)
                if not a:
                    raise FunctionFailed
                set_restful_response_location(a['uuid'], 'action')
                return a
        elif rtp == 'controller':
            if (not ii or for_dir or ii.find('/') == -1) and not method:
                result = self.append_controller(k=k, save=save, **props)
                if 'full_id' in result:
                    set_restful_response_location(result['full_id'], rtp)
                return result
            elif method == 'test':
                return self.test_controller(k=k, i=ii)
            elif method == 'reload':
                return self.reload_controller(k=k, i=ii)
            elif method == 'upnp-rescan':
                return self.upnp_rescan_controllers(k=k)
        elif rtp == 'lcycle':
            if ii:
                if method == 'start':
                    return self.start_cycle(k=k, i=ii)
                elif method == 'stop':
                    return self.stop_cycle(k=k, i=ii, **props)
                elif method == 'reset':
                    return self.reset_cycle_stats(k=k, i=ii)
        elif rtp == 'dmatrix_rule':
            if not ii:
                r = self.create_rule(k=k, v=props)
                if not r:
                    raise FunctionFailed
                set_restful_response_location(r['id'], rtp)
                return r
        elif rtp == 'job':
            if not ii:
                r = self.create_job(k=k, v=props)
                if not r:
                    raise FunctionFailed
                set_restful_response_location(r['id'], rtp)
                return r
        raise MethodNotFound

    @generic_web_api_method
    @restful_api_method
    def PUT(self, rtp, k, ii, save, kind, method, for_dir, props):
        try:
            return super().PUT(rtp, k, ii, save, kind, method, for_dir, props)
        except MethodNotFound:
            pass
        if rtp == 'lvar':
            self.create_lvar(k=k, i=ii, save=save)
            self.set_prop(k=k, i=ii, v=props, save=save)
            return self.state(k=k, i=ii, p=rtp, full=True)
        elif rtp == 'dmatrix_rule':
            if ii:
                return self.create_rule(k=k, u=ii, v=props)
        elif rtp == 'job':
            if ii:
                return self.create_job(k=k, u=ii, v=props)
        elif rtp == 'lmacro':
            if ii:
                return self.create_macro(k=k, i=ii)
        elif rtp == 'lcycle':
            if ii:
                return self.create_cycle(k=k, i=ii)
        elif rtp == 'ext':
            return self.load_ext(k=k, i=ii, save=save, **props)
        raise MethodNotFound

    @generic_web_api_method
    @restful_api_method
    def PATCH(self, rtp, k, ii, save, kind, method, for_dir, props):
        try:
            return super().PATCH(rtp, k, ii, save, kind, method, for_dir, props)
        except MethodNotFound:
            pass
        if rtp == 'lvar':
            if ii:
                if props:
                    return super().set_prop(k=k, i=ii, save=save, v=props)
                else:
                    return True
        elif rtp == 'controller':
            if ii:
                if props:
                    return super().set_controller_prop(k=k,
                                                       i=ii,
                                                       save=save,
                                                       v=props)
                else:
                    return True
        elif rtp == 'dmatrix_rule':
            if ii:
                return self.set_rule_prop(k=k, i=ii, v=props, save=save)
        elif rtp == 'job':
            if ii:
                return self.set_job_prop(k=k, i=ii, v=props, save=save)
        elif rtp == 'lmacro':
            if ii:
                return self.set_macro_prop(k=k, i=ii, v=props, save=save)
        elif rtp == 'lcycle':
            if ii:
                return self.set_cycle_prop(k=k, i=ii, v=props, save=save)
        elif rtp == 'ext':
            if ii:
                return self.set_ext_prop(k=k, i=ii, save=save, v=props)
        raise MethodNotFound

    @generic_web_api_method
    @restful_api_method
    def DELETE(self, rtp, k, ii, save, kind, method, for_dir, props):
        try:
            return super().DELETE(rtp, k, ii, save, kind, method, for_dir,
                                  props)
        except MethodNotFound:
            pass
        if rtp == 'lvar':
            if ii:
                return self.destroy_lvar(k=k, i=ii)
        elif rtp == 'controller':
            if ii:
                return self.remove_controller(k=k, i=ii)
        elif rtp == 'dmatrix_rule':
            if ii:
                return self.destroy_rule(k=k, i=ii)
        elif rtp == 'job':
            if ii:
                return self.destroy_job(k=k, i=ii)
        elif rtp == 'lmacro':
            if ii:
                return self.destroy_macro(k=k, i=ii)
        elif rtp == 'lcycle':
            if ii:
                return self.destroy_cycle(k=k, i=ii)
        elif rtp == 'ext':
            if ii:
                return self.unload_ext(k=k, i=ii)
        raise MethodNotFound


def start():
    http_api = LM_HTTP_API()
    cherrypy.tree.mount(http_api, http_api.api_uri)
    cherrypy.tree.mount(jrpc, jrpc.api_uri)
    cherrypy.tree.mount(LM_REST_API(),
                        LM_REST_API.api_uri,
                        config={
                            '/': {
                                'request.dispatch':
                                    cherrypy.dispatch.MethodDispatcher()
                            }
                        })
    eva.api.jrpc = jrpc
    eva.ei.start()


api = LM_API()
eva.api.api = api
jrpc = LM_JSONRPC_API()
