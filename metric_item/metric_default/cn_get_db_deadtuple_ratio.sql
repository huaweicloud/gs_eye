select pg_stat_get_live_tuples('pg_class'::regclass) as live, pg_stat_get_dead_tuples('pg_class'::regclass) as dead, dead/(dead+live) as pg_class_dead_ratio;
select pg_stat_get_live_tuples('pg_attribute'::regclass) as live, pg_stat_get_dead_tuples('pg_attribute'::regclass) as dead, dead/(dead+live) as pg_attribute_dead_ratio;
select pg_stat_get_live_tuples('pg_proc'::regclass) as live, pg_stat_get_dead_tuples('pg_proc'::regclass) as dead, dead/(dead+live) as pg_proc_dead_ratio;
select pg_stat_get_live_tuples('pg_depend'::regclass) as live, pg_stat_get_dead_tuples('pg_depend'::regclass) as dead, dead/(dead+live) as pg_depend_dead_ratio;
select pg_stat_get_live_tuples('pg_partition'::regclass) as live, pg_stat_get_dead_tuples('pg_partition'::regclass) as dead, dead/(dead+live) as pg_partition_dead_ratio;
select pg_stat_get_live_tuples('pg_statistic'::regclass) as live, pg_stat_get_dead_tuples('pg_statistic'::regclass) as dead, dead/(dead+live) as pg_statistic_dead_ratio;
