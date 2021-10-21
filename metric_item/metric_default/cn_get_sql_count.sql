SELECT user_name
 ,node_name
 ,select_count
 ,update_count
 ,insert_count
 ,delete_count
 ,mergeinto_count
 ,ddl_count
 ,dml_count
 ,dcl_count
FROM pgxc_sql_count;
