SELECT username
    ,nodename
    ,pid
    ,queryid
    ,start_time
    ,block_time
    ,enqueue
    ,resource_pool
    ,estimate_memory
    ,max_peak_memory
    ,spill_info
    ,max_spill_size
    ,average_spill_size
    ,max_peak_iops
    ,warning
    ,query_band
FROM gs_wlm_session_statistics;
