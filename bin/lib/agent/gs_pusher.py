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

try:
    import os
    import sys
    import time
    import socket
    import lib.common.CommonCommand as common
    from lib.common import gs_logmanager as logmgr
    import lib.common.gs_constvalue as varinfo
    import json
except Exception as e:
    sys.exit("FATAL: %s Unable to import module: %s" % (__file__, e))

LOG_MODULE = "Pusher"


def Pusherprotocol(protocol):
    """
    Method for Pusher to push log to metric database
    http:  push by http protocol, must be setting with url and with httpd installed by user self
    ftp:   push by ftp protocol, ftpd must be installed, and username/password is also needed
    sftp:  push by sftp protocol, same as ftp
    local: metric database is on local cluster, only need a global path to copy log, scp will be used in trust mode
    sockServer: push by private socket, and ip/port is needed which is allowed by remote and local server's firewall
    bypass: using local message queue, which is realized by gsql, pushing the metric data at real time
    """
    protocolDict = {
        'http': 1,
        'ftp': 2,
        'sftp': 3,
        'local': 4,
        'sockServer': 5,
        'bypass': 6
    }
    return protocolDict[protocol]


def PusherMethod(method):
    """
    Method for Pusher to push log to metric database
    nokeep:  move all metrid data to push buffer each time, source cluster will keep nothing data after metric data
             pushed to maintainance database
    incremental:   local data will be kept for a long time set by log_keep_time
    """
    methodDict = {
        'nokeep': 1,
        'incremental': 2,
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
        'data': 1,
        'config': 2,
    }
    return filetype[type]


