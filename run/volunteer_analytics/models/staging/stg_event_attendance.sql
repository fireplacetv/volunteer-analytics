
  
  create view "openoakland"."stg_airtable_stg_airtable"."stg_event_attendance__dbt_tmp" as (
    with source as (
    select * from "openoakland"."raw_airtable"."event_attendance"
)

select
    id,
    created_time,
    last_modified,
    json_extract_string(json_blob, '$.attendance_id') as attendance_id,
    json_extract_string(json_blob, '$.event_id') as event_id,
    try_cast(json_extract_string(json_blob, '$.Date') as date) as date,
    json_extract_string(json_blob, '$.Email') as email
from source
  );
