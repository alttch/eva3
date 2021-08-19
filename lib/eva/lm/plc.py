__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.1"

import eva.core
import eva.item
import eva.lm.controller
import eva.lm.macro_api
import eva.lm.extapi
import eva.lm.iec_compiler
import eva.lm.iec_functions
import threading
import time
import os
import re
import shlex
import logging
import rapidjson

from eva.tools import val_to_boolean
from eva.tools import dict_from_str
from eva.tools import parse_func_str
from eva.tools import prepare_safe_serialize

from eva.exceptions import FunctionFailed

from eva.tools import SimpleNamespace

macro_functions = {}
macro_function_codes = {}

macro_iec_functions = {}
macro_api_functions = {}

mfcode = SimpleNamespace(code='', build_time=0)

pf_macros = {}

with_macro_functions_lock = eva.core.RLocker('lm/plc')

spawn = eva.core.spawn


def load_iec_functions():
    macro_iec_functions.clear()
    with open(eva.core.dir_lib + '/eva/lm/iec_functions.json') as fd:
        macro_iec_functions.update(rapidjson.loads(fd.read()))


def load_macro_api_functions():
    macro_api_functions.clear()
    with open(eva.core.dir_lib + '/eva/lm/macro_api_functions.json') as fd:
        macro_api_functions.update(rapidjson.loads(fd.read()))
    pf_macros.clear()
    for f in macro_api_functions:
        pf_macros[f] = VFMacro(f)


def rebuild_mfcode():
    code = ''
    for m, v in macro_function_codes.items():
        code += v + '\n'
    mfcode.code = code
    mfcode.build_time = time.time()
    logging.debug('mfcode rebuilt: {}'.format(mfcode.build_time))


def compile_macro_function_fbd(fcode):
    return eva.lm.iec_compiler.gen_code_from_fbd(fcode)


def compile_macro_sfc(code):
    return eva.lm.iec_compiler.gen_code_from_sfc(code)


def prepare_macro_function_code(fcode, fname, fdescr, i, o):
    var_in = ''
    var_out = ''
    in_params = ''
    if i:
        for v in i:
            descr = v.get('description')
            if descr is None:
                descr = ''
            in_params += '{}=None, '.format(v['var'])
            var_in += '    @var_in    {}    {}\n'.format(v['var'], descr)
    if o:
        for v in o:
            descr = v.get('description')
            if descr is None:
                descr = ''
            var_out += '    @var_in    {}    {}\n'.format(v['var'], descr)
    out = 'def {}({}):\n'.format(fname, in_params[:-2])
    out += '    """\n'
    if fdescr is not None and fdescr != '':
        out += '    @description    {}\n'.format(fdescr)
    out += var_in
    out += var_out
    out += '    """\n'
    for l in fcode.split('\n'):
        out += '    {}\n'.format(l)
    return out


