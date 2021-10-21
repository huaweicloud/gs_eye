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
    kbmemfree     bigint,
    kbmemused     bigint,
    memused       float,
    kbbuffers     bigint,
    kbcached      bigint,
    kbcommit      bigint,
    commit        float
"
echo "sar -r 1 5 | grep Average"
sar -r 1 5 | grep Average | awk '{$1="";print $0}' | sed 's/[ ][ ]*/|/g' | sed 's/^|//g' | sed 's/|$//g'

echo "
    pgpgin_s      float,
    pgpgout_s     float,
    fault_s       float,
    majflt_s      float,
    pgfree_s      float,
    pgscank_s     float,
    pgscand_s     float,
    pgsteal_s     float,
    vmeff         float
"
echo "sar -B 1 5 | grep Average"
sar -B 1 5 | grep Average | awk '{$1="";print $0}' | sed 's/[ ][ ]*/|/g' | sed 's/^|//g' | sed 's/|$//g'

echo "
    MemTotal           int,
    MemFree            int,
    Buffers            int,
    Cached             int,
    SwapCached         int,
    Active             int,
    Inactive           int,
    Active_anon        int,
    Inactive_anon      int,
    Active_file        int,
    Inactive_file      int,
    Unevictable        int,
    Mlocked            int,
    SwapTotal          int,
    SwapFree           int,
    Dirty              int,
    Writeback          int,
    AnonPages          int,
    Mapped             int,
    Shmem              int,
    Slab               int,
    SReclaimable       int,
    SUnreclaim         int,
    KernelStack        int,
    PageTables         int,
    NFS_Unstable       int,
    Bounce             int,
    WritebackTmp       int,
    CommitLimit        int,
    Committed_AS       int,
    VmallocTotal       bigint,
    VmallocUsed        int,
    VmallocChunk       bigint,
    HardwareCorrupted  int,
    AnonHugePages      int,
    HugePages_Total    int,
    HugePages_Free     int,
    HugePages_Rsvd     int,
    HugePages_Surp     int,
    Hugepagesize       int,
    DirectMap4k        int,
    DirectMap2M        int,
    DirectMap1G        int
"
echo "cat /proc/meminfo | awk '{print \$2}'"
cat /proc/meminfo | awk '{print $2}'| tr "\n" "|" | sed -e 's/|$/\n/'

echo "
    node        text,
    zones       text,
    dev         text,
    page1       int,
    page2       int,
    page4       int,
    page8       int,
    page16      int,
    page32      int,
    page64      int,
    page128     int,
    page256     int,
    page512     int,
    page1024    int
"
echo "cat /proc/buddyinfo"
cat /proc/buddyinfo | awk '{$1="";print $0}' | sed 's/[ ][ ]*/|/g' | sed 's/^|//g' | sed 's/|$//g'

echo "
    name          text,
    active_objs   int,
    num_objs      int,
    objsize       int,
    objperslab    int,
    pagesperslab  int,
    tunables      text,
    limits        int,
    batchcount    int,
    sharedfactor  int,
    slabdata      text,
    active_slabs  int,
    num_slabs     int,
    sharedavail   int
"
echo "cat /proc/slabinfo | sort -rnk 3 | sed -n '1,20p'"
cat /proc/slabinfo | sort -rnk 3 | sed -n '1,20p' | sed 's/://g' | sed 's/[ ][ ]*/|/g' | sed 's/^|//g' | sed 's/|$//g'
