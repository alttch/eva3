#!/bin/bash

function show_logs {
    while [ 1 ]; do
        tail -F /opt/eva/log/*.log
    done
}

echo $$ > /var/run/start.pid

while [ 1 ]; do
    if [ -f /.installed  ]; then
        # remove old pid files
        rm -f /opt/eva/var/*.pid
        # start EVA ICS
        /opt/eva/sbin/eva-control start
        show_logs
    else
        # download EVA ICS
        VERSION=`curl -s https://www.eva-ics.com/download/update_info.json|jq -r .version`
        BUILD=`curl -s https://www.eva-ics.com/download/update_info.json|jq -r .build`
        if [ "x${BUILD}" = "x" ] || [ "x${VERSION}" = "x" ]; then
            echo "Unable to connect to eva-ics.com. Will try again in 30 seconds..."
            sleep 30
            continue
        fi
        mkdir -p /opt
        cd /opt
        rm -rf eva
        rm -f eva-dist.tgz
        wget https://www.eva-ics.com/download/${VERSION}/stable/eva-${VERSION}-${BUILD}.tgz -O eva-dist.tgz
        tar xzf eva-dist.tgz
        mv -f eva-${VERSION} eva
        rm -f eva-dist.tgz
        # connect runtime volume if exists
        [ -d /runtime ] && ln -sf /runtime /opt/eva/runtime
        # set layout if defined
        if [ "x${layout}" != "x" ]; then
            sed -i "s/^layout =.*/layout = ${layout}/g" eva/etc/*.ini-dist
        fi
        # connect ui volume if exists
        if [ -d /ui ]; then
            if [ -z "$(ls -A /ui)" ]; then
                # empty ui, putting default
                mv /opt/eva/ui/* /ui/
            fi
            rm -rf /opt/eva/ui
            ln -sf /ui /opt/eva/ui
        fi
        # connect backup volume if exists
        [ -d /backup ] && ln -sf /backup /opt/eva/backup
        # setup EVA ICS
        AUTO_OPTS=
        MQTT_OPTS=
        LINK_OPTS=
        PRODUCT_OPTS=
        if [ "x${auto_install}" != "x" ]; then
            AUTO_OPTS=--auto
            [ "x${link}" = "x1" ] && LINK_OPTS="--link"
            [ "x${mqtt}" != "x" ] && MQTT_OPTS="--mqtt"
            [ "x${product}" != "x" ] && PRODUCT_OPTS="-p"
        fi
        cd /opt/eva
        rm -rf runtime/*_notify.d runtime/*_remote_*.d
        ./easy-setup --force ${AUTO_OPTS} ${MQTT_OPTS} ${mqtt} ${LINK_OPTS} ${PRODUCT_OPTS} ${product}
        if [ $? -eq 0 ]; then
            # create install flag
            touch /.installed
            show_logs
        else
            sleep 10
        fi
    fi
done
