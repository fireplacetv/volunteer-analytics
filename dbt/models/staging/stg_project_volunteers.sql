select
    id,
    created_time,
    last_modified,
    json_extract_string(json_blob, '$.join_id') as join_id,
    json_blob
from {{ source('airtable', 'project_volunteers') }}
