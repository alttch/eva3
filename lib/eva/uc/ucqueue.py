__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"

from eva.itemqueue import ActiveItemQueue
import eva.core


class UC_Queue(ActiveItemQueue):

    def __init__(self, queue_id, keep_history=None, default_priority=100):
        super().__init__(queue_id=queue_id,
                         keep_history=keep_history,
                         default_priority=default_priority,
                         enterprise_layout=eva.core.config.enterprise_layout)
