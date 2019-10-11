#!/usr/bin/env bash

trap '' HUP

echo $$ > $1
while [ 1 ]; do
    $2 $3 $4 $5 $6 $7 $8 $9 > /dev/null
done
