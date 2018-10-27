import time
import logging

intervals = {}

enabled = False


def report(s, i, end=False):
    if not enabled: return False
    ctime = time.time()
    if end:
        intervals.setdefault(i, {})['e'] = ctime
    else:
        ts = ctime
        intervals.setdefault(i, {})['s'] = ctime
    logging.debug('BENCHMARK {} STEP {} at {}'.format(i, s, ctime))


def reset():
    intervals.clear()
