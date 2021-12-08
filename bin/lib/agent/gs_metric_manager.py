#!/usr/bin/env python
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
    import commands
    import signal
    from threading import Thread
    from lib.agent.gs_pusher import Pusher
    from lib.common import gs_constvalue as varinfo
    from lib.common import gs_enumerate as enum
    from lib.common.CommonCommand import CommonCommand as commander
    from lib.common import gs_envchecker as checker, gs_jsonconf as jconf, gs_logmanager as logmgr
    from lib.common.gs_threadpool import GaussThreadPool
except Exception as e:
    sys.exit("FATAL: %s Unable to import module: %s" % (__file__, e))

LOG_MODULE = 'METRIC Manager'


class MetricItem(object):
    """
    Constructor
    """

    def __init__(self, itemDefine, metricSource):
        self.name, itemdict = itemDefine
        self.metricType = enum.MetricMethod(itemdict['type'])

        collector = itemdict['collector']
        self.collectMethod = enum.CollectorMethod(collector['method'])
        self.collectInterval = max(int(collector['interval']), varinfo.METRIC_MIN_ITEM_INTERVAL)
        self.collectTimes = int(collector['times'])

        metricFunc = itemdict['metric_func']
        if self.metricType == enum.MetricMethod("query"):
            self.queryInstance = metricFunc["query_type"]
            self.queryDatabase = metricFunc["query_database"]
            if ".sql" in metricFunc["query_string"]:
                queryFile = os.path.join(varinfo.METRIC_ITEM_DIR, metricSource, metricFunc['query_string'])
                self.queryString = commander.openFile(queryFile, "r")
            else:
                self.queryString = metricFunc["query_string"]

        if self.metricType == enum.MetricMethod("command"):
            if ".sh" in metricFunc["command"]:
                commandFile = os.path.join(varinfo.METRIC_ITEM_DIR, metricSource, metricFunc['command'])
                self.cmdCommand = "sh " + commandFile
            elif ".py" in metricFunc["command"]:
                commandFile = os.path.join(varinfo.METRIC_ITEM_DIR, metricSource, metricFunc['command'])
                self.cmdCommand = "python " + commandFile
            else:
                self.cmdCommand = metricFunc["command"]
            self.cmdOption = metricFunc["option"]
            self.cmdFormation = metricFunc["formation"]

        table = itemdict['table']
        self.tableName = table["name"]
        self.tableDefine = table["define"]


class MetricJob(object):
    """
    Constructor
    """

    def __init__(self, metricItem, hostname):
        self.metricItem = metricItem
        self.hostname = hostname
        self.collectMethod = metricItem.collectMethod
        self.lastSchedTick = 0
        self.interval = max(int(metricItem.collectInterval), varinfo.METRIC_MIN_ITEM_INTERVAL)
        self.schedState = enum.ScheduleState('offline')
        self.logDir = ""

    def itemEnable(self):
        self.collectMethod = enum.CollectorMethod('durative')

    def itemDisable(self):
        self.collectMethod = enum.CollectorMethod('off')

    def itemSchelule(self, threadPool, runProgress, clockTick):
        if self.collectMethod == enum.CollectorMethod('off'):
            return
        self.lastSchedTick = clockTick
        threadPool.Submit(runProgress, self.interval)

    def GetLastSchedTick(self):
        return self.lastSchedTick

    def GetItemCollectMethod(self):
        return self.collectMethod

    def IsItemScheduled(self):
        if self.schedState == enum.ScheduleState('schedule'):
            return True
        else:
            return False


