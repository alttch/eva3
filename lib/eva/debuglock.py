import threading
import logging


def get_caller(stack_len=0):
    import inspect
    return inspect.getouterframes(inspect.currentframe(), 2)[stack_len + 2]


TLock = threading.Lock
TRLock = threading.RLock

active_locks_lock = TLock()

active_locks = {}


def get_active():
    with active_locks_lock:
        return active_locks.copy()


class ADebugLock():

    def __init__(self):
        self._owner = None

    def acquire(self, *args, **kwargs):
        l = self._lock.acquire(*args, **kwargs)
        if not l:
            logging.critical(f'Locking failed {self}')
            return l
        me = super().__str__()
        import traceback
        self._owner = (get_caller(), traceback.format_stack()[:-1])
        with active_locks_lock:
            active_locks[me] = str(self)
        return l

    def __enter__(self):
        self.acquire()

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.release()

    def release(self, *args, **kwargs):
        l = self._lock.release(*args, **kwargs)
        me = super().__str__()
        with active_locks_lock:
            try:
                del active_locks[me]
            except:
                pass
        self._owner = None
        return l

    def __str__(self):
        me = super().__str__()
        o = self._owner
        if o:
            me += ((f' debug locked by {o[0].filename}:'
                    f'{o[0].lineno}:{o[0].function}\n\nTraceback:\n') +
                   '\n'.join(o[1]))
        return me


class Lock(ADebugLock):

    def __init__(self):
        super().__init__()
        self._lock = TLock()


class RLock(ADebugLock):

    def __init__(self):
        super().__init__()
        self._lock = TRLock()


def inject():
    threading.Lock = Lock
    threading.RLock = RLock
