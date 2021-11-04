select ctid,oid,relname from pg_class where oid in(2662,2659,2679);
select ctid,attrelid,attname from pg_attribute where attrelid in(2662,2659,2679);
