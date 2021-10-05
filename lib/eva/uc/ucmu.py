__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.2"

import logging
import eva.item
import eva.uc.controller


class UCMultiUpdate(eva.item.MultiUpdate):

    def set_prop(self, prop, val=None, save=False):
        if prop == 'item+':
            item = eva.uc.controller.get_item(val)
            if item and \
                    (item.item_type == 'unit' or item.item_type == 'sensor'):
                if item in self.items_to_update:
                    return False
                else:
                    self.append(item)
                    self.log_set(prop, item.oid)
                    self.set_modified(save)
                return True
            else:
                return False
        elif prop == 'item-':
            item = eva.uc.controller.get_item(val)
            if item and \
                    (item.item_type == 'unit' or item.item_type == 'sensor'):
                result = self.remove(item)
                if result:
                    self.log_set(prop, item.oid)
                    self.set_modified(save)
                    return True
                else:
                    return False
            else:
                return False
        elif prop == 'items':
            if not val:
                if self.items_to_update:
                    self.items_to_update = []
                    self.set_modified(save)
                return True
            if isinstance(val, list):
                i2u = []
                for i in val:
                    item = eva.uc.controller.get_item(i)
                    if not item or item in i2u:
                        return False
                    i2u.append(item)
                self.items_to_update = i2u
                self.log_set(prop, ','.join(val))
                self.set_modified(save)
                return True
            item_ids = val.split(',')
            i2u = []
            for i in item_ids:
                item = eva.uc.controller.get_item(i)
                if not item or item in i2u:
                    return False
                i2u.append(item)
            self.items_to_update = i2u
            self.log_set(prop, val)
            self.set_modified(save)
            return True
        else:
            return super().set_prop(prop, val, save)
