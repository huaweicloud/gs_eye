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
    import signal
    import lib.common.cluster.gs_instance_manager as dbinfo
    from lib.common import gs_constvalue as varinfo
    from lib.common import gs_envchecker as checker, gs_jsonconf as jconf, gs_logmanager as logmgr
    import lib.agent.gs_pusher as pusher
    from lib.common.gs_threadpool import GaussThreadPool
except Exception as e:
    sys.exit("FATAL: %s Unable to import module: %s" % (__file__, e))

LOG_MODULE = 'METRIC Manager'


def MetricMethod(method):
    """
    Method for metric generating
    none:    default value, only has metric define, but not gathered
    command: gathered by os tools, such as netstat, ps, top, etc.
    query:   gathered by sql language, which need to be gathered from database
    command_in_superuser: such as command, but need higher permission
    log:     gathered from formatting log, such as /var/log/message or pg_log, it also need the log's access permission
    """
    methodDict = {
        'none' : 0,
        'query' : 1,
        'command' : 2,
        'command_in_superuser' : 3,
        'log': 4
    }
    return methodDict[method]


def QueryType(queryType):
    """
    Type for metric query execute location
    none:    default value, meaning nothing
    coordinator: gathered on coordinator, only enabled on coordinator node.
    datanode:   gathered on datanode, only enabled on datanode node
    instance: gathered on all instance which indicated coordinator and datanode, enabled on all nodes
    """
    queryTypeDict = {
        'none' : 0,
        'coordinator' : 1,
        'datanode' : 2,
        'instance' : 3
    }
    return queryTypeDict[queryType]


def CollectorMethod(state):
    """
    State for metric
    off:      default value, current metric item is not in scheduler, will not be scheduled
    durative: meaning current metric item is in scheduler, will be scheduled in next interval
    times:  meaning current metric item is in scheduler, will be scheduled in N times then change to off
    dry:    only for testing
    """
    metricStateDict = {
        'off' : 0,
        'durative' : 1,
        'times' : 2,
        'dry' : 3
    }
    return metricStateDict[state]


def ScheduleState(state):
    """
    Method for metric generating
    none:    default value, only has metric define, but not gathered
    command: gathered by os tools, such as netstat, ps, top, etc.
    query:   gathered by sql language, which need to be gathered from database
    command_in_superuser: such as command, but need higher permission
    log:     gathered from formatting log, such as /var/log/message or pg_log, it also need the log's access permission
    """
    methodState = {
        'offline' : 0,
        'schedule' : 1,
    }
    return methodState[state]


class MetricItem(object):
    """
    Constructor
    """
    def __init__(self, itemDefine):
        self.name, itemdict = itemDefine
        self.method = MetricMethod(itemdict['type'])
        self.interval = int(itemdict['collector']['interval'])
        self.metricFunc = itemdict['metric_func']
        if self.interval < varinfo.METRIC_MIN_ITEM_INTERVAL:
            self.interval = varinfo.METRIC_DEFAULT_ITEM_INTERVAL
        self.collectMethod = CollectorMethod(itemdict['collector']['method'])
        self.lastSchedTick = 0
        self.schedState = ScheduleState('offline')
        self.logDir = ""

    def itemEnable(self):
        self.collectMethod = CollectorMethod('durative')

    def itemDisable(self):
        self.collectMethod = CollectorMethod('off')

    def itemSchelule(self, threadPool, runProgress, clockTick):
        if self.collectMethod == CollectorMethod('off'):
            return
        self.lastSchedTick = clockTick
        threadPool.Submit(runProgress, self.interval)

    def GetLastSchedTick(self):
        return self.lastSchedTick

    def GetItemCollectMethod(self):
        return self.collectMethod

    def IsItemScheduled(self):
        if self.schedState == ScheduleState('schedule'):
            return True
        else:
            return False


