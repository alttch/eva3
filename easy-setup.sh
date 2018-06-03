#!/bin/bash

FORCE=0
INTERACTIVE=1
DEFAULT_USER=root
INSTALL_UC=0
INSTALL_LM=0
INSTALL_SFA=0
MQTT_HOST=
MQTT_PORT=
MQTT_USER=
MQTT_PASSWORD=
MQTT_PREFIX=
LINK=0

REMOTES='0.0.0.0/0'

VALUE=

REQUIRED="realpath python3 pip3 jq sha256sum mosquitto_pub"

function usage {
    echo
    echo "Usage: easy-setup.sh [--force] [--clear] [--auto] [--local-only] [-u USER]"
        echo "          [--mqtt user:password@host:port/prefix] [-p {uc,lm,sfa,all}] [--link]"
    echo
}

function option_error {
    usage
    exit 2
}

function create_notifier {
    [ "x$MQTT_HOST" = "x" ] && return 0
    local T=$1
    echo "Creating notifier for ${T}"
    ./bin/$T-notifier create -i eva_1 -p mqtt -h ${MQTT_HOST} -P ${MQTT_PORT} -A ${MQTT_USER}:${MQTT_PASSWORD} -y || return 1
    ./bin/$T-notifier subscribe -i eva_1 -p state -v '#' -g '#' || return 1
    ./bin/$T-notifier subscribe -i eva_1 -p log -L 20 || return 1
    return 0
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
        echo -n "$1 (Y/N)? "
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

function askMQTT {
    while [ 1 ]; do
        if [ $INTERACTIVE -eq 1 ]; then
            echo -n "MQTT host, required for linking (use empty value to skip MQTT connection for now): "
            read MQTT_HOST
            if [ "x${MQTT_HOST}"  = "x" ]; then
                return
            fi
            echo -n "MQTT port [1883]: "
            read MQTT_PORT
            [ "x${MQTT_PORT}" = "x" ] && MQTT_PORT=1883
            MQTT_USER=
            while [ 1 ]; do
                echo -n "MQTT user: "
                read MQTT_USER
                [ "x$MQTT_USER" != "x" ]; break
            done
            MQTT_PASSWORD=
            while [ 1 ]; do
                echo -n "MQTT password: "
                read -s MQTT_PASSWORD
                echo
                [ "x$MQTT_PASSWORD" != "x" ]; break
            done
            echo -n "MQTT prefix (empty for the root hive): "
            read MQTT_PREFIX
        else
            if [ "x${MQTT_HOST}"  = "x" ]; then
                return
            fi
        fi
        local s="test"
        [ "x${MQTT_PREFIX}" != "x" ] && local s="${MQTT_PREFIX}/test"
        mosquitto_pub -d -h ${MQTT_HOST} -p ${MQTT_PORT} -u ${MQTT_USER} -P ${MQTT_PASSWORD} -t ${s} -m  passed
        if [ $? -ne 0 ]; then
            if [ ${INTERACTIVE} -ne 1 ]; then
                exit 5
            fi
        else
            return
        fi
    done
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
        --link)
            LINK=1
            shift
        ;;
        --mqtt)
            M="$2"
            MQTT_USER=`echo $M|cut -d@ -f1|cut -d: -f1`
            MQTT_PASSWORD=`echo $M|cut -d@ -f1|cut -d: -f2`
            MQTT_HOST=`echo $M|cut -d@ -f2|cut -d: -f1|cut -d/ -f1`
            MQTT_PORT=`echo $M|cut -d@ -f2 |cut -d/ -f1|cut -d: -f2`
            [ "x$MQTT_PORT" = "x" ] && MQTT_PORT=1883
            [ "x$MQTT_PORT" = "x$MQTT_HOST" ] && MQTT_PORT=1883
            MQTT_PREFIX=`echo $M|cut -d/ -f2`
            shift
            shift
        ;;
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
    --local-only)
            echo "This controller will be installed with local-only key access"
            REMOTES="127.0.0.1"
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

if [ $LINK -eq 1 ] && [ "x$MQTT_HOST" = "x" ]; then
    echo "Linking requested but no MQTT HOST specified"
    option_error
fi

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
            echo "Error: etc/$c already present. Remove configs or use --force option. Use --force --clear to perform absolutely clean install"
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

# ASK SOME QUESTIONS

echo
askYN "Should this controller grant API access for the local instances only"
[ $VALUE == "1" ] && REMOTES="127.0.0.1"

askMQTT

if [ "x$MQTT_HOST" != "x" ]; then
    echo
    askYN "Link controllers together"
    [ $VALUE == "1" ] && LINK=1
fi

echo -n > etc/eva_servers

# INSTALL UC

echo
askYN "Install EVA Universal Controller on this host"
[ $VALUE == "1" ] && INSTALL_UC=1

echo

