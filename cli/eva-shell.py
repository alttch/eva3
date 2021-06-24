__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"

import sys
import os
import time
import configparser
import platform
import argparse
import textwrap
import subprocess

from functools import lru_cache

from pathlib import Path
dir_eva = Path(__file__).absolute().parents[1].as_posix()
dir_backup = dir_eva + '/backup'
dir_lib = dir_eva + '/lib'
dir_etc = dir_eva + '/etc'
dir_bin = dir_eva + '/bin'
dir_sbin = dir_eva + '/sbin'
dir_cli = dir_eva + '/cli'
dir_runtime = dir_eva + '/runtime'
dir_venv = dir_eva + '/venv'
sys.path.insert(0, dir_lib)

import eva.features

dir_cwd = os.getcwd()

os.chdir(dir_eva)
os.environ['EVA_DIR'] = dir_eva
path = os.environ.get('PATH', '')
if path:
    path = ':' + path
os.environ['PATH'] = f'{dir_eva}/runtime/xc/shell:{dir_venv}/bin' + path

exec_before_save = None
exec_after_save = None
cmds = []

update_repo = 'https://get.eva-ics.com'

import eva.client.cli

from eva.client.cli import GenericCLI
from eva.client.cli import ControllerCLI
from eva.client.cli import ComplGeneric
from eva.client.cli import ComplUser
from eva.client.cli import ComplKey

import eva.registry


class ComplSubshellCmd(ComplGeneric):

    def __init__(self, cli, for_notifier=False):
        self.for_notifier = for_notifier
        super().__init__(cli)

    def __call__(self, prefix, **kwargs):
        shell = kwargs['parsed_args']._type if not self.for_notifier else \
                kwargs['parsed_args'].p
        c = kwargs['parsed_args'].subcommand
        if shell:
            try:
                os.environ['_ARGCOMPLETE'] = '1'
                os.environ['_ARGCOMPLETE_IFS'] = '\n'
                args = c + [prefix]
                line = 's ' + ' '.join(args)
                os.environ['COMP_POINT'] = str(len(line))
                os.environ['COMP_LINE'] = line
                self.cli.subshell_extra_args = args
                if self.for_notifier:
                    cli.do_start_shell('notifymanager',
                                       '.py',
                                       'product=\'{}\''.format(shell),
                                       restart_interactive=False)
                else:
                    cli.do_start_shell(shell, restart_interactive=False)
                eva.client.cli.completer_stream.seek(0)
                eva.client.cli.complete_only = True
                compl = eva.client.cli.completer_stream.readlines()
                result = [x.decode().strip() for x in compl]
                return result
            finally:
                del os.environ['_ARGCOMPLETE']
                eva.client.cli.complete_only = False
        return


class ComplBackupList(ComplGeneric):

    def __call__(self, prefix, **kwargs):
        code, data = self.cli.call('backup list')
        result = []
        if code:
            return result
        for v in data:
            result.append(v['name'])
        return result


class ComplIOTE(ComplGeneric):

    def __call__(self, prefix, **kwargs):
        code, data = self.cli.call('iote list')
        result = []
        if code:
            return result
        for v in data:
            result.append(v['account'])
        return result


class ComplFeatures(ComplGeneric):

    def __call__(self, prefix, **kwargs):
        import glob
        return [
            x.rsplit('/', 1)[-1].rsplit('.', 1)[0]
            for x in glob.glob('lib/eva/features/*.yml')
        ]


