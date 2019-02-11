#!/bin/sh

while [ 1 ]; do
    if [ -f /.installed  ]; then
        /opt/eva/sbin/eva-control start
        while [ 1 ]; do
            sleep 86400
        done
    else
        # download EVA ICS
        mkdir -p /opt
        cd /opt
        wget https://www.eva-ics.com/download/3.1.1/stable/eva-3.1.1-2018103001.tgz -O eva.tgz
        tar xzf eva.tgz
        mv -f eva-3.1.1 eva
        rm -f eva.tgz
        # setup EVA ICS
        /opt/eva/easy-setup --force --clear && touch /.installed
    fi
done
