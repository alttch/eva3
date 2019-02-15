#!/bin/bash

TERMFLAG=

[ ${repo_uri} ] || repo_uri=https://get.eva-ics.com

function _term {
    /opt/eva/sbin/eva-control stop
    TERMFLAG=1
    [ -f /var/run/start-tail.pid ] && kill `cat /var/run/start-tail.pid` || killall tail
}

function show_logs {
    while [ ! ${TERMFLAG} ]; do
        tail -F /opt/eva/log/*.log &
        c=$!
        echo $c > /var/run/start-tail.pid
        wait $c
    done
}

echo $$ > /var/run/start.pid

while [ ! ${TERMFLAG} ]; do
    if [ -f /.installed  ]; then
        trap _term SIGTERM
        # remove old pid files
        rm -f /opt/eva/var/*.pid
        # start EVA ICS
        /opt/eva/sbin/eva-control start
        show_logs
    else
        cd /opt
        # download EVA ICS
        if [ ${download} ] || [ ${force_distro} ]; then
            /download.sh
            if [ $? -ne 0 ]; then
                echo "Unable to connect to EVA ICS repository. Will try again in 30 seconds..."
                sleep 30
                continue
            fi
        fi
        find . -maxdepth 1 -type d -name "eva*" -exec rm -rf {} \;
        tar xzf eva-dist.tgz
        if [ $? -ne 0 ]; then
            echo "Unable to get EVA ICS distribution. Will try again in 30 seconds..."
            sleep 30
            continue
        fi
        find . -maxdepth 1 -type d -name "eva-*" -exec mv -f {} eva \;
        rm -f eva-dist.tgz
        # connect runtime volume if exists
        [ -d /runtime ] && ln -sf /runtime /opt/eva/runtime
        # set layout if defined
        if [ ${layout} ]; then
            sed -i "s/^layout =.*/layout = ${layout}/g" eva/etc/*.ini-dist
        fi
        # turn on debug mode mode
        if [ ${debug} ] || [ ${development_mode} ]; then
            [ ${development_mode} ] && devmode='\ndevelopment = yes' || devmode=
            sed -i "s/^debug =.*/debug = yes${devmode}/g" eva/etc/*.ini-dist
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
        if [ ${auto_install} ]; then
            AUTO_OPTS=--auto
            [ "x${link}" = "x1" ] && LINK_OPTS="--link"
            [ ${mqtt} ] && MQTT_OPTS="--mqtt"
            [ ${product} ] && PRODUCT_OPTS="-p"
        fi
        cd /opt/eva
        rm -rf runtime/*_notify.d runtime/*_remote_*.d
        if [ ${skip_install} ]; then
            echo "Done. Sleeping forever"
            while [ 1 ]; do sleep 8640; done
        fi
        ./easy-setup --force ${AUTO_OPTS} ${MQTT_OPTS} ${mqtt} ${LINK_OPTS} ${PRODUCT_OPTS} ${product}
        result=$?
        if [ ${result} -eq 0 ]; then
            # create install flag
            touch /.installed
            trap _term SIGTERM
            show_logs
        else
            echo "SETUP FAILED. CODE: ${result}"
            while [ 1 ]; do sleep 86400; done
        fi
    fi
done

exit 0
