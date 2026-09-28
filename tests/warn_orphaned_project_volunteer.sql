{{ config(severity = 'warn') }}

select count(*) as orphaned_count
from {{ ref('fct_project_volunteer') }}
where volunteer_id is null or project_id is null
having orphaned_count > 0
