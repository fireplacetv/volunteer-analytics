with source as (
    select * from {{ source('airtable', 'events') }}
)

select
    id,
    created_time,
    last_modified,
    json_extract_string(json_blob, '$.event_id') as event_id,
    json_extract_string(json_blob, '$.Name') as name,
    try_cast(json_extract_string(json_blob, '$.event_date') as date) as event_date,
    json_extract_string(json_blob, '$.Description') as description,
    json_extract_string(json_blob, '$.Location') as location,
    json_extract_string(json_blob, '$.Event Status') as event_status,
    json_extract_string(json_blob, '$.Check-in URL') as check_in_url,
    json_extract_string(json_blob, '$.QR code') as qr_code,
    json_extract_string(json_blob, '$.Created By[0].id') as created_by_id,
    json_extract_string(json_blob, '$.Created By[0].email') as created_by_email,
    json_extract_string(json_blob, '$.Created By[0].name') as created_by_name
from source
