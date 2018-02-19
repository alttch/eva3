#!/bin/sh

which realpath > /dev/null
if [ $? != 0 ]; then
    echo 'please install realpath'
    exit 1
fi

D=`realpath $0`
cd `dirname ${D}`

which pip3 > /dev/null
if [ $? != 0 ]; then
    echo 'please install pip3'
    exit 1
fi

if [ ! -x ./sbin/check_mods ]; then
    echo "please run in EVA dir!"
    exit 1
fi

echo "Installing EVA LM PLC to `pwd`"

echo "Creating dirs"
mkdir -p ./etc || exit 1
chmod 700 ./etc
mkdir -p ./var || exit 1
mkdir -p ./log || exit 1
mkdir -p ./runtime || exit 1
mkdir -p ./runtime/lm_notify.d || exit 1
chmod 700 ./runtime/lm_notify.d || exit 1
mkdir -p ./runtime/lm_dmatrix_rule.d || exit 1
chmod 700 ./runtime/lm_dmatrix_rule.d || exit 1
mkdir -p ./runtime/lm_lmacro.d || exit 1
mkdir -p ./runtime/lm_lvar.d || exit 1
mkdir -p ./runtime/lm_remote_uc.d || exit 1
chmod 700 ./runtime/lm_remote_uc.d || exit 1
mkdir -p ./runtime/db || exit 1
mkdir -p ./runtime/xc/lm || exit 1
mkdir -p ./xc/cmd || exit 1

cd xc
ln -sf ../runtime/xc/lm

cd ..

echo "Checking mods"
./sbin/check_mods install || exit 1

echo "Doing initial config"

[ -f ./runtime/lm_cvars.json ] || echo "{}" > ./runtime/lm_cvars.json

echo "Finished"

