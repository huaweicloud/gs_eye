#!/usr/bin/env python3
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

try:
    import os
    import sys
    sys.path.append(os.environ.get("METRIC_LIB"))
    import lib.common.cluster.gs_instance_manager as dbinfo
except Exception as e:
    sys.exit("FATAL: Unable to import module: %s" % e)

clusterInfo = dbinfo.getDbInfo(os.environ.get("USER"))
for dbNode in clusterInfo.dbNodes:
    if dbNode.name == clusterInfo.hostname:
        for cn in dbNode.coordinators:
            print("cn_%d %s" % (cn.instanceId, cn.getInstanceStat()))
        for dn in dbNode.datanodes:
            print("dn_%d %s" % (dn.instanceId, dn.getInstanceStat()))
