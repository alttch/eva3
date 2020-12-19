from eva.features import InvalidParameter
from eva.features import eva_jcmd, cli_call


def get_controllers(node):
    controllers = []
    data = eva_jcmd('sfa', 'controller list')
    for d in data:
        if d['id'] == node:
            controllers.append(d['full_id'])
    return controllers


def setup(node=None, key=None):
    if not node or not key:
        raise InvalidParameter
    controllers = get_controllers(node)
    for c in controllers:
        print(c)
        cli_call('sfa',
                 f'controller set {c} masterkey {key}',
                 return_result=True)
        cli_call('sfa', f'controller ma-test {c}', return_result=True)


def remove(node=None):
    if not node:
        raise InvalidParameter
