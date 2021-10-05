__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.2"

import logging
import uuid
import eva.core
import shlex
import schedule
import time
import re

from neotasker import background_worker

from eva.tools import val_to_boolean
from eva.tools import dict_from_str
from eva.tools import parse_func_str

from eva.exceptions import FunctionFailed

with_scheduler_lock = eva.core.RLocker('lm/jobs')

schedule.logger.setLevel(logging.WARNING)


class Job(eva.item.Item):

    def __init__(self, job_uuid=None, **kwargs):
        if not job_uuid:
            _uuid = str(uuid.uuid4())
        else:
            _uuid = job_uuid
        self.enabled = False
        self.macro = None
        self.macro_args = []
        self.macro_kwargs = {}
        self.last_action = None
        self.every = ''
        self.every_set = ''
        super().__init__(_uuid, 'job', **kwargs)
        super().update_config({'group': 'jobs'})

    def get_rkn(self):
        return f'inventory/{self.item_type}/{self.item_id}'

    @with_scheduler_lock
    def schedule(self):
        self.every = ''
        if not self.every_set:
            self.unschedule()
            return
        x = re.split('[\ \t]+', self.every_set)
        if not x:
            self.unschedule()
            return
        try:
            x[0] = int(x[0])
        except:
            x = [1] + x
        interval = x[0]
        period = x[1].lower()
        err = 'Invalid schedule: {}'.format(self.every_set)
        if period not in [
                'second', 'seconds', 'minute', 'minutes', 'hour', 'hours',
                'day', 'days', 'week', 'weeks', 'monday', 'tuesday',
                'wednesday', 'thursday', 'friday', 'saturday', 'sunday'
        ]:
            self.unschedule()
            raise FunctionFailed(err)
        job = schedule.every(interval)
        job.tag(self.item_id)
        getattr(job, period)
        if len(x) > 2:
            if x[2].lower() != 'at' or len(x) != 4:
                self.unschedule()
                raise FunctionFailed(err)
            try:
                job.at(x[3])
            except:
                self.unschedule()
                raise FunctionFailed(err)
            at_interval = ' at {}'.format(x[3])
        else:
            at_interval = ''
        job.do(self.perform)
        self.every = '{} {}'.format(interval, period) + at_interval
        return True

    @with_scheduler_lock
    def unschedule(self):
        schedule.clear(tag=self.item_id)

    def reschedule(self):
        self.unschedule()
        return self.schedule()

    def perform(self):
        if not self.enabled or not self.every or not self.macro:
            logging.debug('Skipping job {}'.format(self.item_id))
            return
        logging.debug('Executing job {}'.format(self.item_id))
        a = eva.lm.controller.exec_macro(macro=self.macro,
                                         argv=self.macro_args,
                                         kwargs=self.macro_kwargs,
                                         source=self)
        if not a:
            logging.error('Job scheduler {} can not exec macro'.format(
                self.item_id))
            self.last_action = None
        else:
            self.last_action = a.uuid

    def serialize(self,
                  full=False,
                  config=False,
                  info=False,
                  props=False,
                  notify=False):
        d = {}
        d['enabled'] = self.enabled
        d['macro'] = self.macro
        d['macro_args'] = self.macro_args
        d['macro_kwargs'] = self.macro_kwargs
        d['every'] = self.every
        d.update(super().serialize(full=full,
                                   config=config,
                                   info=info,
                                   props=props,
                                   notify=notify))
        if 'group' in d:
            del d['group']
        if 'full_id' in d:
            del d['full_id']
        if full or info:
            d['last'] = self.last_action
        if 'notify_events' in d:
            del d['notify_events']
        return d

    def update_config(self, data):
        if 'enabled' in data:
            self.enabled = data['enabled']
        if 'macro' in data:
            self.macro = data['macro']
        if 'every' in data:
            self.every = data['every']
            self.every_set = self.every
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
        super().update_config(data)

    def set_hri(self, v, save=False):

        def parse_str(s):
            d = s if isinstance(s, list) else s.strip().split()
            every = None
            f = None
            for i, x in enumerate(d):
                if x == 'every':
                    f = ' '.join(d[:i])
                    every = ' '.join(d[i + 1:])
                    break
            if not f:
                f = ' '.join(s) if isinstance(s, list) else s
            return every, f

        try:
            every, f = parse_str(v)
        except Exception as e:
            raise FunctionFailed(e)
        if every:
            try:
                if not self.set_prop('every', every):
                    raise Exception
            except:
                raise FunctionFailed('Unable to set job schedule')
        try:
            name, args, kwargs = parse_func_str(f)
        except Exception as e:
            raise FunctionFailed(e)
        if not self.set_prop('macro', name):
            raise FunctionFailed('Unable to set job macro')
        if not self.set_prop('macro_args', args):
            raise FunctionFailed('Unable to set job macro args')
        if not self.set_prop('macro_kwargs', kwargs):
            raise FunctionFailed('Unable to set job macro kwargs')
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
        elif prop == 'macro':
            if self.macro != val:
                self.macro = val
                self.log_set(prop, val)
                self.set_modified(save)
            return True
        elif prop == 'every':
            if self.every_set != val:
                self.every_set = val
                self.log_set(prop, val)
                self.set_modified(save)
                self.reschedule()
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
                self.macro_kwargs = dict_from_str(val)
            self.log_set(prop, val)
            self.set_modified(save)
            return True
        return super().set_prop(prop, val, save)


@background_worker(on_error=eva.core.log_traceback)
def scheduler(**kwargs):
    schedule.run_pending()
    time.sleep(eva.core.sleep_step)
