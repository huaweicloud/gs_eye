#!/usr/bin/env python
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
    import commands
    sys.path.append(os.environ.get("METRIC_LIB"))
    import lib.common.cluster.gs_instance_manager as dbinfo
except Exception as e:
    sys.exit("FATAL: Unable to import module: %s" % e)


query = "\\timing\nset statement_timeout = '5min';\nstart transaction;\n" \
        "create table probe_table(a int, b int, c varchar(100));\n" \
        "insert into probe_table values(generate_series(1, 20), generate_series(10, 30), 'come on baby!');\n" \
        "explain analyze select count(*) from probe_table a inner join probe_table b on a.a = b.b;\n" \
        "drop table probe_table;\ncommit;\n"

file = os.path.dirname(os.path.realpath(__file__)) + "/queryprobe.sql"
if not os.path.isfile(file):
    with open(file, "w") as f:
        f.write(query)

clusterInfo = dbinfo.getDbInfo(os.environ.get("GAUSS_USER"))
command = "gsql -d postgres -p %d -f %s" % (clusterInfo.coordinator.port, file)
status, output = commands.getstatusoutput(command)
if status != 0 or 'ERROR' in output:
    print("Probe is not running correctly, detail: %s" % output)
    sys.exit(1)

result = []
for line in output.split('\n'):
    if "Time" in line:
        result.append(line.split()[1])
    elif "GATHER" in line:
        result.append(line.split('|')[2].strip())
    elif "REDISTRIBUTE" in line or "Seq Scan" in line:
        result += line.split('|')[2].strip()[1:-1].split(',')
    elif "total time" in line:
        result.append(line.split()[2])
print("|".join(result))
