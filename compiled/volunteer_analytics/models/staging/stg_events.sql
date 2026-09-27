with source as (
    select * from "openoakland"."raw_airtable"."events"
)

select
    id,
    created_time,
    last_modified,
    json_extract_string(json_blob, '$.event_id') as event_id,
    json_extract_string(json_blob, '$.name') as name,
    try_cast(json_extract_string(json_blob, '$.event_date') as date) as event_date,
    json_extract_string(json_blob, '$.description') as description,
    coalesce(json_extract_string(json_blob, '$.type'), json_extract_string(json_blob, '$.Type')) as event_type,
    json_extract_string(json_blob, '$.location') as location,
    json_extract_string(json_blob, '$.status') as event_status,
    json_extract_string(json_blob, '$.check_in_url') as check_in_url,
    json_extract_string(json_blob, '$.qr_code') as qr_code,
    json_extract_string(json_blob, '$.created_by_id') as created_by_id,
    json_extract_string(json_blob, '$.created_by_email') as created_by_email,
    json_extract_string(json_blob, '$.created_by_name') as created_by_name
from source