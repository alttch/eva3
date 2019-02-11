#!/bin/bash


while [ 1 ]; do
    if [ -f /.installed  ]; then
        /opt/eva/sbin/eva-control start
        while [ 1 ]; do
            sleep 86400
        done
    else
        # download EVA ICS
        VERSION=`curl -s https://www.eva-ics.com/download/update_info.json|jq -r .version`
        BUILD=`curl -s https://www.eva-ics.com/download/update_info.json|jq -r .build`
        if [ "x${BUILD}" = "x" ] || [ "x${VERSION}" = "x" ]; then
            echo "Unable to connect to eva-ics.com. Will try again in 30 seconds"
            sleep 30
            continue
        fi
        mkdir -p /opt
        cd /opt
        rm -f eva-dist.tgz
        wget https://www.eva-ics.com/download/${VERSION}/stable/eva-${VERSION}-${BUILD}.tgz -O eva-dist.tgz
        tar xzf eva-dist.tgz
        mv -f eva-${VERSION} eva
        rm -f eva-dist.tgz
        # setup EVA ICS
        /opt/eva/easy-setup --force --clear
        if [ $? -eq 0 ]; then
            # preconfigure logging
            /opt/eva/sbin/eva-control stop
            rm -f /opt/eva/log/*
            ln -sf /dev/stdout /opt/eva/log/uc.log
            ln -sf /dev/stdout /opt/eva/log/lm.log
            ln -sf /dev/stdout /opt/eva/log/sfa.log
            # create install flag
            touch /.installed
        fi
    fi
done
