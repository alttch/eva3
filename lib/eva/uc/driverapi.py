__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "3.1.0"
__api__ = 1

import eva.core

def get_version():
    return __api__

def get_polldelay():
    return eva.core.polldelay

def get_timeout():
    return eva.core.timeout

def critical():
    return eva.core.critical()
