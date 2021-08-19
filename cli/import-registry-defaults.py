__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.1"

import sys
import argparse
import logging

logging.basicConfig(level=logging.DEBUG)

from pathlib import Path
sys.path.insert(0, (Path(__file__).absolute().parents[1] / 'lib').as_posix())

import eva.registry

eva.registry.init_defaults(skip_existing=True)
