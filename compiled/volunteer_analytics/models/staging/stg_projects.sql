with source as (
    select * from "openoakland"."raw_airtable"."projects"
)

select
    id,
    created_time,
    last_modified,
    json_extract_string(json_blob, '$.project_id') as project_id,
    json_extract_string(json_blob, '$.project_number') as project_number,
    json_extract_string(json_blob, '$.name') as project_name,
    json_extract_string(json_blob, '$.status') as status,
    json_extract_string(json_blob, '$.stakeholder') as stakeholder,
    json_extract_string(json_blob, '$.description') as description,
    try_cast(json_extract_string(json_blob, '$.start_date') as date) as start_date,
    try_cast(json_extract_string(json_blob, '$.end_date') as date) as end_date
from source