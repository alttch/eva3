#!/bin/bash

/opt/eva/sbin/eva-control stop
killall tail
kill `cat /var/run/start.pid`
rm -f /var/run/start.pid