class ManagementCLI(GenericCLI):

    def prepare_result_data(self, data, api_func, itype):
        if itype not in ['backup']:
            return super().prepare_result_data(data, api_func, itype)
        result = []
        for d in data.copy():
            d['time'] = time.ctime(d['time'])
            result.append(d)
        return result

    def prepare_result_dict(self, data, api_func, itype):
        if api_func not in ['status_controller', 'registry_status']:
            return super().prepare_result_dict(data, api_func, itype)
        result = {}
        for k, v in data.copy().items():
            result[k] = 'running' if v else 'stopped'
        return result

    def add_functions(self):
        super().add_functions()
        self.process_configuration()
        self.add_manager_common_functions()
        self.add_manager_control_functions()
        self.add_manager_backup_functions()
        self.add_manager_registry_functions()
        self.add_manager_edit_functions()
        self.add_management_shells()
        self.add_manager_feature_functions()
        self.add_manager_iote_functions()
        self.add_manager_power_functions()
        self.add_user_defined_functions()

    def process_configuration(self):
        self.products_configured = []
        try:
            for c in ['uc', 'lm', 'sfa']:
                try:
                    if eva.registry.key_get_field(f'config/{c}/service',
                                                  'setup'):
                        self.products_configured.append(c)
                except:
                    pass
        except:
            pass

    def add_manager_registry_functions(self):
        ap_registry = self.sp.add_parser('registry', help='Registry management')

        sp_registry = ap_registry.add_subparsers(dest='_func',
                                                 metavar='func',
                                                 help='Registry commands')

        sp_registry_manage = sp_registry.add_parser('manage',
                                                    help='Manage registry')
        sp_registry_manage.add_argument('key',
                                        help='Registry key',
                                        metavar='NAME',
                                        nargs='?')
        sp_ = sp_registry.add_parser('start', help='Start registry server')
        sp_registry_stop = sp_registry.add_parser('stop',
                                                  help='Stop registry server')
        sp_registry_status = sp_registry.add_parser(
            'status', help='Status of registry server')
        sp_registry_restart = sp_registry.add_parser(
            'restart', help='Restart registry server')

    def add_manager_backup_functions(self):
        ap_backup = self.sp.add_parser('backup', help='Backup management')

        sp_backup = ap_backup.add_subparsers(dest='_func',
                                             metavar='func',
                                             help='Backup commands')

        sp_backup_save = sp_backup.add_parser('save',
                                              help='Backup system state')
        sp_backup_save.add_argument('f',
                                    help='Backup name',
                                    metavar='NAME',
                                    nargs='?')

        sp_backup_restore = sp_backup.add_parser('restore',
                                                 help='Restore system state')
        sp_backup_restore.add_argument(
            'f', help='Backup name',
            metavar='NAME').completer = ComplBackupList(self)
        sp_backup_restore.add_argument('-i',
                                       '--file',
                                       dest='file',
                                       action='append',
                                       nargs='?',
                                       help='Restore single file',
                                       metavar='FILE')
        sp_backup_restore.add_argument(
            '-r',
            '--runtime',
            dest='r',
            help='Completely restore runtime (including databases)',
            action='store_true')
        sp_backup_restore.add_argument('--ui',
                                       dest='ui',
                                       help='Restore ui folder',
                                       action='store_true')
        sp_backup_restore.add_argument('--pvt',
                                       dest='pvt',
                                       help='Restore pvt folder',
                                       action='store_true')
        sp_backup_restore.add_argument('-a',
                                       '--full',
                                       dest='full',
                                       help='Restore everything',
                                       action='store_true')

        sp_backup_list = sp_backup.add_parser('list', help='List backups')

        sp_backup_unlink = sp_backup.add_parser('unlink', help='Delete backup')
        sp_backup_unlink.add_argument(
            'f', help='Backup name',
            metavar='NAME').completer = ComplBackupList(self)

    def add_manager_edit_functions(self):
        ap_edit = self.sp.add_parser('edit', help='Edit configs')

        sp_edit = ap_edit.add_subparsers(dest='_func',
                                         metavar='func',
                                         help='Edit commands')

        sp_edit_crontab = sp_edit.add_parser('crontab', help='Edit crontab')
        sp_edit_venv = sp_edit.add_parser(
            'venv', help='Edit Python virtual environment configuration')
        sp_edit_watchdog_config = sp_edit.add_parser(
            'watchdog-config', help='Edit controller watchdog configuration')
        sp_edit_mailer_config = sp_edit.add_parser(
            'mailer-config', help='Edit mailer configuration')

        ap_masterkey = self.sp.add_parser('masterkey',
                                          help='Masterkey management')

        sp_masterkey = ap_masterkey.add_subparsers(dest='_func',
                                                   metavar='func',
                                                   help='Masterkey commands')

        sp_masterkey_set = sp_masterkey.add_parser(
            'set', help='Set masterkey for all controllers configured')
        sp_masterkey_set.add_argument('a',
                                      metavar='KEY',
                                      help='New masterkey',
                                      nargs='?')
        sp_masterkey_set.add_argument('-a',
                                      '--access',
                                      choices=['local-only', 'remote'],
                                      metavar='ACCESS_TYPE',
                                      help='Access type (local-only / remote)')

    def add_manager_control_functions(self):
        eva.client.cli.shells_available = []
        if not self.products_configured:
            return
        eva.client.cli.shells_available = self.products_configured
        ap_controller = self.sp.add_parser(
            'server', help='Controllers server management functions')
        sp_controller = ap_controller.add_subparsers(dest='_func',
                                                     metavar='func',
                                                     help='Management commands')

        ap_start = sp_controller.add_parser('start',
                                            help='Start controller server(s)')
        ap_start.add_argument('p',
                              metavar='CONTROLLER',
                              help='Controller type (' +
                              ', '.join(self.products_configured) + ')',
                              choices=self.products_configured,
                              nargs='?')
        ap_stop = sp_controller.add_parser('stop',
                                           help='Stop controller server(s)')
        ap_stop.add_argument('p',
                             metavar='CONTROLLER',
                             help='Controller type (' +
                             ', '.join(self.products_configured) + ')',
                             choices=self.products_configured,
                             nargs='?')
        ap_restart = sp_controller.add_parser(
            'restart', help='Restart controller server(s)')
        ap_restart.add_argument('p',
                                metavar='CONTROLLER',
                                help='Controller type (' +
                                ', '.join(self.products_configured) + ')',
                                choices=self.products_configured,
                                nargs='?')
        ap_status = sp_controller.add_parser(
            'status', help='Status of the controller server(s)')
        ap_status.add_argument('p',
                               metavar='CONTROLLER',
                               help='Controller type (' +
                               ', '.join(self.products_configured) + ')',
                               choices=self.products_configured,
                               nargs='?')

        ap_enable = sp_controller.add_parser('enable',
                                             help='Enable controller server')
        ap_enable.add_argument('p',
                               metavar='CONTROLLER',
                               help='Controller type (' +
                               ', '.join(self.products_configured) + ')',
                               choices=self.products_configured)

        ap_disable = sp_controller.add_parser('disable',
                                              help='Disable controller server')
        ap_disable.add_argument('p',
                                metavar='CONTROLLER',
                                help='Controller type (' +
                                ', '.join(self.products_configured) + ')',
                                choices=self.products_configured)

    def add_manager_common_functions(self):
        ap_version = self.sp.add_parser('version',
                                        help='Display version and build')
        ap_update = self.sp.add_parser(
            'update', help='Check and update to new version if exists')
        ap_update.add_argument('--YES',
                               dest='y',
                               help='Update without any prompts',
                               action='store_true')
        ap_update.add_argument('-u',
                               '--repository-url',
                               dest='u',
                               metavar='URL',
                               help='EVA ICS repository url')
        ap_update.add_argument('-i',
                               '--info-only',
                               dest='i',
                               help='Check for a new version without upgrading',
                               action='store_true')
        ap_update.add_argument('-M',
                               '--mirror',
                               dest='mirror',
                               help='Update local mirror',
                               action='store_true')

        ap_mirror = self.sp.add_parser('mirror',
                                       help='Mirror management functions')
        sp_mirror = ap_mirror.add_subparsers(dest='_func',
                                             metavar='func',
                                             help='Management commands')
        ap_mirror_update = sp_mirror.add_parser(
            'update', help='Create / update local EVA ICS mirror')
        ap_mirror_update.add_argument('-u',
                                      '--repository-url',
                                      dest='u',
                                      metavar='URL',
                                      help='EVA ICS repository url')

        ap_mirror_set = sp_mirror.add_parser(
            'set', help='Set mirror (do not run this on primary node)')
        ap_mirror_set.add_argument(
            'MIRROR_URL',
            metavar='URL',
            help='EVA ICS mirror url as http://server:port/mirror,'
            ' "default" to restore default settings')

    def add_manager_feature_functions(self):
        ap_feature = self.sp.add_parser('feature', help='Feature functions')
        sp_feature = ap_feature.add_subparsers(dest='_func',
                                               metavar='func',
                                               help='Management commands')

        ap_list_available = sp_feature.add_parser(
            'list-available', help='List available features')

        ap_help = sp_feature.add_parser('help', help='Get feature help')
        ap_help.add_argument('i',
                             metavar='FEATURE').completer = ComplFeatures(self)

        ap_setup = sp_feature.add_parser('setup', help='Setup feature')
        ap_setup.add_argument('i',
                              metavar='FEATURE').completer = ComplFeatures(self)
        ap_setup.add_argument('c',
                              metavar='PARAMETERS',
                              help='Parameters, name=value, comma separated',
                              nargs='?')
        ap_setup = sp_feature.add_parser('remove', help='Remove feature')
        ap_setup.add_argument('i',
                              metavar='FEATURE').completer = ComplFeatures(self)
        ap_setup.add_argument('c',
                              metavar='PARAMETERS',
                              help='Parameters, name=value, comma separated',
                              nargs='?')

    def add_manager_iote_functions(self):
        ap_iote = self.sp.add_parser('iote',
                                     help='IOTE Cloud management functions')
        sp_iote = ap_iote.add_subparsers(dest='_func',
                                         metavar='func',
                                         help='Management commands')

        ap_join = sp_iote.add_parser('join', help='Join node to IOTE Cloud')
        ap_join.add_argument('i', metavar='ACCOUNT', help='IOTE account')
        ap_join.add_argument('a', metavar='KEY', help='Cloud key')
        ap_join.add_argument('-y',
                             '--force',
                             help='Force join/rejoin',
                             action='store_true')

        ap_get = sp_iote.add_parser('list', help='List IOTE Cloud connections')

        ap_leave = sp_iote.add_parser('leave', help='Leave IOTE Cloud')
        ap_leave.add_argument('i', metavar='ACCOUNT',
                              help='IOTE account').completer = ComplIOTE(self)
        ap_leave.add_argument('-y',
                              '--force',
                              help='Force leave',
                              action='store_true')

    def add_manager_power_functions(self):
        if os.path.exists('/.dockerenv'):
            return
        try:
            with open('/proc/1/cpuset') as fh:
                if fh.read().strip() != '/':
                    return
        except:
            pass
        ap_system = self.sp.add_parser('system', help='System functions')
        sp_system = ap_system.add_subparsers(dest='_func',
                                             metavar='func',
                                             help='System commands')

        ap_reboot = sp_system.add_parser('reboot', help='Reboot the system')
        ap_reboot.add_argument('--YES',
                               dest='y',
                               help='Reboot without any prompts',
                               action='store_true')

        ap_poweroff = sp_system.add_parser('poweroff',
                                           help='Power off the system')
        ap_poweroff.add_argument('--YES',
                                 dest='y',
                                 help='Power off without any prompts',
                                 action='store_true')

    def add_management_shells(self):
        for p in self.products_configured:
            ap = self.sp.add_parser(p, help='{} shell'.format(p.upper()))
            ap.add_argument(
                'subcommand',
                nargs=argparse.REMAINDER).completer = ComplSubshellCmd(self)
            self.api_functions[p] = getattr(self, '{}_shell'.format(p))

        ap_save = self.sp.add_parser('save', help='Save controller config')
        ap_save.add_argument('p',
                             metavar='CONTROLLER',
                             choices=self.products_configured,
                             nargs='?',
                             help='Controller type (' +
                             ', '.join(self.products_configured) + ')')

        ap_ns = self.sp.add_parser('ns', help='Notifier management')
        ap_ns.add_argument('p',
                           metavar='CONTROLLER',
                           choices=self.products_configured,
                           help='Controller type (' +
                           ', '.join(self.products_configured) + ')')
        ap_ns.add_argument(
            'subcommand',
            nargs=argparse.REMAINDER).completer = ComplSubshellCmd(
                self, for_notifier=True)

    def exec_control_script(self, command, product, collect_output=False):
        cmd = '{}/eva-control {} {}'.format(dir_sbin, command,
                                            product if product else '')
        if collect_output:
            with os.popen(cmd) as p:
                result = p.readlines()
            return result
        else:
            os.system(cmd)
            time.sleep(1)

    def uc_shell(self, params):
        code = self.start_shell('uc')
        return self.local_func_result_empty if not code else (code, '')

    def lm_shell(self, params):
        code = self.start_shell('lm')
        return self.local_func_result_empty if not code else (code, '')

    def sfa_shell(self, params):
        code = self.start_shell('sfa')
        return self.local_func_result_empty if not code else (code, '')

    def manage_ns(self, params):
        self.subshell_extra_args = params.get('subcommand', [])
        code = self.start_shell('notifymanager', '.py',
                                'product=\'{}\''.format(params.get('p')))
        return self.local_func_result_empty if not code else (code, '')

    def start_shell(self, p, x='-cmd.py', xp=''):
        sst = p
        code = 10
        old_to = None
        old_force_interactive = False
        while sst or old_to:
            if not sst and old_to:
                sst = old_to
                force_interactive = old_force_interactive
                old_to = None
            else:
                force_interactive = False
            result = self.do_start_shell(sst,
                                         x,
                                         xp,
                                         force_interactive=force_interactive)
            if not result:
                code = 10
                break
            else:
                code = 0
            self.subshell_extra_args = eva.client.cli.shell_switch_to_extra_args
            if self.subshell_extra_args:
                old_to = sst
                old_force_interactive = eva.client.cli.shell_back_interactive
            sst = eva.client.cli.shell_switch_to
            eva.client.cli.shell_switch_to = None
            eva.client.cli.shell_switch_to_extra_args = None
            eva.client.cli.shell_back_interactive = False
        if eva.client.cli.subshell_exit_code:
            code = eva.client.cli.subshell_exit_code + 100
        return code

    def do_start_shell(self,
                       p,
                       x='-cmd.py',
                       xp='',
                       force_interactive=False,
                       restart_interactive=True):
        _xargs = []
        if self.in_json:
            _xargs += ['-J']
        if self.always_suppress_colors:
            _xargs += ['-R']
        try:
            if getattr(self, 'subshell_extra_args'):
                sysargs = ['{}/{}{}'.format(dir_cli, p, x)
                          ] + _xargs + self.subshell_extra_args
            else:
                sysargs = ['{}/{}{}'.format(dir_cli, p, x)] + _xargs
                if self.interactive or force_interactive:
                    sysargs.append('-I')
            with open('{}/{}{}'.format(dir_cli, p, x)) as fd:
                c = fd.read()
            c = """import sys
import eva.client.cli
eva.client.cli.say_bye = False
eva.client.cli.parent_shell_name = 'eva:{nodename}'
eva.client.cli.shells_available = {shells_available}
sys.argv = {argv}
{xp}

""".format(nodename=self.nodename,
            shells_available=self.products_configured if x == '-cmd.py' and
            (len(sys.argv) < 2 or p != sys.argv[1]) else [],
            argv=sysargs,
            xp=xp) + c
            os.chdir(dir_cwd)
            if self.interactive:
                self.save_readline()
            try:
                eva.client.cli.subshell_exit_code = 0
                exec(c)
                self.subshell_extra_args = None
            except SystemExit:
                pass
            return True
        except Exception as e:
            self.print_err(e)
            import traceback
            traceback.print_exc()
            return False
        finally:
            if self.interactive:
                self.full_reset_after_shell(
                    restart_interactive=restart_interactive)

    def full_reset_after_shell(self, restart_interactive=True):
        self.setup_parser()
        if restart_interactive:
            self.start_interactive(reset_sst=False)
        eva.client.cli.say_bye = True
        eva.client.cli.readline_processing = True if \
                not os.environ.get('EVA_CLI_DISABLE_HISTORY') else False
        eva.client.cli.parent_shell_name = None
        os.chdir(dir_eva)

    def iote_list(self, params):
        result = []
        for k, v in eva.registry.key_get('config/clouds/iote',
                                         default={}).items():
            result.append({
                'account': v['account'],
                'domain': k,
                'cloud': 'iote'
            })
        return 0, result

    def iote_leave(self, params):
        code = os.system(dir_sbin + '/iote.sh leave {} {}'.format(
            params.get('i'), '-y' if params.get('force') else ''))
        return self.local_func_result_ok if \
                not code else self.local_func_result_failed

    def iote_join(self, params):
        code = os.system(dir_sbin + '/iote.sh join {} -a {} {}'.format(
            params.get('i'), params.get('a'),
            '-y' if params.get('force') else ''))
        return self.local_func_result_ok if \
                not code else self.local_func_result_failed

    def start_controller(self, params):
        c = params.get('p')
        if c is not None and c not in self.products_configured:
            return self.local_func_result_failed
        self.exec_control_script('start', c)
        return self.local_func_result_ok

    def stop_controller(self, params):
        c = params.get('p')
        if c is not None and c not in self.products_configured:
            return self.local_func_result_failed
        self.exec_control_script('stop', c)
        return self.local_func_result_ok

    def restart_controller(self, params):
        c = params.get('p')
        if c is not None and c not in self.products_configured:
            return self.local_func_result_failed
        self.exec_control_script('restart', c)
        return self.local_func_result_ok

    def status_controller(self, params):
        c = params.get('p')
        if c is not None and c not in self.products_configured:
            return self.local_func_result_failed
        out = self.exec_control_script('status', c, collect_output=True)
        result = {}
        if c:
            try:
                result[c] = out[0].strip().lower().find('running') != -1
            except:
                return self.local_func_result_failed
        else:
            for r in out:
                try:
                    c, s = r.strip().split(': ', 1)
                    result[c.lower()] = s.lower().find('running') != -1
                except:
                    pass
        return 0, result

    def enable_controller(self, params):
        c = params['p']
        if c in self.products_configured:
            if eva.registry.key_get_field(f'config/{c}/service',
                                          'supervisord-program'):
                self.print_err('Server is controlled by supervisord')
                return self.local_func_result_failed
            else:
                eva.registry.key_set_field(f'config/{c}/service', 'enabled',
                                           True)
                return self.local_func_result_ok
        return False

    def disable_controller(self, params):
        c = params['p']
        if c in self.products_configured:
            if eva.registry.key_get_field(f'config/{c}/service',
                                          'supervisord-program'):
                self.print_err('Server is controlled by supervisord')
                return self.local_func_result_failed
            else:
                eva.registry.key_set_field(f'config/{c}/service', 'enabled',
                                           False)
                return self.local_func_result_ok
        return False

    def set_controller_user(self, params):
        c = params['p']
        if c in self.products_configured:
            eva.registry.key_set_field(f'config/{c}/service', 'user',
                                       params['v'])
            return self.local_func_result_ok
        return False

    def get_controller_user(self, params):
        c = params['p']
        if c in self.products_configured:
            return 0, eva.registry.key_set_field(f'config/{c}/service', 'user',
                                                 '')
        return False

    def print_version(self, params):
        result = {'version': self._get_version(), 'build': self._get_build()}
        return 0, result

    def before_save(self):
        if not exec_before_save:
            return True
        return os.system(exec_before_save) == 0

    def after_save(self):
        if not exec_after_save:
            return True
        return os.system(exec_after_save) == 0

    def backup_save(self, params):
        fname = params.get('f')
        if fname is None:
            fname = '{}'.format(time.strftime('%Y%m%d%H%M%S'))
        try:
            os.mkdir(dir_backup)
        except FileExistsError:
            pass
        except:
            self.print_err('Failed to create backup folder')
            return self.local_func_result_failed
        if os.path.isfile(dir_backup + '/' + fname + '.tgz'):
            self.print_err('File already exists')
            return self.local_func_result_failed
        cmd = ('tar', 'czpf', 'backup/{}.tgz'.format(fname),
               '--exclude=etc/*-dist', '--exclude=__pycache__',
               '--exclude=*.md', '--exclude=*.rst', 'runtime/*', 'etc/*',
               'ui/*', 'pvt/*')
        if not self.before_save() or \
                os.system(' '.join(cmd)) or not self.after_save():
            return self.local_func_result_failed
        return 0, {'backup': fname}

    def backup_list(self, params):
        import glob
        files = glob.glob('backup/*.tgz')
        files.sort(key=os.path.getmtime, reverse=True)
        result = []
        for f in files:
            result.append({'name': f[7:-4], 'time': os.path.getmtime(f)})
        return 0, sorted(result, key=lambda k: k['time'], reverse=True)

    def backup_unlink(self, params):
        if not self.before_save():
            return self.local_func_result_failed
        try:
            os.unlink(dir_backup + '/' + params.get('f') + '.tgz')
        except:
            self.after_save()
            return self.local_func_result_failed
        if not self.after_save():
            return self.local_func_result_failed
        return self.local_func_result_ok

    def backup_restore(self, params):
        f = dir_backup + '/' + params.get('f') + '.tgz'
        if not os.path.isfile(f):
            self.print_err('no such backup')
            return self.local_func_result_failed
        if not self.before_save():
            return self.local_func_result_failed
        if params.get('file'):
            for i in params.get('file'):
                try:
                    if not self.backup_restore_file(fname=f, frestore=i):
                        raise Exception('restore failed')
                except:
                    self.after_save()
                    return self.local_func_result_failed
            if not self.after_save():
                return self.local_func_result_failed
            return self.local_func_result_ok
        if params.get('full'):
            self.stop_controller({})
            self.registry_stop({})
            self.clear_runtime()
            self.clear_ui()
            self.clear_pvt()
            try:
                if not self.backup_restore_runtime(fname=f):
                    raise Exception('restore failed')
                if not self.backup_restore_dir(fname=f, dirname='etc'):
                    raise Exception('restore failed')
                if not self.backup_restore_dir(fname=f, dirname='ui'):
                    raise Exception('restore failed')
                if not self.backup_restore_dir(fname=f, dirname='pvt'):
                    raise Exception('restore failed')
            except:
                self.after_save()
                return self.local_func_result_failed
            if not self.after_save():
                return self.local_func_result_failed
            self.registry_start({})
            for cmd in ['import-registry-schema', 'import-registry-defaults']:
                if os.system(f'{dir_eva}/install/{cmd}'):
                    return self.local_func_result_failed
            self.start_controller({})
            return self.local_func_result_ok
        try:
            if params.get('ui'):
                self.clear_ui()
                if not self.backup_restore_dir(fname=f, dirname='ui'):
                    raise Exception('restore failed')
            if params.get('pvt'):
                self.clear_pvt()
                if not self.backup_restore_dir(fname=f, dirname='pvt'):
                    raise Exception('restore failed')
            if not params.get('ui') and not params.get('pvt'):
                self.stop_controller({})
                self.registry_stop({})
                self.clear_runtime()
                if not self.backup_restore_runtime(fname=f):
                    raise Exception('restore failed')
                if not self.backup_restore_dir(fname=f, dirname='etc'):
                    raise Exception('restore failed')
                self.registry_start({})
                for cmd in [
                        'import-registry-schema', 'import-registry-defaults'
                ]:
                    if os.system(f'{dir_eva}/install/{cmd}'):
                        return self.local_func_result_failed
                self.start_controller({})
        except:
            self.after_save()
            return self.local_func_result_failed
        if not self.after_save():
            return self.local_func_result_failed
        return self.local_func_result_ok

    def clear_runtime(self):
        print('Removing runtime')
        cmd = 'rm -rf runtime/*'
        os.system(cmd)
        return True

    def clear_ui(self):
        print('Removing ui')
        cmd = 'rm -rf ui/*'
        os.system(cmd)
        return True

    def clear_pvt(self):
        print('Removing pvt')
        cmd = 'rm -rf pvt/*'
        os.system(cmd)
        return True

    def backup_restore_runtime(self, fname):
        print(self.colored('Restoring runtime...', color='green', attrs=[]))
        cmd = ('tar', 'xpf', fname)
        cmd += ('runtime',)
        return False if os.system(' '.join(cmd)) else True

    def backup_restore_dir(self, fname, dirname):
        print(
            self.colored('Restoring {}...'.format(dirname),
                         color='green',
                         attrs=[]))
        cmd = ('tar', 'xpf', fname, dirname)
        return False if os.system(' '.join(cmd)) else True

    def backup_restore_file(self, fname, frestore):
        print(
            self.colored('Restoring {}...'.format(frestore),
                         color='green',
                         attrs=[]))
        cmd = ('tar', 'xpf', fname, frestore)
        return False if os.system(' '.join(cmd)) else True

    def set_mirror(self, params):

        from eva.tools import ConfigFile

        url = params.get('MIRROR_URL')
        eva_shell_file = 'eva_shell.ini'
        try:
            if os.path.exists(f'{dir_eva}/mirror'):
                raise RuntimeError('Can not set mirror URLs on primary node. '
                                   'If this node should be secondary, '
                                   'remove "mirror" directory')
            if url != 'default':
                if not url.endswith('/'):
                    url += '/'
                eva_mirror = url + 'eva'
                pypi_mirror = url + 'pypi/local'
                from eva.crypto import safe_download
                import rapidjson
                rapidjson.loads(
                    safe_download(eva_mirror + '/update_info.json', timeout=30))
                if safe_download(pypi_mirror + '/index.html',
                                 timeout=30).decode().strip() != '+':
                    raise RuntimeError(
                        'Invalid mirror (PyPi mirror check failed')
                with ConfigFile(eva_shell_file, init_if_missing=True) as cf:
                    cf.set('update', 'url', eva_mirror)
                trusted_host = pypi_mirror.split('/', 3)[2].split(':', 1)[0]
                eva.registry.key_set_field(
                    'config/venv', 'pip-extra-options',
                    f'-i {pypi_mirror} --trusted-host {trusted_host}')
            else:
                try:
                    with ConfigFile(eva_shell_file,
                                    init_if_missing=False) as cf:
                        cf.delete('update', 'url')
                except FileNotFoundError:
                    pass
                eva.registry.key_delete_field('config/venv',
                                              'pip-extra-options')
        except Exception as e:
            self.print_err(e)
            return self.local_func_result_failed
        print(f'Mirror set to ' +
              self.colored(url, color='green', attrs='bold'))
        print()
        if self.interactive:
            print('Now exit EVA shell and log in back')
        return self.local_func_result_ok

    def update_mirror(self, params):
        from eva.tools import ShellConfigFile
        try:
            sfa_listen = eva.registry.key_get_field('config/sfa/main',
                                                    'webapi/listen')
            if sfa_listen.startswith('127.'):
                self.print_err(
                    'The local SFA is configured to listen on the loopback only'
                )
                return self.local_func_result_failed
            if ':' in sfa_listen:
                sfa_port = int(sfa_listen.rsplit(':', 1)[-1])
            else:
                sfa_port = 80
        except Exception as e:
            self.print_err(e)
            self.print_err('mirror requires SFA, which is not configured')
            return self.local_func_result_failed
        import rapidjson
        from eva.crypto import safe_download
        try:
            dir_mirror = dir_eva + '/mirror'
            dir_mirror_pypi = dir_mirror + '/pypi'
            dir_mirror_eva = dir_mirror + '/eva'
            if os.path.isfile(dir_eva + '/venv/bin/pip'):
                pip = dir_eva + '/venv/bin/pip'
            else:
                pip = 'pip3'
            first_install = not os.path.exists(dir_mirror)
            for d in [dir_mirror, dir_mirror_pypi]:
                try:
                    os.mkdir(d)
                except FileExistsError:
                    pass
            with open(f'{dir_eva}/install/mods.list') as fh:
                mods = [x.strip() for x in fh.readlines()]
            print('Updating PyPi mirror')
            print()
            mods_skip = eva.registry.key_get_field('config/venv',
                                                   'skip',
                                                   default=[])
            mods_extra = eva.registry.key_get_field('config/venv',
                                                    'extra',
                                                    default=[])
            for m in mods.copy():
                if m in mods_skip or m.split('=', 1)[0] in mods_skip:
                    print(self.colored(f'- {m}', color='grey'))
                    mods.remove(m)
            for m in mods_extra:
                print(self.colored(f'+ {m}', color='green'))
                mods.append(m)
            if mods_skip or mods_extra:
                print()
            print(f'Python version: '
                  f'{sys.version_info.major}.{sys.version_info.minor}')
            print(f'CPU architecture: {platform.uname().machine}')
            if mirror_extra_python_versions:
                print(f'Extra Python versions: '
                      f'{", ".join(mirror_extra_python_versions)}')
            print()
            if os.getenv('SKIP_PYTHON_MODULES') != '1':
                print(f'Modules: {len(mods)}')
                print(self.colored('-' * 40, color='grey', attrs=[]))
                # update modules
                for mod in mods:
                    if mod:
                        if os.system(f'{dir_sbin}/pypi-mirror '
                                     f'download -p {pip} -b -d '
                                     f'{dir_mirror_pypi}/downloads {mod}'):
                            return self.local_func_result_failed
                # update compiled mods for extra Python versions
                cmods = Path(dir_mirror_pypi).glob(f'**/*-cp*.whl')
                xmods = set()
                srcs_req = set()
                for c in cmods:
                    m = c.name.split('-')
                    mod_name, mod_version = m[0], m[1]
                    xmods.add(f'{mod_name}=={mod_version}')
                for pyver in mirror_extra_python_versions:
                    if pyver != 'source':
                        for xmod in xmods:
                            if os.system(f'{dir_sbin}/pypi-mirror '
                                         f'download -p {pip} -b -d '
                                         f'{dir_mirror_pypi}/downloads '
                                         f'--python-version {pyver} {xmod}'):
                                self.print_warn(
                                    f'No binary package for {xmod}, '
                                    f'will download sources')
                                srcs_req.add(xmod)
                # download modules sources for missing binary mods or for all
                for s in srcs_req \
                        if 'source' not in mirror_extra_python_versions \
                        else mods:
                    if os.system(f'{dir_sbin}/pypi-mirror '
                                 f'download -p {pip} -d '
                                 f'{dir_mirror_pypi}/downloads {s}'):
                        self.print_warn(f'Unable to download sources for {s}')
                # update mirror index
                if os.system(f'{dir_sbin}/pypi-mirror '
                             f'create -d {dir_mirror_pypi}/downloads '
                             f'-m {dir_mirror_pypi}/local'):
                    return self.local_func_result_failed
                print(self.colored('-' * 40, color='grey', attrs=[]))
            print('Updating EVA ICS mirror')
            print()
            build = self._get_build()
            version = self._get_version()
            _update_repo = params.get('u')
            for d in [
                    dir_mirror_eva, f'{dir_mirror_eva}/{version}',
                    f'{dir_mirror_eva}/{version}/nightly',
                    f'{dir_mirror_eva}/yedb'
            ]:
                try:
                    os.mkdir(d)
                except FileExistsError:
                    pass
            if not _update_repo:
                _update_repo = update_repo
            manifest = None
            yedb_manifest = None
            with ShellConfigFile(f'{dir_lib}/eva/registry/info') as fh:
                YEDB_VERSION = fh.get('YEDB_VERSION')
            yedb_uris = [f'yedb/yedb-manifest-{YEDB_VERSION}.json']
            for yedb_arch in [
                    'arm-musleabihf', 'i686-musl', 'x86_64-musl', 'aarch64-musl'
            ]:
                yedb_uris.append(f'yedb/yedb-{YEDB_VERSION}-{yedb_arch}.tar.gz')
            for idx, f in enumerate([
                    f'{version}/nightly/manifest-{build}.json',
                    f'{version}/nightly/UPDATE.rst',
                    f'{version}/nightly/eva-{version}-{build}.tgz',
                    f'{version}/nightly/update-{build}.sh'
            ] + yedb_uris):
                if idx != 1 and os.path.isfile(f'{dir_mirror_eva}/{f}'):
                    print(self.colored(f'- [exists] {f}', color='grey'))
                    if idx == 0 or f.startswith('yedb/yedb-manifest'):
                        with open(f'{dir_mirror_eva}/{f}', 'rb') as fh:
                            content = fh.read()
                else:
                    content = safe_download(
                        f'{_update_repo}/{f}',
                        manifest=yedb_manifest if f.startswith('yedb/') else
                        manifest if not f.endswith('/UPDATE.rst') else None)
                    print(self.colored(f'+ [downloaded] {f}', color='green'))
                    with open(f'{dir_mirror_eva}/{f}', 'wb') as fh:
                        fh.write(content)
                if idx == 0:
                    manifest = rapidjson.loads(content)
                elif f.startswith('yedb/yedb-manifest'):
                    yedb_manifest = rapidjson.loads(content)
            with open(f'{dir_mirror_eva}/update_info.json', 'w') as fh:
                fh.write(
                    rapidjson.dumps(dict(version=str(version),
                                         build=str(build))))
            banner = f'EVA ICS {version} {build} mirror'
            with open(f'{dir_mirror}/index.html', 'w') as fh:
                fh.write(banner)
            import socket
            hostname = ([
                l for l in ([
                    ip
                    for ip in socket.gethostbyname_ex(socket.gethostname())[2]
                    if not ip.startswith("127.")
                ][:1], [[
                    (s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close())
                    for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]
                ][0][1]]) if l
            ][0][0])
            print(self.colored(f'+ update_info.json', color='green'))
            print(self.colored('-' * 40, color='grey', attrs=[]))
            print(banner)
            print()
            print(f'Mirror URL: ' +
                  self.colored(f'http://{hostname}:{sfa_port}/mirror/',
                               color='green',
                               attrs=['bold']))
            print()
            print(f'EVA ICS update: -u http://{hostname}:{sfa_port}/mirror/eva')
            print(f'PIP_EXTRA_OPTIONS="-i http://{hostname}:{sfa_port}'
                  f'/mirror/pypi/local --trusted-host {hostname}"')
            print()
            print('To automatically set the mirror config on'
                  ' other nodes, execute there a command:')
            print()
            print(
                self.colored(
                    f'    eva mirror set http://{hostname}:{sfa_port}/mirror/',
                    color='green',
                    attrs=['bold']))
            print()
            if first_install:
                print()
                print(
                    self.colored(
                        'First time mirroring. Please '
                        'restart SFA to serve the mirror directory',
                        color='yellow',
                        attrs='bold'))
            print()
            return self.local_func_result_ok
        except Exception as e:
            self.print_err(e)
            return self.local_func_result_failed

    @staticmethod
    def _get_build():
        with os.popen('{}/eva-tinyapi -B'.format(dir_sbin)) as p:
            data = p.read()
            return int(data.strip())

    @staticmethod
    def _get_version():
        with os.popen('{}/eva-tinyapi -V'.format(dir_sbin)) as p:
            data = p.read()
            version = data.strip()
            int(version.split('.')[0])
            return version

    @staticmethod
    def _set_file_lock(name):
        lock_file = dir_eva + f'/var/{name}.lock'
        if os.path.exists(lock_file):
            raise RuntimeError
        else:
            with open(lock_file, 'w'):
                pass

    @staticmethod
    def _remove_file_lock(name):
        lock_file = dir_eva + f'/var/{name}.lock'
        try:
            os.unlink(lock_file)
        except FileNotFoundError:
            pass

    def update(self, params):
        import rapidjson
        from eva.crypto import safe_download
        try:
            self._set_file_lock('update')
        except RuntimeError:
            self.print_err('update is already active')
            return self.local_func_result_failed
        try:
            _update_repo = params.get('u')
            if not _update_repo:
                _update_repo = update_repo
            os.environ['EVA_REPOSITORY_URL'] = _update_repo
            print('Using repository : ' +
                  self.colored(_update_repo, color='green', attrs=['bold']))
            print()
            try:
                build = self._get_build()
                version = self._get_version()
            except:
                return self.local_func_result_failed
            try:
                if 'EVA_UPDATE_FORCE_VERSION' in os.environ:
                    new_version, new_build = os.environ[
                        'EVA_UPDATE_FORCE_VERSION'].split(':')
                    new_build = int(new_build)
                    forced_version = True
                else:
                    result = rapidjson.loads(
                        safe_download(_update_repo + '/update_info.json',
                                      timeout=10))
                    new_build = int(result['build'])
                    new_version = result['version']
                    forced_version = False
            except Exception as e:
                self.print_err(e)
                return self.local_func_result_failed
            if params.get('i'):
                return 0, {
                    'build': build,
                    'new_build': new_build,
                    'new_version': new_version,
                    'update_available': build < new_build
                }
            print(
                self.colored('Current build', color='blue', attrs=['bold']) +
                ' : ' + self.colored(f'{build} (v{version})', color='cyan'))
            print(
                self.colored(
                    f'{"Selected" if forced_version else "Latest available"}'
                    ' build',
                    color='blue',
                    attrs=['bold']) + ' : ' +
                self.colored('{} (v{})'.format(new_build, new_version),
                             color='yellow'))
            if build == new_build:
                return self.local_func_result_empty
            if build > new_build:
                print('Your build is newer than update server has')
                return self.local_func_result_failed
            manifest = rapidjson.loads(
                safe_download('{}/{}/nightly/manifest-{}.json'.format(
                    _update_repo, new_version, new_build)))
            if not params.get('y'):
                if version != new_version:
                    try:
                        content = safe_download(
                            '{}/{}/nightly/UPDATE.rst'.format(
                                _update_repo, new_version))
                    except Exception as e:
                        self.print_err(e)
                        print('Unable to download update info: {}'.format(e))
                        return self.local_func_result_failed
                    print()
                    print(content.decode())
                try:
                    u = input('Type ' +
                              self.colored('YES', color='red', attrs=['bold']) +
                              ' (uppercase) to update, or press ' +
                              self.colored('ENTER', color='white') +
                              ' to abort > ')
                except:
                    print()
                    u = ''
                if u != 'YES':
                    return self.local_func_result_empty
            update_script = f'update-{new_build}.sh'
            update_files = [update_script, f'eva-{new_version}-{new_build}.tgz']
            try:
                os.chdir(dir_eva)
                for f in update_files:
                    with open(f, 'wb') as fh:
                        fh.write(
                            safe_download(
                                f'{_update_repo}/{new_version}/nightly/{f}',
                                manifest=manifest))
                if not self.before_save() or \
                    os.system(f'bash {update_script}') or \
                    not self.after_save():
                    self.print_err('FAILED TO APPLY UPDATE! '
                                   'TRYING TO BRING THE NODE BACK ONLINE')
                    self.registry_start({})
                    self.start_controller({})
                    return self.local_func_result_failed
                print('Update completed', end='')
            finally:
                for f in update_files:
                    try:
                        os.unlink(f)
                    except FileNotFoundError:
                        pass
            if params.get('mirror'):
                if not self.before_save():
                    return self.local_func_result_failed
                um_result = self.update_mirror(dict(u=params.get(u)))
                if um_result == self.local_func_result_failed:
                    return um_result
                if not self.after_save():
                    return self.local_func_result_failed
            if self.interactive:
                print('. Now exit EVA shell and log in back')
            else:
                print()
            return self.local_func_result_ok
        except Exception as e:
            self.print_err(e)
            return self.local_func_result_failed
        finally:
            self._remove_file_lock('update')

    def power_reboot(self, params):
        if not params.get('y'):
            try:
                a = input('Reboot this system? (y/N) ')
            except:
                print()
                a = ''
            if a.lower() != 'y':
                return self.local_func_result_empty
        print(self.colored('Rebooting...', color='red', attrs=['bold']))
        return self.local_func_result_failed if \
                os.system('reboot') else self.local_func_result_ok

    def power_poweroff(self, params):
        if not params.get('y'):
            try:
                a = input('Power off this system? (y/N) ')
            except:
                print()
                a = ''
            if a.lower() != 'y':
                return self.local_func_result_empty
        print(self.colored('Powering off...', color='red', attrs=['bold']))
        return self.local_func_result_failed if \
                os.system('poweroff') else self.local_func_result_ok

    def add_user_defined_functions(self):
        if not cmds:
            return
        for c in cmds:
            sp = self.sp.add_parser(c['cmd'], help=c['comment'])

    def exec_cmd(self, a):
        return self.local_func_result_failed if \
                os.system(a) else self.local_func_result_ok

    def edit_crontab(self, params):
        if not self.before_save():
            return self.local_func_result_failed
        c = os.system('crontab -e')
        if not self.after_save() or c:
            return self.local_func_result_failed
        return self.local_func_result_ok

    def edit_venv(self, params):
        code = os.system(
            f'AUTO_PREFIX=1 {dir_sbin}/eva-registry-cli edit config/venv')
        return self.local_func_result_empty if \
                not code else self.local_func_result_failed

    def edit_watchdog_config(self, params):
        code = os.system(
            f'AUTO_PREFIX=1 {dir_sbin}/eva-registry-cli edit config/watchdog')
        return self.local_func_result_empty if \
                not code else self.local_func_result_failed

    def edit_mailer_config(self, params):
        code = os.system(
            f'AUTO_PREFIX=1 {dir_sbin}/eva-registry-cli edit config/common/mailer')
        return self.local_func_result_empty if \
                not code else self.local_func_result_failed

    def save(self, params):
        p = params['p']
        if p:
            if p not in self.products_configured:
                return self.local_func_result_failed
            code, result = self.call('{} save'.format(p))
            return self.local_func_result_empty if not code else (code, '')
        else:
            ok = True
            products_enabled = []
            for c in self.products_configured:
                if eva.registry.get(f'config/{c}/service', 'enabled'):
                    print('{}: '.format(
                        self.colored(p, color='blue', attrs=['bold'])),
                          end='')
                    code, result = self.call('{} save'.format(p))
                    if code:
                        print(self.colored('FAILED', color='red'))
                        ok = False
            return self.local_func_result_empty if ok else (10, '')

    def registry_manage(self, params):
        key = params.get('key')
        if key is None:
            key = ''
        params = f' edit {key}' if key else ''
        if os.system(f'{dir_bin}/eva-registry{params}'):
            return self.local_func_result_failed
        else:
            return self.local_func_result_ok

    def registry_restart(self, params):
        if not os.system(f'{dir_sbin}/eva-control status|grep \ running$'):
            self.print_err('Unable to restart registry server '
                           'while other EVA servers are running')
            return self.local_func_result_failed
        if os.system(f'{dir_sbin}/registry-control restart'):
            return self.local_func_result_failed
        else:
            return self.local_func_result_ok

    def registry_stop(self, params):
        if not os.system(f'{dir_sbin}/eva-control status|grep \ running$'):
            self.print_err('Unable to restart registry server '
                           'while other EVA servers are running')
            return self.local_func_result_failed
        if os.system(f'{dir_sbin}/registry-control stop'):
            return self.local_func_result_failed
        else:
            return self.local_func_result_ok

    def registry_start(self, params):
        if os.system(f'{dir_sbin}/registry-control start'):
            return self.local_func_result_failed
        else:
            return self.local_func_result_ok

    def registry_status(self, params):
        p = subprocess.run(f'{dir_sbin}/registry-control status',
                           shell=True,
                           stdout=subprocess.PIPE)
        if p.returncode:
            return self.local_func_result_failed
        else:
            status = p.stdout.decode().strip()
            return 0, {'registry': status == 'running'}

    def set_masterkey(self, params):

        def set_masterkey_for(p, a, access):
            try:
                if a is None:
                    a = eva.registry.key_get_field(
                        f'config/{p}/apikeys/masterkey', 'key')
                masterkey_data = {
                    'key':
                        a,
                    'master':
                        True,
                    'hosts-allow': [
                        '127.0.0.0/8' if access == 'local-only' else '0.0.0.0/0'
                    ]
                }
                eva.registry.key_set(f'config/{p}/apikeys/masterkey',
                                     masterkey_data)
                return True
            except Exception as e:
                self.print_err(e)
                return False

        import re
        p = params.get('p')
        a = params.get('a')
        access = params.get('access')
        if a and not re.match("^[A-Za-z0-9]*$", a):
            self.print_err('Masterkey should contain only letters and numbers')
            return self.local_func_result_failed
        if p:
            if p not in self.products_configured:
                return self.local_func_result_failed
            result = set_masterkey_for(p, a, access)
            if result:
                print(
                    self.colored(
                        'To apply new masterkey, restart the controller',
                        color='yellow',
                        attrs=['bold']))
            return self.local_func_result_ok if result \
                    else self.local_func_result_failed
        else:
            ok = True
            for p in self.products_configured:
                print('{}: '.format(
                    self.colored(p, color='blue', attrs=['bold'])),
                      end='')
                if set_masterkey_for(p, a, access):
                    print('OK')
                else:
                    print(self.colored('FAILED', color='red'))
                    ok = False
            if ok:
                print(
                    self.colored(
                        'To apply new masterkey, restart the controllers',
                        color='yellow',
                        attrs=['bold']))
            return self.local_func_result_empty if ok else (10, '')

    @lru_cache(maxsize=None)
    def _feature_info(self, name):
        from eva.tools import render_template
        from eva.tools import kb_uri
        fname = f'{dir_lib}/eva/features/{name}.yml'
        version = self._get_version()
        build = self._get_build()
        setup_cmd = f'feature setup {name} '
        if not self.interactive:
            setup_cmd = 'eva ' + setup_cmd
        with open(fname) as fh:
            return render_template(
                fh, {
                    'EVA_VERSION': version,
                    'EVA_BUILD': build,
                    'EVA_DIR': dir_eva,
                    'setup_cmd': setup_cmd,
                    'kb_uri': kb_uri
                })

    def list_features(self, params):
        import glob
        files = glob.glob(f'{dir_lib}/eva/features/*.yml')
        result = []
        for f in files:
            name = f.rsplit('/', 1)[-1].rsplit('.', 1)[0]
            info = self._feature_info(name)
            if not info.get('wip'):
                result.append({
                    'name': name,
                    'description': info['description']
                })
        return 0, sorted(result, key=lambda k: k['name'])

    def feature_help(self, params):
        try:
            info = self._feature_info(params['i']).copy()
        except FileNotFoundError:
            self.print_err(f'Feature not found: {params["i"]}')
            return self.local_func_result_failed
        if 'example' in info:
            example = info['example']
            del info['example']
            if 'help' in info:
                info['help'] += '\n'
            else:
                info['help'] = ''
            info['help'] += 'Example:\n\n  ' + self.colored(example,
                                                            color='white')
        return 0, info

    def feature_setup(self, params):
        print(f'Setting up feature {params["i"]}...')
        return self._feature_setup_remove('setup', params)

    def feature_remove(self, params):
        print(f'Removing feature {params["i"]}...')
        return self._feature_setup_remove('remove', params)

    def _feature_setup_remove(self, mode, params):
        from eva.tools import dict_from_str
        import importlib
        try:
            info = self._feature_info(params['i']).copy()
        except FileNotFoundError:
            self.print_err(f'Feature not found: {params["i"]}')
            return self.local_func_result_failed
        if info.get('wip'):
            self.print_warn(
                'THIS FEATURE IS UNSTABLE AND MAY BREAK THE SYSTEM!')
            self.print_warn('Press Ctrl+C to abort ', end='', flush=True)
            for _ in range(5):
                print(self.colored('.', color='yellow', attrs=['bold']),
                      end='',
                      flush=True)
                time.sleep(1)
            print()
        try:
            c = dict_from_str(params['c'])
        except:
            self.print_err('Invalid parameters')
            return self.local_func_result_failed
        if c is None:
            c = {}
        args_ok = True
        valid_args = []
        for arg, h in info.get(mode, {}).get('mandatory-args', {}).items():
            valid_args.append(arg)
            if arg not in c:
                self.print_err(f'Required parameter "{arg}" not set ({h})')
                args_ok = False
        valid_args += info.get(mode, {}).get('optional-args', {}).keys()
        for arg in c:
            if arg not in valid_args:
                self.print_err(f'Invalid parameter "{arg}"')
                args_ok = False
        if not args_ok:
            return self.local_func_result_failed
        mod = importlib.import_module(f'eva.features.{params["i"]}')
        try:
            fn = getattr(mod, mode)
        except AttributeError:
            self.print_err('Not supported by selected feature')
            return self.local_func_result_failed
        try:
            fn(**c)
        except Exception as e:
            print()
            self.print_err(e)
            return self.local_func_result_failed
        return self.local_func_result_ok


