#!/bin/bash

[ -f /var/run/start.pid ] && kill `cat /var/run/start.pid` || killall bash
