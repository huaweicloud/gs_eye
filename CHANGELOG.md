# gs_archive修改

- 新增特性：

  1. 数据老化功能。数据默认保留90天，超过90天，按天删除数据。
  2. 运维功能。 新增运维线程，定时清理堆积的入库报错的文件。
  3. 兼容python2 & python3。

- 解决问题：

  1. 小文件不能实时入库问题。
  2. 入库报错导致文件堆积，进程退出等问题。
  3. python多线程导入数据，由于GIL导致入库排队。

- 特性变更：

  ​    无

## gs_metricagent修改

- 新增特性：

  1. 新增gs_agent_watcher。用于gs_metricagent独立部署时，本节点监控数据达到阈值时进行老化。
  2. 新增CCN采集。矫正采集信息有效性。
  3. gs_pusher支持scp传输文件模式。
  4. gs_pusher支持断点续传。
  5. 兼容python2 & python3。
  6. client_conf.json参数校验。

- 解决问题：

  1. 采集数据写入和文件压缩并发冲突，小概率导致采集指标为空。
  2. 矫正采集周期准确性。

- 特性变更：

  ​	无

  ​    

# 采集指标修改

- 新增指标：

  1. host_inode_usage_t
  2. host_disk_usage_t
  3. host_fd_count_t
  4. host_fd_deleted_count_t
  5. host_memory_stat_t
  6. host_page_swap_t
  7. host_memory_info_t
  8. host_buddy_info_t
  9. host_other_resource_t
  10. host_zombie_count_t
  11. host_top_cpu_process_t

- 指标变更

  1. 在所有cn采集修改为只在ccn上采集，涉及的表名如下： 

  ​	database_concurrency_enqueue_t

  ​	database_top_activesql_t

  ​	database_topsql_avgtime_t

  ​	database_each_sql_count_t

  ​	database_each_sql_avgtime_t

  ​	database_wait_status_t

  ​	database_workload_struct_t

  2. 从查询所有库修改为只查询postgres库，涉及的表名如下：

  ​	database_concurrency_enqueue_t

  ​	database_each_sql_count_t

  ​	database_each_sql_avgtime_t

  ​	database_catalog_deadtuple_ratio_t

  3. 指标关闭，涉及的表名如下：

  ​	database_catalog_index_backword

  4. count列名修改为cnt，涉及的表名如下（需要重建表）：

  ​	database_concurrency_enqueue_t

  ​	database_wait_status_t

  ​	database_wlmstat_t

  ​	database_residual_thread_t

  5. 表内新增一列，涉及的表名如下（需要重建表）：

  ​	database_object_t

  ​	database_catalog_deadtuple_ratio_t

  6. 删除blocked列涉及的表名如下（需要重建表）：

  ​	host_load_average_t

  ​	host_top_memory_process_t

  ​	host_instace_stat_t

  ​	host_io_stat_t


