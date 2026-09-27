select
    id,
    created_time,
    last_modified,
    json_extract_string(json_blob, '$.join_id') as join_id
from {{ source('airtable', 'project_volunteers') }}
