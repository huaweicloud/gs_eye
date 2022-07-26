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

#TODO: write file to every disk
try:
    import os
    import sys
    import time
except Exception as e:
    sys.exit("FATAL: Unable to import module: %s" % e)


file = os.path.dirname(os.path.realpath(__file__)) + "/foo.txt"

# open file
otime = time.time()
fd = os.open(file, os.O_RDWR | os.O_CREAT)

# write character into file
wtime = time.time()
os.write(fd, "This is test")

# fsync()
ftime = time.time()
os.fsync(fd)

# read file
ltime = time.time()
os.lseek(fd, 0, 0)
rtime = time.time()
str = os.read(fd, 100)

# truncate file
ttime = time.time()
os.ftruncate(fd, 0)

# close file
ctime = time.time()
os.close(fd)

etime = time.time()

opentime_us = int((wtime - otime) * 1000000)
writetime_us = int((ftime - wtime) * 1000000)
fsynctime_us = int((ltime - ftime) * 1000000)
lseektime_us = int((rtime - ltime) * 1000000)
readtime_us = int((ttime - rtime) * 1000000)
closetime_us = int((etime - ctime) * 1000000)

print("%d|%d|%d|%d|%d|%d" % (opentime_us, writetime_us, fsynctime_us, lseektime_us, readtime_us, closetime_us))
