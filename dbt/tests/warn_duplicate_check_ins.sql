{{ config(severity = 'warn') }}

-- Repeat check-ins in Airtable. stg_event_attendance collapses these, so this
-- only surfaces them for cleanup at the source.
select
    json_extract_string(json_blob, '$.event_id') as event_id,
    try_cast(json_extract_string(json_blob, '$.Date') as date) as date,
    json_extract_string(json_blob, '$.email_hash') as email_hash,
    count(*) as check_in_count
from {{ source('airtable', 'event_attendance') }}
where json_extract_string(json_blob, '$.email_hash') is not null
group by all
having count(*) > 1
