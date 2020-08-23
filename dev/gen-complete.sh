#!/bin/sh

prog='eva uc-cmd lm-cmd sfa-cmd uc-notifier lm-notifier sfa-notifier'

for p in $prog; do
  ./dev/generate-completion.py $p etc/bash_completion.d/$p etc/zsh/Completion/_$p
done
