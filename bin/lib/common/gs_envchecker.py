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

try:
    import os
    import sys
    import getopt
    import commands
    import gs_constvalue as varinfo
    import gs_jsonconf as jconf
    import cluster.gs_instance_manager as dbinfo
except Exception as e:
    sys.exit("FATAL: %s Unable to import module: %s" % (__file__, e))


def usage():
    """
Usage:
  ./CMD -h | --help
  Example:
    ./CMD [-u username] &

General options:
    -u, --username                Database username.
    -h, --help                    Show help information for this utility.
    -v, --version                 Show version information.
    """
    sys.exit(usage.__doc__)


class Parameter(object):
    """
    Parameter information
    """
    def __init__(self):
        """
        Constructor
        """
        # database username
        self.username = ""
        self.version = varinfo.GS_METRIC_VERSION

    def initParameter(self):
        """
        Initialize the input parameters
        """
        try:
            opts, args = getopt.getopt(sys.argv[1:], "u:hv", ["username=", "help", "version"])
        except getopt.GetoptError as e:
            sys.exit(e)
        for opt, arg in opts:
            if opt in ("-u", "--username"):
                self.username = arg
            elif opt in ("-h", "--help"):
                usage()
            elif opt in ("-v", "--version"):
                sys.exit(self.version)
            else:
                usage()


class RunEnvironment(Parameter):
    """
    Check parameter validity
    """
    def __init__(self):
        """
        Constructor
        """
        super(RunEnvironment, self).__init__()
        # CN information on the current node
        self.coordinator = []
        # DN information on the current node
        self.datanode = []
        # host name on the current node
        self.hostname = ""
        self.dbNodeList = []
        self.appName = ""
        self.clusterInfo = {}
        self.hostlist = []

    def SetAppName(self, runMode):
        if runMode == 'Server':
            self.appName = varinfo.GS_METRIC_SERVER_NAME
        elif runMode == 'Agent':
            self.appName = varinfo.GS_METRIC_AGENT_NAME
        return

    def checkIsRunning(self):
        """
        Check running status, to prevent more than one application running in background.
        """
        if not self.appName:
            sys.exit("Wrong mode")
        command = "ps -ef | grep %s | grep -v -E 'grep|sh|source|%d' | awk '{print $2}'" \
                  % (self.appName, os.getpid())
        status, output = commands.getstatusoutput(command)
        if status != 0:
            dbinfo.raiseRuntimeError("Failed to check running state", output)
        else:
            pid = [item for item in output.split('\n') if item.isdigit()]
            if pid:
                sys.exit("The script is Already started")

    def checkLogSizeAndTime(self):
        """
        Check log size and time
        """
        # 0 means no limit
        if self.logsize <= 0:
            dbinfo.raiseValueError(__file__, "--logtime", self.logsize)
        self.logsize *= varinfo.DATA_TYPE_MBYTES
        self.logtime = 0 if self.logtime < 0 else (self.logtime * varinfo.CLOCK_TYPE_DAYS)

    def checkDBNode(self):
        """
        Check cluster information
        """
        # Get cluster information from library lib.cluster.dbinfo
        clusterInfo = dbinfo.getDbInfo(self.username)
        self.hostname = clusterInfo.hostname
        for dbNode in clusterInfo.dbNodes:
            self.hostlist.append(dbNode.name)
            if dbNode.name == self.hostname:
                for cn in dbNode.coordinators:
                    self.coordinator.append(dbinfo.DBNodeInfo("coordinator", cn.instanceId, cn.port, cn.datadir))
                for dn in dbNode.datanodes:
                    # 0 indicates master and 1 indicates standby
                    if dn.instanceType in (0, 1):
                        self.datanode.append(dbinfo.DBNodeInfo("datanode", dn.instanceId, dn.port, dn.datadir))
        self.dbNodeList = self.coordinator + self.datanode
        self.clusterInfo = clusterInfo

    def SaveClusterHostList(self):
        """
        Save cluster information
        """
        # Get cluster information from library lib.cluster.dbinfo
        clister_list = {"cluster_list" : self.hostlist}
        clistfile = os.path.join(varinfo.PUSHER_BUFFER_PATH, varinfo.CLUSTER_LIST_FILE)
        jconf.SaveJsonConf(clister_list, clistfile)

    def checkParameter(self):
        """
        Check the input parameters
        """
        self.checkIsRunning()
        self.checkDBNode()
