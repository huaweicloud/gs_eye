# 1 概述

## 1.1 工具简介

1.       DWS运维过程中，对于重大问题和系统性性能问题，缺乏相关分析数据和历史追溯数据，极难快速对系统性的性能问题进行定界。DWS本身为分布式系统，架构复杂度高，内部组件和交互多，涉及数据库、OS、硬件、网络通信等很多领域的技术，因此，对于系统的运维和故障快速恢复，有着极大的诉求。

2.       gs_eye运维工具可对数据库进行实时的监控，对数据库性能指标以及OS等相关资源的指标进行监控，并可视化的展示，使得运维人员能实时了解数据库的监控状况以及资源的使用情况。使用者可以通过在一个节点上安装、启停等操作，完成对整个集群内所有节点的io、网络、数据库资源进行持续分布式监控，将监控的数据存储在本地或者自动导入指定的监控数据库中，从而提升DWS性能问题处理效率。

## 1.2 支持的GaussDB版本

GaussDB 200 6.5.1.x

GaussDB A 8.x.x

## 1.3 支持的操作系统版本

| 操作系统         | 操作系统版本                                                 |
| :--------------- | ------------------------------------------------------------ |
| SUSE操作系统     | SUSE Linux Enterprise Server 15 SP1（SUSE 15.1）、SUSE Linux Enterprise Server 12 SP5（SUSE 12.5）、SUSE Linux Enterprise Server 12 SP3（SUSE 12.3）、SUSE Linux Enterprise Server 11 SP4（SUSE 11.4） |
| RedHat操作系统   | RedHat-7.5-x86_64（RedHat 7.5）                              |
| CentOS操作系统   | CentOS-7.5-aarch64（CentOS 7.5）（仅适配华为鲲鹏916处理器）、CentOS-7.6-aarch64（CentOS 7.6）（仅适配华为鲲鹏 920处理器） |
| 中标麒麟操作系统 | NeoKylin-7.5-aarch64（仅适配华为鲲鹏916处理器）、NeoKylin-7.6-aarch64 |

 

## 1.4 原理说明

gs_eye 分为agent(进程名gs_metricagent)、server(进程名gs_archive)两个组件。

gs_metricagent运行在集群中的每个节点上，按照一定的频率采集和上报数据。

gs_archive需要运行在集群具有cn实例的节点上，负责将agent上报的数据微批导入到数据库中。

## 1.5 部署说明

目前支持3种部署模式：

（1）独立监控集群模式，部署agent和server，监控数据单独在1个集群管理（推荐）。

（2）和生产合部模式，部署agent和server，监控数据在生产集群的一个库存储管理。

（3）只部署Agent监控，监控数据在被监控的集群各个节点本地压缩存储。

## 1.6 规格约束

适用形态：DWS纯软适用

适用版本：GaussDB 200 6.5.1.x、GaussDB A 8.0.x 、GaussDB A 8.1.x

适用OS：SUSE、RedHat、CentOS系列

依赖免密：是

依赖互信：SCP模式

权限：OS(本地omm操作系统用户)，DB（本地omm数据库管理员用户）

## 1.7 资源消耗

据每个指标指定的监控周期进行采集数据， 性能影响较小可以忽略，空间消耗可以根据配置文件指定数据留存的时间，1天监控数据预估占用数据库内空间500MB/天/instance，条数45.4w/day/instance。

# 2 工具命令说明

前提：工具所有涉及的命令，都需要使用omm用户且加载GaussDB环境变量。

​	su - omm 
	source /opt/huawei/Bigdata/mppdb/.mppdbgs_profile

- 安装

  sh gs_metric.sh install

- 卸载

  sh gs_metric.sh uninstall

- 启动/停止所有组件。

  启动：sh gs_metric.sh start

  停止：sh gs_metric.sh stop

- 启动/停止gs_archive。

  启动：sh gs_metric.sh start --server

  停止：sh gs_metric.sh stop --server

- 启动/停止gs_metricagent。

  启动：sh gs_metric.sh start --agent

  停止：gs_metric.sh stop --agent

- 查看各组件状态。

  sh gs_metric.sh status

# 3 安装&使用工具

## 3.1 环境准备

以*/var/metricbase**、/var/metricbase/metricdata*目录举例，安装时可以根据需要进行替换。

前提：使用gs_eye之前，必须保证已安装GuassDB集群且各节点间HTTP或SCP可以正常使用。

- 确认HTTP是否正常：

  登陆任意非CN节点，执行命令curl -m 1 http://*x.x.x.x:xxxx* 返回值不为404，证明http正常。

