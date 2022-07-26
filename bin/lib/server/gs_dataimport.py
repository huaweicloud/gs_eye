#!/usr/bin/env python3
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
    sys.path.append(os.path.dirname(__file__))
    if os.getenv('GPHOME'):
        sys.path.remove(os.path.join(os.getenv('GPHOME'), 'lib'))
    import threading
    import signal
    import time
    import sched
    import datetime
    import zipfile
    from threading import Thread
    from lib.common.gs_threadpool import GaussThreadPool
    from lib.common.CommonCommand import CommonCommand as commander
    import lib.common.CommonCommand as common
    import lib.common.gs_logmanager as logmgr
    import lib.common.gs_constvalue as varinfo
    from lib.common import gs_envchecker as checker, gs_jsonconf as jconf

except Exception as e:
    sys.exit("FATAL: %s Unable to import module: %s" % (__file__, e))

LOG_MODULE = "DATA_IMPORT"


class DataImport:
    def __init__(self, conf, coordinator):
        self.sourceDataPath = conf['data_root_path']
        self.database = conf['metric_database']
        self.data_age = conf['data_age']
        self.max_error_files = int(conf['max_error_files'])
        self.gsMetricPool = GaussThreadPool(5)
        self.interval = conf['interval']
        self.max_deal_package = conf['max_deal_package']
        self.check_paramter()
        self.terminated = False
        self.registered_clusters = []
        signal.signal(signal.SIGINT, lambda signal, frame: self._signal_handler())

    def check_paramter(self):
        self.check_database()
        self.check_source_path()
        self.check_data_age()
        self.check_max_error()
        self.check_interval()
        self.check_max_deal_package()

    def check_database(self):
        if not self.database:
            raise Exception("[metric_database] is not exists. Please check whether the parameters are correct.")
        if self.database[0].isdigit():
            raise Exception("[metric_database] do not support start with digtal.")
        if not self.database.isalnum():
            raise Exception("[metric_database] do not support characters except letters and digits.")

    def check_source_path(self):
        if not self.sourceDataPath :
            raise Exception("[data_root_path] did not config."
                            " Please check whether the parameters are correct or whether the folder exists.")
        if not os.path.exists(self.sourceDataPath) or not os.path.isdir(self.sourceDataPath):
            raise Exception("[data_root_path] is not exists."
                            " Please check whether the parameters are correct or whether the folder exists.")
        if not os.access(self.sourceDataPath, os.R_OK) or not os.access(self.sourceDataPath, os.W_OK):
            raise Exception("[data_root_path]'s permisson denied. Please change the mode for 777.")

    @staticmethod
    def check_interge(paramter):
        if int(paramter) < 0:
            return False
        return True

    def check_data_age(self):
        if not self.check_interge(self.data_age):
            raise Exception("[data_age] is not interge. Please modify the paramter.")
        if int(self.data_age) <= 1:
            raise Exception("[data_age] should be more than 1. Please modify the paramter.")

    def check_max_error(self):
        if not self.check_interge(self.max_error_files):
            raise Exception("[max_error_files] is not interge. Please modify the paramter.")

    def check_interval(self):
        if not self.check_interge(self.interval):
            raise Exception("[interval] is not interge. Please modify the paramter.")

    def check_max_deal_package(self):
        if not self.check_interge(self.max_deal_package):
            raise Exception("[max_deal_package] is not interge. Please modify the paramter.")

    def _signal_handler(self):
        self.terminated = True
        sys.exit()

    def checkDatabaseExist(self):
        sql = "select * from pg_database where datname = '%s'" % self.database
        result = []
        try:
            (status, result) = commander.runGsqlCommand(str(sql))
            if status != 0:
                logmgr.record(LOG_MODULE, "Failed to check database %s from pg_database, err: %s"
                                   % (self.database, result), "PANIC")
        except Exception as e:
            logmgr.record(LOG_MODULE, "exception occur while execute SQL: %s. exception: %s" % (sql, e), "DEBUG")
        if len(result) > 0:
            logmgr.record(LOG_MODULE, "database already exist, no need to create.")
        return len(result) > 0

    def createDatabase(self):
        logmgr.record(LOG_MODULE, "create database: %s to store metric data" % self.database)
        sql = "create database \"%s\"" % self.database
        try:
            (status, result) = commander.runGsqlCommand(str(sql))
            if status != 0:
                logmgr.record(LOG_MODULE, "Failed to create database %s, err: %s" % (self.database, result))
        except Exception as e:
            logmgr.record(LOG_MODULE, "exception occur while execute SQL: %s. exception: %s" % (sql, e), "DEBUG")

    def listExistedCluster(self):
        dirAndFileList = os.listdir(self.sourceDataPath)
        dirList = [element for element in dirAndFileList if not str(element).endswith(".json")]
        return dirList

    def createThreadTask(self):
        logmgr.record(LOG_MODULE, "create import task.")
        register_list = []
        clusters = self.listExistedCluster()
        if len(clusters) == 0:
            logmgr.record(LOG_MODULE, "not found registered cluster.")
            return register_list
        logmgr.record(LOG_MODULE, "found registered cluster: %s" % (",".join(clusters)))
        for cluster in clusters:
            if cluster in self.registered_clusters:
                continue
            else:
                self.registered_clusters.append(cluster)
                register_list.append(cluster)
        return register_list

    def submitRegisteredCluster(self):
        import multiprocessing.dummy as ProcessPool
        pool = ProcessPool.Pool(5)
        try:
            while True:
                register_list = self.createThreadTask()
                for cluster in register_list:
                    try:
                        pool.apply_async(self.run_task, (cluster,))
                    except Exception as e:
                        logmgr.record(LOG_MODULE, "Failed to create import task for cluster [%s], Error:%s" % (cluster,
                                                                                                               str(e)))
                        continue
                time.sleep(10)
        except Exception as e:
            logmgr.record(LOG_MODULE, "Failed to create import task, Error:%s" % str(e))
        finally:
            pool.close()
            pool.join()

    def run_task(self, cluster):
        logmgr.record(LOG_MODULE, "create import task for cluster: %s" % cluster)
        importTask = ImportTask(cluster, self.sourceDataPath, self.database, self.interval, self.max_deal_package)
        importTask.runImport()

    def dataImport(self):
        logmgr.record(LOG_MODULE, "start data import.")
        self.submitRegisteredCluster()

    def initDatabase(self):
        if not self.checkDatabaseExist():
            self.createDatabase()

    def StartDataImport(self):
        """
        function: main function to import data from every cluster.
                  First start the registration thread;
                  Then start the O&M thread;
                  Finally do import data thread.
        output: NA
        """
        logmgr.record(LOG_MODULE, "server is starting ...")
        self.initDatabase()
        register = ClusterRegisterThread('register', self.sourceDataPath, self.database)
        register.start()
        om_thread = OMThread('OM', self.sourceDataPath, self.database, self.data_age, self.max_error_files)
        om_thread.start()
        self.dataImport()