class DatabaseMetricItem(MetricItem):
    """
    Classify method to execute database metric item
    """
    def __init__(self, itemclass, itemDefine, instanceInfo):
        """
        Constructor
        """
        super(DatabaseMetricItem, self).__init__(itemDefine)
        # metric type
        self.queryType = QueryType(self.metricFunc['query_type'])
        # metric string
        if '.sql' in self.metricFunc['query_string']:
            queryFile = os.path.join(varinfo.METRIC_ITEM_DIR, itemclass, self.metricFunc['query_string'])
            self.queryString = open(queryFile, "r").read()
        else:
            self.queryString = self.metricFunc['query_string']
        # number of execution failures
        self.failureCount = 0
        tempFileName = ".tmp_gs_metric_" + self.name
        self.tempfile = os.path.join(varinfo.METRIC_ITEM_DIR, itemclass, tempFileName)
        self.instanceInfo = instanceInfo
        database = itemDefine[1]['metric_func']['query_database']
        self.queryCmd = "gsql -d %s" % database + " -p %s " % instanceInfo.port + " -f "
        if self.queryType == QueryType(instanceInfo.instType) or self.queryType == QueryType("instance"):
            self.schedState = ScheduleState('schedule')
        else:
            self.schedState = ScheduleState('offline')
        logDir = os.path.join(varinfo.METRIC_DATA_BASE_DIR, 'database', instanceInfo.nodename, self.name)
        self.dblog = logmgr.MetricLog(logDir, self.name)
        self.updateQueryString()
        logmgr.recordError(LOG_MODULE, "new database metric added in instance %s: metric name: %s sched:%s, log path %s"
                           % (instanceInfo.nodename, self.name, str(self.schedState), logDir))

    def query(self):
        """
        function : Get the database query result by gsql command
        input : NA
        output : result information
        """
        status, output = commands.getstatusoutput(self.queryCmd + self.tempfile)
        logmgr.recordError(LOG_MODULE, "get query result on node %s for item %s query %s"
                           % (self.instanceInfo.nodename, self.name, self.queryCmd + self.tempfile), "DEBUG")
        if status != 0 or not output:
            logmgr.recordError(LOG_MODULE, "Failed to get query result on node %s for item %s, result %s"
                               % (self.instanceInfo.nodename, self.name, output))
            output = "[DBMetric]: " + output
            self.failureCount += 1
            if self.failureCount >= varinfo.METRIC_MAX_FAILURE:
                # Query the instance status after five consecutive failures
                self.state = dbinfo.getNodeState("DBMetric")
        else:
            # Refresh number of failed after successful query
            self.failureCount = 0
        output = output.replace("GS_LABEL_HEAD\\", "GS_LABEL_HEAD")
        return output

    def reorganizeQuery(self):
        """
        function : Parse the metric item file to get the valid sql
        input : NA
        output : valid sql
        """
        # Set the timeout period to avoid residual sql
        sql = ""
        for query in self.queryString.split(';'):
            query = query.strip()
            # Skip empty sql
            if not query:
                continue
            elif query.lower().startswith("set"):
                sql += ("%s;\n" % query)
            # Use copy to wrap the SQL to get the formatted data
            elif query.lower().startswith("select"):
                sql += ("copy (%s) to stdout delimiter '|';\n" %
                        ("select 'GS_LABEL_HEAD' , * from (" + query + ") tmp"))
            # Prevent command injection for abnormal sql
            else:
                logmgr.recordError(LOG_MODULE, "Invalid sql in file %s query %s" % (self.tempfile, query), "PANIC")
        if sql:
            sql = "set statement_timeout = %d;\n%s" % (self.interval * 1000, sql)
        return sql

    def createTempFile(self):
        """
        function : Create temporary file that are actually executed
        input : NA
        output : NA
        """
        # Separate the resulting data using delimiter
        delimiter = ";\ncopy (select '%s') to stdout;" % (varinfo.DATA_TYPE_DELIMITER)
        with open(self.tempfile, "w") as file:
            file.write(self.queryString.replace(';', delimiter))
        file.close()

    def updateQueryString(self):
        """
        function : Check whether the metric item query string has been changed
        input : NA
        output : NA
        """
        queryString = self.reorganizeQuery()
        if self.queryString != queryString:
            self.queryString = queryString
            # If there are changes, write the new query string to the temporary file
            self.createTempFile()

    def runMetric(self):
        """
        function : Main loop interface for metric database item
        input : global threads, global dbitem
        output : NA
        """
        logmgr.recordError(LOG_MODULE, "[%s], metric name:[%s], scheduled at clock %d "
                           % (self.instanceInfo.nodename, self.name, self.GetLastSchedTick()), "DEBUG")
        if not self.instanceInfo.checkNodeState("Main"):
            return
        if os.path.isfile(self.tempfile) and os.path.getsize(self.tempfile):
            output = self.query()
            self.dblog.logWrite(output)
        # The temporary file does not exist or is empty, write for next schedule
        else:
            return


