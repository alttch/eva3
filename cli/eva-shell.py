__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.2.4"

import sys
import os
import time
import configparser
import platform
import argparse

nodename = platform.node()

dir_eva = os.path.realpath(os.path.dirname(os.path.realpath(__file__)) + '/..')
dir_backup = os.path.dirname(os.path.realpath(__file__)) + '/../backup'
dir_lib = os.path.dirname(os.path.realpath(__file__)) + '/../lib'
dir_etc = os.path.dirname(os.path.realpath(__file__)) + '/../etc'
dir_sbin = os.path.dirname(os.path.realpath(__file__)) + '/../sbin'
dir_cli = os.path.realpath(
    os.path.dirname(os.path.realpath(__file__)) + '/../cli')
dir_runtime = os.path.realpath(
    os.path.dirname(os.path.realpath(__file__)) + '/../runtime')
sys.path.append(dir_lib)

dir_cwd = os.getcwd()

os.chdir(dir_eva)
os.environ['EVA_DIR'] = dir_eva
if not 'PATH' in os.environ: os.environ['PATH'] = ''
os.environ['PATH'] = '{}/xc/shell:'.format(dir_eva) + os.environ['PATH']

exec_before_save = None
exec_after_save = None
cmds = []

update_repo = 'https://get.eva-ics.com'

import eva.client.cli

from eva.client.cli import GenericCLI
from eva.client.cli import ControllerCLI
from eva.client.cli import ComplGeneric


