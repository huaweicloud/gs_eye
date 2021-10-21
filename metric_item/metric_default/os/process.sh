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

echo "
    dentunusd    int,
    file_nr      int,
    inode_nr     int,
    pty_nr       int
"
echo "sar -v 1 5 | grep Average"
sar -v 1 5 | grep Average | awk '{$1="";print $0}' | sed 's/[ ][ ]*/|/g' | sed 's/^|//g' | sed 's/|$//g'

echo "
    counts       int
"
echo "ps -ef | grep defunct | grep -v grep | wc -l"
ps -ef | grep defunct | grep -v grep | wc -l

echo "
    username     text,
    pid          int,
    cpu          float,
    mem          float,
    vsz          int,
    rss          int,
    tty          text,
    stat         text,
    start        text,
    time         text,
    command      text
"
echo "ps aux --sort -pcpu | sed -n '2,21p'"
ps aux --sort -pcpu | sed -n '2,21p' | awk '{out=$1; for(i=2;i<=11;i++){out=out"|"$i}; for(i=12;i<=NF;i++){out=out" "$i}; print out}'

echo "
    username     text,
    pid          int,
    cpu          float,
    mem          float,
    vsz          int,
    rss          int,
    tty          text,
    stat         text,
    start        text,
    time         text,
    command      text
"
echo "ps aux --sort -pmem | sed -n '2,21p'"
ps aux --sort -pmem | sed -n '2,21p' | awk '{out=$1; for(i=2;i<=11;i++){out=out"|"$i}; for(i=12;i<=NF;i++){out=out" "$i}; print out}'

echo "
    nodename         text,
    pid              int,
    command          text,
    state            char,
    ppid             int,
    min_flt          int,
    cmin_flt         int,
    maj_flt          int,
    cmaj_flt         int,
    utime            int,
    stime            int,
    cutime           int,
    cstime           int,
    priority         int,
    nice             int,
    num_threads      int,
    it_real_value    int,
    start_time       bigint,
    pid_vsize        bigint,
    rss              int,
    rsslim           bigint,
    task_cpu         int
"
echo "python \${METRIC_ITEM}os/probe/pid_probe.py"
python ${METRIC_ITEM}os/probe/pid_probe.py | awk '{out=$1; for(i=2;i<6;i++){out=out"|"$i}; for(i=11;i<27;i++){out=out"|"$i}; print out"|"$40}'
