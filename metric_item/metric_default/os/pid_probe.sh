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

export METRIC_BASE=`pwd`/../
export METRIC_ITEM=${METRIC_BASE}/metric_item
export METRIC_LIB=${METRIC_BASE}/bin
gphome=`echo $GPHOME`
if [ "${gphome}" == "" ]; then
    echo "FATAL: Could not get \$GPHOME environment variable."
    exit 1
fi
pythonString=`grep -d skip '#!/usr/bin/env python3' ${gphome}/script/*  | wc -l`
if [ ${pythonString} -eq 0 ]; then
    python2 ${METRIC_ITEM}/metric_default/os/probe/pid_probe.py
else
    python3 ${METRIC_ITEM}/metric_default/os/probe/pid_probe.py
fi

