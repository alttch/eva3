#!/bin/sh

CONTAINERS="farm_uc1 farm_uc2 farm_lm1 farm_sfa"

for c in ${CONTAINERS}; do
    docker exec -t ${c} /tools/restore.sh
done
