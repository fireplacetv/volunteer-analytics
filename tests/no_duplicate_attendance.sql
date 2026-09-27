select volunteer_id, event_id, occasion_date
from {{ ref('fct_attendance') }}
group by volunteer_id, event_id, occasion_date
having count(*) > 1
