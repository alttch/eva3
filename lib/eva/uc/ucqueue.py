__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "3.1.0"

from eva.itemqueue import ActiveItemQueue


class UC_Queue(ActiveItemQueue):

    def __init__(self, queue_id, keep_history=None, default_priority=100):
        super().__init__(
            queue_id=queue_id,
            keep_history=keep_history,
            default_priority=default_priority)
