Enable completion in zsh:

```shell
fpath=(/opt/eva/etc/zsh/Completion $fpath)

autoload -U compinit && compinit
```
