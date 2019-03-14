import logging

class GenericException(Exception):

    def __init__(self, msg=''):
        logging.debug('Exception {}: {}'.format(self.__class__.__name__, msg))
        super().__init__(msg)


class FunctionFailed(GenericException):

    def __str__(self):
        msg = super().__str__()
        return msg if msg else 'Function call failed'


class ResourceNotFound(GenericException):

    def __str__(self):
        msg = super().__str__()
        return msg + ' not found' if msg else 'Resource not found'


class AccessDenied(GenericException):

    def __str__(self):
        msg = super().__str__()
        return msg if msg else 'Access to resource is denied'