@with_macro_functions_lock
def append_macro_function(file_name, rebuild=True):

    def parse_arg(fndoc):
        x = re.split('[\ \t]+', d, 2)
        argname = x[1]
        if len(x) > 2:
            argdescr = x[2]
        else:
            argdescr = ''
        result = {'description': argdescr}
        if argname.find('=') != -1:
            argname, argval = argname.split('=', 1)
            try:
                argval = float(argval)
                if argval == int(argval):
                    argval = int(argval)
            except:
                pass
            result['default'] = argval
        result['var'] = argname
        return result

    try:
        with open(file_name) as fd:
            raw = fd.read()
        fname = os.path.basename(file_name[:-3])
        if raw.startswith('# FBD'):
            l = raw.split('\n')
            jcode = ''
            for i in range(3, len(l)):
                if l[i].startswith('"""'):
                    break
                jcode += l[i]
            j = rapidjson.loads(jcode)
            tp = 'fbd-json'
        else:
            tp = 'py'

        code, src_code = raw, raw

        if tp == 'py':
            code += '\nimport inspect\nfndoc = inspect.getdoc({})\n'.format(
                fname, fname)
            code += 'fnsrc = inspect.getsource({})\n'.format(fname)
        d = {}
        c = compile(code, file_name, 'exec')
        exec(c, d)
        if tp == 'py':
            src = ''
            x = 0
            indent = 4
            for s in d['fnsrc'].split('\n'):
                if x >= 2:
                    if src:
                        src += '\n'
                    src += s[indent:]
                st = s.strip()
                if st.startswith('\'\'\'') or st.startswith('"""'):
                    if not x:
                        indent = len(s) - len(st)
                    x += 1
        elif tp == 'fbd-json':
            src = j
        result = {
            'name': fname,
            'var_in': [],
            'var_out': [],
            'src': src,
            'editable': True,
            'group': 'custom',
            'description': '',
            'type': tp
        }
        if tp == 'py':
            doc = d['fndoc']
            if doc:
                for d in doc.split('\n'):
                    d = d.strip()
                    if d.startswith('@var_in'):
                        result['var_in'].append(parse_arg(d))
                    if d.startswith('@var_out'):
                        result['var_out'].append(parse_arg(d))
                    if d.startswith('@description'):
                        try:
                            result['description'] = re.split('[\ \t]+', d, 1)[1]
                        except:
                            pass
        elif tp == 'fbd-json':
            result['description'] = j.get('description', '')
            for x in j.get('input', []):
                result['var_in'].append({
                    'var': x.get('var'),
                    'description': x.get('description', '')
                })
            for x in j.get('output', []):
                result['var_out'].append({
                    'var': x.get('var'),
                    'description': x.get('description', '')
                })
        macro_functions[fname] = result
        macro_function_codes[fname] = src_code
        if rebuild:
            rebuild_mfcode()
        return True
    except Exception as e:
        raise FunctionFailed(e)


@with_macro_functions_lock
def remove_macro_function(file_name, rebuild=True):
    fname = os.path.basename(file_name)[:-3]
    if fname in macro_functions:
        del macro_functions[fname]
        del macro_function_codes[fname]
        if rebuild:
            rebuild_mfcode()
        return True
    else:
        return False


@with_macro_functions_lock
def get_macro_function_codes():
    return macro_function_codes.copy()


@with_macro_functions_lock
def get_macro_function(fname=None):
    if fname:
        if fname in macro_functions:
            return macro_functions[fname].copy()
        elif fname in macro_iec_functions:
            return macro_iec_functions[fname].copy()
        elif fname in macro_api_functions:
            return macro_api_functions[fname].copy()
        elif fname in eva.lm.extapi.iec_functions:
            return eva.lm.extapi.iec_functions[fname].copy()
        else:
            return None
    else:
        result = macro_functions.copy()
        result.update(macro_iec_functions.copy())
        result.update(macro_api_functions.copy())
        result.update(eva.lm.extapi.iec_functions.copy())
        return result


