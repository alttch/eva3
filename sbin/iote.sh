#!/usr/bin/env bash

D=$(realpath "$0")
cd $(dirname "${D}")/.. || exit 11

CMD=$1
DOMAIN=$2
KEY=
CA_CERTS=
MQTT_PORT=8883
MQTT_USER=eva
FORCE=0

[ -z "$EVA_CLOUD" ] && EVA_CLOUD=c.iote.cloud
[ -z "$EVA_CLOUD_ID" ] && EVA_CLOUD_ID=iote

source <(./sbin/key-as-source config/uc/service UC 2>/dev/null)
source <(./sbin/key-as-source config/lm/service LM 2>/dev/null)
source <(./sbin/key-as-source config/sfa/service SFA 2>/dev/null)

if [ -z "$UC_ENABLED" ] || [ -z "${LM_ENABLED}" ] || [ -z "${SFA_ENABLED}" ]; then
  echo "Unable to read registry key"
  exit 1
fi


function usage {
  echo "Usage $0 <join|leave> <domain> [-a key] [-c ca-certs] [-y]"
  exit 99
}

function test_controller {
  if ! (./sbin/eva-tinyapi -C "$1" -F test|jq .ok|grep true) >& /dev/null; then
    echo "Controller ${1^^} test failed"
    exit 5
  fi
}

function test_node {
  for c in uc lm; do
    CN=${c^^}
    [ "$(eval "echo \$${CN}_ENABLED")" == "1" ] && test_controller $c
  done
}

function check_installed {
  if [ "$UC_SETUP" != "1" ] && [ "$LM_SETUP" != "1" ]; then
    echo "No UC or LM PLC installed on this node"
    exit 6
  fi
}

function on_exit {
  local err=$?
  if [ $err -ne 0 ]; then
    echo "FAILED, CODE: $err"
  fi
}

function check_mqtt {
  if ! ./sbin/check-mqtt --cafile "${CA_CERTS}" \
    "${MQTT_USER}:${KEY}@${DOMAIN}.${EVA_CLOUD}:${MQTT_PORT}/" >& /dev/null; then
      echo "MQTT check failed"
      return 1
  fi
}

function create_notifier {
  N="${EVA_CLOUD_ID}.${DOMAIN}"
  BATCH="create ${N} mqtt:${MQTT_USER}:${KEY}@${DOMAIN}.${EVA_CLOUD}:${MQTT_PORT} -y"
  BATCH="$BATCH;set ${N} ca_certs ${CA_CERTS}"
  BATCH="$BATCH;set ${N} skip_test 1"
  BATCH="$BATCH;subscribe state ${N} -p '#' -g '#'"
  BATCH="$BATCH;subscribe log ${N}"
  BATCH="$BATCH;subscribe server ${N}"
  BATCH="$BATCH;set ${N} api_enabled 1"
  BATCH="$BATCH;set ${N} announce_interval 30"
  BATCH="$BATCH;test ${N}"
  if ! echo "$BATCH" | "./bin/$1-notifier" -R --exec-batch=stdin; then
    destroy_notifier "$1" > /dev/null 2>&1
    return 1
  fi
}

function destroy_notifier {
  "./bin/$1-notifier" destroy "${EVA_CLOUD_ID}.${DOMAIN}" || return 1
}

function destroy_apikey {
  "./sbin/eva-tinyapi" -C "$1" -F destroy_key "i=${EVA_CLOUD_ID}.${DOMAIN}" || return 1
}

function create_apikey {
  N="${EVA_CLOUD_ID}.${DOMAIN}"
  ./sbin/eva-tinyapi -C "$1" -F create_key "i=$N" || return 1
  ./sbin/eva-tinyapi -C "$1" -F set_key_prop "i=$N" p=key "v=${KEY}" || return 1
  ./sbin/eva-tinyapi -C "$1" -F set_key_prop "i=$N" p=groups v='#' || return 1
  ./sbin/eva-tinyapi -C "$1" -F set_key_prop "i=$N" p=hosts_allow v='0.0.0.0/0' || return 1
}

