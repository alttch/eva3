from evacpp import GenericAction

class ItemAction(GenericAction):

    def __init__(self):
        super().__init__()


a = ItemAction()

print(a.get_status())
print(a.set_status(5))
