__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"
__description__ = "Generic PHI, don't use"

__equipment__ = 'abstract'
__api__ = 9
__required__ = []
__mods_required__ = []
__lpi_default__ = None
__features__ = []
__config_help__ = []
__get_help__ = []
__set_help__ = []

__help__ = """
Generic PHI for using as a base for all other UC PHI modules. For a list of the
available functions look directly into the extension code or to EVA ICS
documentation.
"""

import logging
import threading
import sys
import rapidjson
import timeouter as to

import eva.core

from eva.uc.driverapi import critical
from eva.uc.driverapi import get_polldelay
from eva.uc.driverapi import get_sleep_step
from eva.uc.driverapi import get_timeout
from eva.uc.driverapi import handle_phi_event
from eva.uc.driverapi import get_shared_namespace

from eva.x import GenericX

from time import time
from time import sleep
from time import perf_counter

from eva.tools import SimpleNamespace

from neotasker import BackgroundEventWorker, task_supervisor


class PHI(GenericX):
    """
    Override everything. super() constructor may be useful to keep unparsed
    config
    """

    def __init__(self, **kwargs):
        self.phi_id = None
        self.oid = None
        phi_cfg = kwargs.get('phi_cfg')
        if phi_cfg:
            self.phi_cfg = phi_cfg
        else:
            self.phi_cfg = {}
        mod = kwargs.get('_xmod')
        self.__xmod__ = mod
        self.phi_mod_id = mod.__name__.rsplit('.', 1)[-1]
        self.__author = mod.__author__
        self.__license = mod.__license__
        self.__description = mod.__description__
        self.__version = mod.__version__
        self.__api_version = mod.__api__
        self.__equipment = mod.__equipment__
        self.__features = mod.__features__
        self.__required = mod.__required__
        self.__mods_required = mod.__mods_required__
        self.__lpi_default = mod.__lpi_default__
        self._config_help = mod.__config_help__
        self._get_help = mod.__get_help__
        self._set_help = mod.__set_help__
        self.__help = mod.__help__
        if hasattr(mod, '__ports_help__'):
            self.__ports_help = mod.__ports_help__
        else:
            self.__ports_help = ''
        if hasattr(mod, '__shared_namespaces__'):
            self.__shared_namespaces = mod.__shared_namespaces__
            if not isinstance(self.__shared_namespaces, list):
                self.__shared_namespaces = [self.__shared_namespaces]
        else:
            self.__shared_namespaces = []
        if hasattr(mod, '__discover__'):
            self.__discover = mod.__discover__
        else:
            self.__discover = None
        if self.__discover and not isinstance(self.__discover, list):
            self.__discover = [self.__discover]
        if hasattr(mod, '__discover_help__'):
            self._discover_help = mod.__discover_help__
        else:
            self._discover_help = ''
        if isinstance(self.__features, str):
            self.__features = [self.__features]
        else:
            self.__features = sorted(self.__features)
        if isinstance(self.__required, str):
            self.__required = [self.__required]
        else:
            self.__required = sorted(self.__required)
        self._is_required = SimpleNamespace(aao_get=False,
                                            aao_set=False,
                                            action=False,
                                            events=False,
                                            port_get=False,
                                            port_set=False,
                                            status=False,
                                            value=False)
        self._has_feature = SimpleNamespace(aao_get=False,
                                            aao_set=False,
                                            action=False,
                                            cache=False,
                                            events=False,
                                            port_get=False,
                                            port_set=False,
                                            status=False,
                                            universal=False,
                                            value=False)
        for f in self.__required:
            try:
                setattr(self._is_required, f, True)
            except:
                self.log_error('feature unknown: {}'.format(f))
            if f not in self.__features:
                self.__features.append(f)
        for f in self.__features:
            try:
                setattr(self._has_feature, f, True)
            except:
                self.log_error('feature unknown: {}'.format(f))
        if 'cache' in self.__features:
            for v in self._config_help:
                if v['name'] == 'cache':
                    break
            else:
                self._config_help.append({
                    'name': 'cache',
                    'help': 'caches state for N sec',
                    'type': 'float',
                    'required': False
                })
        if 'aao_get' in self.__features:
            for v in self._config_help:
                if v['name'] == 'update':
                    break
            else:
                self._config_help.append({
                    'name': 'update',
                    'help': 'send updates to items every N sec',
                    'type': 'float',
                    'required': False
                })
        if kwargs.get('info_only'):
            return
        if not kwargs.get('config_validated'):
            self.validate_config(self.phi_cfg, config_type='config')
        self.ready = True
        # cache time, useful for aao_get devices
        self._cache_set = 0
        self._cache_data = None
        try:
            self._cache = float(self.phi_cfg.get('cache'))
        except:
            self._cache = 0
        try:
            self._update_interval = float(self.phi_cfg.get('update'))
        except:
            self._update_interval = 0
        self._update_processor = BackgroundEventWorker(
            o=self,
            on_error=eva.core.log_traceback,
            fn=self._run_update_processor)
        self._update_scheduler = None
        self._last_update_state = None
        # benchmarking
        self.__update_count = 0
        self.__update_active = False
        self.__last_update_reset = 0
        self.__benchmark = self.phi_cfg.get('benchmark', False)

    def get_cached_state(self):
        if not self._cache or not self._cache_data:
            return None
        return self._cache_data if \
                time() - self._cache_set < self._cache else None

    def set_cached_state(self, data):
        if not self._cache:
            return False
        self._cache_data = data
        self._cache_set = time()

    def clear_cache(self):
        self._cache_set = 0
        self._cache_data = None

    def get(self, port=None, cfg=None, timeout=0):
        return None, None if \
                self._is_required.value and self._is_required.status else None

    def set(self, port=None, data=None, cfg=None, timeout=0):
        return False

    def load_json(self, s):
        return rapidjson.loads(s)

    def handle_event(self):
        pass

    def start(self):
        return True

    def stop(self):
        return True

    def unload(self):
        return True

    def get_default_lpi(self):
        return self.__lpi_default

    def serialize(self, full=False, config=False, helpinfo=None):
        d = {}
        if helpinfo:
            if helpinfo == 'cfg':
                d = self._config_help.copy()
            elif helpinfo == 'get':
                d = self._get_help.copy()
            elif helpinfo == 'set':
                d = self._set_help.copy()
            elif helpinfo == 'ports':
                d = self.__ports_help
            elif helpinfo == 'discover':
                d = self._discover_help
            else:
                d = None
            return d
        if full:
            d['author'] = self.__author
            d['license'] = self.__license
            d['description'] = self.__description
            if hasattr(self, 'discover') and self.__discover:
                d['can_discover'] = self.__discover
            else:
                d['can_discover'] = None
            d['can_get_ports'] = hasattr(self, 'get_ports')
            d['version'] = self.__version
            d['api'] = self.__api_version
            d['oid'] = self.oid
            d['lpi_default'] = self.__lpi_default
            d['equipment'] = self.__equipment if \
                    isinstance(self.__equipment, list) else [self.__equipment]
            d['features'] = self.__features
            d['required'] = self.__required
            d['mods_required'] = self.__mods_required if \
                    isinstance(self.__mods_required, list) else \
                    [self.__mods_required]
            d['help'] = self.__help
        if config:
            d['cfg'] = self.phi_cfg
        d['mod'] = self.phi_mod_id
        d['id'] = self.phi_id
        return d

    def push_state(self, payload=None):
        self.log_warning('push_state not implemented')
        return False

    def test(self, cmd=None):
        return 'FAILED'

    # don't override the methods below

    def log_debug(self, msg):
        i = self.phi_id if self.phi_id is not None else self.phi_mod_id
        logging.debug('PHI %s: %s' % (i, msg))

    def log_info(self, msg):
        i = self.phi_id if self.phi_id is not None else self.phi_mod_id
        logging.info('PHI %s: %s' % (i, msg))

    def log_warning(self, msg):
        i = self.phi_id if self.phi_id is not None else self.phi_mod_id
        logging.warning('PHI %s: %s' % (i, msg))

    def log_error(self, msg):
        i = self.phi_id if self.phi_id is not None else self.phi_mod_id
        logging.error('PHI %s: %s' % (i, msg))

    def log_error(self, msg):
        i = self.phi_id if self.phi_id is not None else self.phi_mod_id
        logging.error('PHI %s: %s' % (i, msg))

    def log_critical(self, msg):
        self.critical(msg)

    def critical(self, msg):
        i = self.phi_id if self.phi_id is not None else self.phi_mod_id
        logging.critical('PHI %s: %s' % (i, msg))
        critical()

    def get_shared_namespace(self, namespace_id):
        if namespace_id not in self.__shared_namespaces:
            return None
        else:
            return get_shared_namespace(namespace_id)

    @staticmethod
    def generate_port_list(port_min=1,
                           port_max=1,
                           name='port #{}',
                           description='port #{}'):
        result = []
        for i in range(port_min, port_max + 1):
            p = str(i)
            result.append({
                'port': p,
                'name': name.replace('{}', p),
                'description': description.replace('{}', p)
            })
        return result

    def _start(self):
        return self.start()

    def _start_processors(self):
        if self._update_interval and 'aao_get' in self.__features:
            self._update_processor.set_name('phi_update_processor:{}'.format(
                self.oid))
            self._update_processor.start()
            self._update_scheduler = task_supervisor.create_async_job(
                target=self._job_update_scheduler,
                interval=self._update_interval)

    def _stop_processors(self):
        if self._update_scheduler:
            self._update_scheduler.cancel()
            self._update_scheduler = None
        self._update_processor.stop()

    def _stop(self):
        return self.stop()

    async def _job_update_scheduler(self):
        self.log_debug('scheduling update')
        await self._update_processor.trigger()

    async def _run_update_processor(self, **kwargs):
        if not self.__update_active:
            self.__update_active = True
            eva.core.spawn(self._launch_update)
        else:
            self.log_warning('update is already in progress. skipping')

    def _launch_update(self):
        try:
            self._perform_update()
        except:
            self.log_error('update error')
            eva.core.log_traceback()
        finally:
            self.__update_active = False

    def _perform_update(self):
        self.log_debug('performing update')
        to.init(timeout=get_timeout())
        state = self.get(timeout=get_timeout())
        if not state:
            return
        if self._last_update_state:
            stu = {}
            for x, v in state.items():
                if v != self._last_update_state.get(x):
                    stu[x] = v
        else:
            if self.__benchmark:
                self.__last_update_reset = time()
                self.log_warning('benchmark mode')
            stu = state
        if self.__benchmark:
            self.__update_count += 1
        self._last_update_state = state.copy()
        if stu:
            handle_phi_event(self, 'scheduler', stu)
        if self.__benchmark and self.__update_count > 1 / self._update_interval:
            self.log_warning('update benchmark: {}/s'.format(
                round(self.__update_count /
                      (time() - self.__last_update_reset))))
            self.__update_count = 0
            self.__last_update_reset = time()

    def _test(self, cmd=None):
        to.init(timeout=get_timeout())
        return self.test(cmd=cmd)
