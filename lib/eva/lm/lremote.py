__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.0"

import eva.core
import eva.client.remote_controller
import eva.client.remote_item
import eva.lm.controller
import threading
import logging


class LRemoteUC(eva.client.remote_controller.RemoteUC):

    def create_remote_unit(self, state):
        return LRemoteUnit(self, state)

    def create_remote_sensor(self, state):
        return LRemoteSensor(self, state)


class LRemoteUnit(eva.client.remote_item.RemoteUnit):

    def __init__(self, remote_uc, state):
        self.update_lock = threading.Lock()
        self.prv_status = None
        self.prv_value = None
        self.prv_nstatus = None
        self.prv_nvalue = None
        super().__init__(remote_uc, state)

    def start_processors(self):
        eva.lm.controller.pdme(self)
        super().start_processors()

    def update_set_state(self,
                         status=None,
                         value=None,
                         from_mqtt=False,
                         force_virtual=False):
        if not self.update_lock.acquire(timeout=eva.core.timeout):
            logging.critical('LRemoteUnit::update_set_state locking broken')
            eva.core.critical()
            return False
        try:
            _status = self.status
            _value = self.value
            if super().update_set_state(
                    status=status,
                    value=value,
                    from_mqtt=from_mqtt,
                    force_virtual=force_virtual):
                self.prv_status = _status
                self.prv_value = _value
                eva.lm.controller.pdme(self)
                return True
        except:
            eva.core.log_traceback()
            return False
        finally:
            self.update_lock.release()

    def update_nstate(self, nstatus=None, nvalue=None):
        if not self.update_lock.acquire(timeout=eva.core.timeout):
            logging.critical('LRemoteUnit::update_set_state locking broken')
            eva.core.critical()
            return False
        try:
            _nstatus = self.nstatus
            _nvalue = self.nvalue
            if super().update_nstate(nstatus, nvalue):
                self.prv_nstatus = _nstatus
                self.prv_nvalue = _nvalue
                eva.lm.controller.pdme(self, ns=True)
                return True
        except:
            return False
        finally:
            self.update_lock.release()


class LRemoteSensor(eva.client.remote_item.RemoteSensor):

    def __init__(self, remote_uc, state):
        self.update_lock = threading.Lock()
        self.prv_status = None
        self.prv_value = None
        super().__init__(remote_uc, state)

    def start_processors(self):
        eva.lm.controller.pdme(self)
        super().start_processors()

    def update_set_state(self,
                         status=None,
                         value=None,
                         from_mqtt=False,
                         force_virtual=False):
        if not self.update_lock.acquire(timeout=eva.core.timeout):
            logging.critical('LRemoteSensor::update_set_state locking broken')
            eva.core.critical()
            return False
        try:
            _status = self.status
            _value = self.value
            if super().update_set_state(
                    status=status,
                    value=value,
                    from_mqtt=from_mqtt,
                    force_virtual=force_virtual):
                self.prv_status = _status
                self.prv_value = _value
                eva.lm.controller.pdme(self)
                return True
        except:
            eva.core.log_traceback()
            return False
        finally:
            self.update_lock.release()
