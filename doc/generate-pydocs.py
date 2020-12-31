#!/usr/bin/env python3

import glob
import os
import sys
import sh

if len(sys.argv) < 2:
    for i in glob.glob('pydoc/tpl_*.rst'):
        out = i.replace('pydoc/tpl_', 'pydoc/pydoc_')
        os.system(f'pydoc2rst {i} {out} /opt/eva/lib')
else:
    for i in sys.argv[1:]:
        os.system(
            f'pydoc2rst pydoc/tpl_{i}.rst pydoc/pydoc_{i}.rst /opt/eva/lib')

sh.sed(
    '-i',
    's/:module:.*//g',
    'pydoc/pydoc_configs.rst',
)
