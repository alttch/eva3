#!/bin/bash

PRODUCT=$1
USER=$2

function usage {
    echo "Usage: set-run-under-user.sh <product> <user>"
    echo
    echo " where product can be uc, lm, sfa or all"
}


function exec_cmd {
    echo $*
    $*
}


function check_dir_access {
    local d=$1
    local u=$2
    rm -f ${d}/.access_check
    su ${u} -c "touch ${d}/.access_check" > /dev/null 2>&1
    if [ ! -f ${d}/.access_check ]; then
        echo "Please grant an access for user ${u} to ${d} folder"
        return 1
    fi
    rm -f ${d}/.access_check
    return 0
}

function check_file_access {
    local f=$1
    local u=$2
    su ${u} -c "cat ${f}" > /dev/null 2>&1
    if [ $? != 0 ]; then
        echo "Please grant (read only) permissions for ${u} to ${f}"
        return 1
    fi
    return 0
}


function set_runtime_permissions {
    local p=$1
    local u=$2
    if [ -f var/${p}.pid ]; then
        echo "var/${p}.pid exist, is ${p} running? aborting"
        return 1
    fi
    if [ -f var/${p}_safe.pid ]; then
        echo "var/${p}_safe.pid exist, is ${p} running? aborting"
        return 1
    fi
    exec_cmd chown -R ${u} runtime/${p}*
    exec_cmd chown -R ${u} runtime/db/${p}*.db
    exec_cmd chown ${u} etc/${p}_apikeys.ini
    exec_cmd chmod 600 etc/${p}_apikeys.ini
    [ -f log/${p}.log ] && mv -f log/${p}.log log/${p}.log.bak
    return 0
}

if [ "x${USER}" == "x" ]; then
    usage
    exit 2
fi

id ${USER} > /dev/null 2>&1

if [ $? != 0 ]; then
    echo "Invalid user: ${USER}"
    echo
    usage
    exit 1
fi

function set_user {
    local p=$1
    local u=$2
    [ -f etc/eva_servers ] || touch etc/eva_servers
    grep "${p}_USER=" etc/eva_servers > /dev/null 2>&1
    if [ $? != 0 ]; then
        echo "${p}_USER=$u" >> etc/eva_servers
    else
        sed -i "s/\(${p}_USER=\).*/\\1${u}/g" etc/eva_servers
    fi
    echo
    echo "${p} is set up to run under user ${u}"
    echo "!! Make sure to set ${p} API ports to non-privileged (>1024)"
    echo
}

check_dir_access log ${USER} || exit 1
check_dir_access var ${USER} || exit 1
check_dir_access runtime/db ${USER} || exit 1

D=`realpath $0`
cd `dirname ${D}` || exit 4

case ${PRODUCT} in
uc)
    check_file_access etc/${PRODUCT}.ini ${USER} || exit 1
    set_runtime_permissions uc ${USER} || exit 1
    set_user UC ${USER}
    ;;
lm)
    check_file_access etc/${PRODUCT}.ini ${USER} || exit 1
    set_runtime_permissions lm ${USER} || exit 1
    set_user LM ${USER}
    ;;
sfa)
    check_file_access etc/${PRODUCT}.ini ${USER} || exit 1
    set_runtime_permissions sfa ${USER} || exit 1
    set_user SFA ${USER}
    ;;
all)
    $0 uc ${USER} || exit 1
    $0 lm ${USER} || exit 1
    $0 sfa ${USER} || exit 1
    ;;
*)
    usage
    exit 1
esac
exit 0