class ImportTask(object):
    """
    Constructor
    """

    def __init__(self, clusterName, rootPath, database, interval, deal_package_number):
        self.clusterName = clusterName
        self.rootPath = rootPath
        self.database = database
        self.interval = interval
        self.deal_package_number = deal_package_number
        self.tableMapping = self.loadTableMapping()
        logmgr.record(self.clusterName, "init import thread.")

    def loadTableMapping(self):
        confPath = os.path.join(self.rootPath, self.clusterName, "conf",
                                self.clusterName + "_" + varinfo.TABLE_MAP_FILE)
        return jconf.GetTableMappingConf(confPath)

    def runImport(self):
        logmgr.record(self.clusterName, "start import thread.")
        while True:
            try:
                zipFileList = self.dealZipFile()
                if len(zipFileList) == 0:
                    time.sleep(self.interval)
                    continue
                for metric_name, value in self.tableMapping.items():
                    try:
                        data_file = self.merge(metric_name)
                        self.copyIntoDatabase(metric_name, data_file)
                        os.remove(data_file)
                    except Exception:
                        now = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
                        cmd = "mv %s %s" % (data_file, os.path.join(self.rootPath, self.clusterName, "bad_data_files",
                                                                    "%s.%s" % (os.path.basename(data_file), now)))
                        common.runShellCommand(cmd)
                        logmgr.record(self.clusterName, "Failed to deal file[%s]." % data_file)
                cmd = "find %s -maxdepth 1 -name 'data' -type d -exec rm -rf {} \;"\
                      % os.path.join(self.rootPath, self.clusterName, "data/*")
                common.runShellCommand(cmd)
                logmgr.record(self.clusterName, "clean ready files.")
                time.sleep(self.interval)
            except Exception:
                logmgr.record(self.clusterName, "import thread failed.")
                time.sleep(self.interval)
                continue

    def dealZipFile(self):
        """
        function: unzip files
        limtit: 300 files each time
        """

        zipFileList = []
        clusterPath = os.path.join(self.rootPath, self.clusterName, "data")
        for dirPath, _, fileNames in os.walk(clusterPath):
            for fileName in fileNames:
                if fileName.endswith(".zip") and len(zipFileList) < self.deal_package_number:
                    try:
                        zipFileOpe = zipfile.ZipFile(os.path.join(dirPath, fileName))
                        zipFileOpe.extractall(dirPath)
                        os.remove(os.path.join(dirPath, fileName))
                        zipFileList.append(os.path.join(dirPath, fileName))
                    except Exception as e:
                        # the error zip will be mv to xxx/data/error directory.
                        now = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
                        cmd = "mv %s %s" % (os.path.join(dirPath, fileName), os.path.join(self.rootPath,
                                                                                          self.clusterName,
                                                                                          "bad_data_files", "%s.%s"
                                                                                          % (fileName, now)))
                        common.runShellCommand(cmd)
                        logmgr.record(self.clusterName,
                                           "Failed to unzip [%s], please be sure the file [%s] is correct, Result:%s"
                                           % (fileName,
                                              os.path.join(self.rootPath,
                                                           self.clusterName,
                                                           "bad_data_files",
                                                           "%s.%s" % (fileName, now)),
                                              str(e)))
        logmgr.record(self.clusterName, "Deal zip file list: %s" % (",".join(zipFileList)))
        return zipFileList

    def merge(self, metricItem):
        """
        function: This function is used to combine files of the same metric item.
        input: metric item name
        output: NA
        """
        logmgr.record(self.clusterName, "start to merge cluster: %s, metric item: %s" % (self.clusterName,
                                                                                              metricItem))
        merging_file = os.path.join(self.rootPath, self.clusterName, "data_files/%s.merging" % metricItem)
        data_file = os.path.join(self.rootPath, self.clusterName, "data_files/%s.importing" % metricItem)
        cmd = "find %s -name '%s*.log.ready' | xargs cat >> %s" % (os.path.join(self.rootPath, self.clusterName),
                                                                                metricItem, merging_file)
        status, output = common.runShellCommand(cmd)
        if status != 0:
            logmgr.record(self.clusterName, "Failed to merge [%s] files. Output:%s" % (merging_file, output))
        logmgr.record(self.clusterName,
                           "finish to merge cluster: %s, metric item: %s" % (self.clusterName, metricItem))
        os.renames(merging_file, data_file)
        logmgr.record(self.clusterName, "finish to rename merging file [%s] to [%s]" % (merging_file, data_file))
        return data_file

    def copyIntoDatabase(self, metric_name, dataFile):
        logmgr.record(self.clusterName, "start to import data file: %s" % dataFile)
        tableName = "%s.%s" % (self.clusterName, self.tableMapping[metric_name]['table']['name'])
        sql = "copy %s from '%s' delimiter '|';" % (tableName, dataFile)
        i = 0
        while i < 3:
            i += 1
            try:
                logmgr.record(self.clusterName, "execute copy sql: %s" % sql)
                (status, result) = commander.runGsqlCommand(str(sql), database=self.database)
                if status != 0:
                    logmgr.record(LOG_MODULE, "Copy to database failed, cluster: %s, query: %s, output: %s" %
                                       (self.clusterName, sql, result))
                else:
                    logmgr.record(self.clusterName, "finish to import data file: %s" % dataFile)
                    return
                time.sleep(3)
            except Exception as e:
                logmgr.record(LOG_MODULE, "exception occur while execute SQL: %s. exception: %s" % (sql, e))
        raise Exception("Failed to copy data file[%s] to database." % dataFile)


