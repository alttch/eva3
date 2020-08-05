#!/usr/bin/env python3

import glob
import os

for i in glob.glob('pydoc/tpl_*.rst'):
    out = i.replace('pydoc/tpl_', 'pydoc/pydoc_')
    os.system(f'pydoc2rst {i} {out} /opt/eva/lib')
