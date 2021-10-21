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
    import sys
    import time
    import threading
    import lib.common.gs_logmanager as logmgr
except Exception as e:
    sys.exit("FATAL: %s Unable to import module: %s" % (__file__, e))

LOG_MODULE = "Thread_Pool"


class GaussThreadWorker(threading.Thread):
    """
    function : define worker thread
    input : threadID: identity of worker
            name: worker name
            processFunc: worker function pointer
    output : none
    """
    def __init__(self, threadID, name, processFunc):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.processFunc = processFunc

    def run(self):
        self.processFunc()


class GaussThreadPool():
    """
    function : define thread pool
    input : maxWorkers: number of workers
    output : none
    """
    def __init__(self, maxWorkers):
        self.threadList = []
        self.workQueue = []
        self.threads = []
        self.threadID = 1
        self.exitFlag = 0
        self.queueLock = threading.Lock()
        for i in range(1, maxWorkers):
            threadName = "Thread-%s" % (i)
            self.threadList.append(threadName)
        for tName in self.threadList:
            self.thread = GaussThreadWorker(self.threadID, tName, self.process_data)
            self.thread.start()
            self.threads.append(self.thread)
            self.threadID += 1

    def process_data(self):
        while self.exitFlag != 0:
            self.queueLock.acquire()
            if len(self.workQueue) != 0:
                myJob, timeout  = self.workQueue[0]
                self.workQueue.remove(self.workQueue[0])
                self.queueLock.release()
                myJob()
            else:
                self.queueLock.release()
                time.sleep(1)

    def Submit(self, myJob, timeout):
        """
        function : submit
        input : myJob: submit one job for thread pool
                timeout: timeout for this job
        output : none
        """
        logmgr.recordError(LOG_MODULE, "submit", "DEBUG")
        self.queueLock.acquire()
        self.workQueue.append((myJob, timeout))
        self.queueLock.release()

    def CleanPool(self, bForce):
        """
        function : clean this thread pool resource
        input : bForce : whether to wait all work done, false is not wait
        output : none
        """
        # waiting for all workers done
        if bForce is False:
            while len(self.workQueue) != 0:
                continue
        self.exitFlag = 1
        for t in self.threads:
            t.join()
        logmgr.recordError(LOG_MODULE, "clean thread pool")
