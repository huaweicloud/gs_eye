#! /bin/sh
#######################################################################
# Portions Copyright (c): 2021-2025, Huawei Tech. Co., Ltd.
#
# gs_eye is licensed under Mulan PSL v2.
#  You can use this software according to the terms and conditions of the Mulan PSL v2.
#  You may obtain a copy of Mulan PSL v2 at:
#
#           http://license.coscl.org.cn/MulanPSL2
#
#  THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
#  EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
#  MERCHANTABILITY OR FIT FOR A PARTICULA# R PURPOSE.
#  See the Mulan PSL v2 for more details.
#######################################################################

source /opt/huawei/Bigdata/mppdb/.mppdbgs_profile
MET_HOME="/home/omm/gs_metric"

BIN_HOME="${MET_HOME}/bin"
AGENT_BIN="gs_metricagent.py"
SERVER_BIN="gs_archive.py"
RUNMODE="agent"
MET_BIN=""
MET_OPT="-u omm"

START_HOME="${MET_HOME}"
START_BIN="gs_metric.sh"

function usage() {
    cat <<- EOF

Usage:
  ./${START_BIN} help
  Example:
    ./${START_BIN} [[start | stop | status ] [ --server | --agent]] [ install | version | help ]

General options:
    main command:
    start                     Start the scripts in the cluster.
    stop                      Stop the scripts in the cluster.
    status                    Show the script status in the cluster.
        sub options for main command
        --server              Start metric import server to analyze data into maintainace database.
        --agent               Start metric agent client to collect metric from online cluster.
    
    maintain command:
    version                   Show version information.
    help                      Show help information for this utility.
EOF
    exit 0
}

