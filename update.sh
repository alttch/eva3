#!/bin/bash

if [ "x`id -u`" != "x0" ] && [ "x$1" != "x--root" ]; then
    echo "Please run this script as root"
    exit 98
fi

VERSION=3.1.1
BUILD=2018100701

OBS="lm-ei uc-ei INSTALL.txt install.sh install-uc.sh install-lm.sh install-sfa.sh easy-setup.sh sbin/check_mods set-run-under-user.sh"

UC_NEW_CFG="runtime/uc_drivers.json"
UC_NEW_CFG_L="runtime/uc_modbus.json"
LM_NEW_CFG="runtime/lm_extensions.json"

if [ ! -d runtime ] || [ ! -f etc/eva_servers ]; then
    echo "Runtime and configs not found. Please run the script in the folder where EVA ICS is already installed"
    exit 1
fi

source etc/eva_servers

if [ -f ./sbin/eva-tinyapi ]; then
    CURRENT_BUILD=`./sbin/eva-tinyapi -B`
    
    if [ $? != 0 ]; then
        echo "Can't obtain current build"
        exit 1
    fi
    
    if [ $CURRENT_BUILD -ge $BUILD ]; then
        echo "Your build is ${CURRENT_BUILD}, this script can update EVA ICS to ${BUILD} only"
        exit 1
    fi
fi

rm -rf _update

echo "- Starting update to ${VERSION} build ${BUILD}"

mkdir -p _update

touch _update/test

if [ $? -ne 0 ]; then
    echo "Unable to write on partition. Read only file system?"
    exit 1
fi

echo "- Downloading new version tarball"

cd _update || exit 1

wget https://www.eva-ics.com/download/${VERSION}/nightly/eva-${VERSION}-${BUILD}.tgz || exit 1

echo "- Extracting"

tar xzf eva-${VERSION}-${BUILD}.tgz || exit 1

cd ..

echo "- Stopping everything"

./sbin/eva-control stop

echo "- Installing missing modules"

./_update/eva-${VERSION}/install/check_mods install || exit 2

echo "- Removing obsolete files and folders"

for o in ${OBS}; do
    echo $o
    rm -rf ${o}
done

echo "- Adding new runtime configs"

for f in ${UC_NEW_CFG}; do
    [ ! -f $f ] && echo "{}" > $f
    if [ "x$UC_USER" != "x" ]; then
        chown ${UC_USER} $f
    fi
done

for f in ${UC_NEW_CFG_L}; do
    [ ! -f $f ] && echo "[]" > $f
    if [ "x$UC_USER" != "x" ]; then
        chown ${UC_USER} $f
    fi
done

for f in ${LM_NEW_CFG}; do
    [ ! -f $f ] && echo "{}" > $f
    if [ "x$LM_USER" != "x" ]; then
        chown ${LM_USER} $f
    fi
done

if [ ! -d runtime/tpl ]; then
    mkdir runtime/tpl
    chown ${UC_USER} runtime/tpl
fi

if [ ! -d backup ]; then
    mkdir backup
    chmod 700 backup
fi

echo "- Installing new files"

rm -f _update/eva-${VERSION}/ui/index.html
rm -f _update/eva-${VERSION}/update.sh

cp -rf _update/eva-${VERSION}/* . || exit 1

ln -sf ../../../xc/drivers lib/eva/uc/drivers
ln -sf ../../../xc/extensions lib/eva/lm/extensions

echo "- Cleaning up"

rm -rf _update

CURRENT_BUILD=`./sbin/eva-tinyapi -B`

if [ $CURRENT_BUILD = $BUILD ]; then
    echo "- Current build: ${BUILD}"
    echo "---------------------------------------------"
    echo "Update completed. Starting everything back"
    ./sbin/eva-control start
else
    echo "Update failed"
    exit 1
fi
