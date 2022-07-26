select current_database() as database, relname,pg_stat_get_live_tuples(oid) as live, pg_stat_get_dead_tuples(oid) as dead from pg_class where oid in (1249,1255,1259,2608,2619,9016);
