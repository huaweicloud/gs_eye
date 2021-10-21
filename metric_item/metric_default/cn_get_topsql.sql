SELECT usename
 ,coorname
 ,datname
 ,query_start as starttime
 ,now() - query_start AS runtime
 ,now() - xact_start AS xactduration
 ,substr(query, 1, 100) AS query
 ,pid
 ,query_id
 ,state
 ,waiting
 ,enqueue
FROM pgxc_stat_activity
WHERE STATE <> 'idle'
 AND usename <> 'omm'
 AND usename <> 'Ruby'
ORDER BY runtime DESC LIMIT 50;
