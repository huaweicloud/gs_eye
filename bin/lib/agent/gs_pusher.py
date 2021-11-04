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
    import time
    import commands
    import socket
    from lib.common import gs_logmanager as logmgr
    import lib.common.gs_constvalue as varinfo
    import json
except Exception as e:
    sys.exit("FATAL: %s Unable to import module: %s" % (__file__, e))

LOG_MODULE = "Pusher"


def PusherProtocal(protocal):
    """
    Method for Pusher to push log to metric database
    http:  push by http protocal, must be setting with url and with httpd installed by user self
    ftp:   push by ftp protocal, ftpd must be installed, and username/password is also needed
    sftp:  push by sftp protocal, same as ftp
    local: metric database is on local cluster, only need a global path to copy log, scp will be used in trust mode
    sockServer: push by private socket, and ip/port is needed which is allowed by remote and local server's firewall
    bypass: using local message queue, which is realized by gsql, pushing the metric data at real time
    """
    protocalDict = {
        'http' : 1,
        'ftp' : 2,
        'sftp' : 3,
        'local' : 4,
        'sockServer' : 5,
        'bypass' : 6
    }
    return protocalDict[protocal]


def PusherMethod(method):
    """
    Method for Pusher to push log to metric database
    nokeep:  move all metrid data to push buffer each time, source cluster will keep nothing data after metric data
             pushed to maintainance database
    incremental:   local data will be kept for a long time set by log_keep_time
    """
    methodDict = {
        'nokeep' : 1,
        'incremental' : 2,
    }
    return methodDict[method]


def PusherFileType(type):
    """
    Method for Pusher to push log to metric database
    nokeep:  move all metrid data to push buffer each time, source cluster will keep nothing data after metric data
             pushed to maintainance database
    incremental:   local data will be kept for a long time set by log_keep_time
    """
    filetype = {
        'data' : 1,
        'config' : 2,
    }
    return filetype[type]


class Pusher:
    """
    base class for Pusher
    """
    def __init__(self, pushConfig):
        """
        Constructor
        """
        self.pushmethod = pushConfig['method']
        if pushConfig['protocal'] == 'http':
            self.pusher = PusherByHttp(pushConfig['base_url'], pushConfig['cluster_name'])
        self.interval = pushConfig['interval']
        self.pushFileList = {}
        if not os.path.isdir(varinfo.PUSHER_BUFFER_PATH):
            os.makedirs(varinfo.PUSHER_BUFFER_PATH)
        self.pushStateFile = os.path.join(varinfo.PUSHER_BUFFER_PATH, "pusher_state.json")
        if os.path.isdir(self.pushStateFile):
            # Gets information about archive files that have not been pushed from json file
            if os.path.isfile(self.pushStateFile) and os.path.getsize(self.pushStateFile):
                self.pushFileList = json.loads(open(self.pushStateFile, "r").read())
        self.hostname = socket.gethostname()

    def generatePusherData(self):
        filePrefix = self.hostname + time.strftime(varinfo.FILE_TIME_FORMAT, time.localtime())
        newfile = os.path.join(varinfo.PUSHER_BUFFER_PATH, filePrefix + ".zip")
        command = "cd %s; zip -r -m %s data" % (varinfo.MATRIC_LOGBASE, newfile)
        status, output = commands.getstatusoutput(command)
        if status != 0:
            logmgr.recordError("Pusher", "Failed to zip archive file \"%s\", err: %s" % (newfile, output), "DEBUG")
        else:
            # Record archive file status
            self.pushFileList[filePrefix] = "Undo"
        json_str = json.dumps(self.pushFileList)
        with open(self.pushStateFile, 'w+') as json_file:
            json_file.write(json_str)

    def PushData(self):
        filenum = len(self.pushFileList)
        if not filenum:
            logmgr.recordError("Pusher", "Nothing to do", "DEBUG")
            return
        # The total push time is at most equal to the time interval
        timeout = self.interval / filenum
        for fileprefix in self.pushFileList.keys():
            filepath = os.path.join(varinfo.PUSHER_BUFFER_PATH, fileprefix + ".zip")
            if self.pusher.pushData(filepath, timeout) is True:
                self.pushFileList.pop(fileprefix)
                os.remove(filepath)
                logmgr.recordError("Pusher", "rm file %s" % filepath, "DEBUG")
            else:
                self.pushFileList[fileprefix] = "Redo"
        # Record archive files that failed to be pushed
        if self.pushFileList:
            with open(self.pushStateFile, "w") as state:
                state.write(json.dumps(self.pushFileList))
        elif os.path.isfile(self.pushStateFile):
            os.remove(self.pushStateFile)
            logmgr.recordError("Pusher", "rm state file %s" % self.pushStateFile, "DEBUG")

    def PusherSchedule(self, clock):
        if clock % self.interval == 0:
            self.generatePusherData()
            self.PushData()


