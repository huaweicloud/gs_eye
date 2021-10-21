#!/usr/bin/env python
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
    import commands
    import threading
    import signal
    import time
    import lib.common.gs_logmanager as logmgr
    import lib.common.gs_constvalue as varinfo
    from lib.common import gs_envchecker as checker, gs_jsonconf as jconf
    import lib.common.cluster.gs_instance_manager as dbinfo

except Exception as e:
    sys.exit("FATAL: %s Unable to import module: %s" % (__file__, e))

LOG_MODULE = "DATA_IMPORT"


def createDBData(inFile, nodename, instance, outFile):
    """
    function : Deal with database metric data body to write into copy file
    input : data body, instance name, metric information
    output : NA
    """
    logmgr.recordError(LOG_MODULE, "Start to write data into temp  %s" % outFile, "DEBUG")
    data = ""
    path = os.path.dirname(inFile)
    if inFile.endswith(".zip"):
        command = "unzip -o %s -d %s" % (inFile, path)
        status, output = commands.getstatusoutput(command)
        if status != 0:
            return
    # Split the data by timestamp
    delimiter = varinfo.RECORD_BEGIN_DELIMITER + "\n[timer: "
    data = open(inFile[:-3] + "log", "r").read().split(delimiter)
    f = open(outFile, 'w+')
    for item in data:
        if varinfo.DATA_TYPE_DELIMITER not in item:
            continue
        timestamp, value = item.split("]\n", 1)
        # Skip the invalid log information
        if value.startswith("[DBMetric]:"):
            continue
        # Use delimiters to separate data blocks
        value = value.split(varinfo.DATA_TYPE_DELIMITER + "\n")
        # Add the new fields timestamp, instance name
        # The data block location is determined by the delimiter
        f.write(value[1].replace(varinfo.LABEL_HEAD_PREFIX,
                                 "%s|%s|%s" % (timestamp, nodename, instance)))
        # Save the latest timestamp to weed out outdated data
    f.close()


