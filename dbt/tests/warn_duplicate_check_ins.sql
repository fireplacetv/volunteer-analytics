{{ config(severity = 'warn') }}

-- Repeat check-ins in Airtable. stg_event_attendance collapses these, so this
-- only surfaces them for cleanup at the source.
select
    json_extract_string(json_blob, '$.event_id') as event_id,
    try_cast(json_extract_string(json_blob, '$.Date') as date) as date,
    lower(trim(json_extract_string(json_blob, '$.Email'))) as email,
    count(*) as check_in_count
from {{ source('airtable', 'event_attendance') }}
where json_extract_string(json_blob, '$.Email') is not null
group by all
having count(*) > 1
