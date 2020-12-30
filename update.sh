#!/usr/bin/env bash

VERSION=3.3.2
BUILD=2020123002

PYTHON3_MIN=6
PYTHON_MINOR=$(./python3/bin/python3 --version|cut -d. -f2)
if [ "$PYTHON_MINOR" -lt "$PYTHON3_MIN" ]; then
  echo "Python 3.$PYTHON3_MIN is required"
  exit 1
fi

[ -z "${EVA_REPOSITORY_URL}" ] && EVA_REPOSITORY_URL=https://get.eva-ics.com

OBS=""

UC_NEW_CFG="runtime/uc_cs.json"
UC_NEW_CFG_L=""
UC_NEW_DIR="runtime/xc/uc/cs"
LM_NEW_CFG="runtime/lm_cs.json"
LM_NEW_DIR="runtime/xc/lm/functions runtime/lm_job.d runtime/xc/lm/cs runtime/lm_ext_data.d"
SFA_NEW_CFG="runtime/sfa_cs.json"
SFA_NEW_DIR="runtime/xc/sfa/cs"

if [ ! -d runtime ] || [ ! -f etc/eva_servers ]; then
    echo "Runtime and configs not found. Please run the script in the folder where EVA ICS is already installed"
    exit 1
fi

source etc/eva_servers

if ! command -v jq > /dev/null; then
  echo "Please install jq"
  exit 1
fi

if [ -f ./sbin/eva-tinyapi ]; then
    if ! CURRENT_BUILD=$(./sbin/eva-tinyapi -B); then
        echo "Can't obtain current build"
        exit 1
    fi
    
    if [ "$CURRENT_BUILD" -ge "$BUILD" ]; then
        echo "Your build is ${CURRENT_BUILD}, this script can update EVA ICS to ${BUILD} only"
        exit 1
    fi
fi

rm -rf _update

echo "- Starting update to ${VERSION} build ${BUILD}"

mkdir -p _update

if ! touch _update/test; then
    echo "Unable to write. Read-only file system?"
    exit 1
fi

echo "- Downloading new version tarball"

cd _update || exit 1

if [ -f ../eva-${VERSION}-${BUILD}.tgz ]; then
  cp ../eva-${VERSION}-${BUILD}.tgz .
else
  curl -L ${EVA_REPOSITORY_URL}/${VERSION}/nightly/eva-${VERSION}-${BUILD}.tgz \
    -o eva-${VERSION}-${BUILD}.tgz || exit 1
fi

echo "- Extracting"

tar xzf eva-${VERSION}-${BUILD}.tgz || exit 1

cd ..

echo "- Stopping everything"

./sbin/eva-control stop

echo "- Installing missing modules"

./_update/eva-${VERSION}/install/build-venv . || exit 2

if [ "$CHECK_ONLY" = 1 ]; then
  echo
  echo "Checks passed, venv updated. New version files can be explored in the _update dir"
  exit 0
fi

echo "- Removing obsolete files and folders"

for o in ${OBS}; do
    rm -rf ${o}
done

echo "- Adding new runtime configs"

for f in ${UC_NEW_CFG}; do
    [ ! -f $f ] && echo "{}" > $f
    if [ "$UC_USER" ]; then
        chown "${UC_USER}" "$f"
    fi
done

for f in ${UC_NEW_CFG_L}; do
    [ ! -f $f ] && echo "[]" > $f
    if [ "$UC_USER" ]; then
        chown "${UC_USER}" "$f"
    fi
done

for f in ${LM_NEW_CFG}; do
    [ ! -f "$f" ] && echo "{}" > $f
    if [ "$LM_USER" ]; then
        chown "${LM_USER}" "$f"
    fi
done

for f in ${SFA_NEW_CFG}; do
    [ ! -f $f ] && echo "{}" > $f
    if [ "$SFA_USER" ]; then
        chown "${SFA_USER}" "$f"
    fi
done

for f in ${UC_NEW_DIR}; do
    mkdir -p "$f"
    if [ "$UC_USER" ]; then
        chown "${UC_USER}" "$f"
    fi
done

for f in ${LM_NEW_DIR}; do
    mkdir -p "$f"
    if [ "$LM_USER" ]; then
        chown "${LM_USER}" "$f"
    fi
done

chmod 700 ./runtime/lm_ext_data.d || exit 1

for f in ${SFA_NEW_DIR}; do
    mkdir -p "$f"
    if [ "$SFA_USER" ]; then
        chown "${SFA_USER}" "$f"
    fi
done

if [ ! -d runtime/tpl ]; then
    mkdir runtime/tpl
    chown "${UC_USER}" runtime/tpl
fi

if [ ! -d backup ]; then
    mkdir backup
    chmod 700 backup
fi

echo "- Installing new files"

(cd ./lib/eva && ln -sf ../../plugins) || exit 1

rm -f _update/eva-${VERSION}/ui/index.html
rm -f _update/eva-${VERSION}/update.sh

cp -rf _update/eva-${VERSION}/* . || exit 1

mkdir -p ./xc/drivers/phi || exit 1
mkdir -p ./xc/drivers/lpi || exit 1
mkdir -p ./xc/extensions || exit 1

mkdir -p ./runtime/data || exit 1

(cd lib/eva/uc && ln -sf ../../../xc/drivers . ) || exit 1
(cd xc/drivers/phi && ln -sf ../../../lib/eva/uc/generic/generic_phi.py . ) || exit 1
(cd xc/drivers/lpi && ln -sf ../../../lib/eva/uc/generic/generic_lpi.py . ) || exit 1
(cd lib/eva/lm && ln -sf ../../../xc/extensions . ) || exit 1
(cd xc/extensions && ln -sf ../../lib/eva/lm/generic/generic_ext.py generic.py) || exit 1
(cd xc && ln -sf ../runtime/xc/sfa) || exit 1


if [ ! -d ./runtime/xc/cmd ]; then
  if [ -d ./xc/cmd ]; then
    mv -f ./xc/cmd runtime/xc/ || exit 1
    (cd xc && ln -sf ../runtime/xc/cmd) || exit 1
  fi
fi

rm -f bin/eva-shell
ln -sf eva bin/eva-shell

./install/mklinks || exit 1

echo "- Updating tables"

if [ -f ./etc/uc.ini ]; then
  ./sbin/eva-update-tables uc || exit 1
fi

if [ -f ./etc/lm.ini ]; then
  ./sbin/eva-update-tables lm || exit 1
fi
if [ -f ./etc/sfa.ini ]; then
  ./sbin/eva-update-tables sfa || exit 1
fi

echo "- Cleaning up"

rm -rf _update

CURRENT_BUILD=$(./sbin/eva-tinyapi -B)

if [ "$CURRENT_BUILD" = "$BUILD" ]; then
    echo "- Current build: ${BUILD}"
    echo "---------------------------------------------"
    echo "Update completed. Starting everything back"
    ./sbin/eva-control start
else
    echo "Update failed"
    exit 1
fi
