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
    import sys
    import commands
    from ctypes import cdll
    from ctypes import c_void_p
    from ctypes import c_int
    from ctypes import c_char_p
    from ctypes import string_at
    from lib.common import gs_constvalue as varinfo
except Exception as e:
    sys.exit("FATAL: %s Unable to import module: %s" % (__file__, e))


class sqlResult():
    """
    Class for storing search result from database
    """

    def __init__(self, result):
        """
        Constructor
        """
        self.resCount = 0
        self.resSet = []
        self.result = result

    def parseResult(self):
        """
        function : get resCount and resSet from result
        input:NA
        output:NA
        """
        try:
            libPath = os.path.join(os.getenv("GAUSSHOME"), "lib")
            sys.path.append(libPath)
            libc = cdll.LoadLibrary("libpq.so.5.5")
            libc.PQntuples.argTypes = [c_void_p]
            libc.PQntuples.restype = c_int
            libc.PQnfields.argTypes = [c_void_p]
            libc.PQnfields.restype = c_int
            libc.PQgetvalue.restype = c_char_p
            ntups = libc.PQntuples(self.result)
            nfields = libc.PQnfields(self.result)
            libc.PQgetvalue.argTypes = [c_void_p, c_int, c_int]
            self.resCount = ntups
            for i in range(ntups):
                tmpString = []
                for j in range(nfields):
                    paramValue = libc.PQgetvalue(self.result, i, j)
                    if paramValue is not None:
                        tmpString.append(string_at(paramValue))
                    else:
                        tmpString.append("")
                self.resSet.append(tmpString)
        except Exception as e:
            raise Exception("%s" % str(e))


class CommonCommand:
    """
    Common for cluster command
    """
    def __init__(self):
        pass

    @staticmethod
    def executeSqlOnLocalhost(sql, port=varinfo.PORT_COORDINATOR, database="postgres", timeout=300):
        """
        function: write output message
        input : sql
        output: NA
        """
        tmpResult = None
        conn = None
        libc = cdll.LoadLibrary("libpq.so.5.5")
        try:
            libPath = os.path.join(os.getenv("GAUSSHOME"), "lib")
            sys.path.append(libPath)
            conn_opts = "dbname = '%s' application_name = 'OM' options='-c session_timeout=%s'  port = %s " \
                        % (database, timeout, port)
            err_output = ""
            libc.PQconnectdb.argTypes = [c_char_p]
            libc.PQconnectdb.restype = c_void_p
            libc.PQclear.argTypes = [c_void_p]
            libc.PQfinish.argTypes = [c_void_p]
            libc.PQerrorMessage.argTypes = [c_void_p]
            libc.PQerrorMessage.restype = c_char_p
            libc.PQresultStatus.argTypes = [c_void_p]
            libc.PQresultStatus.restype = c_int
            libc.PQexec.argTypes = [c_void_p, c_char_p]
            libc.PQexec.restype = c_void_p
            conn = libc.PQconnectdb(str(conn_opts))
            if conn is None:
                raise Exception("Failed to get connection with database by options: %s" % conn_opts)
            libc.PQstatus.argTypes = [c_void_p]

            if libc.PQstatus(conn) != 0:
                raise Exception("Failed to get connection with database:" % database)
            tmpResult = libc.PQexec(conn, sql)
            if tmpResult is None:
                raise Exception("Can not get correct result by executing sql: %s" % sql)
            status = libc.PQresultStatus(tmpResult)

            resultObj = sqlResult(tmpResult)
            resultObj.parseResult()
            Error = libc.PQerrorMessage(conn)
            if Error is not None:
                err_output = string_at(Error)
            result = resultObj.resSet
            libc.PQclear(tmpResult)
            libc.PQfinish(conn)
            return status, result, err_output
        except Exception as e:
            libc.PQclear.argTypes = [c_void_p]
            libc.PQfinish.argTypes = [c_void_p]
            if tmpResult:
                libc.PQclear(tmpResult)
            if conn:
                libc.PQfinish(conn)
            raise Exception(str(e))

    @staticmethod
    def runGsqlCommand(sql, port=varinfo.PORT_COORDINATOR, database="postgres"):
        """
        function: write output message
        input : sql
        output: NA
        """
        cmd = "gsql -p %s -d %s -c \"%s\" -t -A" % (port, database, sql)
        (status, output) = commands.getstatusoutput(cmd)
        if status != 0:
            raise Exception("Failed to execute cmd: %s" % cmd)
        return status, output

    @staticmethod
    def openFile(queryFile, buffering):
        if not os.path.isfile(queryFile):
            raise Exception("File not found: %s" % queryFile)
        try:
            read = open(queryFile, buffering).read()
        except Exception as e:
            raise Exception("An exception %s occurred while open file: %s" % (e, queryFile))
        return read

    @staticmethod
    def mkDirsWithMod(path, mod):
        if not os.path.isdir(path):
            os.makedirs(path)
            os.chmod(path, mod)

    @staticmethod
    def executeCommand(cmd):
        pass
