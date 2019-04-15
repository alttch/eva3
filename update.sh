#!/usr/bin/env bash

#if [ "x`id -u`" != "x0" ] && [ "x$1" != "x--root" ]; then
    #echo "Please run this script as root"
    #exit 98
#fi

VERSION=3.2.1
BUILD=2019040801

[ "x${EVA_REPOSITORY_URL}" = "x" ] && EVA_REPOSITORY_URL=https://get.eva-ics.com

OBS="lm-ei uc-ei INSTALL.txt install.sh install-uc.sh install-lm.sh install-sfa.sh easy-setup.sh install/check_mods sbin/check_mods sbin/check_mqtt set-run-under-user.sh"

UC_NEW_CFG="runtime/uc_drivers.json"
UC_NEW_CFG_L="runtime/uc_modbus.json runtime/uc_owfs.json"
LM_NEW_CFG="runtime/lm_extensions.json"
LM_NEW_DIR="runtime/lm_lcycle.d"

if [ ! -d runtime ] || [ ! -f etc/eva_servers ]; then
    echo "Runtime and configs not found. Please run the script in the folder where EVA ICS is already installed"
    exit 1
fi

source etc/eva_servers

which jq > /dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "Please install jq"
  exit 1
fi

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

curl ${EVA_REPOSITORY_URL}/${VERSION}/nightly/eva-${VERSION}-${BUILD}.tgz -o eva-${VERSION}-${BUILD}.tgz || exit 1

echo "- Extracting"

tar xzf eva-${VERSION}-${BUILD}.tgz || exit 1

cd ..

echo "- Stopping everything"

./sbin/eva-control stop

./install/mklinks || exit 1

echo "- Installing missing modules"

./_update/eva-${VERSION}/install/build-venv . || exit 2

echo "- Removing obsolete files and folders"

for o in ${OBS}; do
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

for f in ${LM_NEW_DIR}; do
    mkdir -p $f
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

mkdir -p ./xc/drivers/phi || exit 1
mkdir -p ./xc/drivers/lpi || exit 1
mkdir -p ./xc/extensions || exit 1

(cd lib/eva/uc && ln -sf ../../../xc/drivers ) || exit 1
(cd xc/drivers/phi && ln -sf ../../../lib/eva/uc/generic/generic_phi.py ) || exit 1
(cd xc/drivers/lpi && ln -sf ../../../lib/eva/uc/generic/generic_lpi.py ) || exit 1
(cd lib/eva/lm && ln -sf ../../../xc/extensions ) || exit 1
(cd xc/extensions && ln -sf ../../lib/eva/lm/generic/generic_ext.py generic.py) || exit 1

rm -f bin/eva-shell
ln -sf eva bin/eva-shell

echo "- Updating tables"

./sbin/eva-update-tables uc || exit 1
./sbin/eva-update-tables lm || exit 1
./sbin/eva-update-tables sfa || exit 1

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
