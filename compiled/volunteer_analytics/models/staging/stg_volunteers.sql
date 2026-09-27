with source as (
    select * from "openoakland"."raw_airtable"."volunteers"
)

select
    id,
    created_time,
    last_modified,
    json_extract_string(json_blob, '$.volunteer_id') as volunteer_id,
    json_extract_string(json_blob, '$.status') as status,
    json_extract_string(json_blob, '$.first_name') as first_name,
    json_extract_string(json_blob, '$.last_name') as last_name,
    json_extract_string(json_blob, '$.email') as email,
    json_extract_string(json_blob, '$.pronouns') as pronouns,
    json_extract_string(json_blob, '$.age_range') as age_range,
    json_extract_string(json_blob, '$.city') as city,
    json_extract_string(json_blob, '$.state') as state,
    json_extract_string(json_blob, '$.timezone') as timezone,
    json_extract_string(json_blob, '$.linkedin') as linkedin,
    json_extract_string(json_blob, '$.github') as github,
    json_extract_string(json_blob, '$.website_portfolio') as website_portfolio,
    json_extract_string(json_blob, '$.slack_handle') as slack_handle,
    json_extract_string(json_blob, '$.employment_status') as employment_status,
    json_extract_string(json_blob, '$.hours_per_month') as hours_per_month,
    try_cast(json_extract_string(json_blob, '$.joined_date') as date) as joined_date,
    json_extract_string(json_blob, '$.nonprofit_experience_level') as nonprofit_experience_level,
    json_extract_string(json_blob, '$.prior_volunteer_experience') as prior_volunteer_experience,
    json_extract_string(json_blob, '$.board_leadership_experience') as board_leadership_experience,
    json_extract_string(json_blob, '$.grant_writing_experience') as grant_writing_experience,
    json_extract(json_blob, '$.tech_languages_tools') as tech_languages_tools,
    json_extract_string(json_blob, '$.tech_experience_level') as tech_experience_level,
    json_extract_string(json_blob, '$.project_interests') as project_interests,
    json_extract_string(json_blob, '$.accommodations') as accommodations,
    json_extract_string(json_blob, '$.other_notes') as other_notes,
    json_extract_string(json_blob, '$.Profile Update Link') as profile_update_link
from source