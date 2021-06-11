__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"

import os
import getopt
import sys
import subprocess
import time
import rapidjson

from pathlib import Path

dir_eva = Path(__file__).absolute().parents[1].as_posix()
dir_runtime = dir_eva + '/runtime'

cvars = {}


def usage():
    print("""
EVA UC xc test env

Usage: test-uc-xc <xc> [args]
    """)
    sys.exit(99)


cvars_fname = dir_runtime + '/uc_cvars.json'

if len(sys.argv) < 2:
    usage()
print('Reading custom vars from %s' % cvars_fname)
print()

with open(cvars_fname) as fd:
    raw = fd.read()
cvars = rapidjson.loads(raw)

for x in sorted(cvars.keys()):
    print('%s = "%s"' % (x, cvars[x]))

env = os.environ.copy()
if not 'PATH' in env:
    env['PATH'] = ''
env['PATH'] = '%s/bin:%s/xbin:' % (dir_eva, dir_eva) + env['PATH']
env.update(cvars)

print()
print("Starting '%s'" % ' '.join(sys.argv[1:]))
print()
stime = time.time()
print('stime: %f' % stime)

c = sys.argv[1]

if c[0] != '.' and c[0] != '/':
    c = './' + c

cmd = [c]

if len(sys.argv) > 1:
    cmd += sys.argv[2:]

try:
    p = subprocess.Popen(args=cmd,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT,
                         close_fds=True,
                         env=env)
    p.wait()
except:
    print()
    print('Command execution failed')
    sys.exit(2)
out, err = p.communicate()
etime = time.time()
diff = etime - stime
print('etime: %f' % etime)
print('duration: %f sec  ( %f msec )' % (diff, diff * 1000))
print("exitcode: %u" % p.returncode)
print()
print("---- STDOUT ----")
if out:
    print(out.decode())
print("---- STDERR ----")
if err:
    print(err.decode())
print("----------------")
