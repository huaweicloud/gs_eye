#!/usr/bin/env python
#-*- coding:utf-8 -*-
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
adsfaf
try:
    import os
    import getopt
    import sys
    import imp
    imp.reload(sys)
    sys.setdefaultencoding('utf8')
    import time
    import signal
    from lib.common.gs_logmanager import recordError as recordError
    from lib.common.gs_jsonconf import AddTemplateToJconf
    from lib.common import gs_constvalue as varinfo
except Exception as e:
    sys.exit("FATAL: %s Unable to import module: %s" % (__file__, e))

LOG_MODULE = 'Metric OPS'

if __name__ == "__main__":
    """
    function : The entrance
    input : NA
    output : NA
    """
    try:
        #Resolves the command line
        (opts, args) = getopt.getopt(sys.argv[1:], "a:e:d:p:")
    except Exception as ex:
        sys.exit("FATAL: Unable to recognize command: %s" % ex)

    pid = 0
    timeout = 10
    ops = ""
    metricItem = ""
    for (key, value) in opts:
        if key == "-a" or key == "--add":
            ops = "add"
            metricItem = value
            recordError(LOG_MODULE, "add metric %s" % value)
            AddTemplateToJconf("metric_user_define", value)
        if key == "-e" or key == "--enable":
            recordError(LOG_MODULE, "enable metric %s" % value)
            ops = "enable"
            metricItem = value
        if key == "-d" or key == "--disable":
            recordError(LOG_MODULE, "disable metric %s" % value)
            ops = "disable"
            metricItem = value
        if key == "-p" or key == "--pid":
            pid = int(value)

    file = open(varinfo.METRIC_SIGFLAG_FILE, "w+")
    flag = ops + '\n' + metricItem
    file.write(flag)
    file.close()

    if pid == 0:
        recordError(LOG_MODULE, "no pid is input")
        sys.exit(0)
    os.kill(pid, signal.SIGUSR2)
    while timeout > 0:
        if not os.path.isfile(varinfo.METRIC_SIGFLAG_FILE):
            break
        timeout = timeout - 1
        if timeout == 0:
            recordError(LOG_MODULE, "%s : %s is timeout" % (ops, value))
        time.sleep(1)
    sys.exit(0)
