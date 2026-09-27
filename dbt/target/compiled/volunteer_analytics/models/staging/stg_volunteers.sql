with source as (
    select * from "volunteer_data"."airtable"."volunteers"
)

select
    id,
    created_time,
    fields__volunteer_id as volunteer_id,
    fields__first_name as first_name,
    fields__last_name as last_name,
    fields__email as email,
    fields__pronouns as pronouns,
    fields__age_range as age_range,
    fields__city as city,
    fields__state as state,
    fields__timezone as timezone,
    fields__linkedin as linkedin,
    fields__github as github,
    fields__website_portfolio as website_portfolio,
    fields__slack_handle as slack_handle,
    fields__employment_status as employment_status,
    fields__hours_per_month as hours_per_month,
    fields__joined_date as joined_date,
    fields__nonprofit_experience_level as nonprofit_experience_level,
    fields__prior_volunteer_experience as prior_volunteer_experience,
    fields__board_leadership_experience as board_leadership_experience,
    fields__grant_writing_experience as grant_writing_experience,
    fields__tech_skills as tech_skills,
    fields__tech_languages_tools as tech_languages_tools,
    fields__tech_experience_level as tech_experience_level,
    fields__project_interests as project_interests,
    fields__accommodations as accommodations,
    fields__other_notes as other_notes,
    fields__profile_update_link as profile_update_link
from source