def alias(alias_obj, src_obj):
    g = globals()
    try:
        g[alias_obj] = g[src_obj]
        return True
    except:
        return False
