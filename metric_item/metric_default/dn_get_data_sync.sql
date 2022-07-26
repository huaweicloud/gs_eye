select pid,
       sender_pid,
       local_role,
       peer_role,
       state,
       catchup_start,
       catchup_end,
       queue_size,
       queue_lower_tail,
       queue_header,
       queue_upper_tail,
       send_position,
       receive_position
from pg_stat_get_data_senders();
