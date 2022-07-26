select (select current_database()) as database,
       (select count(*) from pg_authid where oid > 16384) user_count,
       (select count(*) from pg_database where oid > 16384) db_count,
       (select count(*) as schema_count from pg_namespace where oid > 16384) schema_count,
       (select count(*) as table_count from pg_class where relkind = 'r' and oid > 16384) table_count;
