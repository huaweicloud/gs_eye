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
    used_count     int,
    pid            int
"
echo "lsof | awk '{print \$2}' | sort | uniq -c | sort -nr | sed -n '1,20p'"
lsof | awk '{print $2}' | sort | uniq -c | sort -nr | sed -n '1,20p' | awk '{print $1"|"$2}'

echo "
    deleted_count  int
"
echo "lsof | grep deleted | wc -l"
lsof | grep deleted | wc -l
