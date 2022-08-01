#!/usr/bin/env python3
# -*- coding:utf-8 -*-
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
#######################################################################
# File: gs_agent_watcher.py
# Description: gs_agent_watcher is used to monitor the disk space occupied by data collected
#              by the agent every hour.
# Function: When the data directory of the agent occupies more than 10 GB of disk space,
#           or the disk usage reaches 80%, or the inode usage reaches 80%, 
#           the agent process will clean the old metirc data, if get metric data size failed,
#           or something like that, the agent process is killed by itself.
# 
# Variable:
#     DISK_USED: threshold of disk usage.
#     DISK_USED_PERCENT: percent of disk/inode usage.
#######################################################################

import os
import sys
import time
import datetime
sys.path.append(os.path.dirname(__file__))
if os.getenv('GPHOME'):
    sys.path.remove(os.path.join(os.getenv('GPHOME'), 'lib'))
import sched
import lib.common.CommonCommand as common
from lib.common import gs_logmanager as logmgr

LOG_MODULE = 'watcher'
# The value of "du" is rounded up. If DISK_USED is 11, the disk usage threshold is 10.
DISK_USED = 11
# The percent of disk usage is 80.
DISK_USED_PERCENT = 80
scheduler = sched.scheduler(time.time, time.sleep)


def check_used_value(data_path):
    """
    function: get the size of data path and check whether the threshold is exceeded.
    input: the path of data directory.
    return: bool
    """
    cmd = "du -s -B GB %s |awk -F 'GB' '{print $1}'" % data_path
    status, output = common.runShellCommand(cmd)
    if status != 0:
        logmgr.record(LOG_MODULE, "Failed get disk used. Result:%s" % output)
        return 2
    if output and int(output.strip()) >= DISK_USED:
        logmgr.record(LOG_MODULE, "Disk used %sGB more than %sGB. Result:%s" % (output.strip(), DISK_USED, output))
        return 1
    return 0


def check_space_used_percent(data_path):
    """
    function: get the used percent of data path and check whether the threshold is exceeded.
    input: the path of data directory.
    return: bool
    """
    cmd = "df -h %s | grep -v Mounted | awk '{print $5}'" % data_path
    status, output = common.runShellCommand(cmd)
    if status != 0:
        logmgr.record(LOG_MODULE, "Failed get disk space used. Result:%s" % output)
        return 2
    if output.endswith('%') and int(output[:-1]) > DISK_USED_PERCENT:
        logmgr.record(LOG_MODULE, "Disk space used percent more than %s. Result:%s" % (DISK_USED_PERCENT, output))
        return 1
    return 0


def check_inode_used_percent(data_path):
    """
    function: get the used percent of data path and check whether the threshold is exceeded.
    input: the path of data directory.
    return: bool
    """
    cmd = "df -i %s | grep -v Mounted | awk '{print $5}'" % data_path
    status, output = common.runShellCommand(cmd)
    if status != 0:
        logmgr.record(LOG_MODULE, "Failed get disk inode used. Result:%s" % output)
        return 2
    if output.endswith('%') and int(output[:-1]) > DISK_USED_PERCENT:
        logmgr.record(LOG_MODULE, "Disk inode used percent more than %s. Result:%s" % (DISK_USED_PERCENT, output))
        return 1
    return 0


def check_used(data_path):
    """
    function: analyse data_path used result
    return:
         0, means check passed, do nothing;
         1, means space or inode or used is over threshold, clean data files;
         2, means shell command failed, kill gs_metricagent process.
    """
    used = check_used_value(data_path)
    space = check_space_used_percent(data_path)
    inode = check_inode_used_percent(data_path)
    if used == 2 or space == 2 or inode == 2:
        return 2
    elif used == 1 or space == 1 or inode == 1:
        return 1
    else:
        return 0


def clean_process():
    """
    constants:
        123: when gs_metricagent is not exists and used python3, status is 123.
        31488: when gs_metricagent is not exists and used python2, status is 31488.
    """

    cmd = "ps -ef | grep gs_metricagent | grep -v grep  | awk '{print $2}' | xargs kill -9"
    status, output = common.runShellCommand(cmd)
    if status == 0:
        pid_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../agent.pid')
        if os.path.exists(pid_file):
            os.remove(pid_file)
        logmgr.record(LOG_MODULE, "Clean gs_metricagent successfully.")
        sys.exit(0)
    elif status == 123 or status == 31488:
        logmgr.record(LOG_MODULE, "There is no gs_metricagent process.")
        sys.exit(0)
    else:
        logmgr.record(LOG_MODULE, "Failed clean gs_metricagent.Result:%s" % output)
        return


def watcher():
    """
    function: Determine whether to kill the process, or cleaning old metric data.
    input: NA
    return: NA
    """
    data_path = os.path.join(os.getenv('GAUSSLOG', '/var/log/Bigdata/mpp/omm'), 'gs_metricdata')
    push_buffer = os.path.join(data_path, "pusherbuffer")
    flag = check_used(data_path)
    if flag == 2:
        clean_process()
    elif flag == 1:
        data_files = []
        cmd = "find %s -type f -name *.zip | sort" % push_buffer     #注意排序
        _, output = common.runShellCommand(cmd)
        data_files = output.splitlines()
        for i in range(0, len(data_files), 300):
            clean_file = "rm -rf %s" %  " ".join(data_files[i: (i + 300)])
            common.runShellCommand(clean_file)
            flag = check_used(data_path)
            if flag == 2:
                clean_process()
            elif flag == 1:
                continue
            else:
                return
    else:
        return


def timer():
    """
    function: Only the watcher is executed on the 300 second.
    """
    watcher()
    monitor()


def monitor():
    """
    function: do timer() 300 second.
    """
    scheduler.enter(300, 1, timer, ())


if __name__ == "__main__":
    logmgr.StartLogManager('watcher')
    watcher()
    monitor()
    scheduler.run()