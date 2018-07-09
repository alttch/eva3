#!/bin/bash

which realpath > /dev/null
if [ $? != 0 ]; then
    echo 'please install realpath'
    exit 1
fi

D=`realpath $0`
cd `dirname ${D}`

if [ -d runtime ]; then
    echo "runtime folder found, the system seems to be live"
    echo "aborting"
    exit 1
fi

echo "Preparing Universal Controller"
sh install-uc.sh || exit 1
echo "Preparing Logic Manager"
sh install-lm.sh || exit 1
echo "Preparing SCADA Final Aggregator"
sh install-sfa.sh || exit
echo ""
echo "Completed!"
echo ""
echo "Now edit etc/*.ini and etc/eva_servers"
echo ""
echo "After you can start EVA with sbin/eva-control start"
