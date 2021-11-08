SELECT resource_pool
    ,attribute
    ,status
    ,enqueue
    ,count(1)
FROM pg_session_wlmstat
WHERE STATUS != 'finished'
    AND attribute != 'Internal'
    AND usename != 'omm'
GROUP BY 1,2,3,4;
