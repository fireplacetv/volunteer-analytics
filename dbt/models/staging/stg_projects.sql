with source as (
    select * from {{ source('airtable', 'projects') }}
)

select
    id,
    created_time,
    last_modified,
    json_extract_string(json_blob, '$.project_id') as project_id
from source
