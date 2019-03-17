__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.0"

import logging

from eva.tools import InvalidParameter


class GenericException(Exception):

    def __init__(self, msg=''):
        super().__init__(str(msg))
        logging.debug('Exception {}: {}'.format(self.__class__.__name__,
                                                str(self)))


class FunctionFailed(GenericException):

    def __str__(self):
        msg = super().__str__()
        return msg if msg else 'Function call failed'


class ResourceNotFound(GenericException):

    def __str__(self):
        msg = super().__str__()
        return msg + ' not found' if msg else 'Resource not found'

class ResourceBusy(GenericException):

    def __str__(self):
        msg = super().__str__()
        return msg if msg else 'Resource is in use'


class ResourceAlreadyExists(GenericException):

    def __str__(self):
        msg = super().__str__()
        return msg + ' already exists' if msg else 'Resource already exists'


class AccessDenied(GenericException):

    def __str__(self):
        msg = super().__str__()
        return msg if msg else 'Access to resource is denied'