function install() {
    for host in ${1}; do
        exist=`ssh -q ${host} "if [ -d ${MET_HOME} ]; then echo 1; else echo 0; fi"`
        if [ "$?" != 0 ]; then
            echo "FATAL: Could not check the path ${MET_HOME} in host ${1}"
            return 5
        elif [ "${exist}" == "0" ]; then
            ssh -q ${host} "mkdir -p ${MET_HOME}"
        fi
        scp -q -r ${MET_HOME}/* ${host}:${MET_HOME}
        if [ "$?" != 0 ]; then
            echo "FATAL: Could not make the path ${MET_HOME} in host ${1}"
            return 6
        else
            echo "Success installed in host: $host"
        fi
    done
}

function check_script() {
    exist=`ssh -q ${1} "if [ -d ${MET_HOME} ]; then echo 1; else echo 0; fi"`
    if [ "$?" != 0 ]; then
        echo "FATAL: Could not check the path ${MET_HOME} in host ${1}"
        return 5
    elif [ "${exist}" == "0" ]; then
        ssh -q ${1} "mkdir -p ${MET_HOME}"
        if [ "$?" != 0 ]; then
            echo "FATAL: Could not make the path ${MET_HOME} in host ${1}"
            return 6
        fi
    fi
    
    exist=`ssh -q ${1} "if [ -d ${BIN_HOME} ]; then echo 1; else echo 0; fi"`
    if [ "$?" != 0 ]; then
        echo "FATAL: Could not check the path ${BIN_HOME} in host ${1}"
        return 7
    elif [ "${exist}" == "0" ]; then
        scp -q -r ${MET_HOME}/* ${1}:${MET_HOME}
        if [ "$?" != 0 ]; then
            echo "FATAL: Could not scp the files ${BIN_HOME} to host ${1}"
            return 8
        fi
    else
        mver=`${BIN_HOME}/${MET_BIN} -v 2>&1`
        rver=`ssh -q ${1} "${BIN_HOME}/${MET_BIN} -v 2>&1"`
        if [ "${rver}" != "${mver}" ]; then
            scp -q -r ${MET_HOME}/* ${1}:${MET_HOME}
            if [ "$?" != "0" ]; then
                echo "FATAL: Could not update the script ${MET_BIN} in host ${1}"
                return 9
            fi
        fi
    fi
    
    return 0
}

function start_daemon() {
    ${START_HOME}/${START_BIN} run --$RUNMODE
    if [ "$?" != "0" ]; then
        echo "FATAL: Could not start in host ${HOSTNAME}"
    else
        echo "Successfully add a timed task in host ${HOSTNAME}"
    fi

    if [ $RUNMODE == "server" ]; then
        return
    fi
    
    for host in ${1}; do
        check_script ${host}
        if [ "$?" == "0" ]; then
            ssh -q ${host} "sh ${START_HOME}/${START_BIN} run --$RUNMODE"
            if [ "$?" != "0" ]; then
                echo "FATAL: Could not add a timed task in host ${host}"
            else
                echo "Successfully add a timed task in host ${host}"
            fi
        fi
    done
}

function stop_daemon() {
    ${START_HOME}/${START_BIN} stop_local --$RUNMODE
    
    if [ $RUNMODE == "server" ]; then
        return
    fi
    
    for host in ${1}; do
        ssh -q ${host} "${START_HOME}/${START_BIN} stop_local --$RUNMODE"
    done
}

function run() {
    if [ -f "${MET_HOME}/${RUNMODE}.pid" ]; then
        pid=`cat ${MET_HOME}/${RUNMODE}.pid`
        if [ -f "/proc/${pid}/cmdline" ]; then
            if [[ `cat /proc/${pid}/cmdline` == *"${BIN_HOME}/${MET_BIN}"* ]]; then
                echo "${MET_BIN} is already in progress"
                exit 0
            fi
        fi
        # echo "ERROR: Wrong ${RUNMODE}.pid file, maybe ${MET_BIN} process is abnormal"
    fi
    
    pid=`ps ux | grep "${MET_BIN}" | grep -v -E 'grep|sh|source' | awk '{print $2}'`
    if [ "${pid}" != "" ]; then
        echo "Warning: ${RUNMODE}.pid file is missing, but ${MET_BIN} is already in progress"
    else
        cd ${BIN_HOME}
        nohup python ${BIN_HOME}/${MET_BIN} ${MET_OPT} 1>${GAUSSLOG}/gs_metricdata/runlog/start.log 2>&1 &
        sleep 2
        pid=`ps ux | grep "${MET_BIN}" | grep -v -E 'grep|sh|source' | awk '{print $2}'`
        if [ "${pid}" != "" ]; then
            echo "${MET_BIN} started successfully"
        else
            echo "${MET_BIN} started failed"
            return 1
        fi
    fi
    echo "${pid}" > ${MET_HOME}/${RUNMODE}.pid
}

function stop() {
    if [ -f "${MET_HOME}/${RUNMODE}.pid" ]; then
        pid=`cat ${MET_HOME}/${RUNMODE}.pid`
        if [ -f "/proc/${pid}/cmdline" ]; then
            if [[ `cat /proc/${pid}/cmdline` != *"${BIN_HOME}/${MET_BIN}"* ]]; then
                pid=`ps ux | grep "${MET_BIN}" | grep -v -E 'grep|sh|source' | awk '{print $2}'`
            fi
        fi
        rm ${MET_HOME}/${RUNMODE}.pid
    else
        pid=`ps ux | grep "${MET_BIN}" | grep -v -E 'grep|sh|source' | awk '{print $2}'`
    fi
    
    if [ "${pid}" != "" ]; then
        kill -9 ${pid}
        if [ "$?" != "0" ]; then
            echo "FATAL: Could not kill process ${pid} in host ${HOSTNAME}"
        else
            echo "Successfully kill process ${pid} in host ${HOSTNAME}"
        fi
    else
        echo "Warning: No process found or killed in host ${HOSTNAME}"
    fi
}

function status() {
    proc=`ps ux | grep "${MET_BIN}" | grep -v -E 'grep|sh|source'`
    if [ "${proc}" == "" ]; then
        echo "Checking for daemon ${MET_BIN} in host ${HOSTNAME}:               unused"
    else
        echo "Checking for daemon ${MET_BIN} in host ${HOSTNAME}:               running"
    fi
    
    if [ $RUNMODE == "server" ]; then
        return
    fi

    for host in ${1}; do
        proc=`ssh -q ${host} "ps ux | grep \"${MET_BIN}\" | grep -v -E 'grep|sh|source'"`
        if [ "${proc}" == "" ]; then
            echo "Checking for daemon ${MET_BIN} in host ${host}:               unused"
        else
            echo "Checking for daemon ${MET_BIN} in host ${host}:               running"
        fi
    done
}

function version() {
    ${BIN_HOME}/${MET_BIN} -v 2>&1
}

function initmode() {
    case "$1" in
        --server)
        MET_BIN=$SERVER_BIN
        RUNMODE="server"
        ;;
        --agent)
        MET_BIN=$AGENT_BIN
        RUNMODE="agent"
        ;;
        *)
        usage
        ;;
    esac
}

function main() {
    environ=`echo $MPPDB_ENV_SEPARATE_PATH`
    if [ "${environ}" == "" ]; then
        echo "FATAL: Could not get environment variable"
        exit 1
    fi
    
    if [ ! -f "${START_HOME}/${START_BIN}" ]; then
        echo "FATAL: Could not find ${START_BIN} in ${START_HOME}"
        exit 2
    fi
    
    cluster=`cm_ctl view | grep nodeName | awk -F ':' '{print $2}' | grep -v "${HOSTNAME}"`
    if [ "$?" != "0" -o "${cluster}" == "" ]; then
        echo "FATAL: Could not get the cluster information"
        exit 4
    fi
    
    case "$1" in
        start)
            initmode "$2"
            start_daemon "${cluster}" "${environ}"
            ;;
        stop)
            initmode "$2"
            stop_daemon "${cluster}"
            ;;
        run)
            initmode "$2"
            run
            ;;
        stop_local)
            initmode "$2"
            stop
            ;;
        status)
            initmode "$2"
            status "${cluster}"
            ;;
        version)
            version
            ;;
        install)
            install "${cluster}"
            ;;
        *)
            usage
            ;;
    esac
}

main "$@"
