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
    import imp
    imp.reload(sys)
    sys.setdefaultencoding('utf8')
    import time
    import lib.common.gs_constvalue as varinfo
    import threading
    import glob
    import gs_jsonconf as jconf
except Exception as e:
    sys.exit("FATAL: %s Unable to import module: %s" % (__file__, e))


# Global log file
_logs = None
lock = threading.Lock()
LOG_MODULE = "LOGGING"


def LogLevel(level):
    levelList = {
        "PANIC" : 9,
        "LOG" : 10,
        "DEBUG" : 11
    }
    return levelList[level]


def RegisterLogModule(moduleName, state):
    global _logs
    if not _logs:
        return
    if moduleName not in _logs.modLevel.keys():
        recordError(LOG_MODULE, "module %s has been registered" % (moduleName))
        return
    newModule = {moduleName : state}
    _logs.modLevel.update(newModule)


def StartLogManager(runMode):
    global _logs
    _logs = RunningLog(runMode)


def recordError(module, msg, level="LOG"):
    """
    function : Record script running error
    input : the function caller, error massage, error detail
    output : NA
    """
    global _logs
    # Prevent too long error messages
    error = "[%s][%s]: %s" % (level, module, msg)
    if len(error) > varinfo.DATA_LEN_ERROR:
        error = error[:varinfo.DATA_LEN_ERROR]
    if not _logs:
        print(error)
        if "PANIC" in level:
            sys.exit()
        return
    if module in _logs.modLevel.keys():
        curModlevel = _logs.modLevel[module]
    else:
        curModlevel = LogLevel("LOG")
    # Use lock to prevent logging errors from multithreaded logging
    if LogLevel(level) <= curModlevel:
        lock.acquire()
        _logs.logWriteAndTimer(error)
        lock.release()
    if "PANIC" in level:
        sys.exit()


class MetricLog:
    """
    Classify method to write logs
    """
    def __init__(self, path, filename):
        """
        Constructor
        """
        if not os.path.isdir(path):
            os.makedirs(path)
        # log path
        self.path = path
        # log name
        self.filename = filename
        # log name with absolute path and timestamp
        self.file = os.path.join(path, filename + time.strftime(varinfo.METRIC_LOGFILE_FORMAT, time.localtime()))
        # log object
        self.log = open(self.file, "w+")

    def getLogSize(self):
        """
        function : Get the log file size
        input : NA
        output : file size
        """
        return os.path.getsize(self.file)

    def isLogNeedSwitch(self):
        """
        function : Check whether log switchover is required
        input : NA
        output : result state
        """
        # Switch logs when file is lost or size limit is reached or every hour
        if not os.path.isfile(self.file) or self.getLogSize() >= varinfo.FILE_MAX_LOGSZIE * varinfo.DATA_TYPE_MBYTES:
            return True
        if time.strftime("-%Y-%m-%d_%H", time.localtime()) not in self.file:
            return True
        return False

    def logSwitch(self):
        """
        function : Switch the current log file to another
        input : NA
        output : NA
        """
        # Avoid residual file descriptors
        self.log.close()
        # If the log directory is deleted, create it here
        if not os.path.isdir(self.path):
            os.makedirs(self.path)
        self.file = os.path.join(self.path, self.filename + time.strftime(
            varinfo.METRIC_LOGFILE_FORMAT, time.localtime()))
        self.log = open(self.file, "w+")

    def logWrite(self, message):
        """
        function : Write the data to the log
        input : result data
        output : NA
        """
        # Overload logWrite to ensure that the file header contains query string
        if self.isLogNeedSwitch():
            self.logSwitch()
        self.logWriteAndTimerWithoutSwitch(message)

    def logFlush(self, message):
        """
        function : Make the log switch properly and write the data to the log
        input : log message
        output : NA
        """
        if self.isLogNeedSwitch():
            self.logSwitch()
        self.log.write(message)
        self.log.flush()

    def logWriteWithoutSwitch(self, message):
        """
        function : Write the data to the log without log switchover
        input : log message
        output : NA
        """
        self.log.write(message)
        self.log.flush()

    def logWriteAndTimer(self, message):
        """
        function : Make the log switch properly and write the data with timestamp to the log
        input : log message
        output : NA
        """
        timer = varinfo.RECORD_BEGIN_DELIMITER + \
                "\n[timer: " + time.strftime(varinfo.RECORD_TIMELABEL_FORMAT, time.localtime()) + "]\n"
        self.logFlush(timer + message)

    def logWriteAndTimerWithoutSwitch(self, message):
        """
        function : Write the data with timestamp to the log without log switchover
        input : log message
        output : NA
        """
        self.logWriteWithoutSwitch(message)

    def __del__(self):
        """
        Destructor
        """
        self.log.close()


