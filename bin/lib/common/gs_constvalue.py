#!/usr/bin/env python3
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
except Exception as e:
    sys.exit("FATAL: %s Unable to import module: %s" % (__file__, e))
# Variable

"""
Version
"""
GS_METRIC_VERSION = "gs_metric 1.0.0.0"

# Byte data type. unit: byte
DATA_TYPE_KBYTES = 1024
DATA_TYPE_MBYTES = 1048576

"""
const value for agent
"""
# Metric default parameters
METRIC_DEFAULT_LOGSIZE_PER_FILE = DATA_TYPE_MBYTES * 20
METRIC_MAX_LOG_COUNT = 50
METRIC_DEFAULT_LOGTIME = 0
METRIC_LOG_RECYCLE_INTERVAL = 600

METRIC_MAX_THREADS = 50
METRIC_MAX_FAILURE = 5

# Metric item interval
METRIC_DEFAULT_ITEM_INTERVAL = 15
METRIC_MIN_ITEM_INTERVAL = 5

GS_METRIC_AGENT_NAME = "gs_metricagent"
GS_METRIC_SERVER_NAME = "gs_archive"

"""
const value for log
"""
DATA_LEN_ERROR = 1024

FILE_MAX_LOGSZIE = 10
FILE_NUM_PUSH_FAILURE = 10
FILE_TIME_FORMAT = "-%Y-%m-%d_%H%M%S"
METRIC_LOGFILE_FORMAT = FILE_TIME_FORMAT + ".log"

# delimiter divides the data block
RECORD_BEGIN_DELIMITER = "--[RECORD]" + "-" * 90
DATA_TYPE_DELIMITER = "-" * 50
RECORD_TIMELABEL_FORMAT = "%Y-%m-%d %H:%M:%S"
LABEL_HEAD_PREFIX = "GS_LABEL_HEAD"

# Invariant

# Time data type, unit: second
CLOCK_TYPE_MINS = 60
CLOCK_TYPE_HOURS = 3600
CLOCK_TYPE_DAYS = 86400

# Timestamp type
TIME_MIN_STAMP = "0000-00-00 00:00:00"
TIME_LEN_STAMP = 22

# Metric item name
METRIC_LEN_DBNAME = 7
METRIC_LEN_SYSNAME = 3

METRIC_APP_BASE = os.getcwd()
METRIC_ITEM_DIR = os.path.join(METRIC_APP_BASE, "..", "metric_item")
METRIC_CONFIG = os.path.join(METRIC_APP_BASE, "..", "conf")
MATRIC_LOGBASE = os.path.join(os.environ.get('GAUSSLOG'), "gs_metricdata")
METRIC_DATA_BASE_DIR = os.path.join(MATRIC_LOGBASE, "data")
PUSHER_BUFFER_PATH = os.path.join(MATRIC_LOGBASE, "pusherbuffer")
METRIC_RUNNING_LOG = os.path.join(MATRIC_LOGBASE, "runlog")
TABLE_MAP_FILE = "tablemapping.json"
HOST_LIST_FILE = "hostlist.json"
METRIC_SIGFLAG_FILE = os.path.join(METRIC_APP_BASE, "metric_flag")

PORT_COORDINATOR = 25308

# empty query string was executed
PGRES_EMPTY_QUERY = 0
# a query command that doesn't return anything was executed properly by the backend, such as set, create table
PGRES_COMMAND_OK = 1
# a query command that returns tuples was executed properly by the backend, PGresult contains the result tuples
PGRES_TUPLES_OK = 2
# Copy Out data transfer in progress
PGRES_COPY_OUT = 3
# Copy In data transfer in progress
PGRES_COPY_IN = 4
# an unexpected response was recv'd from the backend
PGRES_BAD_RESPONSE = 5
# notice or warning message
PGRES_NONFATAL_ERROR = 6
# query failed
PGRES_FATAL_ERROR = 7
# Copy In/Out data transfer in progress
PGRES_COPY_BOTH = 8
# single tuple from larger resultset
PGRES_SINGLE_TUPLE = 9
