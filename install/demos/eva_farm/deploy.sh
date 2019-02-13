#!/bin/sh

CONTAINERS="farm_uc1:10.27.11.101:8812 farm_uc2:10.27.11.102:8812 farm_lm1:10.27.11.111:8817 farm_sfa:10.27.11.199:8828"


MASTERKEY=`grep MASTERKEY docker-compose.yml |head -1|awk -F= '{ print $2 }'`

echo "Deploying EVA ICS cluster"

docker-compose up -d || exit 1

echo
echo -n Waiting for cluster startup

OK=0
while [ ${OK} -ne 1 ]; do
    OK=1
    for c in ${CONTAINERS}; do
        a=`echo ${c}| cut -d: -f2-`
        curl -m3 -sd "k=${MASTERKEY}" http://${a}/sys-api/test|grep '"result": "OK"' > /dev/null 2>&1
        if [ $? -ne 0 ]; then
            sleep 1
            OK=0
            echo -n .
            break
        fi
    done
done

echo
echo "Deploying EVA ICS configuration"

for c in ${CONTAINERS}; do
    cn=`echo ${c} | cut -d: -f1`
    docker exec -t eva_${cn} /tools/restore.sh || exit 1
done

echo
echo "Verifying"
for c in ${CONTAINERS}; do
    cn=`echo ${c} | cut -d: -f1`
    a=`echo ${c}| cut -d: -f2-`
    echo -n "${cn}: "
    curl -m3 -sd "k=${MASTERKEY}" http://${a}/sys-api/test|grep '"result": "OK"' > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        docker exec -t eva_${cn} /tools/restart.sh > /dev/null 2>&1
        if [ $? -ne 0 ]; then
            echo
            echo "Unable to restart EVA ICS node, container: eva_${cn}"
            exit 2
        fi
        curl -m3 -sd "k=${MASTERKEY}" http://${a}/sys-api/test|grep '"result": "OK"' > /dev/null 2>&1
        if [ $? -ne 0 ]; then
            echo "FAILED!"
            exit 2
        fi
    fi
    echo "OK"
done

echo
echo "Deployment completed"
echo
echo "Open http://localhost:8828/ in web browser to enter UI, or execute"
echo
echo "  docker exec -it `grep "container_name:.*sfa" docker-compose.yml |awk '{ print $2 }'` eva-shell"
echo
echo "to run SFA CLI"
echo
