__author__ = "Altertech Group, http://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2017 Altertech Group"
__license__ = "See http://www.eva-ics.com/"
__version__ = "3.0.2"

from eva.itemqueue import ActiveItemQueue


class UC_Queue(ActiveItemQueue):

    def __init__(self, queue_id, keep_history=None, default_priority=100):
        super().__init__(
            queue_id=queue_id,
            keep_history=keep_history,
            default_priority=default_priority)