class DatabaseMetricJob(MetricJob):
    """
    Classify method to execute database metric item
    """

    def __init__(self, metricItem, hostname, instance, database):
        """
        Constructor
        """
        super(DatabaseMetricJob, self).__init__(metricItem, hostname)
        self.instance = instance
        self.database = database

        queryInstance = self.metricItem.queryInstance
        if enum.QueryType(queryInstance) == enum.QueryType(instance.instType) \
                or enum.QueryType(queryInstance) == enum.QueryType("instance"):
            self.schedState = enum.ScheduleState('schedule')
        else:
            self.schedState = enum.ScheduleState('offline')

        logDir = os.path.join(varinfo.METRIC_DATA_BASE_DIR, 'database', instance.nodename, self.metricItem.name)
        self.dblog = logmgr.MetricLog(logDir, self.metricItem.name)
        logmgr.recordError(LOG_MODULE, "new database metric added in instance %s: metric name: %s sched:%s, log path %s"
                           % (instance.nodename, self.metricItem.name, str(self.schedState), logDir))

    def query(self):
        """
        function : Get the database query result by gsql command
        input : NA
        output : result information
        """
        port = self.instance.port
        queryString = self.metricItem.queryString
        sqlList = queryString.strip().split(";")
        sqlList = [element for element in sqlList if element != ""]
        results = []
        for sql in sqlList:
            if str(sql).lower().startswith('set'):
                continue
            try:
                logmgr.recordError(self.metricItem.name, "execute metric sql: %s" % sql)
                (status, result, err_output) = commander.executeSqlOnLocalhost(sql, port, self.database)
                if status != varinfo.PGRES_TUPLES_OK:
                    logmgr.recordError(LOG_MODULE, "Failed to execute SQL: %s." % sql + " Error:\n%s" % err_output)
                else:
                    results.append(result)
            except Exception as e:
                logmgr.recordError(LOG_MODULE, "exception occur while execute SQL: %s. exception: %s"
                                   % (sql, e), "DEBUG")
        return self.formatResult(results, self.instance.nodename)

    def runMetric(self):
        """
        function : Main loop interface for metric database item
        input : global threads, global dbitem
        output : NA
        """
        logmgr.recordError(LOG_MODULE, "[%s], metric name:[%s], scheduled at clock %d "
                           % (self.instance.nodename, self.metricItem.name, self.GetLastSchedTick()), "DEBUG")
        if not self.instance.checkNodeState("Main"):
            return
        output = self.query()
        if output is not None and output != "":
            self.dblog.logWrite(output)

    def formatResult(self, results, instanceId):
        output = ""
        now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        for result in results:
            for row in result:
                if str(row).lower().startswith("set"):
                    continue
                for index in range(len(row)):
                    cell = row[index]
                    cell = cell.replace("|", "$$")
                    cell = cell.replace("\n", " ")
                    row[index] = cell
                data = "|".join(row)
                output += ("%s|%s|%s|" % (now, self.hostname, instanceId) + data + "\n")
        return output


class SystemMetricJob(MetricJob):
    """
    Classify method to execute system metric item
    """

    def __init__(self, metricItem, hostname):
        """"
        Constructor
        """
        super(SystemMetricJob, self).__init__(metricItem, hostname)
        self.schedState = enum.ScheduleState('schedule')
        logDir = os.path.join(varinfo.METRIC_DATA_BASE_DIR, 'system', self.metricItem.name)
        self.dblog = logmgr.MetricLog(logDir, self.metricItem.name)
        logmgr.recordError(LOG_MODULE, "new system metric added in metric name: %s sched:%s, log path %s"
                           % (self.metricItem.name, str(self.schedState), logDir))

    def commandCheck(self):
        """"
        check Command has dangerous command
        """
        # TODO
        return True

    def runCommand(self):
        """
        function : Get the system query result by shell command
        input : NA
        output : result information
        """
        metricItem = self.metricItem
        cmd = metricItem.cmdCommand + " " + metricItem.cmdOption + '|' + metricItem.cmdFormation
        # logmgr.recordError(metricItem.name, "execute metric command: %s" % cmd)
        status, result = commands.getstatusoutput(cmd)
        if status != 0:
            logmgr.recordError(LOG_MODULE, "Failed to execute command: %s." % cmd + " Error:\n%s" % result)
            return ""
        return self.formatResult(result, "system")

    def runMetric(self):
        """
        function : Main loop interface for metric database item
        input : global threads, global dbitem
        output : NA
        """
        logmgr.recordError(LOG_MODULE, "[SYS], metric name:[%s], scheduled at clock %d "
                           % (self.metricItem.name, self.GetLastSchedTick()), "DEBUG")
        output = self.runCommand()
        if output is not None and output != "":
            # logmgr.recordError(self.metricItem.name, "command result: %s" % output)
            self.dblog.logWrite(output)

    def formatResult(self, result, instanceId):
        output = ""
        now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        result = result.split("\n")
        for row in result:
            output += ("%s|%s|%s|" % (now, self.hostname, instanceId) + row + "\n")
        return output