class SystemMetricItem(MetricItem):
    """
    Classify method to execute system metric item
    """
    def __init__(self, itemclass, itemdict):
        """"
        Constructor
        """
        super(SystemMetricItem, self).__init__(itemdict)
        # metric string
        if '.sh' in self.metricFunc['command'] or '.py' in self.metricFunc['command']:
            cmdFile = os.path.join(varinfo.METRIC_ITEM_DIR, itemclass, self.metricFunc['command'])
            self.metricCmd = open(cmdFile, "r").read()
        else:
            self.metricCmd = self.metricFunc['command']
        self.cmdOption = self.metricFunc['option']
        self.outputFormation = self.metricFunc['formation']
        # number of execution failures
        self.failureCount = 0
        tempFileName = ".tmp_gs_metric_" + self.name
        self.tempfile = os.path.join(varinfo.METRIC_ITEM_DIR, itemclass, tempFileName)
        self.schedState = ScheduleState('schedule')
        logDir = os.path.join(varinfo.METRIC_DATA_BASE_DIR, 'system', self.name)
        self.dblog = logmgr.MetricLog(logDir, self.name)
        logmgr.recordError(LOG_MODULE, "new system metric added in metric name: %s sched:%s, log path %s"
                           % (self.name, str(self.schedState), logDir))

    def commandCheck(self):
        """"
        check Command has dangerous command
        """
        #TODO
        return True

    def runCommand(self):
        """
        function : Get the system query result by shell command
        input : NA
        output : result information
        """
        # Some path information may be required by the system items
        if len(self.outputFormation) > 0 :
            cmd = self.metricCmd + " " + self.cmdOption + '|' + self.outputFormation
        else:
            cmd = self.metricCmd + " " + self.cmdOption
        status, output = commands.getstatusoutput(cmd)
        if status != 0 or not output:
            logmgr.recordError("SysMetric", "Failed to get shell result for item \"%s\", err: %s"
                               % (self.name, output))
            output = "[SysMetric]: " + output
        else :
            output = varinfo.LABEL_HEAD_PREFIX + '|' + output
            output = output.replace("\n", "\n" + varinfo.LABEL_HEAD_PREFIX + '|')
            output = varinfo.DATA_TYPE_DELIMITER + "\n" + output + "\n" + varinfo.DATA_TYPE_DELIMITER
        return output

    def runMetric(self):
        """
        function : Main loop interface for metric database item
        input : global threads, global dbitem
        output : NA
        """
        logmgr.recordError(LOG_MODULE, "[SYS], metric name:[%s], scheduled at clock %d "
                           % (self.name, self.GetLastSchedTick()), "DEBUG")
        output = self.runCommand()
        self.dblog.logWrite(output)


