with source as (
    select * from {{ source('airtable', 'event_attendance') }}
)

select
    id,
    created_time,
    last_modified,
    json_extract_string(json_blob, '$.attendance_id') as attendance_id,
    json_extract_string(json_blob, '$.event_id') as event_id,
    json_extract_string(json_blob, '$.volunteer_id') as volunteer_id,
    try_cast(json_extract_string(json_blob, '$.date') as date) as date,
    json_extract_string(json_blob, '$.status') as status
from source
