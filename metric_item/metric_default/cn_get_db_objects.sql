select count(*) as user_count from pg_authid where oid > 16384;
select count(*) as db_count from pg_database where oid > 16384;
select count(*) as schema_count from pg_namespace where oid > 16384;
select count(*) as table_count from pg_class where relkind = 'r' and oid > 16384;
