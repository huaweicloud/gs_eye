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
    dev        text,
    tps        float,
    rd_sec     float,
    wr_sec     float,
    avgrq_sz   float,
    avgqu_sz   float,
    await      float,
    svctm      float,
    util       float
"
echo "sar -dp 1 5 | grep Average | grep -v tps"
sar -dp 1 5 | grep Average | grep -v tps | awk '{$1="";print $0}' | sed 's/[ ][ ]*/|/g' | sed 's/^|//g' | sed 's/|$//g'

echo "
    dev               text,
    inodes            bigint,
    iused             bigint,
    ifree             bigint,
    iused_percentage  text,
    mount_on          text
"
echo "df -i | grep -v Filesystem"
df -i | grep -v Filesystem | sed 's/[ ][ ]*/|/g' | sed 's/^|//g' | sed 's/|$//g'

echo "
    dev               text,
    blocks_1k         bigint,
    used              bigint,
    available         bigint,
    used_percentage   varchar(10),
    mount_on          text
"
echo "df | grep -v Filesystem"
df | grep -v Filesystem | sed 's/[ ][ ]*/|/g' | sed 's/^|//g' | sed 's/|$//g'

echo "
    opentime_us   int,
    writetime_us  int,
    fsynctime_us  int,
    lseektime_us  int,
    readtime_us   int,
    closetime_us  int
"
echo "python3 \${METRIC_ITEM}os/probe/io_probe.py"
python3 ${METRIC_ITEM}os/probe/io_probe.py
