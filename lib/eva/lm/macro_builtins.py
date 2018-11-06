def alias(alias_obj, src_obj):
    g = globals()
    try:
        g[alias_obj] = g[src_obj]
        return True
    except:
        return False


def sleep(t, safe=True):
    if safe:
        time_start = time()
        time_end = time_start + t
        while time() < time_end:
            if is_shutdown():
                return False
            _sleep(_polldelay)
        return True
    else:
        _sleep(t)
        return True
