#!/bin/sh

if [ ! $3 ]; then
    echo "Usage: $0 <greenhouse_number> <temp|hum|soilm|ldr> <value>"
    exit 99
fi

MASTERKEY=`grep MASTERKEY docker-compose.yml |head -1|awk -F= '{ print $2 }'`

which jq > /dev/null
JQ=$?

curl -v -m5 -d "k=${MASTERKEY}&i=greenhouse${1}/env/${2}&s=1&v=${3}" http://10.27.11.10${1}:8812/uc-api/update | ( [ ${JQ} -eq 0 ] && jq || cat )

echo