class MetricManager():
    """
    function:
    """

    def __init__(self, metricMgrConfjson, itemDirList, options):
        self.maxThreads = int(metricMgrConfjson['max_threads'])
        self.clusterName = metricMgrConfjson['pusher']["cluster_name"]
        self.metricMgrConfjson = metricMgrConfjson
        self.gsMatricPool = GaussThreadPool(self.maxThreads)
        self.metricConfig = ""
        self.clockcount = 0
        self.stopflag = 0
        self.itemRefreshflag = 1
        self.pushConfigFlag = 1
        self.itemDirList = itemDirList
        self.itemList = []
        self.jobList = []
        self.itemListDict = {}
        self.hostname = options.hostname
        self.instanceList = options.dbNodeList
        self.databases = self.getDatabases()
        signal.signal(signal.SIGINT, lambda signal, frame: self._signal_handler())
        signal.signal(signal.SIGUSR2, lambda signal, frame: self._metric_handler())
        self.terminated = False
        if "pusher" in metricMgrConfjson.keys():
            self.pusher = Pusher(metricMgrConfjson['pusher'])

    def _signal_handler(self):
        self.terminated = True
        sys.exit()

    def _metric_handler(self):
        label = open(varinfo.METRIC_SIGFLAG_FILE, "r").read().split('\n')
        flag = label[0]
        item = label[1]
        if "add" in flag:
            self.pushConfigFlag = 1
            self.itemRefreshflag = 1
        if "disable" in flag:
            self.disableMetric(item)
        if "enable" in flag:
            self.enableMetric(item)
        os.remove(varinfo.METRIC_SIGFLAG_FILE)

    def disableMetric(self, name):
        for item in self.itemList:
            if name not in item.name:
                continue
            item.itemDisable()
        return

    def enableMetric(self, name):
        for item in self.itemList:
            if name not in item.name:
                continue
            item.itemEnable()
        return

    def clockTick(self):
        """
        function : scheduler timer
        input : NA
        output : NA
        """
        time.sleep(1)
        self.clockcount = self.clockcount + 1

    def getClockTick(self):
        return self.clockcount

    def initQueryType(self, item):
        queryType = [item["metric_func"]["query_type"]]
        if queryType[0] == "none":
            queryType = []
        if queryType[0] == "instance":
            queryType = ["coordinator", "datanode"]
        return queryType

    def initDatabaseList(self, item):
        database = [item["metric_func"]["query_database"]]
        if database[0].lower() == "all":
            database = self.databases
        return database

    def getDatabases(self):
        firstPrimaryInstance = [element for element in self.instanceList if "master" in element.datadir][0]
        querySql = "select datname from pg_database"
        result = []
        try:
            (status, result, err_output) = commander.executeSqlOnLocalhost(querySql, firstPrimaryInstance.port)
            if status != varinfo.PGRES_TUPLES_OK:
                raise Exception("Failed to execute SQL: %s." % querySql + " Error:\n%s" % err_output)
            if len(result) == 0:
                raise Exception("Failed to execute SQL: %s." % querySql + " Return record is null")
        except Exception as e:
            logmgr.recordError(LOG_MODULE, "exception occur while execute SQL: %s. exception: %s"
                               % (querySql, e), "DEBUG")
        database = [str(element[0]).strip() for element in result if
                    "template1" not in element and "template0" not in element]
        return database

    def initMetricItem(self, metricList, metricSource):
        logmgr.recordError(LOG_MODULE, "transfer metric conf to item")
        nameList = map(lambda metricItem: metricItem.name, self.itemList)
        for itemName in metricList.keys():
            if itemName in nameList:
                continue
            item = metricList[itemName]
            self.itemList.append(MetricItem((itemName, item), metricSource))

    def createJob(self, metricItem):
        for instance in self.instanceList:
            for database in self.databases:
                self.jobList.append(DatabaseMetricJob(metricItem, self.hostname, instance, database))

    def initMetricJob(self):
        logmgr.recordError(LOG_MODULE, "init metric job base on metric item")
        jobNameList = map(lambda metricJob: metricJob.metricItem.name, self.jobList)
        for metricItem in self.itemList:
            if metricItem.name in jobNameList:
                continue
            if metricItem.collectMethod == "off":
                continue
            if metricItem.metricType == enum.MetricMethod("command"):
                self.jobList.append(SystemMetricJob(metricItem, self.hostname))
            elif metricItem.metricType == enum.MetricMethod("query"):
                self.createJob(metricItem)
            else:
                logmgr.recordError(LOG_MODULE, "init metric job found illegal metric type: %s" % metricItem.metricType)

    def itemListRefresh(self):
        if self.itemRefreshflag == 0:
            return
        logmgr.recordError(LOG_MODULE, "start fresh metric item")
        for directory in self.itemDirList:
            checkpath = os.path.join(varinfo.METRIC_ITEM_DIR, directory, "metricdef.json")
            if not os.path.isfile(checkpath):
                logmgr.recordError(LOG_MODULE, "Failed to get json in %s" % checkpath)
                continue
            metriclist = jconf.MetricItemListGet(checkpath)
            self.initMetricItem(metriclist, directory)
            self.initMetricJob()
        self.itemRefreshflag = 0
        logmgr.recordError(LOG_MODULE, "end fresh metric item")

    def itemListSchedule(self):
        currentClock = self.getClockTick()
        if currentClock % 10 == 0:
            logmgr.recordError(LOG_MODULE, "current clock is %d" % currentClock)
        for job in self.jobList:
            if job.GetItemCollectMethod() == enum.CollectorMethod('off'):
                continue
            if job.IsItemScheduled() is False:
                continue
            if currentClock - job.GetLastSchedTick() >= job.interval:
                job.itemSchelule(self.gsMatricPool, job.runMetric(), currentClock)

    def dataMetric(self):
        logmgr.recordError(LOG_MODULE, "start data metric.")
        while self.stopflag == 0:
            self.clockTick()
            self.itemListRefresh()
            self.itemListSchedule()
            if self.terminated == 1:
                self.gsMatricPool.CleanPool(False)
                break

    def loadTableMap(self):
        for directory in self.itemDirList:
            checkPath = os.path.join(varinfo.METRIC_ITEM_DIR, directory, "metricdef.json")
            if not os.path.isfile(checkPath):
                logmgr.recordError(LOG_MODULE, "Failed to get json in %s" % checkPath)
                continue
            metricList = jconf.MetricItemListGet(checkPath)
            for item in metricList.keys():
                if item not in self.itemListDict.keys():
                    self.itemListDict[item] = {'table': metricList[item]['table']}

    def registerOnServer(self):
        logmgr.recordError(LOG_MODULE, "start register on server ...")
        pushConfig = self.metricMgrConfjson["pusher"]
        targetPath = pushConfig["base_url"]
        clusterPath = targetPath + "/" + pushConfig['cluster_name']
        if self.pusher.pusher.checkUrlOption(clusterPath):
            logmgr.recordError(LOG_MODULE, "found cluster path: %s on server, no need to register" % clusterPath)
            return
        self.loadTableMap()
        tableMapFile = os.path.join(varinfo.PUSHER_BUFFER_PATH, self.clusterName + "_" + varinfo.TABLE_MAP_FILE)
        jconf.SaveJsonConf(self.itemListDict, tableMapFile)
        self.pusher.pusher.pushFileToServer(tableMapFile, targetPath, 10)
        hostListFile = os.path.join(varinfo.PUSHER_BUFFER_PATH, self.clusterName + "_" + varinfo.HOST_LIST_FILE)
        self.pusher.pusher.pushFileToServer(hostListFile, targetPath, 10)
        logmgr.recordError(LOG_MODULE, "successfully to push file: %s and %s to server" % (tableMapFile, hostListFile))

    def startManager(self):
        logmgr.recordError(LOG_MODULE, "agent is starting ...")
        self.registerOnServer()

        pusher = PushThread('push', self.metricMgrConfjson["pusher"])
        pusher.start()

        self.dataMetric()


class PushThread(Thread):
    def __init__(self, name, metricMgrConfjson):
        super(PushThread, self).__init__()
        self.name = name
        self.metricMgrConfjson = metricMgrConfjson
        self.pusher = Pusher(metricMgrConfjson)
        logmgr.recordError(self.name, "init push thread.")

    def run(self):
        logmgr.recordError(self.name, "start push thread.")
        while True:
            time.sleep(self.metricMgrConfjson["interval"])
            self.pusher.PusherSchedule()


def RunMetricManager():
    """
    function : The interface of operation execution
    input : NA
    output : NA
    """
    # Initialize and check parameters
    logmgr.StartLogManager('agent')
    options = checker.RunEnvironment()
    options.SetAppName('Agent')
    options.initParameter()
    options.checkParameter()
    metricMgrConfjson = jconf.GetMetricManagerJsonConf(os.path.join(varinfo.METRIC_CONFIG, "client_conf.json"))
    options.SaveClusterHostList(metricMgrConfjson['GlobalManager']['pusher']["cluster_name"])
    itemDirList = ['metric_default', 'metric_user_define']
    metricMgr = MetricManager(metricMgrConfjson['GlobalManager'], itemDirList, options)
    metricMgr.startManager()