lock = threading.Lock()
registerFlag = ""


class ClusterRegisterThread(Thread):
    def __init__(self, name, rootPath, database):
        super(ClusterRegisterThread, self).__init__()
        self.name = name
        self.rootPath = rootPath
        self.database = database
        logmgr.record(self.name, "init register thread.")

    def run(self):
        logmgr.record(self.name, "start register thread.")
        global registerFlag
        while True:
            time.sleep(60)
            registerConfList = self.listRegisterConf()
            if len(registerConfList) == 0:
                logmgr.record(self.name, "not found new cluster register on server.")
                continue
            logmgr.record(self.name, "found new cluster, received conf file %s." % (",".join(registerConfList)))

            from itertools import groupby
            groupedConfList = groupby(registerConfList, key=lambda x: ("_".join(str(x).rsplit("_")[:-1])))

            for (clusterName, confList) in groupedConfList:
                confList = sorted(confList)
                if not self.verifyConfList(confList):
                    break
                self.registerCluster(clusterName, confList)
                self.archiveRegisterConfList(confList, clusterName)

    def registerCluster(self, clusterName, confList):
        logmgr.record(self.name, "init schema, table and directory for cluster: %s." % clusterName)
        tableMappingFile = confList[1]
        self.initSchemaAndTable(clusterName, tableMappingFile)
        hostListFile = confList[0]
        self.initDir(clusterName, hostListFile)

    def listRegisterConf(self):
        dirAndFileList = os.listdir(self.rootPath)
        configFileList = [element for element in dirAndFileList if str(element).endswith(".json")]
        return configFileList

    def verifyConfList(self, confList):
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

        dataFileDir = os.path.join(self.rootPath, clusterName, "data_files")
        commander.mkDirsWithMod(dataFileDir,
                                stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

        badDataFiles = os.path.join(self.rootPath, clusterName, "bad_data_files")
        commander.mkDirsWithMod(badDataFiles,
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
            logmgr.record(self.name, "Failed to check schema %s exists, err: %s" % (clusterName, output), "PANIC")
        if int(output) != 0:
            logmgr.record(self.name, "schema %s already exists, no need to create." % clusterName)
            return
        logmgr.record(self.name, "create schema: %s for cluster: %s " % (clusterName, clusterName))
        sql = "create schema %s" % clusterName
        (status, output) = commander.runGsqlCommand(sql, database=self.database)
        if status != 0:
            logmgr.record(self.name, "Failed to create schema %s, err: %s" % (clusterName, output), "PANIC")

    def initTable(self, clusterName, tableMappingFile):
        tableMappingList = jconf.GetTableMappingConf(os.path.join(self.rootPath, tableMappingFile))
        begin = datetime.date.today() + datetime.timedelta(days=1)
        for metricName in tableMappingList:
            self.createTable(clusterName, tableMappingList[metricName]["table"], begin)

    def createTable(self, schema, tableMapping, begin):
        tableName = tableMapping["name"]
        logmgr.record(self.name, "create table: %s.%s in database: %s" % (schema, tableName, self.database))

        tableDefine = tableMapping["define"]
        columns = ""
        for column in tableDefine:
            columns += "%s %s," % (column, tableDefine[column])
        columns = columns[0:-1]

        sql = "CREATE TABLE IF NOT EXISTS " \
              "%s.%s " \
              "(time timestamptz, " \
              "hostname text, " \
              "instance text, " \
              "%s ) " \
              "PARTITION BY RANGE (time) " \
              "(PARTITION p_0 VALUES LESS THAN (\'%s\'));" \
              % (schema, tableName, columns, begin)

        (status, output) = commander.runGsqlCommand(sql, database=self.database)
        if status != 0 or output.split("\n")[-1] != "CREATE TABLE":
            logmgr.record(self.name, "Failed to create table %s, sql:%s, err: %s" % (tableName, sql, output))

    def archiveRegisterConfList(self, confList, cluster):
        for confFile in confList:
            confFile = os.path.join(self.rootPath, confFile)
            dst = os.path.join(self.rootPath, cluster, "conf")
            cmd = "mv %s %s" % (confFile, dst)
            common.runShellCommand(cmd)


class OMThread(Thread):
    def __init__(self, name, root_path, database, data_age, max_error_files):
        super(OMThread, self).__init__()
        self.name = name
        self.data_age = data_age
        self.root_path = root_path
        self.database = database
        self.max_error_files = max_error_files
        self.scheduler = sched.scheduler(time.time, time.sleep)

    def do_data_aging(self):
        """
        function: Data is stored for a certain period of time.
        requirements: Forward compatibility must be ensured because V1 has create too many partitions when created table
        step:
            1. get all table information and partition numbers.
            2. if today's partition was created, clean the partitions which after that.
                 if partition's numbers is not more than self.data_age, do nothing.
                 if partition's numbers is more than self.data_age, drop the earliest partitions.
               else
                  drop the earliest partition; create today partition.
        """
        table_ids = []
        for _, dir_name in enumerate(os.listdir(self.root_path)):
            tables = self.get_tables(dir_name)
            for table_oid, table_name in tables:
                # drop old partition
                partition_number = self.get_partition_number(table_oid, table_name)
                if self.data_age < partition_number:
                    self.drop_partition(dir_name, table_oid, table_name, count=partition_number - self.data_age)
                partition_number = self.get_partition_number(table_oid, table_name)
                if self.data_age >= partition_number:
                    # create new partition
                    new_number, new_boundary = self.get_new_partition(dir_name, table_oid, table_name)
                    self.create_partition(dir_name, table_name, new_number, new_boundary)

    def adapt_old_version(self):
        table_ids = []
        for _, dir_name in enumerate(os.listdir(self.root_path)):
            tables = self.get_tables(dir_name)
            for table_oid, table_name in tables:
                # drop old partition
                partition_dic = self.get_partition_name_and_boundary(table_oid, table_name)
                partition_bondaries = sorted(list(partition_dic.keys()))
                # if today's partition has created, we sholud delete partitions which after today's partition.
                today = datetime.datetime.today()
                today_bondary = datetime.datetime.strptime(today.strftime('%Y-%m-%d'), '%Y-%m-%d') \
                                + datetime.timedelta(days=1)
                if (today_bondary) in partition_bondaries:
                    bondary_index = partition_bondaries.index(today_bondary)
                    drop_list = []
                    for i in partition_bondaries[bondary_index+2:]:
                        drop_list.append(partition_dic[i])
                    self.drop_partition(dir_name, table_oid, table_name, drop_list=drop_list)

    def create_missing_partition(self):
        """
        function:
            when the server restart, we should create the partition which has not create between the restart and last
             stop.
        step:
            1. get the boundary before create partition for every table.
            2. create new partition for every table.
            3. do date aging after creating partitions. Because of maybe be created too much partition.
        """
        table_ids = []
        today = datetime.datetime.today()
        for _, dir_name in enumerate(os.listdir(self.root_path)):
            tables = self.get_tables(dir_name)
            for table_oid, table_name in tables:
                partition_number, partition_boundary = self.get_latest_partition(table_oid)
                if not partition_boundary:
                    logmgr.record(self.name, "the table[%s] have not partition,please rebuild the table." % table_name)
                    continue
                partition_boundary_date = datetime.datetime.strptime(partition_boundary, "%Y-%m-%d %H:%M:%S")
                number = (today - partition_boundary_date).days
                if number > 0:
                    for _ in range(number):
                        partition_number += 1
                        partition_boundary_date = partition_boundary_date + datetime.timedelta(days=1)
                        self.create_partition(dir_name, table_name, "%s" % (partition_number), partition_boundary_date)
        # clean the old partition and create partitiont for today. Because the partition may be more than self.data_age.
        self.do_data_aging()

    def get_partition_name_and_boundary(self, table_oid, table_name):
        """
        function: get the table's partition name and partition boundary
        input: table's oid , table's name
        output: [str1,str2..].
                e.g. ['p1|bonundary1', 'p2|bonundary2']
        """
        partition_dic = {}
        sql = "select relname, boundaries[1]::date as nextpartbound" \
              " from pg_partition where parentid = '%s'::regclass and parttype = 'p' order by boundaries;"\
              % table_oid
        _, partitions = commander.runGsqlCommand(sql, database=self.database)
        for partition in partitions.splitlines():
            tmp = partition.split('|')
            if len(tmp) != 2:
                logmgr.record(self.name, "Failed to get partition for %s, result:%s" % (table_name, partition))
            else:
                partition_dic[datetime.datetime.strptime(tmp[1], "%Y-%m-%d %H:%M:%S")] = tmp[0]
        return partition_dic


    def get_latest_partition(self, table_oid):
        """
        function: get the latest partition by table's oid
        input: table's oid
        output: [latest_partition_number, latest_partition_boundary]
        """
        sql = "select regexp_substr(relname, '\d+') as nextpartname, boundaries[1]::date as nextpartbound" \
              " from pg_partition where parentid = '%s'::regclass and parttype = 'p' order by boundaries desc limit 1;"\
              % table_oid
        _, latest_partition = commander.runGsqlCommand(sql, database=self.database)
        if latest_partition:
            return int(latest_partition.split('|')[0]), latest_partition.split('|')[1]
        else:
            return "", ""

    def get_partition_number(self, table_oid, table_name):
        sql = "select count(*) from pg_partition where parentid = %s and parttype = 'p'" % (table_oid)
        _, partition_number = commander.runGsqlCommand(sql, database=self.database)
        if not partition_number or not partition_number.strip().isdigit():
            raise Exception("Failed to get partition number of %s, result: %s" % (table_name, partition_number))
        else:
            return int(partition_number.strip())

    def get_tables(self, schema):
        result = []
        logmgr.record(self.name, "start get table's oid and table's name of schema[%s]." % schema)
        sql = "select c.oid as oid, c.relname as tablename from pg_class c, pg_namespace n" \
              " where n.nspname = '%s' and c.relnamespace = n.oid;" % schema
        _, tables = commander.runGsqlCommand(sql, database=self.database)
        for line in tables.splitlines():
            result.append([line.split("|")[0], line.split("|")[1]])
        logmgr.record(self.name, "Successfully get table's oid and table's name of schema[%s]." % schema)
        return result

    def drop_partition(self, schema, table_oid, table_name, count=0, drop_list=None):
        logmgr.record(self.name, "start drop old partition %s." % table_name)
        partitions_list = []
        if drop_list:
            partitions_list = drop_list
        elif count:
            get_partitions = "select relname, boundaries[1]::date from pg_partition where parentid='%s'::regclass" \
                             " and parttype='p' order by boundaries asc limit %s;" % (table_oid, count)
            _, partitions = commander.runGsqlCommand(get_partitions, database=self.database)
            today = datetime.datetime.today()
            for line in partitions.splitlines():
                if (datetime.datetime.strptime(line.split('|')[1], "%Y-%m-%d %H:%M:%S") - today).days == 0:
                    break
                else:
                    partitions_list.append(line.split('|')[0])

        for partition in partitions_list:
            drop_partition = "alter table %s.%s drop partition %s;" % (schema, table_name, partition)
            status, output = commander.runGsqlCommand(drop_partition, database=self.database)
            if status != 0 or output != "ALTER TABLE":
                logmgr.record(self.name, "Failed to drop partition %s for %s.%s, err: %s" % (partition, schema,
                                                                                             table_name, output))
                continue
            logmgr.record(self.name, "Finish to drop partition %s for %s.%s" % (partition, schema, table_name))
        logmgr.record(self.name, "Successfully drop partition for %s.%s" % (schema, table_name))

    def get_new_partition(self, schema, table_oid, table_name):
        logmgr.record(self.name, "start to create new partition for %s." % table_name)
        new_partition = "select regexp_substr(relname, '\d+') + 1 as nextpartname, boundaries[1]::date + '1 Days'" \
                            " as nextpartbound from pg_partition where parentid = '%s'::regclass and parttype = 'p'" \
                            " order by boundaries desc limit 1;" % table_oid
        _, new_partition = commander.runGsqlCommand(new_partition, database=self.database)
        if new_partition:
            return int(new_partition.split('|')[0]), new_partition.split('|')[1]
        else:
            return "", ""

    def create_partition(self, schema, table_name, partition_name, partition_boundary):
        create_partition = "alter table %s.%s add partition p_%s values less than ('%s');"\
                           % (schema, table_name, partition_name, partition_boundary)
        status, output = commander.runGsqlCommand(create_partition, database=self.database)
        if status != 0:
            logmgr.record(self.name, "Failed to create partition for table:%s, partition: %s,"
                                     " partition_boundary:%s.Error:%s." % (table_name, partition_name,
                                                                           partition_boundary, output))
        else:
            logmgr.record(self.name, "Successfully create partition for table:%s, partition: %s,"
                                     " partition_boundary:%s." % (table_name, partition_name, partition_boundary))

    def clean_error_files(self):
        """
        function: clean files when files is more than error_number.
        """
        for data_path in os.listdir(self.root_path):
            if not os.path.isdir(os.path.join(self.root_path, data_path)):
                continue
            error_files = os.listdir(os.path.join(self.root_path, data_path, 'bad_data_files'))
            delete_files = len(error_files) - self.max_error_files
            if delete_files > 0:
                for i in range(0, delete_files, 300):
                    cmd = "cd %s;rm -rf %s" % (os.path.join(self.root_path, data_path, 'bad_data_files'),
                                               " ".join(sorted(error_files)[i: (i + 300)]))
                    status, output = common.runShellCommand(cmd)
                    if status != 0:
                        logmgr.record(self.name, "Failed to clean bad_data_files and there is %s bad_data_files."
                                      % len(error_files))
                    else:
                        logmgr.record(self.name, "Successfully to clean bad_data_files %s" % len(error_files))

    def data_aging(self):
        """
        function:
            1.we will drop and create partition at 12:00 every day when partition is more than data_age
            2.we will clean files each hour when files is more than error_number.

        """
        now = datetime.datetime.now()
        if now.hour == 23:
            self.do_data_aging()
        self.clean_error_files()
        self.monitor()

    def monitor(self):
        self.scheduler.enter(3600, 1, self.data_aging, ())

    def run(self):
        """
        function: the main function for om thread
                1. when we restart process, we should create the partition
                    because create only one partition or do not create partition when we create table.
                2. we create a monitor to do some thing.
        """
        logmgr.record(self.name, "start om thread.")
        self.create_missing_partition()
        self.adapt_old_version()
        self.monitor()
        self.scheduler.run()


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
