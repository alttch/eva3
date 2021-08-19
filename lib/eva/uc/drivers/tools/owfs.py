"""
OWFS helper module
"""

__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.1"

from eva.uc.owfs import is_bus
from eva.uc.owfs import get_bus as _get_bus

from eva.exceptions import ResourceNotFound
from eva.exceptions import ResourceBusy


def get_bus(bus_id, timeout=None):
    """
    Get OWFS virtual bus

    Returns:
        OWFS virtual bus object

    Raises:
        eva.exceptions.ResourceNotFound: if the bus doesn't exist
        eva.exceptions.ResourceBusy: if the bus is busy (unable to get within
                                     core timeout)
        RuntimeError: if connection error has been occured
        """
    bus = _get_bus(bus_id, timeout)
    if bus:
        return bus
    elif bus is None:
        raise ResourceNotFound(f'OWFS bus {bus_id} not available or')
    elif bus is False:
        raise RuntimeError(f'OWFS bus {bus_id} connection error')
    elif bus == 0:
        raise ResourceBusy(f'OWFS bus {bus_id} is locked')