class Pusher:
    """
    function:
        1. the pusher is used to push data file from agent.
        2. it support two transport method(HTTP/SCP).
        3. You should configure the clint_conf.json before calling pusher.
    """
    def __init__(self, pushConfig):
        """
        function: init the parameter
        class parameter:
            self.pushmethod is the parameter that set whether http is keep
            self.pusher is the class that do things
            self.interval is the parameter that controls the push interval.
            self.pushStateFile is a file that use to record
        clint_conf.json:
            method corresponds to self.pushmethod
            interval corresponds to self.interval
            base_url: when data will be pushed by http, base_url should be like 'http://xxx.xxx.xxx:xxx/xxx'.
                      when data will be pushed by scp. base_url must comply with the usage specifications of the scp.
        """
        if pushConfig['method']:
            self.pushmethod = pushConfig['method']
        if pushConfig['protocol'].strip() == 'http':
            self.pusher = PusherByHttp(pushConfig['base_url'], pushConfig['cluster_name'])
        elif pushConfig['protocol'].strip() == 'scp':
            self.pusher = PusherByScp(pushConfig['base_url'], pushConfig['cluster_name'])
        else:
            logmgr.record("Pusher", "Can not support %s to transport files." % pushConfig['protocol'].strip())
        if not pushConfig['max_compress_files']:
            self.max_compress_files = 1000
        else:
            self.max_compress_files = pushConfig['max_compress_files']
        if not pushConfig['interval']:
            self.interval = 5
        else:
            self.interval = pushConfig['interval']
        self.pushFileList = {}
        if not os.path.isdir(varinfo.PUSHER_BUFFER_PATH):
            os.makedirs(varinfo.PUSHER_BUFFER_PATH)
        self.pushStateFile = os.path.join(varinfo.PUSHER_BUFFER_PATH, "pusher_state.json")
        if os.path.isfile(self.pushStateFile) and os.path.getsize(self.pushStateFile) > 0:
            logmgr.record("Pusher", "load json to init pushFileList.")
            self.pushFileList = json.loads(open(self.pushStateFile, "r").read())
        self.hostname = socket.gethostname()

    def generatePusherData(self):
        cmd = "cd %s; find data -name *.ready" % varinfo.MATRIC_LOGBASE
        status, output = common.runShellCommand(cmd)
        if status != 0:
            logmgr.record("Pusher", "Failed to find ready file, err: %s" % output)
            return
        if output:
            file_list = output.splitlines()
            for i in range(0, len(file_list), self.max_compress_files):
                # When the compression is completed within one second,
                # the names of the two compressed files may be the same. so filePrefix + str(i)
                filePrefix = self.hostname + time.strftime(varinfo.FILE_TIME_FORMAT, time.localtime()) + str(i)
                newfile = os.path.join(varinfo.PUSHER_BUFFER_PATH, filePrefix + ".zip")
                command = "cd %s; zip -m %s %s" % (varinfo.MATRIC_LOGBASE, newfile,
                                                   " ".join(file_list[i: (i + self.max_compress_files)]))
                status, output = common.runShellCommand(command)
                if status != 0:
                    logmgr.record("Pusher", "Failed to zip archive file \"%s\", err: %s" % (newfile, output))
                else:
                    # the new zip that was not be transferred is defined "Undo".
                    logmgr.record("Pusher", "Successfully to zip:%s; archive files: %s" % (newfile, output))
                    self.pushFileList[filePrefix] = "Undo"
            json_str = json.dumps(self.pushFileList)
            with open(self.pushStateFile, 'w+') as json_file:
                json_file.write(json_str)
                json_file.flush()

    def PushData(self):
        filenum = len(self.pushFileList)
        if not filenum:
            logmgr.record("Pusher", "Nothing to do", "DEBUG")
            return
        import copy
        tmpFileList = copy.deepcopy(self.pushFileList)
        # The total push time is at most equal to the time interval
        timeout = self.interval / filenum
        for fileprefix in self.pushFileList.keys():
            try:
                filepath = os.path.join(varinfo.PUSHER_BUFFER_PATH, fileprefix + ".zip")
                if self.pusher.pushData(filepath, timeout) is True:
                    logmgr.record(LOG_MODULE, "successfully to push data: %s" % filepath)
                    tmpFileList.pop(fileprefix)
                    logmgr.record("Pusher", "fileprefix: %s" % fileprefix)
                    os.remove(filepath)
                    logmgr.record("Pusher", "rm file %s" % filepath)
                else:
                    # the new zip that fail to be transferred is defined "Redo".
                    tmpFileList[fileprefix] = "Redo"
            except Exception as e:
                logmgr.record(LOG_MODULE, "Failed to push data: %s, reson:%s" % (fileprefix + ".zip", str(e)))
                continue
        self.pushFileList = copy.deepcopy(tmpFileList)
        # Record archive files that failed to be pushed
        logmgr.record("Pusher", "after cleaning %s" % ",".join(tmpFileList))
        if tmpFileList:
            with open(self.pushStateFile, "w") as state:
                state.write(json.dumps(tmpFileList))
                state.flush()
        elif os.path.isfile(self.pushStateFile):
            self.pushFileList = {}
            os.remove(self.pushStateFile)
            logmgr.record("Pusher", "rm state file %s" % self.pushStateFile)

    def PusherSchedule(self):
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
            status, output = common.runShellCommand(command)
            if status != 0 or "<title>404 Not Found</title>" in output:
                logmgr.record("Pusher", "check remote base path %s failed" % self.remotePushBase)
                return False
            command = "curl -m 1 %s" % self.remoteConfPath
            status, output = common.runShellCommand(command)
            if status != 0 or "<title>404 Not Found</title>" in output:
                logmgr.record("Pusher", "check remote conf path %s failed" % self.remoteConfPath)
                return False
            command = "curl -m 1 %s" % self.remoteDataPath
            status, output = common.runShellCommand(command)
            if status != 0 or "<title>404 Not Found</title>" in output:
                logmgr.record("Pusher", "check remote data path %s failed" % self.remoteDataPath)
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
        status, output = common.runShellCommand(command)
        if status != 0 or "<title>404 Not Found</title>" in output:
            logmgr.record("Pusher", "check remote path %s failed" % url)
            return False
        return True

    def pushFile(self, sourceFile, filetype, timeout):
        """
        function : Push archive files to remote server
        input : NA
        output : NA
        """
        if not self.checkUrlOptions():
            return False
        if filetype == PusherFileType('data'):
            url = self.remoteDataPath
        elif filetype == PusherFileType('config'):
            url = self.remoteConfPath
        else:
            logmgr.record(LOG_MODULE, "Error file type \"%s\" to \"%s\"" % (sourceFile, filetype))
            return False

        if not self.checkUrlOption(url):
            return False

        if os.path.isfile(sourceFile):
            command = "curl -m %d -T %s %s" % (timeout, sourceFile, url)
            status, output = common.runShellCommand(command)
            # It will be redone next time if failed to push
            if status != 0 or ("<title>" in output and "201 Created" not in output):
                logmgr.record(LOG_MODULE, "Failed to curl \"%s\" to \"%s\" err: %s" % (sourceFile, url, output))
                return False
            return True
        else:
            # The archive may have been deleted by log manager or others
            logmgr.record(LOG_MODULE, "The archive file does not exist May be deleted by log manager")
            return True

    def pushFileToServer(self, sourceFile, url, timeout):
        """
        function : Push archive files to remote server
        input : NA
        output : NA
        """
        if not self.checkUrlOption(url):
            return False
        command = "curl -m %d -T %s %s" % (timeout, sourceFile, url)
        status, output = common.runShellCommand(command)
        # It will be redone next time if failed to push
        if status != 0 or ("<title>" in output and "201 Created" not in output):
            logmgr.record(LOG_MODULE, "Failed to curl \"%s\" to \"%s\" err: %s" % (sourceFile, url, output))
            return False
        return True

    def pushData(self, file, timeout):
        """
        function : Push archive files to remote server
        input : NA
        output : NA
        """
        return self.pushFile(file, PusherFileType('data'), timeout)


