#!/usr/bin/env bash

D=`realpath $0`
cd `dirname ${D}`/..

CMD=$1
DOMAIN=$2
KEY=
CA_CERTS=
MQTT_PORT=8883
MQTT_USER=eva
FORCE=0

[ ! $EVA_CLOUD ] && EVA_CLOUD=c.iote.cloud
[ ! $EVA_CLOUD_ID ] && EVA_CLOUD_ID=iote

function usage {
    echo "Usage $0 <join|leave> <domain> [-a key] [-c ca-certs] [-y]"
    exit 99
}

function test_controller {
  (./sbin/eva-tinyapi -C $1 -F test|jq .ok|grep true) > /dev/null 2>&1
  if [ $? -ne 0 ]; then
    echo "Controller ${1^^} test failed"
    exit 5
  fi
}

function test_node {
  for c in uc lm; do
    CN=${c^^}
    [ "x$(eval "echo \$${CN}_ENABLED")" == "xyes" ] && test_controller $c
  done
}

function check_installed {
  if [ ! -f etc/uc.ini ] && [ ! -f etc/lm.ini ]; then
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
  ./sbin/check-mqtt --cafile ${CA_CERTS} \
    ${MQTT_USER}:${KEY}@${DOMAIN}.${EVA_CLOUD}:${MQTT_PORT}/ > /dev/null 2>&1
  if [ $? -ne 0 ]; then
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
  echo $BATCH | ./bin/$1-notifier -R --exec-batch=stdin
  if [ $? -ne 0 ]; then
    destroy_notifier $1 > /dev/null 2>&1
    return 1
  fi
}

function destroy_notifier {
  ./bin/$1-notifier destroy ${EVA_CLOUD_ID}.${DOMAIN} || return 1
}

function destroy_apikey {
  ./sbin/eva-tinyapi -C $1 -F destroy_key i=${EVA_CLOUD_ID}.${DOMAIN} || return 1
}

function create_apikey {
  N="${EVA_CLOUD_ID}.${DOMAIN}"
  ./sbin/eva-tinyapi -C $1 -F create_key i=$N || return 1
  ./sbin/eva-tinyapi -C $1 -F set_key_prop i=$N p=key v=${KEY} || return 1
  ./sbin/eva-tinyapi -C $1 -F set_key_prop i=$N p=groups v='#' || return 1
  ./sbin/eva-tinyapi -C $1 -F set_key_prop i=$N p=hosts_allow v='0.0.0.0/0' || return 1
}

shift
shift

while [ $1 ]; do
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

source ./etc/eva_servers

case $CMD in
  join)
    trap on_exit exit
    check_installed
    [ ! $DOMAIN ] && usage
    echo "Joining ${DOMAIN}.${EVA_CLOUD}"
    if [ $FORCE -ne 1 ]; then
      grep -E "^${DOMAIN} ${EVA_CLOUD} " etc/iote.domains > /dev/null 2>&1
      if [ $? -eq 0 ]; then
        echo "Node already joined"
        exit 4
      fi
    fi
    if [ ! $CA_CERTS ]; then
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
    if [ ! $KEY ]; then
      echo -n "Cloud key: "
      read -s KEY
      echo
    fi
    test_node
    check_mqtt || exit 7
    for c in uc lm; do
      CN=${c^^}
      if [ "x$(eval "echo \$${CN}_ENABLED")" == "xyes" ]; then
        destroy_notifier $c > /dev/null 2>&1
        create_notifier $c || exit 3
        ./sbin/eva-control restart $c || exit 3
        destroy_apikey $c > /dev/null 2>&1
        create_apikey $c > /dev/null || exit 3
      fi
    done
    grep -E "^${DOMAIN} ${EVA_CLOUD} " etc/iote.domains > /dev/null 2>&1 || \
      echo $DOMAIN $EVA_CLOUD $EVA_CLOUD_ID >> etc/iote.domains
    echo
    echo "Node joined ${DOMAIN}.${EVA_CLOUD}"
    ;;
  leave)
    trap on_exit exit
    check_installed
    [ ! $DOMAIN ] && usage
    echo "Leaving ${DOMAIN}.${EVA_CLOUD}"
    if [ $FORCE -ne 1 ]; then
      grep -E "^${DOMAIN} ${EVA_CLOUD} " etc/iote.domains > /dev/null 2>&1
      if [ $? -ne 0 ]; then
        echo "Node not in cloud"
        exit 4
      fi
    fi
    test_node
    for c in uc lm; do
      CN=${c^^}
      if [ "x$(eval "echo \$${CN}_ENABLED")" == "xyes" ]; then
        ./sbin/eva-tinyapi -C $c -F notify_leaving i=${EVA_CLOUD_ID}.${DOMAIN} > /dev/null 2>&1
        destroy_notifier $c > /dev/null 2>&1
        ./sbin/eva-control restart $c || exit 3
        destroy_apikey $c > /dev/null 2>&1
      fi
    done
    grep -vE "^${DOMAIN} ${EVA_CLOUD} " etc/iote.domains > etc/iote.domains.tmp
    mv -f etc/iote.domains.tmp etc/iote.domains
    echo
    echo "Node left ${DOMAIN}.${EVA_CLOUD}"
    ;;
  list)
    [ -f etc/iote.domains ] && cat etc/iote.domains
    ;;
  *)
    usage
    ;;
esac
