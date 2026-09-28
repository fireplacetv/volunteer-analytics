-- Orphaned rows (null volunteer_id) are covered by warn_orphaned_attendance
select volunteer_id, event_id, occasion_date
from {{ ref('fct_attendance') }}
where volunteer_id is not null
group by volunteer_id, event_id, occasion_date
having count(*) > 1
