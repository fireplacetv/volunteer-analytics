with source as (
    select * from {{ source('airtable', 'events') }}
)

select
    id,
    created_time,
    last_modified,
    json_extract_string(json_blob, '$.event_id') as event_id,
    coalesce(json_extract_string(json_blob, '$.name'), json_extract_string(json_blob, '$.Name')) as name,
    try_cast(json_extract_string(json_blob, '$.event_date') as date) as event_date,
    coalesce(json_extract_string(json_blob, '$.description'), json_extract_string(json_blob, '$.Description')) as description,
    coalesce(json_extract_string(json_blob, '$.type'), json_extract_string(json_blob, '$.Type')) as event_type,
    coalesce(json_extract_string(json_blob, '$.location'), json_extract_string(json_blob, '$.Location')) as location,
    coalesce(json_extract_string(json_blob, '$.status'), json_extract_string(json_blob, '$."Event Status"')) as event_status,
    json_extract_string(json_blob, '$.created_by_id') as created_by_id
from source
