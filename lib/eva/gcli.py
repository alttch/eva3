import os
import sys
import getopt
import importlib

import termcolor
import readline
import argparse
import json
import shlex
from pygments import highlight, lexers, formatters


def safe_colored(text, color=None, on_color=None, attrs=None, rlsafe=False):
    if os.getenv('ANSI_COLORS_DISABLED') is None:
        fmt_str = '\033[%dm'
        if rlsafe:
            fmt_str = '\001' + fmt_str + '\002'
        fmt_str += '%s'
        if color is not None:
            text = fmt_str % (termcolor.COLORS[color], text)

        if on_color is not None:
            text = fmt_str % (termcolor.HIGHLIGHTS[on_color], text)

        if attrs is not None:
            for attr in attrs:
                text = fmt_str % (termcolor.ATTRIBUTES[attr], text)

        if rlsafe:
            text += '\001' + termcolor.RESET + '\002'
        else:
            text += termcolor.RESET
    return text


class GCLI(object):

    def __init__(self, name, prog=None):
        self.debug = False
        self.name = name
        self.suppress_colors = False
        self.always_suppress_colors = False
        self.default_prompt = '> '
        self.prompt = None
        self.always_json = []
        self.local_func_result_ok = (0, {'ok': True})
        self.local_func_result_failed = (10, {'ok': False})
        self.local_func_result_empty = (0, '')
        self.always_print = []
        self.common_api_functions = {}
        self.common_pd_cols = {}
        self.common_pd_idx = {}
        self.arg_sections = []
        self.say_bye = True
        self.readline_processing = True
        self.history_length = 300
        self.history_file = os.path.expanduser('~') + '/.eva_history'
        self.pd_cols = self.common_pd_cols
        self.api_functions = {}
        self.fancy_indentsp = {}
        self.common_fancy_indentsp = {}
        self.batch_file = None
        self.batch_stop_on_err = True
        self.prog_name = prog
        self.interactive = False
        self.pd = None
        self.argcomplete = None
        self.parse_primary_args()

    def colored(self, text, color=None, on_color=None, attrs=None,
                rlsafe=False):
        if not self.can_colorize():
            return str(text)
        return safe_colored(
            text, color=color, on_color=on_color, attrs=attrs, rlsafe=rlsafe)

    def start_interactive(self):
        self.reset_argcomplete()
        if self.readline_processing:
            readline.set_history_length(self.history_length)
            try:
                if self.history_file:
                    readline.read_history_file(self.history_file)
            except:
                pass

    def finish_interactive(self):
        if self.say_bye: print('Bye')
        if self.readline_processing:
            try:
                if self.history_file:
                    readline.write_history_file(self.history_file)
            except:
                pass

    class ComplGlob(object):

        def __init__(self, mask=None):
            self.mask = mask if mask else '*'

        def __call__(self, prefix, **kwargs):
            result = []
            for m in self.mask:
                result += glob.glob(prefix + m)
            return result

    def setup_parser(self):
        if not self.interactive and not self.batch_file:
            self.ap = argparse.ArgumentParser(
                description=self.name, prog=self.prog_name)
        else:
            self.ap = argparse.ArgumentParser(usage=argparse.SUPPRESS, prog='')
        self.add_primary_options()
        self.add_primary_subparser()
        self.add_functions()
        self.load_argcomplete()

    def load_argcomplete(self):
        try:
            self.argcomplete = importlib.import_module('argcomplete')
        except:
            pass

    def reset_argcomplete(self):
        if self.argcomplete:
            completer = self.argcomplete.CompletionFinder(
                self.ap,
                default_completer=self.argcomplete.completers.SuppressCompleter(
                ))
            readline.set_completer_delims("")
            readline.set_completer(completer.rl_complete)
            readline.parse_and_bind("tab: complete")

    def print_json(self, obj):
        j = self.format_json(obj)
        if self.can_colorize():
            j = highlight(j, lexers.JsonLexer(), formatters.TerminalFormatter())
        print(j)

    def format_json(self, obj, minimal=False):
        return json.dumps(obj, indent=4, sort_keys=True) \
                    if not minimal else \
                    json.dumps(obj)

    def print_err(self, *args):
        for s in args:
            print(self.colored(s, color='red', attrs=[]))

    def print_warn(self, s, w=True):
        print(
            self.colored(
                ('WARNING: ' if w else '') + s, color='yellow', attrs=['bold']))

    def print_debug(self, s):
        print(self.colored(s, color='grey', attrs=['bold']))

    def can_colorize(self):
        return not self.suppress_colors and \
                not self.always_suppress_colors and \
                sys.stdout.isatty()

    def get_prompt(self):
        return self.prompt if self.prompt else self.default_prompt

    def print_interactive_help(self):
        print('type command to execute. Append |N' + \
                    ' to repeat every |N sec (|cN to clear screen)')
        print()
        print('Special commands:')
        print('q: quit')
        print('j: toggle json mode')
        print('r: toggle raw mode (no colors)')
        print()

    def add_primary_options(self):
        self.ap.add_argument(
            '-J',
            '--json',
            help='Print result as JSON',
            action='store_true',
            dest='_json',
            default=False)
        self.ap.add_argument(
            '-R',
            '--raw-output',
            help='Print raw results (no colors) and suppress prompt updates',
            action='store_true',
            dest='_raw',
            default=False)
        if not self.interactive:
            self.ap.add_argument(
                '-I',
                '--interactive',
                help='Enter interactive (command prompt) mode',
                action='store_true',
                dest='__interactive',
                default=False)

    def parse_primary_args(self):
        try:
            o, a = getopt.getopt(sys.argv[1:], 'JIR', [
                'exec-batch=', 'pass-batch-err', 'interactive', 'debug',
                'raw-output', 'json'
            ])
            for i, v in o:
                if i == '--exec-batch':
                    self.batch_file = v
                    self.prompt = '# '
                elif i == '--pass-batch-err':
                    self.batch_stop_on_err = False
                elif i == '--interactive' or i == '-I':
                    self.interactive = True
                elif i == '-D' or i == '--debug':
                    self.debug = True
                elif i == '-R' or i == '--raw-output':
                    self.always_suppress_colors = True
        except:
            pass

    def add_functions():
        pass

    def add_primary_subparser(self):
        self.sp = self.ap.add_subparsers(
            dest='_type', metavar='command', help='command or type')

    def prepare_result_data(self, data, func, itype):
        return data

    def prepare_result_dict(self, data, func, itype):
        return data

    def fancy_print_result(self, result, func, itype, indent=0, print_ok=True):
        if result and isinstance(result, dict):
            self.fancy_print_dict(
                result, func, itype, indent=indent, print_ok=print_ok)
        elif result and isinstance(result, list):
            self.fancy_print_list(result, func, itype)
        elif result:
            self.fancy_print_other(result, func, itype)

    def fancy_print_other(self, result, func, itype):
        print(result)

    def fancy_print_dict(result, func, itype, indent=0, print_ok=True):
        _result = self.prepare_result_dict(result, func, itype)
        rprinted = False
        out = None
        err = None
        indentsp = self.fancy_indentsp.get(api_func, itype)
        if not indentsp: indentsp = 10
        for v in sorted(_result.keys()):
            if isinstance(_result[v], dict):
                if indent:
                    print(
                        ' ' * (indent * indentsp),
                        end=self.colored('>' * indent) + ' ')
                print(
                    ((self.colored('{:>%u} ', color='blue', attrs=['bold']) +
                      self.colored(':') + self.colored('  {}', color='yellow'))
                     % max(map(len, _result))).format(v, ''))
                self.fancy_print_result(_result[v], func, itype, indent + 1)
            else:
                if indent:
                    print(
                        ' ' * (indent * indentsp),
                        end=self.colored('>' * indent) + ' ')
                if isinstance(_result[v], list):
                    _r = []
                    for vv in _result[v]:
                        _r.append(str(vv))
                    _v = ', '.join(_r)
                else:
                    _v = _result[v]
                print(((self.colored('{:>%u} ', color='blue', attrs=['bold']) +
                        self.colored(':') + self.colored(' {}', color='yellow'))
                       % max(map(len, _result))).format(v, _v))
            rprinted = True
        if not rprinted and not indent and print_ok:
            print('OK')

    def fancy_print_list(self, result, func, itype):
        self.import_pandas()
        df = self.pd.DataFrame(
            data=self.prepare_result_data(result, func, itype))
        if func in self.pd_cols:
            cols = self.pd_cols[func]
        else:
            cols = list(df)
        df = df.ix[:, cols]
        try:
            idxcol = self.pd_idx.get(func)
            if idxcol is None: idxcol = 'id'
            if idxcol in list(df):
                df.set_index(idxcol, inplace=True)
            else:
                idxcol = list(df)[0]
                df.set_index(list(df)[0], inplace=True)
            out = df.fillna(' ').to_string().split('\n')
            print(
                self.colored(
                    idxcol + out[0][len(idxcol):], color='blue', attrs=[]))
            print(self.colored('-' * len(out[0]), color='grey'))
            # dirty hack for old pandas ver
            x = 2 if out[1].startswith(idxcol + ' ') else 1
            for o in out[x:]:
                s = re.sub('^NaN', '   ', o)
                print(s)
        except:
            raise

    def import_pandas(self):
        if not self.pd:
            self.pd = importlib.import_module('pandas')
            self.pd.set_option('display.expand_frame_repr', False)
            self.pd.options.display.max_colwidth = 100

    def call(self, args=[]):
        _args = args if isinstance(args, list) else shlex.split(args)
        return self.execute_function(args=_args, return_result=True)

    def run(self):
        # primary run or lopp
        # TODO
        pass

    def execute_function(self, args=None, return_result=False):
        # TODO
        pass

    def prepare_run(self, func, params, a):
        """
        final step: execute tasks before function execution (e.g. read local
        file), modify execution params if necessary (e.g. put file contents
        into param value)

        in case of any error or invalid params - return non-zero code, this
        will prevent function execution and specified code will be returned
        back to shell
        """
        return 0

    def print_failed_result(self, result):
        self.print_err('FAILED')
        if 'error' in result:
            self.print_err(result['error'])

    def result_failed(self, message):
        code, result = self.local_func_result_failed
        result['error'] = message
        return code, result

    def result_ok(self, data=None):
        if data:
            return 0, data
        else:
            return self.local_func_result_failed

    def result_empty():
        return self.local_func_result_empty

    def process_result(self, result, code, func, itype, a):
        if code:
            self.print_failed_result(result)
        self.fancy_print_result(result, func, itype, print_ok=code == 0)
        return code

    def get_api_func(self, itype, func):
        if func is None:
            f = self.api_functions.get(itype)
            return f if f else itype
        else:
            f = self.api_functions.get(itype + ':' + func)
            return f if f else itype + '_' + func
