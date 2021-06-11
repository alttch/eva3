__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"

import sys
import yaml
import argparse
import os

from pathlib import Path
from neotermcolor import cprint

eva_dir = Path(__file__).absolute().parents[1]
locale_dir = Path(__file__).absolute().parents[1] / 'pvt/locales'

ap = argparse.ArgumentParser()

ap.add_argument('FILE', help='File to parse (YAML or JSON)')
ap.add_argument('COMMAND', choices=['generate', 'compile', 'stat'])
ap.add_argument('-o',
                '--output-dir',
                help=f'Locale output directory (default: {locale_dir}',
                default=locale_dir,
                metavar='DIR')
ap.add_argument('-l',
                '--lang',
                required=True,
                action='append',
                type=str,
                help='Languages',
                metavar='LANG')

a = ap.parse_args()

# don't use set, need ordered
MSG_IDS = []

with open(a.FILE) as fh:
    content = yaml.safe_load(fh)


def parse_content(content):
    if isinstance(content, str):
        if content not in MSG_IDS:
            MSG_IDS.append(content)
    elif isinstance(content, list):
        for c in content:
            parse_content(c)
    elif isinstance(content, dict):
        for k, v in content.items():
            parse_content(v)


parse_content(content)

for lang in a.lang:
    po_file = Path(a.output_dir) / f'{lang}/LC_MESSAGES'
    ldir = Path(
            a.FILE).absolute().parent.as_posix()[len(eva_dir.as_posix()) +
                                                 1:]
    if '/' in ldir:
        po_file /= ldir.split('/', 1)[-1]
    po_file /= Path(a.FILE).with_suffix('.po').name
    po_file.parent.mkdir(parents=True, exist_ok=True)
    if po_file.exists():
        pass
    print(f'[{a.COMMAND[0]}] {po_file} ', end='')
    if a.COMMAND == 'generate':
        if po_file.exists():
            write_header = False
            with po_file.open() as fh:
                existing_ids = [
                    i.split(maxsplit=1)[-1].strip()[1:-1]
                    for i in fh.readlines()
                    if i.startswith('msgid ')
                ]
            del existing_ids[0]
            m_ids = [i for i in MSG_IDS if i not in existing_ids]
        else:
            write_header = True
            m_ids = MSG_IDS
        if m_ids or write_header:
            with po_file.open('a') as fh:
                if write_header:
                    fh.write('#, fuzzy\nmsgid ""\nmsgstr ""\n'
                             '"Content-Type: text/plain; charset=utf-8\\n"\n')
                for i in m_ids:
                    fh.write(f'\nmsgid "{i}"\nmsgstr ""\n')
        cprint(f'+{len(m_ids)}', color='cyan' if m_ids else 'grey')
    elif a.COMMAND == 'compile':
        mo_file = po_file.with_suffix('.mo')
        if not mo_file.exists(
        ) or mo_file.stat().st_mtime < po_file.stat().st_mtime:
            code = os.system(f'msgfmt {po_file} -o {mo_file}')
            if code:
                raise RuntimeError(f'command exited with code {code}')
            cprint('OK', color='green')
        else:
            cprint('skipped', color='grey')
    elif a.COMMAND == 'stat':
        with po_file.open() as fh:
            strs = [x for x in fh.readlines() if x.startswith('msgstr ')]
            del strs[0]
            translated = len(
                [x for x in strs if x.split(maxsplit=1)[1].strip() != '""'])
            missing = len(strs) - translated
            print(f' translated: {translated}', end='')
            if missing:
                print(', missing: ', end='')
                cprint(missing, color='yellow')
            else:
                print()
