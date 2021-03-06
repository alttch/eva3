#!/usr/bin/env bash

trap '' HUP

CONTROLLER=$1
PROCESS=$2

D=`realpath $0`
cd `dirname ${D}`/..

source ./etc/watchdog > /dev/null 2>&1

if [ "x$WATCHDOG_INTERVAL" = "x" ]; then
    ( >&2 echo "WARNING: watchdog not configured" )
    exit 1
fi

[ "x${WATCHDOG_MAX_TIMEOUT}" = "x" ] && WATCHDOG_MAX_TIMEOUT=5

export EVA_DIR=`pwd`
PIDFILE=./var/${CONTROLLER}_watchdog.pid

echo $$ > ${PIDFILE}

while [ 1 ]; do
    sleep ${WATCHDOG_INTERVAL}
    find ./var/${CONTROLLER}_reload -mmin +5 -exec rm -f {} \; > /dev/null 2>&1
    [ -f ./var/${CONTROLLER}.reload ] && continue
    ./sbin/eva-tinyapi -C ${CONTROLLER} -F test -T ${WATCHDOG_MAX_TIMEOUT} > /dev/null 2>&1
    if [ $? != 0 ]; then
        echo "${PROCESS} not responding, sending restart"
        if [ "x${WATCHDOG_DUMP}" = "xyes" ]; then
            ./sbin/eva-tinyapi -C ${CONTROLLER} -F dump -T ${WATCHDOG_MAX_TIMEOUT} > /dev/null 2>&1
        fi
        rm -f ${PIDFILE}
        ./sbin/${CONTROLLER}-control restart
        exit
    fi
done