class ComplSubshellCmd(ComplGeneric):

    def __init__(self, cli, for_notifier=False):
        self.for_notifier = for_notifier
        super().__init__(cli)

    def __call__(self, prefix, **kwargs):
        shell = kwargs[
            'parsed_args']._type if not self.for_notifier else kwargs[
                'parsed_args'].p
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
                    cli.do_start_shell(
                        'notifymanager',
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
        if code: return result
        for v in data:
            result.append(v['name'])
        return result


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
        if api_func not in ['status_controller']:
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
        self.add_manager_edit_functions()
        self.add_management_shells()
        self.add_manager_power_functions()
        self.add_user_defined_functions()

    def process_configuration(self):
        self.products_configured = []
        for f in ['uc', 'lm', 'sfa']:
            if os.path.isfile('{}/{}.ini'.format(
                    dir_etc, f)) and os.path.isfile('{}/{}_apikeys.ini'.format(
                        dir_etc, f)):
                self.products_configured.append(f)

    def add_manager_backup_functions(self):
        ap_backup = self.sp.add_parser('backup', help='Backup management')

        sp_backup = ap_backup.add_subparsers(
            dest='_func', metavar='func', help='Backup commands')

        sp_backup_save = sp_backup.add_parser(
            'save', help='Backup system state')
        sp_backup_save.add_argument(
            'f', help='Backup name', metavar='NAME', nargs='?')

        sp_backup_restore = sp_backup.add_parser(
            'restore', help='Restore system state')
        sp_backup_restore.add_argument(
            'f', help='Backup name',
            metavar='NAME').completer = ComplBackupList(self)
        sp_backup_restore.add_argument(
            '-i',
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
        sp_backup_restore.add_argument(
            '--xc',
            dest='xc',
            help='Restore xc (cmd, drivers and macro extensions)',
            action='store_true')
        sp_backup_restore.add_argument(
            '--ui', dest='ui', help='Restore ui folder', action='store_true')
        sp_backup_restore.add_argument(
            '-a',
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

        sp_edit = ap_edit.add_subparsers(
            dest='_func', metavar='func', help='Edit commands')

        sp_edit_crontab = sp_edit.add_parser('crontab', help='Edit crontab')

        ap_masterkey = self.sp.add_parser(
            'masterkey', help='Masterkey management')

        sp_masterkey = ap_masterkey.add_subparsers(
            dest='_func', metavar='func', help='Masterkey commands')

        sp_masterkey_set = sp_masterkey.add_parser(
            'set', help='Set masterkey for all controllers configured')
        sp_masterkey_set.add_argument(
            'a', metavar='KEY', help='New masterkey', nargs='?')
        sp_masterkey_set.add_argument(
            '-a',
            '--access',
            choices=['local-only', 'remote'],
            metavar='ACCESS_TYPE',
            help='Access type')

    def add_manager_control_functions(self):
        eva.client.cli.shells_available = []
        if not self.products_configured:
            return
        eva.client.cli.shells_available = self.products_configured
        ap_controller = self.sp.add_parser(
            'server', help='Controllers server management functions')
        sp_controller = ap_controller.add_subparsers(
            dest='_func', metavar='func', help='Management commands')

        ap_start = sp_controller.add_parser(
            'start', help='Start controller server(s)')
        ap_start.add_argument(
            'p',
            metavar='CONTROLLER',
            help='Controller type (' + ', '.join(self.products_configured) +
            ')',
            choices=self.products_configured,
            nargs='?')
        ap_stop = sp_controller.add_parser(
            'stop', help='Stop controller server(s)')
        ap_stop.add_argument(
            'p',
            metavar='CONTROLLER',
            help='Controller type (' + ', '.join(self.products_configured) +
            ')',
            choices=self.products_configured,
            nargs='?')
        ap_restart = sp_controller.add_parser(
            'restart', help='Restart controller server(s)')
        ap_restart.add_argument(
            'p',
            metavar='CONTROLLER',
            help='Controller type (' + ', '.join(self.products_configured) +
            ')',
            choices=self.products_configured,
            nargs='?')
        ap_status = sp_controller.add_parser(
            'status', help='Status of the controller server(s)')
        ap_status.add_argument(
            'p',
            metavar='CONTROLLER',
            help='Controller type (' + ', '.join(self.products_configured) +
            ')',
            choices=self.products_configured,
            nargs='?')

        ap_enable = sp_controller.add_parser(
            'enable', help='Enable controller server')
        ap_enable.add_argument(
            'p',
            metavar='CONTROLLER',
            help='Controller type (' + ', '.join(self.products_configured) +
            ')',
            choices=self.products_configured)

        ap_disable = sp_controller.add_parser(
            'disable', help='Disable controller server')
        ap_disable.add_argument(
            'p',
            metavar='CONTROLLER',
            help='Controller type (' + ', '.join(self.products_configured) +
            ')',
            choices=self.products_configured)

    def add_manager_common_functions(self):
        ap_version = self.sp.add_parser(
            'version', help='Display version and build')
        ap_update = self.sp.add_parser(
            'update', help='Check and update to new version if exists')
        ap_update.add_argument(
            '--YES',
            dest='y',
            help='Update without any prompts',
            action='store_true')
        ap_update.add_argument(
            '-u',
            '--repository-url',
            dest='u',
            metavar='URL',
            help='update repository url')
        ap_update.add_argument(
            '-i',
            '--info-only',
            dest='i',
            help='Check for a new version without upgrading',
            action='store_true')

    def add_manager_power_functions(self):
        ap_system = self.sp.add_parser('system', help='System functions')
        sp_system = ap_system.add_subparsers(
            dest='_func', metavar='func', help='System commands')

        ap_reboot = sp_system.add_parser('reboot', help='Reboot the system')
        ap_reboot.add_argument(
            '--YES',
            dest='y',
            help='Reboot without any prompts',
            action='store_true')

        ap_poweroff = sp_system.add_parser(
            'poweroff', help='Power off the system')
        ap_poweroff.add_argument(
            '--YES',
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
        ap_save.add_argument(
            'p',
            metavar='CONTROLLER',
            choices=self.products_configured,
            nargs='?',
            help='Controller type (' + ', '.join(self.products_configured) +
            ')')

        ap_ns = self.sp.add_parser('ns', help='Notifier management')
        ap_ns.add_argument(
            'p',
            metavar='CONTROLLER',
            choices=self.products_configured,
            help='Controller type (' + ', '.join(self.products_configured) +
            ')')
        ap_ns.add_argument(
            'subcommand',
            nargs=argparse.REMAINDER).completer = ComplSubshellCmd(
                self, for_notifier=True)

    def exec_control_script(self, command, product, collect_output=False):
        cmd = '{}/eva-control {} {}'.format(dir_sbin, command, product
                                            if product else '')
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
        code = self.start_shell('notifymanager', '.py', 'product=\'{}\''.format(
            params.get('p')))
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
            result = self.do_start_shell(
                sst, x, xp, force_interactive=force_interactive)
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
            c = open('{}/{}{}'.format(dir_cli, p, x)).read()
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
            if self.interactive: self.save_readline()
            try:
                eva.client.cli.subshell_exit_code = 0
                exec(c)
                self.subshell_extra_args = None
            except SystemExit:
                pass
            return True
        except:
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

    def start_controller(self, params):
        c = params['p']
        if c is not None and c not in self.products_configured:
            return self.local_func_result_failed
        self.exec_control_script('start', c)
        return self.local_func_result_ok

    def stop_controller(self, params):
        c = params['p']
        if c is not None and c not in self.products_configured:
            return self.local_func_result_failed
        self.exec_control_script('stop', c)
        return self.local_func_result_ok

    def restart_controller(self, params):
        c = params['p']
        if c is not None and c not in self.products_configured:
            return self.local_func_result_failed
        self.exec_control_script('restart', c)
        return self.local_func_result_ok

    def status_controller(self, params):
        c = params['p']
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
        if params['p'] in self.products_configured:
            f = open(dir_etc + '/eva_servers')
            lines = f.readlines()
            f.close()
            new_lines = []
            new_lines.append("{}_ENABLED=yes\n".format(params['p'].upper()))
            for line in lines:
                if "{}_SUPERVISORD".format(params['p'].upper()) in line:
                    self.print_err('Server is controlled by supervisord')
                    return self.local_func_result_failed
                if "{}_ENABLED".format(params['p'].upper()) not in line:
                    new_lines.append(line)
            with open(dir_etc + '/eva_servers', "w") as f:
                f.writelines(new_lines)
            return self.local_func_result_ok
        return False

    def disable_controller(self, params):
        if params['p'] in self.products_configured:
            f = open(dir_etc + '/eva_servers')
            lines = f.readlines()
            f.close()
            new_lines = []
            new_lines.append("{}_ENABLED=no\n".format(params['p'].upper()))
            for line in lines:
                if "{}_SUPERVISORD".format(params['p'].upper()) in line:
                    self.print_err('Server is controlled by supervisord')
                    return self.local_func_result_failed
                if "{}_ENABLED".format(params['p'].upper()) not in line:
                    new_lines.append(line)
            with open(dir_etc + '/eva_servers', "w") as f:
                f.writelines(new_lines)
            return self.local_func_result_ok
        return False

    def set_controller_user(self, params):
        if params['p'] in self.products_configured:
            f = open(dir_etc + '/eva_servers')
            lines = f.readlines()
            f.close()
            new_lines = []
            new_lines.append("{}_USER={}\n".format(params['p'].upper(),
                                                   params['v']))
            for line in lines:
                if "{}_USER".format(params['p'].upper()) not in line:
                    new_lines.append(line)
            with open(dir_etc + '/eva_servers', "w") as f:
                f.writelines(new_lines)
            return self.local_func_result_ok
        return False

    def get_controller_user(self, params):
        if params['p'] in self.products_configured:
            f = open(dir_etc + '/eva_servers')
            lines = f.readlines()
            f.close()
            u_dict = dict([(i.split('=')[0], i.split('=')[-1]) for i in lines])
            return 0, u_dict.get("{}_USER".format(params['p'].upper())).rstrip()
        return False

    def print_version(self, params):
        with os.popen('{}/eva-tinyapi -V; {}/eva-tinyapi -B'.format(
                dir_sbin, dir_sbin)) as p:
            data = p.readlines()
        if len(data) != 2:
            return self.local_func_result_failed
        result = {'version': data[0].strip(), 'build': data[1].strip()}
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
        if fname is None: fname = '{}'.format(time.strftime('%Y%m%d%H%M%S'))
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
               '--exclude=*.md', '--exclude=*.rst', 'runtime', 'xc/cmd',
               'xc/drivers/phi', 'xc/extensions', 'etc', 'ui')
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
        if not self.before_save(): return self.local_func_result_failed
        try:
            os.unlink(dir_backup + '/' + params.get('f') + '.tgz')
        except:
            self.after_save()
            return self.local_func_result_failed
        if not self.after_save(): return self.local_func_result_failed
        return self.local_func_result_ok

    def backup_restore(self, params):
        f = dir_backup + '/' + params.get('f') + '.tgz'
        if not os.path.isfile(f):
            self.print_err('no such backup')
            return self.local_func_result_failed
        if not self.before_save(): return self.local_func_result_failed
        if params.get('file'):
            for i in params.get('file'):
                try:
                    if not self.backup_restore_file(fname=f, frestore=i):
                        raise Exception('restore failed')
                except:
                    self.after_save()
                    return self.local_func_result_failed
            if not self.after_save(): return self.local_func_result_failed
            return self.local_func_result_ok
        if params.get('full'):
            self.clear_runtime(full=True)
            self.clear_xc()
            self.clear_ui()
            try:
                if not self.backup_restore_runtime(fname=f, json_only=False):
                    raise Exception('restore failed')
                if not self.backup_restore_dir(fname=f, dirname='etc'):
                    raise Exception('restore failed')
                if not self.backup_restore_dir(fname=f, dirname='xc'):
                    raise Exception('restore failed')
                if not self.backup_restore_dir(fname=f, dirname='ui'):
                    raise Exception('restore failed')
            except:
                self.after_save()
                return self.local_func_result_failed
            if not self.after_save(): return self.local_func_result_failed
            return self.local_func_result_ok
        try:
            if params.get('xc'):
                self.clear_xc()
                if not self.backup_restore_dir(fname=f, dirname='xc'):
                    raise Exception('restore failed')
            if params.get('ui'):
                self.clear_ui()
                if not self.backup_restore_dir(fname=f, dirname='ui'):
                    raise Exception('restore failed')
            else:
                self.clear_runtime(full=params.get('r'))
                if not self.backup_restore_runtime(
                        fname=f, json_only=not params.get('r')):
                    raise Exception('restore failed')
                if not self.backup_restore_dir(fname=f, dirname='etc'):
                    raise Exception('restore failed')
        except:
            self.after_save()
            return self.local_func_result_failed
        if not self.after_save(): return self.local_func_result_failed
        return self.local_func_result_ok

    def clear_runtime(self, full=False):
        print('Removing runtime' + (' (completely)...' if full else '...'))
        cmd = 'rm -rf runtime/*' if full else \
                'find runtime -type f -name "*.json" -exec rm -f {} \\;'
        os.system(cmd)
        return True

    def clear_xc(self):
        print('Removing xc')
        cmd = 'rm -rf xc/drivers/phi/* xc/extensions/* xc/cmd/*'
        os.system(cmd)
        return True

    def clear_ui(self):
        print('Removing ui')
        cmd = 'rm -rf ui/*'
        os.system(cmd)
        return True

    def backup_restore_runtime(self, fname, json_only=True):
        print(
            self.colored('Restoring runtime' + \
                         (' (completely)...' if \
                         not json_only else ' (json)...'),
            color='green',
            attrs=[]))
        cmd = ('tar', 'xpf', fname)
        if json_only: cmd += ('--wildcards', 'runtime/*.json')
        cmd += ('runtime',)
        return False if os.system(' '.join(cmd)) else True

    def backup_restore_dir(self, fname, dirname):
        print(
            self.colored(
                'Restoring {}...'.format(dirname), color='green', attrs=[]))
        cmd = ('tar', 'xpf', fname, dirname)
        return False if os.system(' '.join(cmd)) else True

    def backup_restore_file(self, fname, frestore):
        print(
            self.colored(
                'Restoring {}...'.format(frestore), color='green', attrs=[]))
        cmd = ('tar', 'xpf', fname, frestore)
        return False if os.system(' '.join(cmd)) else True

    def update(self, params):
        import requests
        import jsonpickle
        _update_repo = params.get('u')
        if not _update_repo:
            _update_repo = update_repo
        os.environ['EVA_REPOSITORY_URL'] = _update_repo
        try:
            with os.popen('{}/eva-tinyapi -B'.format(dir_sbin)) as p:
                data = p.read()
                build = int(data.strip())
        except:
            return self.local_func_result_failed
        try:
            with os.popen('{}/eva-tinyapi -V'.format(dir_sbin)) as p:
                data = p.read()
                version = data.strip()
                int(version.split('.')[0])
        except:
            return self.local_func_result_failed
        try:
            r = requests.get(_update_repo + '/update_info.json', timeout=5)
            if r.status_code != 200:
                raise Exception('HTTP ERROR')
            result = jsonpickle.decode(r.text)
            new_build = int(result['build'])
            new_version = result['version']
        except:
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
            ' : ' + self.colored(build, color='yellow'))
        print(
            self.colored(
                'Latest available build', color='blue', attrs=['bold']) +
            ' : ' + self.colored(
                '{} (v{})'.format(new_build, new_version), color='yellow'))
        if build == new_build:
            return self.local_func_result_empty
        if build > new_build:
            print('Your build is newer than update server has')
            return self.local_func_result_failed
        if not params.get('y'):
            if version != new_version:
                try:
                    r = requests.get('{}/{}/stable/UPDATE.rst'.format(
                        _update_repo, new_version))
                    if not r.ok:
                        raise Exception('server response code {}'.format(
                            r.status_code))
                except Exception as e:
                    print('Unable to download update manifest: {}'.format(e))
                    return self.local_func_result_failed
                print()
                print(r.text)
            try:
                u = input('Type ' +
                          self.colored('YES', color='red', attrs=['bold']) +
                          ' (uppercase) to update, or press ' +
                          self.colored('ENTER', color='white') + ' to abort > ')
            except:
                print()
                u = ''
            if u != 'YES':
                return self.local_func_result_empty
        url = '{}/{}/stable/update.sh'.format(_update_repo, new_version)
        cmd = ('curl -s ' + url + ' | bash /dev/stdin')
        if os.system(dir_sbin + '/eva-control stop') or \
            not self.before_save() or \
            os.system(cmd) or \
            not self.after_save():
            return self.local_func_result_failed
        print('Update completed', end='')
        if self.interactive:
            print('. Now exit EVA shell and log in back')
        else:
            print()
        return self.local_func_result_ok

    def power_reboot(self, params):
        if not params.get('y'):
            try:
                a = input('Reboot this system? (y/N) ')
            except:
                print()
                a = ''
            if a.lower() != 'y': return self.local_func_result_empty
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
            if a.lower() != 'y': return self.local_func_result_empty
        print(self.colored('Powering off...', color='red', attrs=['bold']))
        return self.local_func_result_failed if \
                os.system('poweroff') else self.local_func_result_ok

    def add_user_defined_functions(self):
        if not cmds: return
        for c in cmds:
            sp = self.sp.add_parser(c['cmd'], help=c['comment'])

    def exec_cmd(self, a):
        return self.local_func_result_failed if \
                os.system(a) else self.local_func_result_ok

    def edit_crontab(self, params):
        if not self.before_save(): return self.local_func_result_failed
        c = os.system('crontab -e')
        if not self.after_save() or c: return self.local_func_result_failed
        return self.local_func_result_ok

    def save(self, params):
        p = params['p']
        if p:
            if p not in self.products_configured:
                return self.local_func_result_failed
            code, result = self.call('{} save'.format(p))
            return self.local_func_result_empty if not code else (code, '')
        else:
            ok = True
            for p in self.products_configured:
                print(
                    '{}: '.format(
                        self.colored(p, color='blue', attrs=['bold'])),
                    end='')
                code, result = self.call('{} save'.format(p))
                if code:
                    print(self.colored('FAILED', color='red'))
                    ok = False
            return self.local_func_result_empty if ok else (10, '')

    def set_masterkey(self, params):

        def set_masterkey_for(p, a, access):
            try:
                in_section = False
                key_found = False
                nf = []
                for st in open('{}/{}_apikeys.ini'.format(dir_etc,
                                                          p)).readlines():
                    st = st.strip()
                    s = st.split(';')[0].strip()
                    if s == '[masterkey]':
                        in_section = True
                    elif s.startswith('['):
                        in_section = False
                    elif s.find('=') != -1:
                        i = s.split('=')[0].strip()
                        if i == 'key' and in_section and a:
                            key_found = True
                            nf.append('key = {}'.format(a))
                            continue
                        if i == 'hosts_allow' and in_section and access:
                            nf.append('hosts_allow = {}'.format(
                                '127.0.0.1'
                                if access == 'local-only' else '0.0.0.0/0'))
                            continue
                    nf.append(st)
                if a and not key_found:
                    raise Exception(
                        'masterkey not found in {}_apikeys.ini'.format(p))
                open('{}/{}_apikeys.ini'.format(dir_etc, p),
                     'w').write('\n'.join(nf) + '\n')
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
                print(
                    '{}: '.format(
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
    'update': cli.update,
    'system:reboot': cli.power_reboot,
    'system:poweroff': cli.power_poweroff,
    'save': cli.save,
    'ns': cli.manage_ns,
    'backup:save': cli.backup_save,
    'backup:list': cli.backup_list,
    'backup:unlink': cli.backup_unlink,
    'backup:restore': cli.backup_restore,
    'edit:crontab': cli.edit_crontab,
    'masterkey:set': cli.set_masterkey
}

cfg = configparser.ConfigParser(inline_comment_prefixes=';')
try:
    cfg.read(dir_etc + '/eva_shell.ini')
    try:
        nodename = cfg.get('shell', 'nodename')
    except:
        pass
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

cli.default_prompt = '# '
cli.arg_sections += ['backup', 'server', 'edit', 'masterkey', 'system']
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

  www.eva-ics.com (c) 2012-2019 Altertech
"""
if '-I' in sys.argv or '--interactive' in sys.argv:
    print(cli.colored(banner, color='blue'))
    cli.execute_function(['version'])
    print()
code = cli.run()
sys.exit(code)
