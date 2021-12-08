#!/usr/bin/env python
# coding=utf-8
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
    import stat
    import sys
    import imp
    imp.reload(sys)
    sys.setdefaultencoding('utf8')
    import threading
    import signal
    import time
    import datetime
    import zipfile
    from threading import Thread
    from lib.common.gs_threadpool import GaussThreadPool
    from lib.common.CommonCommand import CommonCommand as commander
    import lib.common.gs_logmanager as logmgr
    import lib.common.gs_constvalue as varinfo
    from lib.common import gs_envchecker as checker, gs_jsonconf as jconf

except Exception as e:
    sys.exit("FATAL: %s Unable to import module: %s" % (__file__, e))

LOG_MODULE = "DATA_IMPORT"


class DataImport:
    def __init__(self, conf, coordinator):
        self.sourceDataPath = conf['data_root_path']
        self.database = conf['metric_database'].lower()
        self.gsMetricPool = GaussThreadPool(5)
        self.terminated = False
        signal.signal(signal.SIGINT, lambda signal, frame: self._signal_handler())

    def _signal_handler(self):
        self.terminated = True
        sys.exit()

    def checkDatabaseExist(self):
        sql = "select * from pg_database where datname = '%s'" % self.database
        result = []
        try:
            (status, result, err_output) = commander.executeSqlOnLocalhost(str(sql))
            if status != varinfo.PGRES_TUPLES_OK:
                logmgr.recordError(LOG_MODULE, "Failed to check database %s from pg_database, err: %s"
                                   % (self.database, err_output), "PANIC")
        except Exception as e:
            logmgr.recordError(LOG_MODULE, "exception occur while execute SQL: %s. exception: %s" % (sql, e), "DEBUG")
        if len(result) > 0:
            logmgr.recordError(LOG_MODULE, "database already exist, no need to create.")
        return len(result) > 0

    def createDatabase(self):
        logmgr.recordError(LOG_MODULE, "create database: %s to store metric data" % self.database)
        sql = "create database %s" % self.database
        try:
            (status, result, err_output) = commander.executeSqlOnLocalhost(str(sql))
            if status != varinfo.PGRES_COMMAND_OK:
                logmgr.recordError(LOG_MODULE, "Failed to create database %s, err: %s" % (self.database, err_output))
        except Exception as e:
            logmgr.recordError(LOG_MODULE, "exception occur while execute SQL: %s. exception: %s" % (sql, e), "DEBUG")

    def listExistedCluster(self):
        dirAndFileList = os.listdir(self.sourceDataPath)
        dirList = [element for element in dirAndFileList if not str(element).endswith(".json")]
        return dirList

    def createThreadTask(self):
        logmgr.recordError(LOG_MODULE, "create import task.")
        importTaskList = []
        clusters = self.listExistedCluster()
        if len(clusters) == 0:
            logmgr.recordError(LOG_MODULE, "not found registered cluster.")
            return importTaskList
        logmgr.recordError(LOG_MODULE, "found registered cluster: %s" % (",".join(clusters)))
        for cluster in clusters:
            logmgr.recordError(LOG_MODULE, "create import task for cluster: %s" % cluster)
            importTaskList.append(ImportTask(cluster, self.sourceDataPath, self.database))
        return importTaskList

    @staticmethod
    def unmarkRegisterFlag():
        global registerFlag
        try:
            lock.acquire()
            registerFlag = ""
        finally:
            lock.release()

    def submitRegisteredCluster(self):
        importTaskList = self.createThreadTask()
        for importTask in importTaskList:
            self.gsMetricPool.Submit(importTask.runImport(), 30)
        self.unmarkRegisterFlag()

    def addNewCluster(self, cluster):
        logmgr.recordError(LOG_MODULE, "create import task for cluster: %s" % cluster)
        importTask = ImportTask(cluster, self.sourceDataPath, self.database)
        self.gsMetricPool.Submit(importTask.runImport(), 30)
        self.unmarkRegisterFlag()

    def dataImport(self):
        logmgr.recordError(LOG_MODULE, "start data import.")
        self.submitRegisteredCluster()
        while True:
            if registerFlag == "":
                logmgr.recordError(LOG_MODULE, "not found new cluster to create import task")
            else:
                clusterName = registerFlag
                logmgr.recordError(LOG_MODULE, "found new cluster: %s to create import task" % clusterName)
                self.addNewCluster(clusterName)
            time.sleep(60)

    def initDatabase(self):
        if not self.checkDatabaseExist():
            self.createDatabase()

    def StartDataImport(self):
        logmgr.recordError(LOG_MODULE, "server is starting ...")
        self.initDatabase()

        register = ClusterRegisterThread('register', self.sourceDataPath, self.database)
        register.start()

        self.dataImport()


