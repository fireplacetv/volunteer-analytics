with source as (
    select * from {{ source('airtable', 'meeting_attendance') }}
)

select
    id,
    created_time,
    last_modified,
    try_cast(json_extract_string(json_blob, '$.Date') as date) as date,
    json_extract_string(json_blob, '$.Name') as name,
    json_extract_string(json_blob, '$.Email') as email,
    json_extract_string(json_blob, '$.Feedback') as feedback,
    json_extract_string(json_blob, '$.Notes') as notes
from source