class PLC(eva.item.ActiveItem):

    def __init__(self):
        super().__init__(eva.core.config.system_name, 'plc')
        self.update_config({
            'group': 'lm',
            'action_enabled': True,
            'action_queue': 1,
            'action_allow_termination': False,
        })

    async def _run_action_processor(self, a, **kwargs):
        if a.item:
            if not self.queue_lock.acquire(timeout=eva.core.config.timeout):
                logging.critical('PLC::_t_action_processor locking broken')
                eva.core.critical()
                return
            try:
                self.current_action = a
                if not self.action_enabled:
                    logging.info(
                     '%s actions disabled, canceling action %s' % \
                     (self.full_id, a.uuid))
                    a.set_canceled()
                if not a.item.action_enabled:
                    logging.info(
                     '%s actions disabled, canceling action %s' % \
                     (a.item.full_id, a.uuid))
                    a.set_canceled()
                else:
                    if not self.action_may_run(a):
                        logging.info(
                                '%s ignoring action %s' % \
                                 (self.full_id, a.uuid))
                        a.set_ignored()
                    elif a.is_status_queued() and a.set_running():
                        spawn(self._t_action, a)
            except:
                logging.critical(
                        '%s action processor got an error, restarting' % \
                                (self.full_id))
                eva.core.log_traceback()
            finally:
                self.current_action = None
                self.action_xc = None
                self.queue_lock.release()

    def _t_action(self, a):
        try:
            import eva.runner
            self.action_log_run(a)
            self.action_before_run(a)
            env_globals = {}
            env_globals.update(eva.lm.extapi.env)
            env_globals.update(a.item.api.get_globals())
            env_globals.update(eva.lm.iec_functions.g)
            env_globals['_source'] = a.source
            env_globals['args'] = a.argv.copy()
            # deprecated
            env_globals['argv'] = env_globals['args']
            env_globals['kwargs'] = a.kwargs.copy()
            env_globals['is_shutdown'] = a.is_shutdown_func
            env_globals['_polldelay'] = eva.core.config.polldelay
            env_globals['_timeout'] = eva.core.config.timeout
            for i, v in env_globals['kwargs'].items():
                env_globals[i] = v
            env_globals['_0'] = a.item.item_id
            env_globals['_00'] = a.item.full_id
            for i, v in eva.core.cvars.copy().items():
                try:
                    value = v
                    env_globals[i] = value
                except:
                    env_globals[i] = v
            for i in range(1, 9):
                try:
                    env_globals['_%u' % i] = a.argv[i - 1]
                except:
                    env_globals['_%u' % i] = ''
            xc = eva.runner.PyThread(item=a.item,
                                     env_globals=env_globals,
                                     bcode=eva.lm.macro_api.mbi_code,
                                     mfcode=mfcode)
            xc.run()
            self.action_after_run(a, xc)
            if xc.exitcode < 0:
                a.set_terminated(exitcode=xc.exitcode, out=xc.out, err=xc.err)
                logging.error('macro %s action %s terminated' % \
                        (a.item.full_id, a.uuid))
            elif xc.exitcode == 0:
                a.set_completed(exitcode=xc.exitcode, out=xc.out, err=xc.err)
                logging.debug('macro %s action %s completed' % \
                        (a.item.full_id, a.uuid))
            else:
                a.set_failed(exitcode=xc.exitcode, out=xc.out, err=xc.err)
                logging.error('macro %s action %s failed, code: %u' % \
                        (a.item.full_id, a.uuid, xc.exitcode))
            self.action_after_finish(a, xc)
        except Exception as e:
            logging.error(e)
            import eva.core
            eva.core.log_traceback()


class MacroAction(eva.item.ItemAction):

    def __init__(self,
                 item,
                 argv=[],
                 kwargs={},
                 priority=None,
                 action_uuid=None,
                 source=None,
                 is_shutdown_func=None):
        self.argv = argv
        self.kwargs = kwargs
        self.source = source
        self.is_shutdown_func = is_shutdown_func if \
                is_shutdown_func else eva.core.is_shutdown_requested
        super().__init__(item=item, priority=priority, action_uuid=action_uuid)

    def serialize(self):
        d = super().serialize()
        d['args'] = prepare_safe_serialize(self.argv)
        d['kwargs'] = prepare_safe_serialize(self.kwargs)
        return d


