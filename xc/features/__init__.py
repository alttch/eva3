__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2020 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.3.2"

import neotermcolor

from .common import OS_ID, OS_LIKE

from .common import UnsupportedOS

from .common import install_system_packages

from .common import append_python_libraries
from .common import remove_python_libraries

from .common import restart_controller

from .common import ConfigFile, ShellConfigFile

from .common import InvalidParameter

from .common import download_phis, remove_phis


def print_err(*args, **kwargs):
    neotermcolor.cprint(*args, color='red', **kwargs)
