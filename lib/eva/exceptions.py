import logging

class GenericException(Exception):

    def __init__(self, msg=None):
        logging.debug('Exception {}: {}'.format(self.__class__.__name__, msg))
        super().__init__(msg)


class FunctionFailed(GenericException):
    pass


class ResourceNotFound(GenericException):
    pass


class AccessDenied(GenericException):
    pass
