{{ config(severity = 'warn') }}

select count(*) as orphaned_count
from {{ ref('fct_attendance') }}
where volunteer_id is null
having orphaned_count > 0
