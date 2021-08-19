from __future__ import print_function

__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.1"

import os
import sys
import getopt
import importlib

import neotermcolor
import readline
import argparse
import rapidjson
import shlex
import threading
from pygments import highlight, lexers, formatters
from collections import OrderedDict


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
        self.pd_cols = {}
        self.arg_sections = []
        self.say_bye = True
        self.readline_processing = True
        self.history_length = 300
        self.history_file = os.path.expanduser('~') + '/.eva_history'
        self.api_functions = {}
        self.fancy_indentsp = {}
        self.common_fancy_indentsp = {}
        self.batch_file = None
        self.batch_stop_on_err = True
        self.prog_name = prog
        self.interactive = False
        self.argcomplete = None
        self.parse_primary_args()

    def colored(self,
                text,
                color=None,
                on_color=None,
                attrs=None,
                rlsafe=False):
        if not self.can_colorize():
            return str(text)
        return neotermcolor.colored(text,
                                    color=color,
                                    on_color=on_color,
                                    attrs=attrs,
                                    readline_safe=rlsafe)

    def start_interactive(self):
        self.reset_argcomplete()
        if self.readline_processing:
            readline.set_history_length(self.history_length)
            self.load_readline()

    def load_readline(self):
        try:
            if self.history_file:
                readline.read_history_file(self.history_file)
        except:
            pass

    def finish_interactive(self):
        self.save_readline()
        if self.say_bye:
            print('Bye')

    def save_readline(self):
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
            import glob
            for m in self.mask:
                for f in glob.glob(prefix + m):
                    yield f

    def setup_parser(self):
        if not self.interactive and not self.batch_file:
            self.ap = argparse.ArgumentParser(description=self.name,
                                              prog=self.prog_name)
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
            readline.set_completer_delims('')
            readline.set_completer(completer.rl_complete)
            readline.parse_and_bind('tab: complete')

    def print_json(self, obj):
        j = self.format_json(obj)
        if self.can_colorize():
            j = highlight(j, lexers.JsonLexer(), formatters.TerminalFormatter())
        print(j)

    def format_json(self, obj, minimal=False):
        return rapidjson.dumps(obj, indent=4, sort_keys=True) \
                    if not minimal else \
                    rapidjson.dumps(obj)

    @staticmethod
    def safe_print(val, extra=0):
        width, height = os.get_terminal_size(0)
        print(val[:width + extra])

    def plot_line_chart(self, data, rows, max_label_width):

        # https://github.com/kroitor/asciichart/tree/master/asciichartpy
        # Copyright © 2016 Igor Kroitor
        from math import ceil, floor, isnan

        def _isnum(n):
            return not isnan(n)

        def colored(char, color):
            if not color:
                return char
            else:
                return color + char + "\033[0m"

        def _plot(series, cfg=None):
            if len(series) == 0:
                return ''

            if not isinstance(series[0], list):
                if all(isnan(n) for n in series):
                    return ''
                else:
                    series = [series]

            cfg = cfg or {}

            colors = cfg.get('colors', [None])

            minimum = cfg.get(
                'min', min(filter(_isnum, [j for i in series for j in i])))
            maximum = cfg.get(
                'max', max(filter(_isnum, [j for i in series for j in i])))

            default_symbols = ['┼', '┤', '╶', '╴', '─', '╰', '╭', '╮', '╯', '│']
            symbols = cfg.get('symbols', default_symbols)

            if minimum > maximum:
                raise ValueError('The min value cannot exceed the max value.')

            interval = maximum - minimum
            offset = cfg.get('offset', 3)
            height = cfg.get('height', interval)
            ratio = height / interval if interval > 0 else 1

            min2 = int(floor(minimum * ratio))
            max2 = int(ceil(maximum * ratio))

            def clamp(n):
                return min(max(n, minimum), maximum)

            def scaled(y):
                return int(round(clamp(y) * ratio) - min2)

            rows = max2 - min2

            width = 0
            for i in range(0, len(series)):
                width = max(width, len(series[i]))
            width += offset

            placeholder = cfg.get(
                'format', '{:' +
                str(8 if max_label_width < 8 else max_label_width) + '.2f} ')

            result = [[' '] * width for i in range(rows + 1)]

            # axis and labels
            for y in range(min2, max2 + 1):
                label = placeholder.format(maximum - ((y - min2) * interval /
                                                      (rows if rows else 1)))
                result[y - min2][max(offset - len(label), 0)] = label
                result[y - min2][offset -
                                 1] = symbols[0] if y == 0 else symbols[
                                     1]  # zero tick mark

            # first value is a tick mark across the y-axis
            d0 = series[0][0]
            if _isnum(d0):
                result[rows - scaled(d0)][offset - 1] = symbols[0]

            for i in range(0, len(series)):

                color = colors[i % len(colors)]

                # plot the line
                for x in range(0, len(series[i]) - 1):
                    d0 = series[i][x + 0]
                    d1 = series[i][x + 1]

                    if isnan(d0) and isnan(d1):
                        continue

                    if isnan(d0) and _isnum(d1):
                        result[rows - scaled(d1)][x + offset] = colored(
                            symbols[2], color)
                        continue

                    if _isnum(d0) and isnan(d1):
                        result[rows - scaled(d0)][x + offset] = colored(
                            symbols[3], color)
                        continue

                    y0 = scaled(d0)
                    y1 = scaled(d1)
                    if y0 == y1:
                        result[rows - y0][x + offset] = colored(
                            symbols[4], color)
                        continue

                    result[rows - y1][x + offset] = colored(
                        symbols[5], color) if y0 > y1 else colored(
                            symbols[6], color)
                    result[rows - y0][x + offset] = colored(
                        symbols[7], color) if y0 > y1 else colored(
                            symbols[8], color)

                    start = min(y0, y1) + 1
                    end = max(y0, y1)
                    for y in range(start, end):
                        result[rows - y][x + offset] = colored(
                            symbols[9], color)

            return '\n'.join([''.join(row).rstrip() for row in result])

        config = {'height': rows}
        if self.can_colorize():
            config['colors'] = ['\033[32m']
        print(_plot(data, cfg=config))

    def plot_bar_chart(self, data):
        BAR = '❚'
        TICK = '▏'

        width, height = os.get_terminal_size(0)
        spaces = 8
        extra = 20 if self.can_colorize() else 0
        max_label_length = 0
        max_value_label_length = 0
        min_value = None
        max_value = None
        for label, value in data:
            if value is not None:
                if len(label) > max_label_length:
                    max_label_length = len(label)
                if len(str(value)) > max_value_label_length:
                    max_value_label_length = len(str(value))
                if min_value is None or value < min_value:
                    min_value = value
                if max_value is None or value > max_value:
                    max_value = value
        if max_value is None:
            max_value = 0
        if min_value is None:
            min_value = 0
        plot_width = width - spaces - max_label_length - max_value_label_length
        if max_value > 0:
            max_bar_len = max_value - min_value
        else:
            max_bar_len = abs(min_value - max_value)
        zoom = plot_width / max_bar_len if max_bar_len else 1
        for label, value in data:
            if value is None:
                line = self.colored('NaN', color='magenta')
            else:
                if min_value >= 0:
                    line = BAR * int((value - min_value) * zoom)
                    if not line:
                        line = f'{TICK if value else " "}{value}'
                    else:
                        line += f' {value}'
                    line = self.colored(line,
                                        color='green' if value else 'grey')
                elif max_value < 0:
                    line = BAR * int((abs(max_value - value)) * zoom)
                    if not line:
                        line = f'{value} {(TICK) if value else ""}'
                        line = line.rjust(plot_width + spaces + 1)
                    else:
                        line = f'{value} ' + line
                        line = line.rjust(plot_width + spaces)
                    line = self.colored(line,
                                        color='yellow' if value else 'grey')
                else:
                    if value >= 0:
                        line = BAR * int(value * zoom) + f' {value}'
                        line = self.colored(line,
                                            color='green' if value else 'grey')
                        line = ' ' * (1 + int(
                            abs(min_value) * zoom + len(str(min_value)))) + line
                    else:
                        bar = BAR * int(abs(value) * zoom)
                        if not bar:
                            bar = TICK
                        line = f'{value} ' + bar
                        line = line.rjust(
                            1 +
                            int(abs(min_value) * zoom + len(str(min_value))))
                        line = self.colored(line, color='yellow')
            self.safe_print(
                f'{self.colored(label.rjust(max_label_length), color="cyan")}'
                f' {line}', extra)

    def print_err(self, *args, **kwargs):
        for s in args:
            print(self.colored(s, color='red', attrs=[]),
                  file=sys.stderr,
                  **kwargs)

    def print_warn(self, s, w=True, **kwargs):
        print(
            self.colored(('WARNING: ' if w else '') + s,
                         color='yellow',
                         attrs=['bold']), **kwargs)

    def print_debug(self, s, **kwargs):
        print(self.colored(s, color='grey', attrs=['bold']), **kwargs)

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
        self.ap.add_argument('-J',
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
        self.ap.add_argument('-O',
                             '--output-file',
                             help='Store output to local file',
                             dest='_output_file',
                             metavar='FILE')
        if not self.interactive:
            self.ap.add_argument('-I',
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
        self.sp = self.ap.add_subparsers(dest='_type',
                                         metavar='command',
                                         help='command or type')

    def prepare_result_data(self, data, func, itype):
        return data

    def prepare_result_dict(self, data, func, itype):
        return data

    def fancy_print_result(self, result, func, itype, indent=0, print_ok=True):
        if result and isinstance(result, dict):
            self.fancy_print_dict(result,
                                  func,
                                  itype,
                                  indent=indent,
                                  print_ok=print_ok)
        elif result and isinstance(result, list):
            self.fancy_print_list(result, func, itype)
        elif result:
            self.fancy_print_other(result, func, itype)

    def fancy_print_other(self, result, func, itype):
        print(result)

    def fancy_print_dict(self, result, func, itype, indent=0, print_ok=True):
        _result = self.prepare_result_dict(result, func, itype)
        rprinted = False
        out = None
        err = None
        indentsp = self.fancy_indentsp.get(f'{itype}_{func}')
        if not indentsp:
            indentsp = 10
        for v in sorted(_result.keys()):
            if isinstance(_result[v], dict):
                if indent:
                    print(' ' * (indent * indentsp),
                          end=self.colored('>' * indent) + ' ')
                print((
                    (self.colored('{:>%u} ', color='blue', attrs=['bold']) +
                     self.colored(':') + self.colored('  {}', color='yellow')) %
                    max(map(len, _result))).format(v, ''))
                self.fancy_print_result(_result[v], func, itype, indent + 1)
            else:
                if indent:
                    print(' ' * (indent * indentsp),
                          end=self.colored('>' * indent) + ' ')
                if isinstance(_result[v], list):
                    _r = []
                    for vv in _result[v]:
                        _r.append(str(vv))
                    _v = ', '.join(_r)
                else:
                    _v = _result[v]
                print(
                    ((self.colored('{:>%u} ', color='blue', attrs=['bold']) +
                      self.colored(':') + self.colored(' {}', color='yellow')) %
                     max(map(len, _result))).format(v, _v))
            rprinted = True
        if not rprinted and not indent and print_ok:
            print('OK')

    def list_to_str(self, l):
        return ', '.join(l) if isinstance(
            l, list) else (str(l) if l is not None else '')

    def fancy_print_list(self, result, func, itype):
        table = []
        for r in self.prepare_result_data(result, func, itype):
            t = OrderedDict()
            if func in self.pd_cols:
                for c in self.pd_cols[func]:
                    t[c] = self.list_to_str(r[c])
            else:
                for i, c in r.items():
                    t[i] = self.list_to_str(c)
            table.append(t)
        import rapidtables
        header, rows = rapidtables.format_table(table,
                                                rapidtables.FORMAT_GENERATOR)
        # header = header[:w]
        print(self.colored(header, color='blue', attrs=[]))
        print(self.colored('-' * len(header), color='grey', attrs=[]))
        for r in rows:
            print(r)

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

    def result_empty(self):
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