- 确认scp是否正常：

  使用omm用户登陆任意非CN节点，执行scp xxx omm@*x.x.x.x*:/home/omm/ ，无报错，证明scp命令执行正常。

  *x.x.x.x* 代表gs_archive进程所在节点的IP。

  *xxxx* 代表gs_archive进程所在节点的http通信端口号。

  根据实际需要选择通信工具，使用HTTP传输，请按照3.1.1进行环境准备；

### 3.1.1 使用HTTP作为传输数据（SuSE不建议使用HTTP）

1. 安装HTTPD服务。

   mount /opt/CentOS-7-x86_64-DVD-2003.iso /media/ -o loop

   https://www.cnblogs.com/setout/p/11075324.html（如果需要先卸载，install换成erase）

2. 配置httpd：/etc/httpd/conf/httpd.conf（配置文件） /var/log/httpd/error_log 排查日志。

   Listen *8090* # 配置为未使用端口号

   DocumentRoot "*/var/metricbase*" # httpd根目录

   <Directory "*/var/metricbase/metricdata*"> # 数据的家目录

   *Dav On*

   *Options All*

   *Order allow,deny*

   *Allow from all*

3. 创建数据的家目录，并配置httpd根目录权限777。

   rm -rf */var/metricbase/metricdata* 
    mkdir -p */var/metricbase/metricdata* 
    chmod -R 777 */var/metricbase* 
    chown -R omm: */var/metricbase*

### 3.1.2 使用SCP作为传输工具

1. 保证各节点集群用户可以免密登陆。

2. 创建数据的家目录根目录权限600。

   rm -rf */var/metricbase/metricdata* 
   mkdir -p */var/metricbase/metricdata* 
   chmod -R 777 */var/metricbase* 
   chown -R omm: */var/metricbase*

## 3.2 上传工具

步骤 1      打开WinSCP工具，将**gs_eye-trunk.zip**上传到某个CN节点/home/omm目录下。

步骤 2      使用PuTTY工具，以omm用户登录此节点。

步骤 3      执行以下命令，防止“PuTTY”超时退出。

​	TMOUT=0

步骤 4      创建安装目录。

​	source /opt/huawei/Bigdata/mppdb/.mppdbgs_profile && gs_ssh -c "rm -rf /home/omm/gs_metric/"

步骤 5      解压gs_eye.zip到/home/omm/gs_metric。

​	unzip -d /home/omm/gs_metric/ /home/omm/**gs_eye-trunk**.zip

​	mv /home/omm/gs_metric/**gs_eye-trunk**/* /home/omm/gs_metric/

​	chmod u+x /home/omm/gs_metric/ -R

## 3.3 配置工具

### 3.3.1 server_conf.json配置（gs_archive）

配置文件内容如下：

{ 
 "_comment" : "config for data import", 
 "interval" : 5, 
 "metric_database": "gsmetric", 
 "data_root_path": "*/var/metricbase/metricdata/*", 
 "max_deal_package": 300, 
 "data_age" : 90, 
 "max_error_files" : 300 
 }

表3-1 参数说明

| 参数             | 参数说明                             | 取值范围                               |
| ---------------- | ------------------------------------ | -------------------------------------- |
| interval         | 每次copy入库间隔时长，单位秒         | [0, ∞]                                 |
| metric_database  | 导入数据库名称                       | 字符串。字符串不能以数字开头           |
| data_root_path   | 数据目录                             | 文件路径字符串。集群用户可读写         |
| max_deal_package | 每次入库可处理压缩包的数量，单位：个 | [1, ∞]                                 |
| data_age         | 数据有效期，单位：天                 | [2, ∞]。超出有效期后，会删除最早的数据 |

 

### 3.3.2 client_conf.json配置（gs_metricagent）

配置文件内容如下：

{ "_comment" : "config for default metric item", 
 "GlobalManager":{ 
 "_comment" : "global config for metric manager", 
 "max_threads" : 50, 
 "max_retry_times" : 5, 
 "pusher" : { 
 "method" : "nokeep", 
 "protocol" : "http", 
 "base_url" : "http://*x.x.x.x:8090/metricdata/*", 
 "interval" : 60, 
 "cluster_name" : "cluster2" 
 } 
 } 
 }

表3-2 参数说明

 

