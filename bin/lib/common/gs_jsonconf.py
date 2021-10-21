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
    import json
    import gs_logmanager as logmgr
    from collections import OrderedDict
except Exception as e:
    sys.exit("FATAL: %s Unable to import module: %s" % (__file__, e))

LOG_MODULE = "JSONCONFIG"


def MetricItemListCheck(metricItemList):
    tableList = []
    for i in metricItemList:
        tableList.append(metricItemList[i]['table']['name'])
    if len(tableList) != len(set(tableList)):
        logmgr.recordError("JsonConfig", "unique id in metricdev.json has repeated value, please check", "PANIC")
        return False
    return True


def MetricItemListGet(confFile):
    metricItemList = {}
    if os.path.isfile(confFile):
        metricItemList = json.loads(open(confFile, "r").read(), object_pairs_hook=OrderedDict)
    else:
        logmgr.recordError("JsonConfig", "config file is not exist", "PANIC")
        return metricItemList
    if "_comment" in metricItemList.keys():
        metricItemList.pop('_comment')
    if MetricItemListCheck(metricItemList) is not True:
        metricItemList.clear()
        return metricItemList
    return metricItemList


def GetMetricManagerJsonConf(confFile):
    mgrDict = {}
    if os.path.isfile(confFile):
        mgrDict = json.loads(open(confFile, "r").read(), object_pairs_hook=OrderedDict)
    else:
        logmgr.recordError("JsonConfig", "config file is not exist", "PANIC")
    return mgrDict


def GetLogModudeState(confFile):
    modState = {}
    if os.path.isfile(confFile):
        modState = json.loads(open(confFile, "r").read())
    else:
        logmgr.recordError("JsonConfig", "config file is not exist", "PANIC")
    return modState


def GetImportConf(confFile):
    importConf = {}
    if os.path.isfile(confFile):
        importConf = json.loads(open(confFile, "r").read(), object_pairs_hook=OrderedDict)
    else:
        logmgr.recordError("JsonConfig", "config file is not exist", "PANIC")
    return importConf


def SaveJsonConf(jsonDict, path):
    json_str = json.dumps(jsonDict)
    dirname = os.path.dirname(path)
    if not os.path.isdir(dirname):
        os.makedirs(dirname)
    with open(path, 'w+') as json_file:
        json_file.write(json_str)


def GetTableMappingConf(confFile):
    tablemap = {}
    if os.path.isfile(confFile):
        tablemap = json.loads(open(confFile, "r").read(), object_pairs_hook=OrderedDict)
    else:
        logmgr.recordError("JsonConfig", "config file is not exist", "PANIC")
    return tablemap


def GetClusterListConf(confFile):
    cluster_list_dict = {}
    cluster_list = []
    if os.path.isfile(confFile):
        cluster_list_dict = json.loads(open(confFile, "r").read(), object_pairs_hook=OrderedDict)
        cluster_list = cluster_list_dict['cluster_list']
    else:
        logmgr.recordError("JsonConfig", "config file is not exist", "PANIC")
    return cluster_list