class Macro(eva.item.ActiveItem):

    def __init__(self, item_id=None, **kwargs):
        super().__init__(item_id, 'lmacro', **kwargs)
        self.api = eva.lm.macro_api.MacroAPI(pass_errors=False,
                                             send_critical=False)
        self.pfcode = None

    def update_config(self, data):
        if 'pass_errors' in data:
            self.api.pass_errors = data['pass_errors']
        if 'send_critical' in data:
            self.api.send_critical = data['send_critical']
        super().update_config(data)

    def set_prop(self, prop, val=None, save=False):
        if prop == 'pass_errors':
            v = val_to_boolean(val)
            if v is not None:
                if self.api.pass_errors != v:
                    self.api.pass_errors = v
                    self.log_set(prop, v)
                    self.set_modified(save)
                return True
            else:
                return False
        elif prop == 'send_critical':
            v = val_to_boolean(val)
            if v is not None:
                if self.api.send_critical != v:
                    self.api.send_critical = v
                    self.log_set(prop, v)
                    self.set_modified(save)
                return True
            else:
                return False
        elif prop == 'src':
            if isinstance(val, str):
                code = val
            elif isinstance(val, dict):
                try:
                    v = val.copy()
                    if 'name' in v:
                        del v['name']
                    code = '# SFC\n# auto generated code, ' + \
                            'do not modify\n"""\n{}\n"""\n'.format(
                        rapidjson.dumps(v)) + compile_macro_sfc(val)
                except Exception as e:
                    logging.error(
                        'Unable to compile macro source for {}: {}'.format(
                            self.oid, e))
                    return False
            else:
                return False
            try:
                file_name = eva.core.format_xc_fname(
                    fname=self.action_exec if self.action_exec else '{}.py'.
                    format(self.item_id))
                eva.core.prepare_save()
                with open(file_name, 'w') as fd:
                    fd.write(code)
                eva.core.finish_save()
                return True
            except FunctionFailed:
                raise
            except Exception as e:
                logging.error('Unable to write macro source for {}: {}'.format(
                    self.oid, e))
                return False
        return super().set_prop(prop, val, save)

    def notify(self,
               retain=None,
               skip_subscribed_mqtt=False,
               for_destroy=False):
        pass

    def serialize(self,
                  full=False,
                  config=False,
                  info=False,
                  props=False,
                  notify=False):
        d = {}
        if full or config or props:
            d['pass_errors'] = self.api.pass_errors
            d['send_critical'] = self.api.send_critical
        d.update(super().serialize(full=full,
                                   config=config,
                                   info=info,
                                   props=props,
                                   notify=notify))
        if not notify:
            d['action_enabled'] = self.action_enabled
        else:
            if 'action_enabled' in d:
                del d['action_enabled']
        if 'action_queue' in d:
            del d['action_queue']
        if 'action_allow_termination' in d:
            del d['action_allow_termination']
        if 'action_timeout' in d:
            del d['action_timeout']
        if 'mqtt_control' in d:
            del d['mqtt_control']
        if 'term_kill_interval' in d:
            del d['term_kill_interval']
        if 'notify_events' in d:
            del d['notify_events']
        if props:
            d['src'] = ''
        return d


class VFMacro(Macro):

    def __init__(self, f):
        super().__init__(f)
        self.pfcode = 'out = ' + f + '(*args, **kwargs)'
        self.update_config({
            'group': '@func',
            'action_enabled': True,
            'action_exec': '@___vfm___' + f
        })


