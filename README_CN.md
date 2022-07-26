[脚本介绍]

gs_metric.py    监控脚本主体，为单节点运行，可对操作系统和Gauss数据库指标进行监控
gs_metric.sh    对gs_metric.py脚本的封装，用于集群级脚本的管理

gs_archive.py   数据入库脚本主体，作为服务端，定时分析数据，并导入运维库中


---------------------------------------------------------------------------------------
gs_metric.py

[参数说明]

1.   -i, --indir         指定监控项所在目录;
2.   -o, --outdir        指定日志输出路径;
3.   -u, --username      数据库用户名;
4.   -w, --password      用户密码，默认为空，线下环境"omm"用户无需指定;
5.   --logsize           保留的日志大小，默认1024，单位为MB;
6.   --logtime           保留的日志时长，默认无限制，单位为天;
7.   --url               服务端的URL，用于接收日志文件，默认为空，表示不推送;
8.   --interval          推送日志文件的时间间隔，默认30，单位为分;
9.   -h, --help          显示帮助信息;
10.  -v, --version       显示版本号;


[用法举例]

线下环境使用omm用户，线上使用Ruby用户，source环境变量后执行;

1. 添加可执行权限
chmod +x gs_metric.py

2. 脚本启动
./gs_metric.py -i metric_item/ -o /tmp/ -u omm &

3. 增加其他参数
./gs_metric.py -i metric_item/ -o /tmp/ -u omm --logsize=300 --logtime=7 &
./gs_metric.py -i metric_item/ -o /tmp/ -u omm --url=127.0.0.1/metric --interval=10


[结果说明]

1.  gs_metric-xxxx-xx-xx_xxxxxx.log     脚本运行日志，记录脚本运行状况
2.  database/cn_xxxx/xxxx               各实例下各监控项结果
3.  system/xxxx                         操作系统资源项监控结果
4.  metric_item/metric_item.conf        若不指定，脚本会根据指定目录自动生成监控配置文件


[注意]

监控脚本会解析指定目录下所有xxxx.sh、cn_xxxx.sql、dn_xxxx.sql文件，并定期执行;


---------------------------------------------------------------------------------------
gs_metric.sh

[参数说明]

1.   start           开启集群监控，并添加定时任务;
2.   stop            停止集群监控，并移除定时任务;
3.   status          检测集群内各节点监控脚本的运行状态;
4.   version         显示版本号;
5.   help            显示帮助信息;

使用前需修改相应的环境变量：
1.   MET_HOME="${GAUSSHOME}/bin/dfx_tool/gs_metric"       工具工作目录，绝对路径;
2.   BIN_HOME="${MET_HOME}/bin"                           gs_metric.py脚本所在目录，默认不变;
3.   MET_BIN="gs_metric.py"                               监控脚本名称，默认不变;
3.   ITEM_HOME="${MET_HOME}/metric_item"                  监控项文件所在目录，默认不变;
3.   LOG_HOME="${GAUSSLOG}"                               输出的日志文件所在目录;
4.   MET_OPT="-u omm"                                     其他的gs_metric.py参数，例如：-u omm -w Gauss_234等;
5.   START_HOME="${MET_HOME}"                             gs_metric.sh脚本所在目录，默认不变;
7.   START_BIN="gs_metric.sh"                             管理脚本名称，默认不变;


[用法举例]

1. 添加可执行权限
chmod +x gs_metric.sh

2. 脚本启动
./gs_metric.sh start

3. 脚本停止
./gs_metric.sh stop

4. 检测状态
./gs_metric.sh status

5. 显示版本
./gs_metric.sh version

6. 显示帮助
./gs_metric.sh help


[结果说明]

所有结果立即返回


[注意]

start功能仅在各节点添加定时任务，脚本最晚需要1分钟启动


---------------------------------------------------------------------------------------
gs_archive.py

[参数说明]

1.   -o, --outdir        指定日志输出路径;
2.   -d, --database      运维库名称，默认为: "gsmetric";
3.   -u, --username      数据库用户名;
4.   -w, --password      用户密码，默认为空，线下环境"omm"用户无需指定;
5.   --datatime          运维库保留数据时长，默认30，单位为天;
6.   --interval          数据入库的时间间隔，默认30，单位为分;
7.   --logsize           保留的日志大小，默认1024，单位为MB;
8.   --logtime           保留的日志时长，默认无限制，单位为天;
9.   -h, --help          显示帮助信息;
10.  -v, --version       显示版本号;


[用法举例]

线下环境使用omm用户，线上使用Ruby用户，source环境变量后执行;
gs_archive.py适用于8.1及以下版本环境，使用python2;

1. 添加可执行权限
chmod +x gs_archive.py

2. 脚本启动
./gs_archive.py -o /tmp/ -u omm &

3. 增加其他参数
./gs_metric.py -o /tmp/ -u omm --datatime=30 --logsize=300 &


[结果说明]

1. gs_archive-xxxx-xx-xx_xxxxxx.log        脚本运行日志，记录脚本运行状况
2. gs_archive_dump-xxxx-xx-xx_xxxxxx       数据入库情况日志，记录入库详细过程
