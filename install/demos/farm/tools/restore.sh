#!/bin/sh

eva-shell -R --exec-batch=stdin <<EOF
server stop
backup restore --runtime setup
backup restore --ui setup
server start
EOF