class Cycle(eva.item.Item):

    def __init__(self, item_id=None, **kwargs):
        super().__init__(item_id, 'lcycle', **kwargs)
        self.macro = None
        self.macro_args = []
        self.macro_kwargs = {}
        self.on_error = None
        self.interval = 1
        self.ict = 100
        self.autostart = False
        self.cycle_future = None
        self._cycle_lock = threading.RLock()
        self.cycle_enabled = False
        self.cycle_status = 0
        self.iterations = 0
        self.set_time = time.time()
        self.ieid = [0, 0]

    def update_config(self, data):
        if 'macro' in data:
            self.macro = eva.lm.controller.get_macro(data['macro'], pfm=True)
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
        if 'on_error' in data:
            self.on_error = eva.lm.controller.get_macro(data['on_error'],
                                                        pfm=True)
        if 'interval' in data:
            self.interval = data['interval']
        if 'ict' in data:
            self.ict = data['ict']
        if 'autostart' in data:
            self.autostart = data['autostart']
        super().update_config(data)

    def set_hri(self, v, save=False):

        def parse_str(s):
            d = s if isinstance(s, list) else s.strip().split()
            interval = None
            f = None
            for i, x in enumerate(d):
                if x == 'interval':
                    try:
                        interval = float(d[i + 1])
                        if len(d) > i + 2:
                            raise Exception
                    except:
                        raise ValueError('Invalid interval')
                    f = ' '.join(d[:i])
                    break
            if not f:
                f = ' '.join(s) if isinstance(s, list) else s
            return interval, f

        try:
            interval, f = parse_str(v)
        except Exception as e:
            raise FunctionFailed(e)
        if interval:
            try:
                if not self.set_prop('interval', interval):
                    raise Exception
            except:
                raise FunctionFailed('Unable to set cycle interval')
        try:
            name, args, kwargs = parse_func_str(f)
        except Exception as e:
            raise FunctionFailed(e)
        if not self.set_prop('macro', name):
            raise FunctionFailed('Unable to set cycle macro')
        if not self.set_prop('macro_args', args):
            raise FunctionFailed('Unable to set cycle macro args')
        if not self.set_prop('macro_kwargs', kwargs):
            raise FunctionFailed('Unable to set cycle macro kwargs')
        if save:
            self.save()
        return True

    def set_prop(self, prop, val=None, save=False):
        if prop == 'macro':
            if self.cycle_enabled:
                return False
            if val is None:
                if self.macro is not None:
                    self.macro = val
                    self.log_set(prop, val)
                    self.set_modified(save)
                return True
            macro = eva.lm.controller.get_macro(val, pfm=True)
            if macro:
                if not self.macro or self.macro.oid != macro.oid:
                    self.macro = macro
                    self.log_set(prop, val)
                    self.set_modified(save)
                return True
            else:
                return False
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
        elif prop == 'on_error':
            if val is None:
                if self.on_error is not None:
                    self.on_error = val
                    self.log_set(prop, val)
                    self.set_modified(save)
                return True
            macro = eva.lm.controller.get_macro(val, pfm=True)
            if macro:
                if not self.on_error or self.on_error.oid != macro.oid:
                    self.on_error = macro
                    self.log_set(prop, val)
                    self.set_modified(save)
                return True
            else:
                return False
        elif prop == 'interval':
            if self.cycle_enabled:
                return False
            try:
                interval = float(val)
            except:
                return False
            if interval > 0:
                if self.interval != interval:
                    self.interval = interval
                    self.log_set(prop, val)
                    self.set_modified(save)
                    self.notify()
                return True
            else:
                return False
        elif prop == 'ict':
            try:
                ict = int(val)
            except:
                return False
            if ict > 0:
                if self.ict != ict:
                    self.ict = ict
                    self.log_set(prop, val)
                    self.set_modified(save)
                return True
            else:
                return False
        elif prop == 'autostart':
            try:
                autostart = val_to_boolean(val)
                if autostart is None:
                    raise ValueError('Invalid value')
            except:
                return False
            if self.autostart != autostart:
                self.autostart = autostart
                self.log_set(prop, val)
                self.set_modified(save)
            return True
        else:
            return super().set_prop(prop, val, save)

    def _t_cycle(self):
        logging.debug('%s cycle started' % self.full_id)
        self.cycle_status = 1
        self.set_time = time.time()
        self.ieid = eva.core.generate_ieid()
        self.notify()
        self.c = 0
        scheduled = time.perf_counter()
        while self.cycle_enabled:
            try:
                scheduled += self.interval
                self.c += 1
                if self.c > self.ict:
                    self.notify()
                    self.c = 0
                if self.macro:
                    self.iterations += 1
                    self.set_time = time.time()
                    self.ieid = eva.core.generate_ieid()
                    try:
                        result = eva.lm.controller.exec_macro(
                            self.macro,
                            argv=self.macro_args,
                            kwargs=self.macro_kwargs,
                            wait=self.interval,
                            source=self,
                            is_shutdown_func=self.is_shutdown)
                    except Exception as e:
                        ex = e
                        result = None
                    if not result:
                        logging.error('cycle %s exception %s' %
                                      (self.full_id, ex))
                        if self.on_error:
                            eva.lm.controller.exec_macro(self.on_error,
                                                         argv=['exception', ex],
                                                         source=self)
                    elif time.perf_counter() > scheduled:
                        logging.error('cycle {} timeout'.format(self.full_id))
                        scheduled = time.perf_counter() + self.interval
                        if self.on_error:
                            eva.lm.controller.exec_macro(
                                self.on_error,
                                argv=['timeout', result.serialize()],
                                source=self)
                    elif not result.is_status_completed():
                        logging.error('cycle %s exec error' % (self.full_id))
                        eva.lm.controller.exec_macro(
                            self.on_error,
                            argv=['exec_error',
                                  result.serialize()],
                            source=self)
                if self.interval >= 1:
                    while time.perf_counter(
                    ) < scheduled and self.cycle_enabled:
                        time.sleep(eva.core.sleep_step)
                else:
                    try:
                        time.sleep(scheduled - time.perf_counter())
                    except:
                        pass
            except:
                eva.core.log_traceback()
        logging.debug('%s cycle stopped' % self.full_id)
        self.cycle_status = 0
        self.set_time = time.time()
        self.ieid = eva.core.generate_ieid()
        self.notify()

    def start(self, autostart=False):
        if (autostart and
                not self.autostart) or not self.macro or self.cycle_enabled:
            self.notify()
            return False
        self.cycle_enabled = True
        with self._cycle_lock:
            self.cycle_future = spawn(self._t_cycle)
        return True

    def stop(self, wait=True):
        with self._cycle_lock:
            if self.cycle_future:
                if isinstance(self.cycle_future, threading.Thread):
                    f_is_running = self.cycle_future.is_alive
                    f_wait = self.cycle_future.join
                else:
                    f_is_running = self.cycle_future.running
                    f_wait = self.cycle_future.result
                if f_is_running():
                    self.cycle_status = 2
                    self.set_time = time.time()
                    self.ieid = eva.core.generate_ieid()
                    self.notify()
                    self.cycle_enabled = False
                    if wait or True:
                        try:
                            f_wait()
                        except:
                            eva.core.log_traceback()
            else:
                self.cycle_enabled = False
        return True

    def reset_stats(self):
        self.iterations = 0
        self.c = 0
        self.set_time = time.time()
        self.ieid = eva.core.generate_ieid()
        self.notify()
        return True

    def is_running(self):
        return self.cycle_enabled

    def is_shutdown(self):
        return not self.cycle_enabled

    def serialize(self,
                  full=False,
                  config=False,
                  info=False,
                  props=False,
                  notify=False):
        d = {}
        d.update(super().serialize(full=full,
                                   config=config,
                                   info=info,
                                   props=props,
                                   notify=notify))
        d['interval'] = self.interval
        if not config and not props:
            d['status'] = self.cycle_status
            d['iterations'] = self.iterations
            d['set_time'] = self.set_time
            d['ieid'] = self.ieid
        if not notify:
            d['ict'] = self.ict
            d['macro'] = self.macro.full_id if self.macro else None
            if d['macro'] and d['macro'].startswith('@func/'):
                d['macro'] = '@' + d['macro'][6:]
            d['on_error'] = self.on_error.full_id if self.on_error else None
            d['macro_args'] = self.macro_args
            d['macro_kwargs'] = self.macro_kwargs
        if config or props:
            d['autostart'] = self.autostart
        if 'notify_events' in d:
            del d['notify_events']
        return d

    def destroy(self):
        super().destroy()
        self.notify(for_destroy=True)