class PusherByScp:
    """
    function: the pusher is used to push data file from agent by scp.
    Dependence:
        1. configure the base_url, protocol in clint_conf.json
        2. base_url should like "user@ip:path".
        3. protocol should be "scp".
        4. the user's are trust for each node.
    """

    def __init__(self, url, clusterName):
        """
        Constructor
        """
        self.remotePushBase = url + "/" + clusterName
        self.cluterName = clusterName
        self.remoteConfPath = self.remotePushBase + "/conf/"
        self.remoteDataPath = self.remotePushBase + "/data/" + socket.gethostname() + "/"

    def pushFile(self, sourceFile, filetype, timeout):
        """
        function : Push archive files to remote server
        input : NA
        output : NA
        """
        if filetype == PusherFileType('data'):
            url = self.remoteDataPath
        elif filetype == PusherFileType('config'):
            url = self.remoteConfPath
        else:
            logmgr.record(LOG_MODULE, "Error file type \"%s\" to \"%s\"" % (sourceFile, filetype))
            return False

        if os.path.isfile(sourceFile):
            command = "scp %s %s" % (sourceFile, url)
            status, output = common.runShellCommand(command)
            # It will be redone next time if failed to push
            if status != 0:
                logmgr.record(LOG_MODULE, "Failed to scp \"%s\" to \"%s\" err: %s" % (sourceFile, url, output))
                return False
            logmgr.record(LOG_MODULE, "successfully push file \"%s\" to \"%s\"" % (sourceFile, url))
            return True
        else:
            # The archive may have been deleted by log manager or others
            logmgr.record(LOG_MODULE, "The archive file does not exist May be deleted by log manager")
            return True

    def pushFileToServer(self, sourceFile, url, timeout):
        """
        function : Push archive files to remote server
        input : NA
        output : NA
        """
        # if not self.checkUrlOption(url):
        #     return False
        command = "scp %s %s" % (sourceFile, url)
        status, output = common.runShellCommand(command)
        # It will be redone next time if failed to push
        if status != 0:
            logmgr.record(LOG_MODULE, "Failed to scp \"%s\" to \"%s\" err: %s" % (sourceFile, url, output))
            return False
        logmgr.record(LOG_MODULE, "successfully push file \"%s\" to \"%s\" server" % (sourceFile, url))
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
        logmgr.record(LOG_MODULE, "local mode is not support, will be realized in future")

    def pushData(self, file, timeout):
        """
        function : Push archive files to remote server
        input : NA
        output : NA
        """
        logmgr.record(LOG_MODULE, "local mode is not support, will be realized in future")


class PusherByFtp:
    """
    Classify method to push logs to remote server
    """

    def __init__(self, pushMethod, interval, options):
        """
        Constructor
        """
        logmgr.record(LOG_MODULE, "ftp mode is not support, will be realized in future")

    def pushData(self, file, timeout):
        """
        function : Push archive files to remote server
        input : NA
        output : NA
        """
        logmgr.record(LOG_MODULE, "ftp mode is not support, will be realized in future")


class PusherBySockServer:
    """
    Classify method to push metric to self socket server
    """

    def __init__(self, pushMethod, interval, options):
        """
        Constructor
        """
        logmgr.record("Pusher", "Socket server mode is not support, will be realized in future")

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
        logmgr.record("Pusher", "SockServer mode is not support, will be realized in future")