| 参数               | 参数说明                                             | 取值范围                                                     |
| ------------------ | ---------------------------------------------------- | ------------------------------------------------------------ |
| max_threads        | 采集任务的并发数量                                   | [1, ∞]                                                       |
| max_retry_times    | 暂未使用                                             | -                                                            |
| method             | 使用http时，需要指定为nokeep                         | ["", "nokeep"]                                               |
| protocol           | 传输数据使用的协议                                   | ['scp', 'http']                                              |
| base_url           | 传输数据使用的链接                                   | 1.使用scp时，参数格式为：omm@x.x.x.x: /var/metricbase/metricdata；2.使用http时，参数格式为：http://x.x.x.x:8090/metricdata/ |
| interval           | 推送数据时间间隔                                     | [0, ∞]                                                       |
| cluster_name       | 被采集的集群名称；在数据导入到的时候，用作schema名。 | 字符串。1.多个集群时，各个集群名称不能一样。2.不要包含特殊字符 |
| max_compress_files | 每次推送数据包，最多压缩的文件数量。                 | [1, ∞]                                                       |



## 3.4 安装工具

source /opt/huawei/Bigdata/mppdb/.mppdbgs_profile && sh gs_metric.sh install

## 3.5 启动工具

source /opt/huawei/Bigdata/mppdb/.mppdbgs_profile && sh gs_metric.sh start

## 3.6 停止工具

source /opt/huawei/Bigdata/mppdb/.mppdbgs_profile && sh gs_metric.sh stop

## 3.7 卸载工具

source /opt/huawei/Bigdata/mppdb/.mppdbgs_profile && sh gs_metric.sh uninstall

# 4 附录

## 4.1 目录文件说明

表4-1 目录文件

| 目录/文件                                  | 路径                                                  | 备注                 |
| ------------------------------------------ | ----------------------------------------------------- | -------------------- |
| gs_metricagent（agent）日志                | $GAUSSLOG/gs_metricdata/runlog/agent/                 | 所有节点             |
| gs_archive（server）日志                   | $GAUSSLOG/gs_metricdata/runlog/server/                | (gs_archive进程节点) |
| agent 采集到本地数据目录                   | $GAUSSLOG/gs_metricdata/data/                         | 所有节点             |
| agent 准备推送的数据目录                   | $GAUSSLOG/gs_metricdata/pusherbuffer                  | 所有节点             |
| Server未成功入库的*cluster2*的数据文件路径 | */var/metricbase/metricdata/cluster2/bad_data_files/* | (gs_archive进程节点) |
| Server接收到*cluster2*数据的存放路径       | */var/metricbase/metricdata/cluster2/data/*           | (gs_archive进程节点) |

 

## 4.2 数据存储说明

1.  数据库名由server_conf.json中metric_database定义；
2.  数据所在schema由client_conf.json中cluster_name定义。
3.  登陆数据库：gsql -p 25308 -d gsmetric -r
4.  切换schema：set current_schema='cluster2';

## 4.3 常见问题

### 4.3.1 配置类问题

1. 查看进程是否启动。

   sh gs_metric.sh status 

   进程未启动：看/home/omm/gs_metric/start.log中是否有提示参数错误或者代码错误信息。

### 4.3.2 数据未入库类问题

1. 先排查4.3.1 配置类问题

2. 排查gs_agent_watcher是否有问题。

   查看$GAUSSLOG/gs_metricdata/runlog/watcher/最新的日志中，是否有kill进程操作。

   如果有，先确认磁盘使用率是否达到80%，inode使用率是否达到80%，$GAUSSLOG/gs_metricdata目录的大小已经大于10G。

   查询磁盘使用率：df -h $GAUSSLOG/gs_metricdata/

   查询inode使用率：df -i $GAUSSLOG/gs_metricdata/

   查询文件夹大小：du -sh $GAUSSLOG/gs_metricdata

3. 排查gs_metricagent是否有问题。

   查看$GAUSSLOG/gs_metricdata/runlog/agent/日志中，是否有相关报错；搜索关键字Pusher，发送数据文件是否报错。如果有报错，先排查clinet_conf.json中protocol是否正确；base_url是否正确；base_url地址是否有权限传输。

   查看$GAUSSLOG/gs_metricdata/data/中，相关的指标文件中，数据列数量是否和metric_default.json一致。

4. 排查gs_achive是否有问题。

   登陆gs_archive所在节点。

   查看$GAUSSLOG/gs_metricdata/runlog/server/日志，根据数据表名称进行检索，排查是否入库报错。

   入库错误的数据文件会被保存在*/var/metricbase/metricdata/cluster2/bad_data_files/* 目录下，可以通过日志中的gsql命令，重新尝试导入复现错误。