class RunningLog:
    """
    Classify method to manage logs
    """
    def __init__(self, runMode):
        """
        Constructor
        """
        # script startup time
        self.runMode = runMode
        self.logBase = os.path.join(varinfo.METRIC_RUNNING_LOG, runMode)
        if not os.path.isdir(self.logBase):
            os.makedirs(self.logBase)
        # log retention size, unit: byte
        self.logsize = varinfo.METRIC_DEFAULT_LOGSIZE_PER_FILE
        # log retention time, unit: second
        self.maxFileCount = os.path.join(varinfo.METRIC_RUNNING_LOG, runMode)
        # managed log files
        self.curFileBase = os.path.join(self.logBase, runMode)
        self.curFile = os.path.join(self.curFileBase +
                                    time.strftime(varinfo.FILE_TIME_FORMAT, time.localtime()) + ".log")
        # management interval
        self.interval = varinfo.CLOCK_TYPE_MINS
        # log object
        self.log = open(self.curFile, "w+")
        self.modLevel = {}
        self.reloadLogModule(os.path.join(varinfo.METRIC_CONFIG, "logconf.json"))

    def getLogSize(self):
        """
        function : Get the log file size
        input : NA
        output : file size
        """
        return os.path.getsize(self.curFile)

    def isLogNeedSwitch(self):
        """
        function : Check whether log switchover is required
        input : NA
        output : result state
        """
        # Switch logs when file is lost or size limit is reached or every hour
        if not os.path.isfile(self.curFile) or self.getLogSize() >= varinfo.METRIC_DEFAULT_LOGSIZE_PER_FILE:
            return True
        if time.strftime("-%Y-%m-%d_%H", time.localtime()) not in self.curFile:
            return True
        return False

    def logRecycle(self):
        """
        function : Register the names and paths of logs to be managed
        input : file path, file name
        output : NA
        """
        logList = glob.glob(self.logBase + "/*.log")
        logList.sort()
        count = len(logList)
        if count <= varinfo.METRIC_MAX_LOG_COUNT:
            return
        for i in range(0, count - varinfo.METRIC_MAX_LOG_COUNT):
            if os.path.isfile(logList[i]):
                os.remove(logList[i])
                recordError(LOG_MODULE, "%s is removed" % logList[i])

    def LogRecycleSched(self, clock):
        """
        function : Main loop interface for log management
        input : NA
        output : NA
        """
        if clock % varinfo.METRIC_LOG_RECYCLE_INTERVAL == 0:
            self.logRecycle()

    def logSwitch(self):
        """
        function : Switch the current log file to another
        input : NA
        output : NA
        """
        # Avoid residual file descriptors
        self.log.close()
        # If the log directory is deleted, create it here
        if not os.path.isdir(self.curFileBase):
            os.makedirs(self.curFileBase)
        self.curFile = os.path.join(self.curFileBase + time.strftime(
            varinfo.METRIC_LOGFILE_FORMAT, time.localtime()))
        self.log = open(self.curFile, "w+")

    def logFlush(self, message):
        """
        function : Make the log switch properly and write the data to the log
        input : log message
        output : NA
        """
        if self.isLogNeedSwitch():
            self.logSwitch()
        self.log.write(message + "\n")
        self.log.flush()

    def logWriteWithoutSwitch(self, message):
        """
        function : Write the data to the log without log switchover
        input : log message
        output : NA
        """
        self.log.write(message + "\n")
        self.log.flush()

    def logWriteAndTimer(self, message):
        """
        function : Make the log switch properly and write the data with timestamp to the log
        input : log message
        output : NA
        """
        timer = time.strftime(varinfo.RECORD_TIMELABEL_FORMAT, time.localtime()) + " "
        self.logFlush(timer + message)

    def reloadLogModule(self, logConfig):
        modConf = jconf.GetLogModudeState(logConfig)
        for key in modConf.keys():
            if "_comment" in key:
                continue
            self.modLevel[key] = LogLevel(modConf[key])

    def GetModuleLevel(self, module):
        if module in self.modLevel.keys():
            return self.modLevel[module]
        return LogLevel("LOG")
