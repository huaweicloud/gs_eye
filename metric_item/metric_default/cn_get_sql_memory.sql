SELECT usename
 ,datname
 ,query_id
 ,pid
 ,substr(query,1,200) as query
 ,contextname
 ,level
 ,parent
 ,pg_size_pretty(totalsize) AS total
 ,pg_size_pretty(freesize) AS freesize
 ,pg_size_pretty(usedsize) AS usedsize
FROM pv_session_memory_detail a
 ,pg_stat_activity b
WHERE split_part(a.sessid ,'.', length(replace(a.sessid,'.','..')) - length(a.sessid) + 1)  = b.pid
ORDER BY totalsize DESC limit 100;
