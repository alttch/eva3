#!/bin/bash

FORCE=0
INTERACTIVE=1
DEFAULT_USER=root
INSTALL_UC=0
INSTALL_LM=0
INSTALL_SFA=0

VALUE=

REQUIRED="realpath python3 pip3 jq sha256sum mosquitto_pub sqlite3"

function usage {
    echo
    echo "Usage: easy-install.sh [--force] [--clear] [--auto] [-u USER] [-p {uc,lm,sfa,all}]"
    echo
}

function option_error {
    usage
    exit 2
}

function check_required_exec {
    local p=$1
    echo -n "Checking $p => "
    RESULT=`which $p 2>&1`
    if [ $? != 0 ]; then
        echo "Missing! Please install"
        return 1
    fi
    echo ${RESULT}
    return 0
}

function askYN {
    if [ $INTERACTIVE -ne 1 ]; then
        VALUE=2
        return
    fi
    local v=
    while [ "x$v" == "x" ]; do
        echo -n "$1 "
        read a
        case $a in
            y|Y)
                v=1
            ;;
            n|N)
                v=0
            ;;
        esac
    done
    VALUE=$v
}

function askUser {
    USER=$2
    [ $INTERACTIVE -ne 1 ] && return
    while [ 1 ]; do
        echo -n "$1 [$2]: "
        read u
        if [ "x$u" == "x" ]; then
            u=$2
        fi
        id $u > dev/null 2>&1
        if [ $? -eq 0 ]; then
            USER=$u
            return
        fi
        echo "Invalid user: $u"
    done
}

while [[ $# -gt 0 ]]
do
    key="$1"
    case $key in
        -u)
            DEFAULT_USER="$2"
            shift
            shift
        ;;
        -p)
            case $2 in
                uc|UC)
                    INSTALL_UC=1
                ;;
                lm|LM)
                    INSTALL_LM=1
                ;;
                sfa|SFA)
                    INSTALL_SFA=1
                ;;
                all)
                    INSTALL_UC=1
                    INSTALL_LM=1
                    INSTALL_SFA=1
                ;;
                *)
                    option_error
                ;;
            esac
            shift
            shift
        ;;
        --force)
            echo "Warning: using force installation, stopping EVA and removing old configs"
            FORCE=1
            ./sbin/eva-control stop
            shift
        ;;
        --clear)
            echo "Warning: asked to clear runtime. Doing"
            ./sbin/eva-control stop
            rm -rf runtime/*
            shift
        ;;
        -h|--help)
            usage
            exit 99
        ;;
        --auto)
            INTERACTIVE=0
            echo "Will perform automatic install"
            shift
        ;;
        *)
            option_error
        ;;
    esac
done

e=0
for r in ${REQUIRED}; do
    check_required_exec $r || e=1
done
[ $e -ne 0 ] && exit 1


D=`realpath $0`
cd `dirname ${D}`

echo


if [ $FORCE -eq 0 ]; then
    CFGS="eva_servers uc_apikeys.ini lm_apikeys.ini sfa_apikeys.ini"
    for c in ${CFGS}; do
        if [ -f etc/$c ]; then
            echo "Error: etc/$c already present. Remove configs or use --force option"
            exit 2
        fi
    done
fi

MASTERKEY=`head -1024 /dev/urandom | sha256sum | awk '{ print $1 }'`

if [ $INTERACTIVE -eq 1 ]; then
    echo
    echo "Your new masterkey: ${MASTERKEY}"
    echo
fi

# INSTALL UC

echo
askYN "Install EVA Universal Controller on this host(Y/N)?"
[ $VALUE == "1" ] && INSTALL_UC=1

echo

echo -n > etc/eva_servers

if [ $INSTALL_UC -eq 1 ]; then
    echo "Installing EVA Universal Controller"
    sh install-uc.sh
    echo "UC_ENABLED=yes" >> etc/eva_servers
    echo
    UC_OPKEY=`head -1024 /dev/urandom | sha256sum | awk '{ print $1 }'`
    if [ $INTERACTIVE -eq 1 ]; then
        echo "Your UC operator key: ${UC_OPKEY}"
        echo
    fi
    askUser "Enter the user account to run under (root is recommended for UC)" ${DEFAULT_USER}
    id ${USER} > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "Invalid user: ${USER}"
        exit 2
    fi
    [ ! -f etc/uc.ini ] && cp etc/uc.ini-dist etc/uc.ini
    chmod 644 etc/uc.ini
    echo "Generating uc_apikeys.ini"
    cat > etc/uc_apikeys.ini << EOF
[masterkey]
key = ${MASTERKEY}
master = yes
hosts_allow = 127.0.0.1

[operator]
key = ${UC_OPKEY}
sysfunc = yes
groups = #
allow = cmd
hosts_allow = 0.0.0.0/0

EOF
    chown ${USER} etc/uc_apikeys.ini
    chmod 600 etc/uc_apikeys.ini
    if [ "x$USER" != "xroot" ]; then
        chmod 777 runtime/db
        ./set_run_under_user.sh uc ${USER} || exit 1
    fi
    ./sbin/uc-control start
    sleep 3
    ./bin/uc-cmd test > /dev/null 2>&1
    if [ $? != 0 ]; then
        echo "Unable to test UC"
        ./sbin/eva-control stop
        exit 5
    fi
fi

if [ $INSTALL_UC -eq 0 ] && [ $INSTALL_LM -eq 0 ] && [ $INSTALL_SFA -eq 0 ]; then
    echo "No products selected, nothing was installed"
    exit 0
fi

echo "Install completed!"

echo

echo "MASTERKEY: ${MASTERKEY}"

if [ $INSTALL_UC -eq 1 ]; then
    echo "UC_OPERATOR_KEY: ${UC_OPKEY}"
fi

exit 0