class MetricManager():
    """
    function:
    """
    def __init__(self, metricMgrConfjson, itemDirList, instanceList):
        self.maxThreads = int(metricMgrConfjson['max_threads'])
        self.gsMatricPool = GaussThreadPool(self.maxThreads)
        self.metricConfig = ""
        self.clockcount = 0
        self.stopflag = 0
        self.itemRefreshflag = 1
        self.pushConfigFlag = 1
        self.itemDirList = itemDirList
        self.itemList = []
        self.itemListDict = {}
        self.instanceList = instanceList
        self.databases = self.getDatabases()
        signal.signal(signal.SIGINT, lambda signal, frame: self._signal_handler())
        signal.signal(signal.SIGUSR2, lambda signal, frame: self._metric_handler())
        self.terminated = False
        if "pusher" in metricMgrConfjson.keys():
            self.pusher = pusher.Pusher(metricMgrConfjson['pusher'])

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
        status, output = commands.getstatusoutput("gsql -d postgres -p 25308 -c 'select datname from pg_database'")
        if status != 0 or not output:
            logmgr.recordError("SysMetric", "Failed to query all database")
        array = output.split("\n")[2:-2]
        database = [element.strip() for element in array if "template1" not in element and "template0" not in element]
        return database

    def initMetricItem(self, itemClass, metriclist):
        metricNameList = map(lambda metricItem: metricItem.name, self.itemList)
        for itemdict in metriclist.keys():
            item = metriclist[itemdict]
            if itemdict in metricNameList:
                continue
            if MetricMethod(item['type']) == MetricMethod('query'):
                queryType = self.initQueryType(item)
                queryDatabase = self.initDatabaseList(item)
                for inst in self.instanceList:
                    if inst.instType not in queryType:
                        continue
                    for database in queryDatabase:
                        item["metric_func"]["query_database"] = database
                        self.itemList.append(DatabaseMetricItem(itemClass, (itemdict, item), inst))
            elif MetricMethod(item['type']) == MetricMethod('command'):
                self.itemList.append(SystemMetricItem(itemClass, (itemdict, item)))

    def updateItemDict(self, metriclist):
        for item in metriclist.keys():
            if item not in self.itemListDict.keys():
                self.itemListDict[item] = {'table' : metriclist[item]['table']}

    def pushConfig(self):
        if self.pushConfigFlag == 0:
            return
        tableMapFile = os.path.join(varinfo.PUSHER_BUFFER_PATH, varinfo.TABLE_MAP_FILE)
        jconf.SaveJsonConf(self.itemListDict, tableMapFile)
        flag1 = self.pusher.pusher.pushFile(tableMapFile, pusher.PusherFileType('config'), 10)
        hostListFile = os.path.join(varinfo.PUSHER_BUFFER_PATH, varinfo.HOST_LIST_FILE)
        flag2 = self.pusher.pusher.pushFile(hostListFile, pusher.PusherFileType('config'), 10)
        if flag1 and flag2:
            self.pushConfigFlag = 0

    def itemListRefresh(self):
        if self.itemRefreshflag == 0:
            return
        for dir in self.itemDirList:
            checkpath = os.path.join(varinfo.METRIC_ITEM_DIR, dir, "metricdef.json")
            if not os.path.isfile(checkpath):
                logmgr.recordError(LOG_MODULE, "Failed to get json in %s" % checkpath)
                continue
            metriclist = jconf.MetricItemListGet(checkpath)
            self.initMetricItem(dir, metriclist)
            self.updateItemDict(metriclist)
        self.itemRefreshflag = 0

    def itemListSchedule(self):
        currentClock = self.getClockTick()
        for item in self.itemList:
            if item.GetItemCollectMethod() == CollectorMethod('off'):
                continue
            if item.IsItemScheduled() is False:
                continue
            if currentClock - item.GetLastSchedTick() >= item.interval:
                item.itemSchelule(self.gsMatricPool, item.runMetric(), currentClock)

    def startManager(self):
        logmgr.recordError(LOG_MODULE, "Starting metric manager")
        while self.stopflag == 0:
            self.clockTick()
            self.itemListRefresh()
            self.pushConfig()
            self.itemListSchedule()
            self.pusher.PusherSchedule(self.clockcount)
            if self.terminated == 1:
                self.gsMatricPool.CleanPool(False)
                break


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
    options.SaveClusterHostList()
    metricMgrConfjson = jconf.GetMetricManagerJsonConf(os.path.join(varinfo.METRIC_CONFIG, "client_conf.json"))
    itemDirList = ['metric_default', 'metric_user_define']
    metricMgr = MetricManager(metricMgrConfjson['GlobalManager'], itemDirList, options.dbNodeList)
    metricMgr.startManager()
