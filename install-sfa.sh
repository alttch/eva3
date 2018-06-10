#!/bin/bash

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

echo "Installing EVA SFA to `pwd`"

echo "Creating dirs"
mkdir -p ./etc || exit 1
chmod 755 ./etc
mkdir -p ./var || exit 1
mkdir -p ./log || exit 1
mkdir -p ./runtime || exit 1
mkdir -p ./runtime/sfa_notify.d || exit 1
chmod 700 ./runtime/sfa_notify.d || exit 1
mkdir -p ./runtime/sfa_remote_uc.d || exit 1
chmod 700 ./runtime/sfa_remote_uc.d || exit 1
mkdir -p ./runtime/sfa_remote_lm.d || exit 1
chmod 700 ./runtime/sfa_remote_lm.d || exit 1
mkdir -p ./runtime/db || exit 1
touch runtime/db/sfa.db || exit 1
mkdir -p ./xc/cmd || exit 1
mkdir -p pvt
chmod 700 pvt

echo "Checking mods"
./sbin/check_mods install || exit 1

echo "Doing initial config"

[ -f ./runtime/sfa_cvars.json ] || echo "{}" > ./runtime/sfa_cvars.json

echo "Finished"

