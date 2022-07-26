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
        'none': 0,
        'query': 1,
        'command': 2,
        'command_in_superuser': 3,
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
        'none': 0,
        'coordinator': 1,
        'datanode': 2,
        'instance': 3,
        'ccn': 4
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
        'off': 0,
        'durative': 1,
        'times': 2,
        'dry': 3
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
        'offline': 0,
        'schedule': 1,
    }
    return methodState[state]
