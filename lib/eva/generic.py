__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.2"

ia_status_created = 0  # action just created
ia_status_pending = 1  # put in global queue
ia_status_queued = 2  # queued in item action processor queue
ia_status_refused = 3  # refused to queue (item doesn't support queues)
ia_status_dead = 4  # queueing into item queue took too long
ia_status_canceled = 5  # canceled for some reason
ia_status_ignored = 6  # queued but ignored to run (item already in state)
ia_status_running = 7  # currently running
ia_status_failed = 8  # failed to run
ia_status_terminated = 9  # executed but terminated
ia_status_completed = 10  # executed and finished successfully

import threading


class GenericAction(object):

    def __init__(self):
        self._status = ia_status_created
        self.processed = threading.Event()
        self.finished = threading.Event()

    def get_status(self):
        return self._status

    def set_status(self, status):
        self._status = status
        if status not in [ia_status_created, ia_status_pending]:
            self.processed.set()
        if status in [
                ia_status_refused, ia_status_dead, ia_status_canceled,
                ia_status_ignored, ia_status_failed, ia_status_terminated,
                ia_status_completed
        ]:
            self.finished.set()

    def is_processed(self):
        return self.processed.is_set()

    def is_finished(self):
        return self.finished.is_set()

    def is_status_created(self):
        return self._status == ia_status_created

    def is_status_pending(self):
        return self._status == ia_status_pending

    def is_status_queued(self):
        return self._status == ia_status_queued

    def is_status_refused(self):
        return self._status == ia_status_refused

    def is_status_dead(self):
        return self._status == ia_status_dead

    def is_status_canceled(self):
        return self._status == ia_status_canceled

    def is_status_ignored(self):
        return self._status == ia_status_ignored

    def is_status_running(self):
        return self._status == ia_status_running

    def is_status_failed(self):
        return self._status == ia_status_failed

    def is_status_terminated(self):
        return self._status == ia_status_terminated

    def is_status_completed(self):
        return self._status == ia_status_completed
