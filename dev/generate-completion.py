#!/usr/bin/env python3

import os
import sys
import json

result = {}

def get_opts(prg):
    with os.popen(('{} -h|grep -v "^           "|grep -A999 -E "^  command|^  func"|grep -B999 ^optional|' +
            'tail -n+2|head -n-2').format(prg)) as p:
        return [s.split()[0].strip() for s in p.readlines()]

program = sys.argv[1]
output = sys.argv[2]
output_zsh = sys.argv[3]

def fill_opts(storage, program):
    print(program)
    o = get_opts(program)
    if not o:
        return
    for arg in o:
        storage[arg] = {}
        fill_opts(storage[arg], ('{} {}'.format(program, arg)))

fill_opts(result, program)
# open('1.json', 'w').write(json.dumps(result))

# result = json.loads(open('1.json').read())

deep = 1

F = ''
F_ZSH = ''


def addc(program, result, deep=1):
    if not result:
        return
    global F, F_ZSH
    wn = []
    for x, v in result.items():
        if v: wn.append(x)
    X = ''
    X += '_%s() {\n' % program
    X += '  local cur prev words cword\n'
    X += '  _init_completion || return\n'
    X += '  if [[ $cword -eq %u ]]; then\n' % deep
    X += '    COMPREPLY=( $( compgen -W \'' + ' '.join(sorted(result.keys())) + '\' -- "$cur" ))\n'
    X += '  else\n'
    if wn:
        X += '    case "${words[%u]}" in\n' % deep
        X += '      ' + '|'.join(sorted(wn)) + ')\n'
        X += '        _%s_${words[%u]}\n' % (program, deep)
        X += '        ;;\n'
        X += '      *)\n'
        X += '        COMPREPLY=( $( compgen -W \'$(ls)\' -- $cur ))\n'
        X += '        ;;\n'
        X += '    esac\n'
    else:
        X += '    COMPREPLY=( $( compgen -W \'$(ls)\' -- $cur ))\n'
    X += '  fi\n'
    X += '}\n'
    if F: X += '\n'
    F = X + F
    X = ''
    X += '_%s() {\n' % program
    X += '  local cword\n'
    X += '  let cword=CURRENT-1\n'
    X += '  if [[ $cword -eq %u ]]; then\n' % deep
    X += '    compadd "$@" ' + ' '.join(sorted(result.keys())) + '\n'
    X += '  else\n'
    if wn:
        X += '    case "${words[%u]}" in\n' % (deep + 1)
        X += '      ' + '|'.join(sorted(wn)) + ')\n'
        X += '        _%s_${words[%u]}\n' % (program, deep + 1)
        X += '        ;;\n'
        X += '      *)\n'
        X += '        _files\n'
        X += '        ;;\n'
        X += '    esac\n'
    else:
        X += '    _files\n'
    X += '  fi\n'
    X += '}\n'
    if F_ZSH: X += '\n'
    F_ZSH = X + F_ZSH
    for w in wn:
        addc('{}_{}'.format(program, w), result[w], deep=deep+1)

addc(program, result)
F += '\ncomplete -F _%s %s' % (program, program)
open(output, 'w').write(F)
F_ZSH = '#compdef {}\n\n{}'.format(program, F_ZSH)
open(output_zsh, 'w').write(F_ZSH)