def make_exec_cmd_func(cmd):

    def _function(params):
        return cli.exec_cmd(cmd)

    return _function


_me = 'EVA ICS Management CLI version %s' % (__version__)

if os.path.basename(sys.argv[0]) == 'eva-shell' and len(sys.argv) < 2:
    sys.argv = [sys.argv[0]] + ['-I']

cli = ManagementCLI('eva', _me, remote_api_enabled=False, prog='eva')

_api_functions = {
    'server:start': cli.start_controller,
    'server:stop': cli.stop_controller,
    'server:restart': cli.restart_controller,
    'server:status': cli.status_controller,
    'server:enable': cli.enable_controller,
    'server:disable': cli.disable_controller,
    'server:get_user': cli.get_controller_user,
    'server:set_user': cli.set_controller_user,
    'version': cli.print_version,
    'feature:list-available': cli.list_features,
    'feature:help': cli.feature_help,
    'feature:setup': cli.feature_setup,
    'feature:remove': cli.feature_remove,
    'mirror:update': cli.update_mirror,
    'mirror:set': cli.set_mirror,
    'update': cli.update,
    'system:reboot': cli.power_reboot,
    'system:poweroff': cli.power_poweroff,
    'save': cli.save,
    'ns': cli.manage_ns,
    'iote:list': cli.iote_list,
    'iote:join': cli.iote_join,
    'iote:leave': cli.iote_leave,
    'backup:save': cli.backup_save,
    'backup:list': cli.backup_list,
    'backup:unlink': cli.backup_unlink,
    'backup:restore': cli.backup_restore,
    'registry:manage': cli.registry_manage,
    'registry:restart': cli.registry_restart,
    'registry:start': cli.registry_start,
    'registry:stop': cli.registry_stop,
    'registry:status': cli.registry_status,
    'edit:crontab': cli.edit_crontab,
    'edit:venv': cli.edit_venv,
    'edit:watchdog-config': cli.edit_watchdog_config,
    'edit:mailer-config': cli.edit_mailer_config,
    'masterkey:set': cli.set_masterkey
}

