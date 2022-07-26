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
    sys.path.append(os.path.dirname(__file__))
    if os.getenv('GPHOME'):
        sys.path.remove(os.path.join(os.getenv('GPHOME'), 'lib'))
    import signal
    from threading import Thread
    import lib.common.CommonCommand as common
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
                self.cmdCommand = "%s " % common.judgeVersion + commandFile
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
        # query_type is paramater in metricdef.json; instance.type is in dbInfo.json after starting;
        # 1. query_type is 'coordinator' or 'datanode',instance.type is same as query_type;
        #        it means the item will do on all coordinators or all datanodes.
        # 2. query_type is 'instance',instance.type is 'coordinator' or 'datanode';
        #        it means the item will do on all coordinators and all datanodes.
        # 3. query_type is 'ccn', instance.type is 'coordinator'; it means the item will do on all coordinators.
        if enum.QueryType(queryInstance) == enum.QueryType(instance.type) \
                or enum.QueryType(queryInstance) == enum.QueryType("instance") \
                or (enum.QueryType(queryInstance) == enum.QueryType("ccn")
                    and enum.QueryType(instance.type) == enum.QueryType("coordinator")):
            self.schedState = enum.ScheduleState('schedule')
            logDir = os.path.join(varinfo.METRIC_DATA_BASE_DIR, 'database', instance.instanceName, self.metricItem.name)
            self.dblog = logmgr.MetricLog(logDir, self.metricItem.name + "_" + self.database)
        else:
            self.schedState = enum.ScheduleState('offline')
        logmgr.record(LOG_MODULE, "new database metric added in instance %s, metric name: %s, database:%s,"
                                       " queryInstance:%s, ccn:%s, instancetype:%s, coordinator:%s, schedState:%s,"
                           % (instance.instanceName, self.metricItem.name, database, enum.QueryType(queryInstance),
                              enum.QueryType("ccn"), enum.QueryType(instance.type), enum.QueryType("coordinator"),
                              str(self.schedState)))


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
        sql_time_str = ""
        sql_string = ""
        for sql in sqlList:
            if str(sql).lower().startswith('set'):
                sql_time_str = str(sql).strip('\n')
                continue
            try:
                sql_string = sql_time_str + ";" + sql
                logmgr.record(self.metricItem.name, "execute metric sql: %s" % sql_string)
                (status, result) = commander.runGsqlCommandWithSeparator(sql_string, port, self.database)
                if status != 0:
                    logmgr.record(LOG_MODULE, "Failed to execute SQL: %s." % sql_string + " Error:\n%s" % result)
                else:
                    results.append(result)
            except Exception as e:
                logmgr.record(LOG_MODULE, "exception occur while execute SQL: %s. exception: %s"
                                   % (sql_string, e), "DEBUG")
        return self.formatResult(results, self.instance.instanceName)

    def is_ccn(self):
        port = self.instance.port
        sql = "select node_name from pgxc_node where nodeis_central;"
        (status, result) = commander.runGsqlCommand(sql, port, "postgres")
        if status != 0:
            logmgr.record(LOG_MODULE, "Failed to get ccn: %s." % sql + " Error:\n%s" % result)
            return False
        else:
            logmgr.record(LOG_MODULE, "Get ccn result:%s, instanceName:%s." % (result, self.instance.instanceName))
            if result.strip() == self.instance.instanceName:
                return True
            else:
                return False

    def runMetric(self):
        """
        function : Main loop interface for metric database item
        input : global threads, global dbitem
        output : NA
        """
        logmgr.record(LOG_MODULE, "instance name:[%s], database name:[%s], metric name:[%s], scheduled at clock %d"
                           % (self.instance.instanceName, self.database, self.metricItem.name, self.GetLastSchedTick()))
        # 1. the instance is not coordinator or not master datanode, will skip it.
        # 2. the instance is coordinator, the query_type is ccn, and current coordinator is not ccn, will skip it.
        if not self.instance.checkNodeState("Main"):
            return
        if (enum.QueryType(self.metricItem.queryInstance) == enum.QueryType("ccn")
                and enum.QueryType(self.instance.type) == enum.QueryType("coordinator") and not self.is_ccn()):
            return
        output = self.query()
        if output is not None and output != "":
            self.dblog.logFlush(output)
            cmd = "mv %s %s" % (self.dblog.file, self.dblog.file + ".ready")
            status, result = common.runShellCommand(cmd)
            if status != 0:
                logmgr.record(LOG_MODULE, "Filed to rename %s file, Error:%s." % (self.dblog.file + ".ready", result))
            else:
                logmgr.record(LOG_MODULE, "%s file is ready to compress." % (self.dblog.file + ".ready"))
        else:
            logmgr.record(LOG_MODULE, "No data is collected for item[%s]." % self.metricItem.name)

    def formatResult(self, results, instanceId):
        output = ""
        now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        for result in results:
            for row in result:
                if not row or str(row).lower().startswith("set"):
                    continue
                for index in range(len(row)):
                    cell = row[index]
                    cell = cell.replace("|", "$$")
                    cell = cell.replace("\n", " ")
                    cell = cell.replace("\r", " ")
                    row[index] = cell
                output = "%s%s%s\n"  % (output, "%s|%s|%s|" % (now, self.hostname, instanceId), "|".join(row))
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
        logmgr.record(LOG_MODULE, "new system metric added in metric name: %s sched:%s, log path %s"
                           % (self.metricItem.name, str(self.schedState), logDir))

    def commandCheck(self):
        """"
        check Command has dangerous command
        """
        return True

    def runCommand(self):
        """
        function : Get the system query result by shell command
        input : NA
        output : result information
        """
        metricItem = self.metricItem
        cmd = metricItem.cmdCommand + " "
        if metricItem.cmdOption:
            cmd += metricItem.cmdOption
        if metricItem.cmdFormation:
            cmd += '|' + metricItem.cmdFormation
        # logmgr.record(metricItem.name, "execute metric command: %s" % cmd)
        status, result = common.runShellCommand(cmd)
        if status != 0:
            logmgr.record(LOG_MODULE, "Failed to execute command: %s." % cmd + " Error:\n%s" % result)
            return ""
        return self.formatResult(result, "system")

    def runMetric(self):
        """
        function : Main loop interface for metric database item
        input : global threads, global dbitem
        output : NA
        """
        logmgr.record(LOG_MODULE, "[SYS], metric name:[%s], scheduled at clock %d "
                           % (self.metricItem.name, self.GetLastSchedTick()), "DEBUG")
        output = self.runCommand()
        if output is not None and output != "":
            self.dblog.logWrite(output)
            cmd = "mv %s %s" % (self.dblog.file, self.dblog.file + ".ready")
            status, result = common.runShellCommand(cmd)
            if status != 0:
                logmgr.record(LOG_MODULE, "Filed to rename %s file, Error:%s." % (self.dblog.file + ".ready", result))
            else:
                logmgr.record(LOG_MODULE, "%s file is ready to compress." % self.dblog.file + ".ready")

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
        self.check_maxThreads()
        self.clusterName = metricMgrConfjson['pusher']["cluster_name"]
        self.check_clusterName()
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

    def check_maxThreads(self):
        if not self.maxThreads:
            raise Exception("[max_threads] is not exists or not a number."
                            " Please check whether the parameters are correct.")

    def check_clusterName(self):
        if not self.clusterName:
            raise Exception("[cluster_name] is not exists. Please check whether the parameters are correct.")
        if self.clusterName[0].isdigit():
            raise Exception("[cluster_name] do not support start with digtal.")
        if not self.clusterName.isalnum():
            raise Exception("[cluster_name] do not support characters except letters and digits.")

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
        time.sleep(5)
        self.clockcount = self.clockcount + 5

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
        database = item.queryDatabase
        if database.lower() == "all":
            database = self.databases
            return database
        else:
            return [database]

    def getDatabases(self):
        firstPrimaryInstance = [element for element in self.instanceList if element.instanceType in [-1, 0]][0]
        querySql = "select datname from pg_database"
        result = []
        try:
            (status, result) = commander.runGsqlCommand(querySql, firstPrimaryInstance.port)
            if status != 0:
                raise Exception("Failed to execute SQL: %s." % querySql + " Error:\n%s" % result)
            if len(result) == 0:
                raise Exception("Failed to execute SQL: %s." % querySql + " Return record is null")
        except Exception as e:
            logmgr.record(LOG_MODULE, "exception occur while execute SQL: %s. exception: %s"
                               % (querySql, e), "DEBUG")
        database = [str(element).strip() for element in result.splitlines() if
                    "template1" not in element and "template0" not in element and "gsmetric" not in element]
        return database

    def initMetricItem(self, metricList, metricSource):
        logmgr.record(LOG_MODULE, "transfer metric conf to item")
        nameList = map(lambda metricItem: metricItem.name, self.itemList)
        for itemName in metricList.keys():
            if itemName in nameList:
                continue
            item = metricList[itemName]
            self.itemList.append(MetricItem((itemName, item), metricSource))

    def createJob(self, metricItem):
        dbs = self.initDatabaseList(metricItem)
        for instance in self.instanceList:
            for database in dbs:
                job = DatabaseMetricJob(metricItem, self.hostname, instance, database)
                if job.schedState == enum.ScheduleState('offline'):
                    continue
                self.jobList.append(job)

    def initMetricJob(self):
        logmgr.record(LOG_MODULE, "init metric job base on metric item")
        jobNameList = list(map(lambda metricJob: metricJob.metricItem.name, self.jobList))
        for metricItem in self.itemList:
            if metricItem.name in jobNameList:
                continue
            if metricItem.collectMethod == enum.CollectorMethod("off"):
                continue
            if metricItem.metricType == enum.MetricMethod("command"):
                self.jobList.append(SystemMetricJob(metricItem, self.hostname))
            elif metricItem.metricType == enum.MetricMethod("query"):
                self.createJob(metricItem)
            else:
                logmgr.record(LOG_MODULE, "init metric job found illegal metric type: %s" % metricItem.metricType)

    def itemListRefresh(self):
        if self.itemRefreshflag == 0 and self.getClockTick() % 86400:
            return
        logmgr.record(LOG_MODULE, "start fresh metric item")
        for directory in self.itemDirList:
            checkpath = os.path.join(varinfo.METRIC_ITEM_DIR, directory, "metricdef.json")
            if not os.path.isfile(checkpath):
                logmgr.record(LOG_MODULE, "Failed to get json in %s" % checkpath)
                continue
            metriclist = jconf.MetricItemListGet(checkpath)
            self.initMetricItem(metriclist, directory)
            self.initMetricJob()
        self.itemRefreshflag = 0
        logmgr.record(LOG_MODULE, "end fresh metric item")

    def freshActiveJobs(self):
        active_jobs = []
        currentClock = self.getClockTick()
        for job in self.jobList:
            if job.GetItemCollectMethod() == enum.CollectorMethod('off') or not job.IsItemScheduled():
                logmgr.record(LOG_MODULE, "current clock is %d, metricitem:%s is off" % (currentClock,
                                                                                         job.metricItem.name))
                continue
            elif currentClock - job.GetLastSchedTick() >= job.interval:
                job.lastSchedTick = currentClock
                job.schedState = enum.ScheduleState('offline')
                active_jobs.append(job)
        return active_jobs

    def itemSchelule(self, job):
        try:
            currentClock = self.getClockTick()
            logmgr.record(LOG_MODULE, "current clock is %d, metricitem:%s start" % (currentClock,
                                                                                         job.metricItem.name))
            job.runMetric()
            job.schedState = enum.ScheduleState('schedule')
            logmgr.record(LOG_MODULE, "current clock is %d, metricitem:%s finish" % (currentClock,
                                                                                          job.metricItem.name))
        except Exception as e:
            logmgr.record(LOG_MODULE, job.metricItem.name + ", " + str(e))

    def dataMetric(self):
        logmgr.record(LOG_MODULE, "start data metric.")
        import multiprocessing.dummy as ProcessPool
        pool = ProcessPool.Pool(self.maxThreads)
        while self.stopflag == 0:
            try:
                self.clockTick()
                self.itemListRefresh()
                active_jobs = self.freshActiveJobs()
                pool.imap(self.itemSchelule, active_jobs)
                if self.terminated == 1:
                    self.gsMatricPool.CleanPool(False)
                    break
            except Exception as e:
                logmgr.record(LOG_MODULE, "Failed to do data metric in %s.Error:%s" % (self.clockcount, str(e)))
                continue
        pool.close()
        pool.join()

    def loadTableMap(self):
        for directory in self.itemDirList:
            checkPath = os.path.join(varinfo.METRIC_ITEM_DIR, directory, "metricdef.json")
            if not os.path.isfile(checkPath):
                logmgr.record(LOG_MODULE, "Failed to get json in %s" % checkPath)
                continue
            metricList = jconf.MetricItemListGet(checkPath)
            for item in metricList.keys():
                if item not in self.itemListDict.keys():
                    self.itemListDict[item] = {'table': metricList[item]['table']}

    def registerOnServer(self):
        logmgr.record(LOG_MODULE, "start register on server ...")
        pushConfig = self.metricMgrConfjson["pusher"]
        targetPath = pushConfig["base_url"]
        self.loadTableMap()
        tableMapFile = os.path.join(varinfo.PUSHER_BUFFER_PATH, self.clusterName + "_" + varinfo.TABLE_MAP_FILE)
        jconf.SaveJsonConf(self.itemListDict, tableMapFile)
        self.pusher.pusher.pushFileToServer(tableMapFile, targetPath, 10)
        hostListFile = os.path.join(varinfo.PUSHER_BUFFER_PATH, self.clusterName + "_" + varinfo.HOST_LIST_FILE)
        self.pusher.pusher.pushFileToServer(hostListFile, targetPath, 10)
        logmgr.record(LOG_MODULE, "successfully to push file: %s and %s to server" % (tableMapFile, hostListFile))

    def startManager(self):
        logmgr.record(LOG_MODULE, "agent is starting ...")
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
        logmgr.record(self.name, "init push thread.")

    def run(self):
        logmgr.record(self.name, "start push thread.")
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