shift
shift

while [ "$1" ]; do
  case $1 in
    -a)
      shift
      KEY=$1
      shift
      ;;
    -c)
      shift
      CA_CERTS=$1
      shift
      ;;
    -y)
      shift
      FORCE=1
      ;;
    *)
      usage
      ;;
  esac
done

case $CMD in
  join)
    trap on_exit exit
    check_installed
    [ -z "$DOMAIN" ] && usage
    echo "Joining ${DOMAIN}.${EVA_CLOUD}"
    if [ $FORCE -ne 1 ]; then
      if AUTO_PREFIX=1 ./sbin/eva-registry-cli get-field \
        "config/clouds/${EVA_CLOUD_ID}" "${DOMAIN}.${EVA_CLOUD}" >& /dev/null; then
              echo "Node already joined"
              exit 4
      fi
    fi
    if [ -z "$CA_CERTS" ]; then
      source /etc/os-release
      [ "x$ID_LIKE" = "x" ] && ID_LIKE=$ID
      case $ID_LIKE in
        debian)
          CA_CERTS=/etc/ssl/certs/ca-certificates.crt
          ;;
        fedora)
          CA_CERTS=/etc/ssl/certs/ca-bundle.trust.crt
          ;;
      esac
    fi
    if [ ! $CA_CERTS ]; then
      echo "Unable to detect ca-certs bundle. Please specify it manually"
      exit 2
    fi
    if [ ! -f ${CA_CERTS} ]; then
      echo "Unable to find ca-certs bundle ${CA_CERTS}"
      exit 2
    fi
    if [ -z "$KEY" ]; then
      echo -n "Cloud key: "
      read -sr KEY
      echo
    fi
    test_node
    check_mqtt || exit 7
    for c in uc lm; do
      CN=${c^^}
      if [ "$(eval "echo \$${CN}_ENABLED")" == "1" ]; then
        destroy_notifier $c > /dev/null 2>&1
        create_notifier $c || exit 3
        ./sbin/eva-control restart $c || exit 3
        destroy_apikey $c > /dev/null 2>&1
        create_apikey $c > /dev/null || exit 3
      fi
    done
    AUTO_PREFIX=1 ./sbin/eva-registry-cli set-field \
      "config/clouds/${EVA_CLOUD_ID}" "${DOMAIN}.${EVA_CLOUD}/account" "${DOMAIN}" > /dev/null || exit 8
    echo
    echo "Node joined ${DOMAIN}.${EVA_CLOUD}"
    ;;
  leave)
    trap on_exit exit
    check_installed
    [ -z "$DOMAIN" ] && usage
    echo "Leaving ${DOMAIN}.${EVA_CLOUD}"
    if [ $FORCE -ne 1 ]; then
      if ! AUTO_PREFIX=1 ./sbin/eva-registry-cli get-field \
        "config/clouds/${EVA_CLOUD_ID}" "${DOMAIN}.${EVA_CLOUD}" >& /dev/null; then
              echo "Node not in the cloud"
              exit 4
      fi
    fi
    test_node
    for c in uc lm; do
      CN=${c^^}
      if [ "$(eval "echo \$${CN}_ENABLED")" == "1" ]; then
        ./sbin/eva-tinyapi -C $c -F notify_leaving i="${EVA_CLOUD_ID}.${DOMAIN}" > /dev/null 2>&1
        destroy_notifier $c > /dev/null 2>&1
        ./sbin/eva-control restart $c || exit 3
        destroy_apikey $c > /dev/null 2>&1
      fi
    done
    AUTO_PREFIX=1 ./sbin/eva-registry-cli delete-field \
      "config/clouds/${EVA_CLOUD_ID}" "${DOMAIN}.${EVA_CLOUD}" > /dev/null || exit 8
    echo
    echo "Node left ${DOMAIN}.${EVA_CLOUD}"
    ;;
  list)
    ( AUTO_PREFIX=1 ./sbin/eva-registry-cli get config/clouds/iote | jq -r ) 2> /dev/null
    ;;
  *)
    usage
    ;;
esac