from eva.tools import ShellConfigFile

try:
    with ShellConfigFile('eva_config') as f:
        nodename = f.get('SYSTEM_NAME')
except (FileNotFoundError, KeyError):
    nodename = platform.node()

cfg = configparser.ConfigParser(inline_comment_prefixes=';')
try:
    cfg.read(dir_etc + '/eva_shell.ini')
    try:
        exec_before_save = cfg.get('shell', 'exec_before_save')
    except:
        pass
    try:
        exec_after_save = cfg.get('shell', 'exec_after_save')
    except:
        pass
    try:
        update_repo = cfg.get('update', 'url')
    except:
        pass
    try:
        mirror_extra_python_versions = cfg.get('update',
                                               'mirror_extra_python_versions')
        mirror_extra_python_versions = [
            x.strip()
            for x in mirror_extra_python_versions.split(',')
            if x.strip()
        ]
    except:
        mirror_extra_python_versions = []
    try:
        for c in cfg.options('cmd'):
            if c not in _api_functions:
                try:
                    x = cfg.get('cmd', c)
                    if x.find('#') == -1:
                        x = x.strip()
                        comment = c
                    else:
                        x, comment = x.split('#', 1)
                        x = x.strip()
                        comment = comment.strip()
                    cmds.append({'cmd': c, 'comment': comment})
                    _api_functions[c] = make_exec_cmd_func(x)
                except:
                    pass
    except:
        pass
except:
    pass

eva.features.print_err = cli.print_err
eva.features.print_warn = cli.print_warn
eva.features.print_debug = cli.print_debug
eva.features.cli = cli

cli.default_prompt = '# '
cli.arg_sections += [
    'backup', 'server', 'edit', 'masterkey', 'system', 'iote', 'mirror',
    'feature', 'registry'
]
cli.set_api_functions(_api_functions)
cli.add_user_defined_functions()
cli.nodename = nodename
# cli.set_pd_cols(_pd_cols)
# cli.set_pd_idx(_pd_idx)
# cli.set_fancy_indentsp(_fancy_indentsp)
banner = """     _______    _____       _______________
    / ____/ |  / /   |     /  _/ ____/ ___/
   / __/  | | / / /| |     / // /    \__ \\
  / /___  | |/ / ___ |   _/ // /___ ___/ /
 /_____/  |___/_/  |_|  /___/\____//____/

  www.eva-ics.com (c) 2021 Altertech
"""
if '-I' in sys.argv or '--interactive' in sys.argv:
    print(cli.colored(banner, color='blue'))
    cli.execute_function(['version'])
    print()
code = cli.run()
sys.exit(code)
