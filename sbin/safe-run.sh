#!/usr/bin/env bash

( kill -0 `cat $1` ) > /dev/null 2>&1
if [ "x$?" = "x0" ]; then
    (>&2 echo "Process already active")
    exit 11
fi
echo $$ > $1
while [ 1 ]; do
    $2 $3 $4 $5 $6 $7 $8 $9 > /dev/null
done
