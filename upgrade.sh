#!/bin/bash

if [ "x`id -u`" != "x0" ] && [ "x$1" != "x--root" ]; then
    echo "Please run this script as root"
    exit 98
fi

VERSION=3.1.0
BUILD=2018070902

OBS="lm-ei uc-ei INSTALL.txt"

UC_NEW_CFG="runtime/uc_drivers.json"
LM_NEW_CFG="runtime/lm_extensions.json"

if [ ! -d runtime ] || [ ! -f etc/eva_servers ]; then
    echo "Runtime and configs not found. Please run the script in the folder where EVA ICS is already installed"
    exit 1
fi

source etc/eva_servers

CURRENT_BUILD=`./sbin/eva-tinyapi -B`

if [ $? != 0 ]; then
    echo "Can't obtain current build"
    exit 1
fi

if [ $CURRENT_BUILD -ge $BUILD ]; then
    echo "Your build is ${CURRENT_BUILD}, this script can upgrade EVA ICS to ${BUILD} only"
    exit 1
fi

echo "- Starting upgrade to ${VERSION} build ${BUILD}"

mkdir -p _upgrade

echo "- Downloading new version tarball"

cd _upgrade || exit 1

wget https://www.eva-ics.com/download/${VERSION}/nightly/eva-${VERSION}-${BUILD}.tgz || exit 1

echo "- Extracting"

tar xzf eva-${VERSION}-${BUILD}.tgz || exit 1

cd ..

echo "- Stopping everything"

./sbin/eva-control stop

echo "- Installing missing modules"

./_upgrade/eva-${VERSION}/sbin/check_mods install || exit 

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

for f in ${LM_NEW_CFG}; do
    [ ! -f $f ] && echo "{}" > $f
    if [ "x$LM_USER" != "x" ]; then
        chown ${LM_USER} $f
    fi
done

echo "- Installing new files"

rm -f _upgrade/eva-${VERSION}/ui/index.html

cp -rf _upgrade/eva-${VERSION}/* . || exit 1

echo "- Cleaning up"

rm -rf _upgrade

CURRENT_BUILD=`./sbin/uc-control version|sed 's/.*build //g'|awk '{ print $1 }'`

if [ $CURRENT_BUILD = $BUILD ]; then
    echo "- Current build: ${BUILD}"
    echo "---------------------------------------------"
    echo "Upgrade completed. Starting everything back"
    ./sbin/eva-control start
else
    echo "Upgrade failed"
    exit 1
fi