class PusherByHttp:
    """
    Classify method to push logs to remote server
    """
    def __init__(self, url, clusterName):
        """
        Constructor
        """
        self.remotePushBase = url + "/" + clusterName
        self.cluterName = clusterName
        self.remoteConfPath = self.remotePushBase + "/conf/"
        self.remoteDataPath = self.remotePushBase + "/data/" + socket.gethostname() + "/"

    def checkUrlOptions(self):
        """
        Check remote server url if exists
        """
        # TODO: 使用https代替http服务
        if self.remotePushBase:
            # It is necessary to check the log push interval
            # The curl command tests the connection with a one-second timeout
            # TODO: 探活服务端
            command = "curl -m 1 %s" % self.remotePushBase
            status, output = commands.getstatusoutput(command)
            if status != 0 or "<title>404 Not Found</title>" in output:
                logmgr.recordError("Pusher", "check remote base path %s failed" % self.remotePushBase)
                return False
            command = "curl -m 1 %s" % self.remoteConfPath
            status, output = commands.getstatusoutput(command)
            if status != 0 or "<title>404 Not Found</title>" in output:
                logmgr.recordError("Pusher", "check remote conf path %s failed" % self.remoteConfPath)
                return False
            command = "curl -m 1 %s" % self.remoteDataPath
            status, output = commands.getstatusoutput(command)
            if status != 0 or "<title>404 Not Found</title>" in output:
                logmgr.recordError("Pusher", "check remote data path %s failed" % self.remoteDataPath)
                return False
            return True

    def checkUrlOption(self, url):
        """
        Check remote server url if exists
        """
        # TODO: 使用https代替http服务
        # It is necessary to check the log push interval
        # The curl command tests the connection with a one-second timeout
        # TODO: 探活服务端
        command = "curl -m 1 %s" % url
        status, output = commands.getstatusoutput(command)
        if status != 0 or "<title>404 Not Found</title>" in output:
            logmgr.recordError("Pusher", "check remote path %s failed" % url)
            return False
        return True

    def pushFile(self, sourceFile, filetype, timeout):
        """
        function : Push archive files to remote server
        input : NA
        output : NA
        """
        # if not self.checkUrlOptions():
        #     return False
        if filetype == PusherFileType('data'):
            url = self.remoteDataPath
        elif filetype == PusherFileType('config'):
            url = self.remoteConfPath
        else:
            logmgr.recordError(LOG_MODULE, "Error file type \"%s\" to \"%s\"" % (sourceFile, filetype))
            return False

        if not self.checkUrlOption(url):
            return False

        if os.path.isfile(sourceFile):
            command = "curl -m %d -T %s %s" % (timeout, sourceFile, url)
            status, output = commands.getstatusoutput(command)
            # It will be redone next time if failed to push
            if status != 0 or ("<title>" in output and "201 Created" not in output):
                logmgr.recordError(LOG_MODULE, "Failed to curl \"%s\" to \"%s\" err: %s" % (sourceFile, url, output))
                return False
            return True
        else:
            # The archive may have been deleted by log manager or others
            logmgr.recordError(LOG_MODULE, "The archive file does not exist May be deleted by log manager")
            return True

    def pushData(self, file, timeout):
        """
        function : Push archive files to remote server
        input : NA
        output : NA
        """
        return self.pushFile(file, PusherFileType('data'), timeout)


class PusherByLocal:
    """
    Classify method to push logs to local global directory
    """
    def __init__(self):
        """
        Constructor
        """
        logmgr.recordError(LOG_MODULE, "local mode is not support, will be realized in future")

    def pushData(self, file, timeout):
        """
        function : Push archive files to remote server
        input : NA
        output : NA
        """
        logmgr.recordError(LOG_MODULE, "local mode is not support, will be realized in future")


class PusherByFtp:
    """
    Classify method to push logs to remote server
    """
    def __init__(self, pushMethod, interval, options):
        """
        Constructor
        """
        logmgr.recordError(LOG_MODULE, "ftp mode is not support, will be realized in future")

    def pushData(self, file, timeout):
        """
        function : Push archive files to remote server
        input : NA
        output : NA
        """
        logmgr.recordError(LOG_MODULE, "ftp mode is not support, will be realized in future")


class PusherBySockServer:
    """
    Classify method to push metric to self socket server
    """
    def __init__(self, pushMethod, interval, options):
        """
        Constructor
        """
        logmgr.recordError("Pusher", "Socket server mode is not support, will be realized in future")

    def checkSockServerIsAlive(self):
        """
        Check remote socket server is alived
        """
        return True

    def pushData(self, file, timeout):
        """
        function : Push archive files to remote server
        input : NA
        output : NA
        """
        logmgr.recordError("Pusher", "SockServer mode is not support, will be realized in future")
