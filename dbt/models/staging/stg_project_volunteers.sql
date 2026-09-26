with source as (
    select * from {{ source('airtable', 'project_volunteers') }}
)

select
    id,
    created_time,
    fields__join_id as join_id
from source
