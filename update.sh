#!/usr/bin/env bash

VERSION=3.4.0
BUILD=2021061205

PYTHON3_MIN=6
PYTHON_MINOR=$(./python3/bin/python3 --version|cut -d. -f2)
if [ "$PYTHON_MINOR" -lt "$PYTHON3_MIN" ]; then
  echo "Python 3.$PYTHON3_MIN is required"
  exit 1
fi

[ -z "${EVA_REPOSITORY_URL}" ] && EVA_REPOSITORY_URL=https://get.eva-ics.com

export EVA_REPOSITORY_URL

OBS="./sbin/layout-converter ./sbin/uc-control ./sbin/lm-control ./sbin/sfa-control"

UC_NEW_DIR="runtime/xc/uc/cs"
LM_NEW_DIR="runtime/xc/lm/functions runtime/xc/lm/cs"
SFA_NEW_DIR="runtime/xc/sfa/cs"

if [ ! -d ./runtime ]; then
  echo "Runtime dir not found. Please run the script in the folder where EVA ICS is already installed"
  exit 1
fi

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

if [ -f ./runtime/uc_cvars.json ] || [ -f ./runtime/lm_cvars.json ] || [ -f ./runtime/sfa_cvars.json ]; then
  echo "EVA ICS obsolete configuration found. Checking..."
  ./python3/bin/python3 ./_update/eva-${VERSION}/cli/convert-legacy-configs.py check --dir $(pwd) || exit 3
fi

echo "- Installing missing modules"

./_update/eva-${VERSION}/install/build-venv . || exit 2

if [ "$CHECK_ONLY" = 1 ]; then
  echo
  echo "Checks passed, venv updated. New version files can be explored in the _update dir"
  exit 0
fi

echo "- Removing obsolete files and folders"

for o in ${OBS}; do
  rm -rf "${o}"
done

if [ ! -d ./backup ]; then
  mkdir ./backup
  chmod 700 ./backup
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

[ -x ./sbin/registry-control ] && ./sbin/registry-control stop

./install/install-yedb || exit 2

if [ -f /etc/systemd/system/eva-ics.service ]; then
  if ! grep eva-ics-registry /etc/systemd/system/eva-ics.service >& /dev/null; then
    if [ "$(id -u)" = "0" ]; then
      echo "- Installing EVA ICS registry service"
      PREFIX=$(pwd)
      sed "s|/opt/eva|${PREFIX}|g" ./etc/systemd/eva-ics-registry.service > /etc/systemd/system/eva-ics-registry.service
      sed "s|/opt/eva|${PREFIX}|g" ./etc/systemd/eva-ics.service > /etc/systemd/system/eva-ics.service
      if systemctl -a |grep eva-ics|grep active >& /dev/null ; then
        echo "- Enabling EVA ICS registry service"
        systemctl enable eva-ics-registry.service
        systemctl daemon-reload
      fi
    else
      echo "- WARNING! EVA ICS sevice is installed but update isn't launched under root"
      echo "- WARNING! Please install new eva-ics.service and eva-ics-registry.service manually"
      sleep 3
    fi
  fi
fi

./sbin/registry-control start || exit 2

./install/import-registry-schema || exit 8
./install/import-registry-defaults || exit 8

if [ -f ./runtime/uc_cvars.json ] || [ -f ./runtime/lm_cvars.json ] || [ -f ./runtime/sfa_cvars.json ]; then
  echo "EVA ICS obsolete configuration found. Staring conversion"
  ./install/convert-legacy-configs import --clear || exit 4
fi

source <(./sbin/key-as-source config/uc/service UC 2>/dev/null)
source <(./sbin/key-as-source config/lm/service LM 2>/dev/null)
source <(./sbin/key-as-source config/sfa/service SFA 2>/dev/null)

if [ -z "$UC_ENABLED" ] || [ -z "${LM_ENABLED}" ] || [ -z "${SFA_ENABLED}" ]; then
  echo "Unable to read registry key"
  exit 8
fi

echo "- Creating new runtime dirs"

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

for f in ${SFA_NEW_DIR}; do
  mkdir -p "$f"
  if [ "$SFA_USER" ]; then
    chown "${SFA_USER}" "$f"
  fi
done

if [ ! -d runtime/tpl ]; then
  mkdir ./runtime/tpl
  if [ "$UC_USER" ]; then
    chown "${UC_USER}" ./runtime/tpl
  fi
fi

echo "- Updating tables"

if [ "$UC_SETUP" == "1" ]; then
  ./sbin/eva-update-tables uc || exit 1
fi

if [ "$LM_SETUP" == "1" ]; then
  ./sbin/eva-update-tables lm || exit 1
fi

if [ "$SFA_SETUP" == "1" ]; then
  ./sbin/eva-update-tables sfa || exit 1
fi

echo "- Cleaning up"

rm -rf _update

CURRENT_BUILD=$(./sbin/eva-tinyapi -B)

if [ "$CURRENT_BUILD" = "$BUILD" ]; then
  echo "- Current build: ${BUILD}"
  echo "---------------------------------------------"
  echo "Update completed. Starting everything back"
  ./sbin/registry-control start
  ./sbin/eva-control start
else
  echo "Update failed"
  exit 1
fi