class DataImport:
    def __init__(self, conf, coordinator):
        self.interval = conf['interval']
        clusterConf = conf['cluster_list']
        if "_comment" in clusterConf.keys():
            clusterConf.pop('_comment')
        self.clusterList = []
        for c in clusterConf.keys():
            if clusterConf[c] == "on":
                self.clusterList.append(c)
        self.sourceDataPath = conf['data_root_path']
        self.queryCmdPrefix = "gsql -d postgres -p " + str(coordinator.port) + " -c "
        self.database = conf['metric_database'].lower()
        self.tableMapping = {}
        self.statistics = {'insert': 0}
        logmgr.recordError(LOG_MODULE, "Init data importor %s " % self.queryCmdPrefix)
        self.terminated = False
        signal.signal(signal.SIGINT, lambda signal, frame: self._signal_handler())

    def _signal_handler(self):
        self.terminated = True
        sys.exit()

    def loadTableMapping(self, cluster):
        tablemap = jconf.GetTableMappingConf(os.path.join(self.configPath, varinfo.TABLE_MAP_FILE))
        if len(tablemap) == 0:
            logmgr.recordError(LOG_MODULE, "Cluster %s failed to load table map file" % (cluster))
        self.tableMapping[cluster] = tablemap

    def checkAndInitDir(self):
        for c in self.clusterList:
            self.configPath = os.path.join(self.sourceDataPath, c, "conf")
            self.dataPath = os.path.join(self.sourceDataPath, c, "data")
            if not os.path.isdir(self.configPath):
                os.makedirs(self.configPath)
            if not os.path.isdir(self.dataPath):
                os.makedirs(self.dataPath)
            clistfile = os.path.join(self.configPath, varinfo.CLUSTER_LIST_FILE)
            if not os.path.isfile(clistfile):
                return
            cluster_list = jconf.GetClusterListConf(clistfile)
            for c in cluster_list:
                hostpath = os.path.join(self.dataPath, c)
                if os.path.isdir(hostpath):
                    continue
                os.makedirs(hostpath)
                os.chmod(hostpath, 0o777)

    def initDatabase(self):
        """
        Check whether the database exists, if not, create it
        """
        # Get database information from pg_database
        sql = "copy (select count(*) from pg_database where datname = '%s') to stdout;" % self.database
        status, output = commands.getstatusoutput("%s \"%s\"" % (self.queryCmdPrefix, sql))
        if status != 0 or int(output) > 1:
            logmgr.recordError(LOG_MODULE, "Failed to check database \"%s\" from pg_database, err: %s"
                                     % (self.database, output))
        elif output != "1":
            sql = "create database %s;" % self.database
            status, output = commands.getstatusoutput("%s \"%s\"" % (self.queryCmdPrefix, sql))
            if status != 0 or output.upper() != "CREATE DATABASE":
                logmgr.recordError(LOG_MODULE, "Failed to create database \"%s\", err: %s" % (self.database, output))
        # The next step requires connecting to the new library
        self.queryCmdPrefix = self.queryCmdPrefix.replace("postgres", self.database, 1)

    def checkSchema(self, schema):
        """
        function : Check whether the schema exists, if not, create it
        input : NA
        output : result state
        """
        result = True
        # Get schema information from pg_namespace
        sql = "copy (select count(*) from pg_namespace where nspname = '%s') to stdout;" % schema
        status, output = commands.getstatusoutput("%s \"%s\"" % (self.queryCmdPrefix, sql))
        if status != 0 or int(output) > 1:
            logmgr.recordError(LOG_MODULE,
                            "Failed to check schema \"%s\" from pg_namespace" % schema)
            result = False
        elif output != "1":
            # Create the schema for data import
            sql = "create schema %s;" % schema
            status, output = commands.getstatusoutput("%s \"%s\"" % (self.queryCmdPrefix, sql))
            if status != 0 or output.upper() != "CREATE SCHEMA":
                logmgr.recordError(LOG_MODULE, "Failed to create schema \"%s\"" % schema)
                result = False
        return result

    def checkBasicTable(self, schema, tableName, tableDefine):
        """
        function : Check whether the basic table exists, if not, create it
        input : NA
        output : result state
        """
        result = True
        # Table to record the relation between metric item and query
        table = "%s.%s(time timestamp, hostname text, instance text," % (schema, tableName)
        for d in tableDefine:
            table = table + "%s %s," % (d, tableDefine[d])
        table = table[0:-1] + ");"
        sql = "create table if not exists %s" % table
        status, output = commands.getstatusoutput("%s \"%s\"" % (self.queryCmdPrefix, sql))
        if status != 0 or "ERROR" in output.upper() or (output and "CREATE TABLE" not in output.upper()):
            logmgr.recordError(LOG_MODULE, "Failed to check basic table \"%s\" err: %s" % (tableName, output))
            result = False
        return result

    def initSchemaAndTable(self, cluster):
        self.checkSchema(cluster)
        self.loadTableMapping(cluster)
        if cluster not in self.tableMapping.keys():
            return
        tableList = self.tableMapping[cluster]
        for tableKey in tableList:
            tableName = tableList[tableKey]['table']['name']
            self.checkBasicTable(cluster, tableName, tableList[tableKey]['table']['define'])

    def copyDataIntoDatabase(self, cluster, file):
        """
        function : Copy data file into database
        input : host name
        output : NA
        """
        if os.path.getsize(file) == 0:
            os.remove(file)
            return
        (path, filename) = os.path.split(file)
        element = path.replace(self.sourceDataPath, "", 1).split('/')
        element = [i for i in element if i != '']
        currentCluster = element[0]
        if currentCluster != cluster:
            logmgr.recordError(LOG_MODULE, "Error log for cluster %s,source cluster %s, file %s" %
                                                 (cluster, currentCluster, file))
            return
        type = element[4]
        if type == "database":
            instance = element[-2]
        else:
            instance = "system"
        tableKey = element[-1]
        nodename = element[2]

        if tableKey not in self.tableMapping[cluster].keys():
            logmgr.recordError(LOG_MODULE, "metric label %s has no table to store data " % tableKey)
            return

        dataFile = os.path.join(path, filename + '.tmp')
        createDBData(file, nodename, instance, dataFile)
        if not os.path.isfile(dataFile):
            logmgr.recordError(LOG_MODULE, "metric data %s has not been created " % dataFile)
            self.initSchemaAndTable(cluster)
            return
        # Use transactions to guarantee rollback in case of failure
        tableName = "%s.%s" % (cluster, self.tableMapping[cluster][tableKey]['table']['name'])
        sql = "start transaction;\n"
        sql += "copy %s from '%s' delimiter '|';\n" % (tableName, dataFile)
        sql += "commit;"
        status, output = commands.getstatusoutput("%s \"%s\"" % (self.queryCmdPrefix, sql))
        if status != 0 or "ROLLBACK" in output.upper():
            logmgr.recordError(LOG_MODULE, "Copy to database failed cluster %s, query %s, output %s" %
                                                 (cluster, sql, output))
            return
        # Get the number of rows of data into the database
        output = output.lower()
        idx = output.find('copy')
        # Insert number of rows after the copy field
        while idx >= 0:
            output = output[idx + 5:]
            idx = output[:output.find('\n')]
            if idx.isdigit():
                self.statistics["insert"] += int(idx)
            # Multiple copies have multiple results
            idx = output.find('copy')
        os.remove(file)
        os.remove(dataFile)

    def getDealFileList(self, zipFile):
        """
        function : Decompress the log file
        input : file name, file name with absolute path, storage path
        output : result state
        """
        command = "zipinfo %s |grep .log" % (zipFile)
        status, output = commands.getstatusoutput(command)
        if status != 0:
            logmgr.recordError(LOG_MODULE, "Error get zipinfo file : %s  " % (zipFile, output))
            return
        tmpList = output.split('\n')
        fileList = []
        for l in tmpList:
            m = l.split()
            fileList.append(m[-1])
        return fileList

    def UnzipMetricData(self, zipFile):
        """
        function : Decompress the log file
        input : file name, file name with absolute path, storage path
        output : result state
        """
        result = True
        path = os.path.dirname(zipFile)
        if not os.path.isdir(path):
            os.makedirs(path)
        command = "unzip -o %s -d %s" % (zipFile, path)
        status, output = commands.getstatusoutput(command)
        if status != 0:
            logmgr.recordError(LOG_MODULE, "Error unzip file : %s, err: %s" % (zipFile, output), "DEBUG")
            result = False
        return result

    def dealZipFile(self, cluster, zipFile):
        fileList = self.getDealFileList(zipFile)
        baseDir = os.path.dirname(zipFile)
        if self.UnzipMetricData(zipFile) is False:
            return
        for f in fileList:
            fileName = os.path.join(baseDir, f)
            self.copyDataIntoDatabase(cluster, fileName)

    def checkAndDealData(self, cluster):
        """
        function : Access to the metric item and log file
        input : host name, instance name, metric item, file path
        output : NA
        """
        logmgr.recordError(LOG_MODULE, "Deal data start : %s %s " % (cluster, self.sourceDataPath), "DEBUG")
        basedataPath = os.path.join(self.sourceDataPath, cluster, "data")
        hostlist = os.listdir(basedataPath)
        for h in hostlist:
            checkPath = os.path.join(basedataPath, h)
            if not os.path.isdir(checkPath):
                continue
            for z in os.listdir(checkPath):
                if not z.endswith(".zip"):
                    continue
                zipFile = os.path.join(checkPath, z)
                self.dealZipFile(cluster, zipFile)
                os.remove(zipFile)

    def RunDataImport(self, cluster):
        while True:
            time.sleep(self.interval)
            self.checkAndDealData(cluster)
            if self.terminated is True:
                break
        return

    def StartDataImport(self):
        self.checkAndInitDir()
        self.initDatabase()
        for s in self.clusterList:
            if "_comment" in s:
                continue
            self.initSchemaAndTable(s)
        threads = {}
        for cluster in self.clusterList:
            threads[cluster] = threading.Thread(target=self.RunDataImport, args=(cluster,))
            threads[cluster].start()

        for t in threads:
            threads[t].join()


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