class ImportTask(object):
    """
    Constructor
    """

    def __init__(self, clusterName, rootPath, database):
        self.clusterName = clusterName
        self.rootPath = rootPath
        self.database = database
        self.tableMapping = self.loadTableMapping()
        logmgr.recordError(self.clusterName, "init import thread.")

    def loadTableMapping(self):
        confPath = os.path.join(self.rootPath, self.clusterName, "conf",
                                self.clusterName + "_" + varinfo.TABLE_MAP_FILE)
        return jconf.GetTableMappingConf(confPath)

    def runImport(self):
        logmgr.recordError(self.clusterName, "start import thread.")
        while True:
            zipFileList = self.getAllZips()
            if len(zipFileList) == 0:
                continue
            logmgr.recordError(self.clusterName, "received zip file list: %s" % (",".join(zipFileList)))
            for zipFile in zipFileList:
                self.dealZipFile(zipFile)
            time.sleep(30)

    def getAllZips(self):
        zipFileList = []
        clusterPath = os.path.join(self.rootPath, self.clusterName, "data")
        for dirPath, dirNames, fileNames in os.walk(clusterPath):
            for fileName in fileNames:
                if fileName.endswith(".zip"):
                    zipFileList.append(os.path.join(dirPath, fileName))
        return zipFileList

    def dealZipFile(self, zipFile):
        fileList = self.unzipZipFile(zipFile)
        logmgr.recordError(self.clusterName, "unzip data file list: %s, from zip file: %s"
                           % (",".join(fileList), zipFile))
        for dataFile in fileList:
            self.copyIntoDatabase(dataFile)

    @staticmethod
    def unzipZipFile(zipFile):
        (path, fileName) = os.path.split(zipFile)
        zipFileOpe = zipfile.ZipFile(zipFile)
        dirAndFileList = zipFileOpe.namelist()
        fileList = [os.path.join(path, element) for element in dirAndFileList if str(element).endswith(".log")]
        zipFileOpe.extractall(path)
        os.remove(zipFile)
        return fileList

    def copyIntoDatabase(self, dataFile):
        metricName = os.path.split(dataFile)[0].split("/")[-1]
        tableName = "%s.%s" % (self.clusterName, self.tableMapping[metricName]['table']['name'])
        sql = "copy %s from '%s' delimiter '|';" % (tableName, dataFile)
        try:
            logmgr.recordError(self.clusterName, "execute copy sql: %s" % sql)
            (status, result, err_output) = commander.executeSqlOnLocalhost(str(sql), database=self.database)
            if status != varinfo.PGRES_COMMAND_OK:
                logmgr.recordError(LOG_MODULE, "Copy to database failed, cluster: %s, query: %s, output: %s" %
                                   (self.clusterName, sql, err_output))
        except Exception as e:
            logmgr.recordError(LOG_MODULE, "exception occur while execute SQL: %s. exception: %s" % (sql, e), "ERROR")


lock = threading.Lock()
registerFlag = ""  # type: str


