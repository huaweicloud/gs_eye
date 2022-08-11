#!/usr/bin/env python3
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
    import json
    import lib.common.CommonCommand as common
    import lib.common.gs_logmanager as logmgr
except Exception as e:
    sys.exit("FATAL: %s Unable to import module: %s" % (__file__, e))


def raiseValueError(owner, opt, value):
    """
    function : Raise parameter value error
    input : the function caller, param name, param value
    output : NA
    """
    error = "Invalid parameter, detail: %s %s" % (opt, value)
    raise ValueError("%s\nTry '%s -h' for more information." % (error, owner))


def raiseRuntimeError(msg, detail):
    """
    function : Raise script running error
    input : error massage, error detail
    output : NA
    """
    error = "%s, detail: %s" % (msg, detail)
    raise RuntimeError(error)


def checkPathValid(path):
    """
    function : Check whether the end character of the path is '/'
    input : path
    output : valid path
    """
    return path + "/" if path[-1] != '/' else path


def getDbInfo(username):
    """
    function : the interface to get the cluster information
    input : database username
    output : cluster information object
    """
    clusterInfo = ClusterInfo()
    clusterInfo.getDbInfo(username)
    return clusterInfo


class Instance:
    """
    Database instance information
    """
    def __init__(self, instanceType, instanceId, port, datadir, pid):
        """
        Constructor
        """
        # instance type, -1 indicates cn, 0 indicates dn master and 1 indicates dn standby
        self.instanceType = instanceType
        self.instanceId = instanceId
        self.port = port
        self.datadir = datadir
        self.pid = pid

    def getInstanceStat(self):
        state = ""
        command = "cat /proc/%s/stat" % self.pid
        status, output = common.runShellCommand(command)
        if not status and output:
            state = output
        return state


class DBNodeInfo:
    """
    Database instance information
    """
    def __init__(self, metricType, instanceId, port, datadir, instanceType):
        """
        Constructor
        """
        # instance type, cn or dn
        if metricType == 'coordinator':
            self.instanceName = 'cn' + '_' + str(instanceId)
        elif metricType == 'datanode':
            self.instanceName = 'dn' + '_' + str(instanceId)
        self.instanceType = instanceType
        self.type = metricType
        self.port = port
        self.datadir = datadir
        self.state = "Down"

    def getNodeState(self, owner):
        """
        function : Get the instance state
        input : the function caller
        output : state information
        """
        # It is necessary to get the instance state when multiple queries fail
        self.state = "Down"
        command = "gs_ctl query -D %s | grep local_role | awk '{print $3}' | sed -n '1p'" % self.datadir
        status, output = common.runShellCommand(command)
        if status != 0:
            logmgr.record(owner, "Failed to get node %s state" % self.instanceName)
        elif output:
            self.state = output
        return self.state

    def checkNodeState(self, owner):
        """
        function : check the instance state
        input : the function caller
        output : result state
        """
        # If the current state is primary, return directly
        if self.state in ("Primary", "Normal"):
            return True
        # Check whether the state changes from another state to primary
        if self.getNodeState(owner) in ("Primary", "Normal"):
            logmgr.record(owner, "node %s state changed to %s" % (self.instanceName, self.state))
            return True
        return False


class DBNode:
    """
    Database node information
    """
    def __init__(self, name):
        """
        Constructor
        """
        # host name
        self.name = name
        # coordinator instances
        self.coordinators = []
        # datanode instances
        self.datanodes = []


class ClusterInfo:
    """
    Cluster information
    """
    def __init__(self):
        # cluster information file name
        self.filename = "dbinfo.json"
        # cluster information file path
        self.path = checkPathValid(os.path.dirname(os.path.realpath(__file__)))
        # cluster information file
        self.file = self.path + self.filename
        # database node information
        self.dbNodes = []
        # current host name
        self.hostname = self.getHostname()
        # current host coordinator
        self.coordinator = None
        # process id changed flag
        self.changed = False

    def getHostname(self):
        """
        function : get the current host name
        input : NA
        output : host name
        """
        status, hostname = common.runShellCommand("hostname")
        if status != 0 or not hostname:
            raiseRuntimeError("Failed to get hostname", hostname)
        return hostname

    def checkInstancePid(self, instance):
        """
        function : get the instance progress id
        input : instance
        output : NA
        """
        pid = 0
        # Get the process id from the postmaster.pid file in the instance directory
        command = "cat %s/postmaster.pid | sed -n '1p'" % instance[3]
        status, output = common.runShellCommand(command)
        if not status and output.isdigit():
            pid = int(output)
        # The cluster information file needs to be updated because the process id is changed
        if instance[4] != pid:
            instance[4] = pid
            self.changed = True

    def getDbInfoFromStaticConfig(self, username):
        """
        function : get the cluster information dictionary form static configuration file
        input : database username
        output : NA
        """
        # Get the Gauss environment variable for import library
        libpath = os.environ.get("GPHOME")
        if not libpath:
            raiseRuntimeError("Failed to get libpath", "The environment variable is not initialized.")
        sys.path.append(checkPathValid(libpath) + "script/gspylib/common")
        # Use the library DbClusterInfo to parse static file
        # TODO: 使用cm_ctl view获取集群信息
        try:
            import DbClusterInfo
        except Exception as e:
            raiseRuntimeError("FATAL: Unable to import module", e)
        # Converting to a dictionary is like reading from a json file
        instance = {}
        cluster = {}
        clusterInfo = DbClusterInfo.dbClusterInfo()
        clusterInfo.initFromStaticConfig(username)
        # Use dictionary to save cluster information
        for dbNode in clusterInfo.dbNodes:
            instance['coordinators'] = []
            for cn in dbNode.coordinators:
                instance['coordinators'].append([cn.instanceType, cn.instanceId, cn.port, cn.datadir, 0])
            instance['datanodes'] = []
            for dn in dbNode.datanodes:
                instance['datanodes'].append([dn.instanceType, dn.instanceId, dn.port, dn.datadir, 0])
            cluster[dbNode.name] = instance.copy()
        # The cluster information file needs to be updated
        self.changed = True
        return cluster

    def saveDbInfo(self, cluster):
        """
        function : save the cluster information
        input : cluster information dictionary
        output : NA
        """
        # Parse the cluster information dictionary and check the process id
        for dbName in cluster.keys():
            dbNode = DBNode(dbName)
            for cn in cluster[dbName]['coordinators']:
                if dbName == self.hostname:
                    self.checkInstancePid(cn)
                    self.coordinator = Instance(int(cn[0]), int(cn[1]), cn[2], cn[3], cn[4])
                    dbNode.coordinators.append(self.coordinator)
                else:
                    dbNode.coordinators.append(Instance(int(cn[0]), int(cn[1]), cn[2], cn[3], cn[4]))
            for dn in cluster[dbName]['datanodes']:
                if dbName == self.hostname:
                    self.checkInstancePid(dn)
                dbNode.datanodes.append(Instance(int(dn[0]), int(dn[1]), dn[2], dn[3], dn[4]))
            self.dbNodes.append(dbNode)
        # Process id changes or cluster information retrieved from the library need to save json files
        if self.changed:
            with open(self.file, "w") as config:
                config.write(json.dumps(cluster))

    def getDbInfo(self, username):
        """
        function : get the cluster information
        input : database username
        output : NA
        """
        # Get the cluster information dictionary
        if os.path.isfile(self.file):
            cluster = json.loads(open(self.file, "r").read())
        else:
            cluster = self.getDbInfoFromStaticConfig(username)
        self.saveDbInfo(cluster)
