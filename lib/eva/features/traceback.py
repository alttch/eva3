import eva.registry


def setup():
    for c in ['uc', 'lm', 'sfa']:
        eva.registry.key_set_field(f'config/{c}/main', 'server/show-traceback',
                                   True)
    print('Completed. Restart the controllers to have traceback enabled')


def remove():
    for c in ['uc', 'lm', 'sfa']:
        eva.registry.key_set_field(f'config/{c}/main', 'server/show-traceback',
                                   False)
    print('Restart the controllers to have traceback disabled')
