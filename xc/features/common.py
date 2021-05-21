__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.3.3"

import os
import sys
import subprocess
import rapidjson

from pathlib import Path

dir_eva = Path(__file__).absolute().parents[3].as_posix()

sudo = os.environ['SUDO'] + ' ' if 'SUDO' in os.environ else ''

from eva.tools import ShellConfigFile, ConfigFile
from eva.tools import dict_from_str
from eva.tools import val_to_boolean

from eva.exceptions import InvalidParameter
from eva.exceptions import FunctionFailed
from eva.exceptions import GenericException


class UnsupportedOS(GenericException):

    def __str__(self):
        msg = super().__str__()
        return 'Unsupported OS or distribution' + (', ' + msg if msg else '')


def get_os():
    with ShellConfigFile('/etc/os-release') as fh:
        try:
            os_id = fh.get('ID')
        except KeyError:
            raise RuntimeError('Unable to detect Linux distribution')
        try:
            os_id_like = fh.get('ID_LIKE')
        except KeyError:
            os_id_like = os_id
    i = os_id_like.split()
    if 'debian' in i:
        os_id_like = 'debian'
    elif 'fedora' in i:
        os_id_like = 'fedora'
    return os_id, os_id_like


OS_ID, OS_LIKE = get_os()

CONTROLLERS = {'uc': 'UC', 'lm': 'LM PLC', 'sfa': 'SFA'}


def exec_shell(cmd, input=None, passthru=False):
    from . import print_err
    if passthru:
        code = os.system(cmd)
        if code:
            raise RuntimeError(f'shell command failed (code {code}):\n{cmd}')
    else:
        p = subprocess.run(cmd,
                           input=input,
                           shell=True,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
        if p.returncode != 0:
            print_err('FAILED')
            print_err(p.stderr.decode(), end='')
            raise RuntimeError(f'command failed: {cmd}')


def eva_jcmd(controller, cmd, input=input, passthru=False):
    from . import print_err
    p = subprocess.run(f'{dir_eva}/bin/eva {controller} -J {cmd}',
                       shell=True,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    if p.returncode != 0:
        print_err('FAILED')
        print_err(p.stderr.decode(), end='')
        raise RuntimeError(f'command failed: {cmd}')
    try:
        return rapidjson.loads(p.stdout.decode())
    except:
        raise RuntimeError(f'invalid JSON output: {cmd}')


def install_system_packages(packages, prepare=True):
    try:
        if OS_LIKE == 'debian':
            pre_cmd = f'{sudo}apt-get update'
            installer = f'{sudo}apt-get install -y --no-install-recommends '
        elif OS_LIKE == 'fedora':
            pre_cmd = None
            installer = f'{sudo}yum install -y '
        if pre_cmd and prepare:
            print('Preparing...')
            exec_shell(pre_cmd)
        print('Installing packages: ' + ' '.join(packages))
        exec_shell(installer + ' '.join(packages))
    except:
        if os.getuid() != 0:
            from . import print_err
            print_err(
                '\nIf the command requires root permissions but EVA ICS is '
                'managed by the regular user,\ntry repeating it with '
                'SUDO=sudo OS env variable set (sudo should accept commands'
                ' without the password)')
        raise


def rebuild_python_venv():
    print('Rebuilding venv...')
    exec_shell(dir_eva + '/install/build-venv')


def restart_controller(controller=''):
    print(f'Restarting {CONTROLLERS.get(controller)}...')
    exec_shell(f'{dir_eva}/sbin/eva-control restart {controller}',
               passthru=True)


def append_python_libraries(libs, rebuild_venv=True):
    import eva.registry as registry
    with registry.key_as_dict('config/venv') as venv:
        extra = venv.get('extra', [])
        for lib in libs:
            lib_id = lib.split('=', 1)[0]
            print(f'Adding extra Python library dependency: {lib}')
            for x in extra.copy():
                x_id = x.split('=', 1)[0]
                if x_id == lib_id:
                    extra.remove(x)
            extra.append(lib)
        venv.set_modified()
    if rebuild_venv:
        rebuild_python_venv()


def remove_python_libraries(libs, rebuild_venv=True):
    import eva.registry as registry
    with registry.key_as_dict('config/venv') as venv:
        extra = venv.get('extra', [])
        for lib in libs:
            print(f'Removing extra Python library dependency: {lib}')
            try:
                extra.remove(lib)
                venv.set_modified()
            except ValueError:
                pass
    if rebuild_venv:
        rebuild_python_venv()


def cli_call(controller, cmd, return_result=False):
    from . import print_err
    import subprocess
    dcmd = controller
    if dcmd:
        dcmd += ' '
    dcmd += cmd
    cmd = f'{dir_eva}/bin/eva {controller}' + (' -J --quiet '
                                               if return_result else ' ') + cmd
    p = subprocess.run(cmd,
                       shell=True,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    if p.returncode != 0:
        print_err('FAILED')
        print_err(p.stderr.decode(), end='')
        raise RuntimeError(f'command failed: {cmd}')
    else:
        return p.stdout.decode()


def download_phis(phis):
    from . import cli
    for phi in phis:
        print(f'Downloading PHI module {phi}')
        cli_call('uc', f'phi download -y {phi}', return_result=True)


def remove_phis(phis):
    from . import cli
    for phi in phis:
        phi = phi.rsplit('/', 1)[-1].rsplit('.', 1)[0]
        print(f'Removing PHI module {phi}')
        cli_call('uc', f'phi unlink {phi}', return_result=True)


def is_enabled(p):
    with ShellConfigFile('eva_servers') as fh:
        try:
            return val_to_boolean(fh.get(f'{p.upper()}_ENABLED'))
        except KeyError:
            return False
