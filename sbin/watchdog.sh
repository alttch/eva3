#!/usr/bin/env bash

trap '' HUP

CONTROLLER=$1
PROCESS=$2

D=$(realpath "$0")
cd "$(dirname "${D}")/.." || exit 1

source <(./sbin/key-as-source config/watchdog WATCHDOG)

if [ -z "$WATCHDOG_INTERVAL" ]; then
    ( >&2 echo "WARNING: watchdog not configured or unable to read registry key" )
    exit 1
fi

[ -z "${WATCHDOG_MAX_TIMEOUT}" ] && WATCHDOG_MAX_TIMEOUT=5

EVA_DIR=$(pwd)
PIDFILE="./var/${CONTROLLER}_watchdog.pid"
export EVA_DIR

echo $$ > "${PIDFILE}"

while true; do
    sleep "${WATCHDOG_INTERVAL}"
    find "./var/${CONTROLLER}"_reload -mmin +5 -exec rm -f {} \; >& /dev/null
    [ -f "./var/${CONTROLLER}.reload" ] && continue
    if ! ./sbin/eva-tinyapi -C "${CONTROLLER}" -F test -T "${WATCHDOG_MAX_TIMEOUT}" >& /dev/null; then
        echo "${PROCESS} not responding, sending restart"
        if [ "${WATCHDOG_DUMP}" = "1" ]; then
            ./sbin/eva-tinyapi -C "${CONTROLLER}" -F dump -T "${WATCHDOG_MAX_TIMEOUT}" >& /dev/null
        fi
        rm -f "${PIDFILE}"
        ./sbin/eva-control restart "${CONTROLLER}"
        exit
    fi
done
