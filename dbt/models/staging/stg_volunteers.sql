with source as (
    select * from {{ source('airtable', 'volunteers') }}
)

select
    id,
    created_time,
    last_modified,
    json_extract_string(json_blob, '$.volunteer_id') as volunteer_id,
    json_extract_string(json_blob, '$.status') as status,
    -- Pseudonymized at ingestion (dlt/airtable_pipeline/pii.py): fake names and a keyed email hash
    json_extract_string(json_blob, '$.first_name') as first_name,
    json_extract_string(json_blob, '$.last_name') as last_name,
    json_extract_string(json_blob, '$.email_hash') as email_hash,
    json_extract_string(json_blob, '$.state') as state,
    json_extract_string(json_blob, '$.timezone') as timezone,
    json_extract_string(json_blob, '$.employment_status') as employment_status,
    json_extract_string(json_blob, '$.hours_per_month') as hours_per_month,
    try_cast(json_extract_string(json_blob, '$.joined_date') as date) as joined_date,
    json_extract_string(json_blob, '$.nonprofit_experience_level') as nonprofit_experience_level,
    json_extract_string(json_blob, '$.board_leadership_experience') as board_leadership_experience,
    json_extract_string(json_blob, '$.grant_writing_experience') as grant_writing_experience,
    json_extract(json_blob, '$.tech_languages_tools') as tech_languages_tools,
    json_extract_string(json_blob, '$.tech_experience_level') as tech_experience_level
from source
