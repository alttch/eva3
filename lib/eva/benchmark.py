import time
import logging

prevstep = None

intervals = []

enabled = False


def report(s, clear=False):
    global prevstep, enabled
    if not enabled: return False
    ctime = time.time()
    interval = ctime - prevstep if prevstep else None
    if clear:
        prevstep = None
    else:
        prevstep = ctime
    logging.warning('BENCHMARK STEP {} at {} (diff: {})'.format(
        s, ctime, interval))
    if interval is not None and clear: intervals.append(interval)


def reset():
    global prevstep
    prevstep = None
    intervals.clear()
