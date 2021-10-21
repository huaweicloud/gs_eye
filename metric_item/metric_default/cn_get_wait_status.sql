set statement_timeout = '5min';
SELECT wait_status
 ,wait_event
 ,count(*) AS cnt
FROM pgxc_thread_wait_status
WHERE wait_status <> 'wait cmd'
 AND wait_status <> 'synchronize quit'
 AND wait_status <> 'none'
GROUP BY 1,2
ORDER BY 3 DESC limit 50;
