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
    set_time                float,
    start_xact_time         float,
    create_time             float,
    insert_time             float,
    gather_time             float,
    redistribute_min_time   float,
    redistribute_max_time   float,
    scan_tB_min_time        float,
    scan_tB_max_time        float,
    scan_tA_min_time        float,
    scan_tA_max_time        float,
    analyze_total_time      float,
    drop_time               float,
    commit_time             float,
    total_probe_time        float
"
echo "python \${METRIC_ITEM}os/probe/query_probe.py"
python ${METRIC_ITEM}os/probe/query_probe.py
