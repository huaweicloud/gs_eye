set statement_timeout = '10min';
SELECT application_name
 ,count(*) AS finished_jobs_count
 ,sum(duration) AS jobs_total_time
 ,jobs_total_time / finished_jobs_count AS jobs_avg_time
FROM pgxc_wlm_session_info
WHERE start_time >= current_date
 AND start_time < current_date + 1
GROUP BY 1;
