__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.2"

import logging

from eva.tools import InvalidParameter
from eva.tools import kb_uri


class GenericException(Exception):

    def __init__(self, msg='', kb=None):
        super().__init__(str(msg))
        self.kb = kb
        logging.debug('Exception {}: {}'.format(self.__class__.__name__,
                                                str(self)))

    def __str__(self):
        msg = super().__str__()
        if self.kb:
            if not msg:
                msg = ''
            msg += kb_uri(self.kb)
        return msg


class FunctionFailed(GenericException):
    """
    raised with function failed with any reason
    """

    def __str__(self):
        msg = super().__str__()
        return msg if msg else 'Function call failed'


class ResourceNotFound(GenericException):
    """
    raised when requested resource is not found
    """

    def __str__(self):
        msg = super().__str__()
        return msg + ' not found' if msg else 'Resource not found'


class ResourceBusy(GenericException):
    """
    raised when requested resource is busy (e.g. can't be changed)
    """

    def __str__(self):
        msg = super().__str__()
        return msg if msg else 'Resource is in use'


class ResourceAlreadyExists(GenericException):
    """
    raised when requested resource already exists
    """

    def __str__(self):
        msg = super().__str__()
        return msg + ' already exists' if msg else 'Resource already exists'


class AccessDenied(GenericException):
    """
    raised when call has no access to the resource
    """

    def __str__(self):
        msg = super().__str__()
        return msg if msg else 'Access to resource is denied'


class MethodNotImplemented(GenericException):
    """
    raised when requested method exists but requested functionality is not
    implemented
    """

    def __str__(self):
        msg = super().__str__()
        return msg if msg else 'Method not implemented'


class TimeoutException(GenericException):
    """
    raised when call is timed out
    """
    pass


def ecall(eresult):
    code, result = eresult
    import eva.client.apiclient as a
    if code == a.result_ok:
        if isinstance(result, dict) and len(
                result.keys()) == 1 and result.get('ok'):
            return True
        else:
            return result
    if result:
        err = result.get('error')
    else:
        err = ''
    if code == a.result_already_exists:
        raise ResourceAlreadyExists(err)
    elif code == a.result_not_found:
        raise ResourceNotFound(err)
    elif code == a.result_busy:
        raise ResourceBusy(err)
    elif code == a.result_invalid_params:
        raise InvalidParameter(err)
    elif code == a.result_not_implemented:
        raise MethodNotImplemented(err)
    elif code == a.result_forbidden:
        raise AccessDenied(err)
    else:
        raise FunctionFailed(err)
