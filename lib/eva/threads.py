__author__ = "Altertech Group, http://www.altertech.com/"
__copyright__ = "Copyright (C) 2018-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.1.2"

import threading


class BackgroundWorker:

    def __init__(self, name=None):
        self.__thread = None
        self.__active = False
        self.name = ('_t_' + name) if name is not None else None

    def start(self, *args, **kwargs):
        if not (self.__active and self.__thread and self.__thread.isAlive()):
            _kwargs = kwargs.copy()
            if '_daemon' in _kwargs:
                daemon = _kwargs['_daemon']
                del _kwargs['_daemon']
            else:
                daemon = False
            self.__thread = threading.Thread(
                target=self.run, name=self.name, args=args, kwargs=_kwargs)
            self.__thread.setDaemon(daemon)
            self.__active = True
            self.before_start()
            self.__thread.start()
            self.after_start()

    def stop(self, wait=True):
        if self.__active and self.__thread and self.__thread.isAlive():
            self.before_stop()
            self.__active = False
            self.after_stop()
            if wait:
                self.__thread.join()

    def is_active(self):
        return self.__active

    # ----- override below this -----

    def run(self, *args, **kwargs):
        self.__active = False
        raise Exception('not implemented')

    def before_start(self):
        pass

    def after_start(self):
        pass

    def before_stop(self):
        pass

    def after_stop(self):
        pass
