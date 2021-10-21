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
    runq_sz     int,
    plist_sz    int,
    ldavg_1     float,
    ldavg_5     float,
    ldavg_15    float
"
echo "sar -q 1 5 | grep Average"
sar -q 1 5 | grep Average | awk '{$1="";print $0}' | sed 's/[ ][ ]*/|/g' | sed 's/^|//g' | sed 's/|$//g'

echo "
    cur_user    float,
    nice        float,
    system      float,
    iowait      float,
    steal       float,
    idle        float
"
echo "sar -u 1 5 | grep Average"
sar -u 1 5 | grep Average | awk '{$1="";$2="";print $0}' | sed 's/[ ][ ]*/|/g' | sed 's/^|//g' | sed 's/|$//g'