class ClusterRegisterThread(Thread):
    def __init__(self, name, rootPath, database):
        super(ClusterRegisterThread, self).__init__()
        self.name = name
        self.rootPath = rootPath
        self.database = database
        logmgr.recordError(self.name, "init register thread.")

    def run(self):
        logmgr.recordError(self.name, "start register thread.")
        global registerFlag
        while True:
            time.sleep(60)
            registerConfList = self.listRegisterConf()
            if len(registerConfList) == 0:
                logmgr.recordError(self.name, "not found new cluster register on server.")
                continue
            logmgr.recordError(self.name, "found new cluster, received conf file %s." % (",".join(registerConfList)))

            from itertools import groupby
            groupedConfList = groupby(registerConfList, key=lambda x: (str(x).rsplit("_")[0]))

            for (clusterName, confList) in groupedConfList:
                confList = sorted(confList)
                if not self.verifyConfList(confList):
                    return
                self.registerCluster(clusterName, confList)
                self.archiveRegisterConfList(confList, clusterName)
                while registerFlag != "":
                    logmgr.recordError(self.name, "wait for cluster: %s finishing register" % registerFlag)
                    time.sleep(1)
                self.markRegisterFlag(clusterName)

    def registerCluster(self, clusterName, confList):
        logmgr.recordError(self.name, "init schema, table and directory for cluster: %s." % clusterName)
        tableMappingFile = confList[1]
        self.initSchemaAndTable(clusterName, tableMappingFile)
        hostListFile = confList[0]
        self.initDir(clusterName, hostListFile)

    def listRegisterConf(self):
        dirAndFileList = os.listdir(self.rootPath)
        configFileList = [element for element in dirAndFileList if str(element).endswith(".json")]
        return configFileList

    @staticmethod
    def verifyConfList(confList):
        if len(confList) != 2:
            return False
        if str(confList[0]).split("_")[-1] != "hostlist.json":
            return False
        if str(confList[1]).split("_")[-1] != "tablemapping.json":
            return False
        return True

    def initSchemaAndTable(self, clusterName, tableMappingFile):
        self.initSchema(clusterName)
        self.initTable(clusterName, tableMappingFile)

    def initDir(self, clusterName, hostListFile):
        commander.mkDirsWithMod(os.path.join(self.rootPath, clusterName),
                                stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

        commander.mkDirsWithMod(os.path.join(self.rootPath, clusterName, "conf"),
                                stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

        dataDir = os.path.join(self.rootPath, clusterName, "data")
        commander.mkDirsWithMod(dataDir,
                                stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

        hostList = jconf.GetHostListConf(os.path.join(self.rootPath, hostListFile))
        for host in hostList:
            commander.mkDirsWithMod(os.path.join(dataDir, host),
                                    stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

    @staticmethod
    def markRegisterFlag(clusterName):
        global registerFlag
        try:
            lock.acquire()
            registerFlag = clusterName
        finally:
            lock.release()

    def initSchema(self, clusterName):
        sql = "select count(*) from pg_namespace where nspname = '%s'" % clusterName
        (status, output) = commander.runGsqlCommand(sql, database=self.database)
        if status != 0:
            logmgr.recordError(self.name, "Failed to check schema %s exists, err: %s" % (clusterName, output), "PANIC")
        if int(output) != 0:
            logmgr.recordError(self.name, "schema %s already exists, no need to create." % clusterName)
            return
        logmgr.recordError(self.name, "create schema: %s for cluster: %s " % (clusterName, clusterName))
        sql = "create schema %s" % clusterName
        (status, output) = commander.runGsqlCommand(sql, database=self.database)
        if status != 0:
            logmgr.recordError(self.name, "Failed to create schema %s, err: %s" % (clusterName, output), "PANIC")

    def initTable(self, clusterName, tableMappingFile):
        tableMappingList = jconf.GetTableMappingConf(os.path.join(self.rootPath, tableMappingFile))
        begin = datetime.date.today()
        end = begin + datetime.timedelta(days=90)
        for metricName in tableMappingList:
            self.createTable(clusterName, tableMappingList[metricName]["table"], begin, end)

    def createTable(self, schema, tableMapping, begin, end):
        tableName = tableMapping["name"]
        logmgr.recordError(self.name, "create table: %s.%s in database: %s" % (schema, tableName, self.database))

        tableDefine = tableMapping["define"]
        columns = ""
        for column in tableDefine:
            columns += "%s %s," % (column, tableDefine[column])
        columns = columns[0:-1]

        sql = "CREATE TABLE IF NOT EXISTS " \
              "%s.%s " \
              "(time timestamp, " \
              "hostname text, " \
              "instance text, " \
              "%s ) " \
              "PARTITION BY RANGE (time) " \
              "( PARTITION p START (\'%s\') END (\'%s\') EVERY (\'1 Days\'));" \
              % (schema, tableName, columns, begin, end)

        (status, output) = commander.runGsqlCommand(sql, database=self.database)
        if status != 0 or output.split("\n")[-1] != "CREATE TABLE":
            logmgr.recordError(self.name, "Failed to create table %s, err: %s" % (tableName, output))

    def archiveRegisterConfList(self, confList, cluster):
        import shutil
        for confFile in confList:
            confFile = os.path.join(self.rootPath, confFile)
            dst = os.path.join(self.rootPath, cluster, "conf")
            shutil.move(confFile, dst)


def RunDataImport():
    """
    function : The entrance
    input : NA
    output : NA
    """
    logmgr.StartLogManager('server')
    options = checker.RunEnvironment()
    options.SetAppName('Server')
    options.initParameter()
    options.checkParameter()
    importConf = jconf.GetImportConf(os.path.join(varinfo.METRIC_CONFIG, "server_conf.json"))
    app = DataImport(importConf, options.coordinator[0])
    app.StartDataImport()