if [ $INSTALL_UC -eq 1 ]; then
    echo "Installing EVA Universal Controller"
    sh install-uc.sh || exit 1
    echo "UC_ENABLED=yes" >> etc/eva_servers
    echo
    UC_OPKEY=`head -1024 /dev/urandom | sha256sum | awk '{ print $1 }'`
    UC_LM_KEY=`head -1024 /dev/urandom | sha256sum | awk '{ print $1 }'`
    UC_SFA_KEY=`head -1024 /dev/urandom | sha256sum | awk '{ print $1 }'`
    if [ $INTERACTIVE -eq 1 ]; then
        echo "Your UC operator key: ${UC_OPKEY}"
        echo "Your UC integration key for LM PLCs: ${UC_LM_KEY}"
        echo "Your UC integration key for SFA: ${UC_SFA_KEY}"
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
    rm -f etc/uc_apikeys.ini
    cat > etc/uc_apikeys.ini << EOF
[masterkey]
key = ${MASTERKEY}
master = yes
hosts_allow = 127.0.0.1

[operator]
key = ${UC_OPKEY}
sysfunc = yes
groups = #
hosts_allow = 0.0.0.0/0

[lm]
key = ${UC_LM_KEY}
groups = #
allow = cmd
hosts_allow = ${REMOTES}

[sfa]
key = ${UC_SFA_KEY}
groups = #
hosts_allow = ${REMOTES}

EOF
    chmod 600 etc/uc_apikeys.ini
    create_notifier uc || exit 1
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

# INSTALL LM

echo
askYN "Install EVA Logical Manager PLC on this host"
[ $VALUE == "1" ] && INSTALL_LM=1

echo

if [ $INSTALL_LM -eq 1 ]; then
    echo "Installing EVA LM PLC"
    sh install-lm.sh || exit 1
    echo "LM_ENABLED=yes" >> etc/eva_servers
    echo
    LM_OPKEY=`head -1024 /dev/urandom | sha256sum | awk '{ print $1 }'`
    LM_SFA_KEY=`head -1024 /dev/urandom | sha256sum | awk '{ print $1 }'`
    if [ $INTERACTIVE -eq 1 ]; then
        echo "Your LM operator key: ${LM_OPKEY}"
        echo "Your LM integration key for SFA: ${LM_SFA_KEY}"
        echo
    fi
    askUser "Enter the user account to run under (root is recommended for LM PLC only if you are sure)" ${DEFAULT_USER}
    id ${USER} > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "Invalid user: ${USER}"
        exit 2
    fi
    [ ! -f etc/lm.ini ] && cp etc/lm.ini-dist etc/lm.ini
    chmod 644 etc/lm.ini
    echo "Generating lm_apikeys.ini"
    rm -f etc/lm_apikeys.ini
    cat > etc/lm_apikeys.ini << EOF
[masterkey]
key = ${MASTERKEY}
master = yes
hosts_allow = 127.0.0.1

[operator]
key = ${LM_OPKEY}
sysfunc = yes
groups = #
hosts_allow = 0.0.0.0/0

[sfa]
key = ${LM_SFA_KEY}
groups = #
allow = dm_rule_props, dm_rules_list
hosts_allow = ${REMOTES}

EOF
    chmod 600 etc/lm_apikeys.ini
    create_notifier lm || exit 1
    if [ "x$USER" != "xroot" ]; then
        chmod 777 runtime/db
        ./set_run_under_user.sh lm ${USER} || exit 1
    fi
    ./sbin/lm-control start
    sleep 3
    ./bin/lm-cmd test > /dev/null 2>&1
    if [ $? != 0 ]; then
        echo "Unable to test LM"
        ./sbin/eva-control stop
        exit 5
    fi
    if [ $LINK -eq 1 ]; then
        echo "Linking local UC to LM PLC"
        ./bin/lm-cmd append_controller -u http://localhost:8812 -a ${UC_LM_KEY} -m eva_1 -y
        if [ $? != 0 ]; then
            echo "Linking failed!"
            ./sbin/eva-control stop
            exit 5
        fi
    fi
fi

# COMPLETED

if [ $INSTALL_UC -eq 0 ] && [ $INSTALL_LM -eq 0 ] && [ $INSTALL_SFA -eq 0 ]; then
    echo "No products selected, nothing was installed"
    exit 0
fi

echo "Setup completed!"

echo

echo "MASTERKEY: ${MASTERKEY}"

echo

if [ $INSTALL_UC -eq 1 ]; then
    echo "UC_OPERATOR_KEY: ${UC_OPKEY}"
    echo "UC_LM_KEY: ${UC_LM_KEY}"
    echo "UC_SFA_KEY: ${UC_SFA_KEY}"
    echo
fi

if [ $INSTALL_LM -eq 1 ]; then
    echo "LM_OPERATOR_KEY: ${LM_OPKEY}"
    echo "LM_SFA_KEY: ${LM_SFA_KEY}"
    echo
fi

exit 0
