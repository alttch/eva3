#!/usr/bin/env bash

D=`realpath $0`
cd `dirname ${D}`/..

CMD=$1
DOMAIN=$2
KEY=
CA_CERTS=

function usage {
    echo "Usage $0 <join|quit> <domain> [-a key] [-c ca-certs]"
    exit 99
}

function test_controller {
  (./sbin/eva-tinyapi -C $1 -F test|jq .ok|grep true) > /dev/null 2>&1
  if [ $? -ne 0 ]; then
    echo "Controller ${1^^} test failed"
    exit 5
  fi
}

function on_exit {
  local err=$?
  if [ $err -ne 0 ]; then
    echo "FAILED, CODE: $err"
  fi
}

function create_notifier {
  local T=$1
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
    *)
      usage
      ;;
  esac
done

case $CMD in
  join)
    trap on_exit exit
    [ ! $DOMAIN ] && usage
    grep -E "^${DOMAIN}$" etc/iote.domains > /dev/null 2>&1
    if [ $? -eq 0 ]; then
      echo "Node already joined"
      exit 4
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
    if [ ! $CA_CERTS ] || [ ! -f $CA_CERTS ]; then
      echo "Unable to detect ca-certs bundle. Please specify it manually"
      exit 2
    fi
    if [ ! $KEY ]; then
      echo -n "Cloud key: "
      read -s KEY
      echo
    fi
    [ -f etc/uc.ini ] && test_controller uc
    [ -f etc/lm.ini ] && test_controller lm
    for c in "uc lm"; do
      if [ -f etc/uc.ini ]; then
        destroy_notifier $c > /dev/null 2>&1
        create_notifier $c || exit 3
        ./sbin/eva-control restart $c || exit 3
        destroy_apikey $c > /dev/null 2>&1
        create_apikey $c || exit 3
      fi
    done
    echo $DOMAIN >> etc/iote.domains
    ;;
  leave)
    trap on_exit exit
    [ ! $DOMAIN ] && usage
    [ -f etc/uc.ini ] && test_controller uc
    [ -f etc/lm.ini ] && test_controller lm
    for c in "uc lm"; do
      if [ -f etc/uc.ini ]; then
        destroy_notifier $c
        ./sbin/eva-control restart $c || exit 3
        destroy_apikey $c
      fi
    done
    ;;
  get)
    [ -f etc/iote.domains ] && cat etc/iote.domains
    ;;
  *)
    usage
    ;;
esac
