with source as (
    select * from "openoakland"."stg_airtable_stg_airtable"."stg_volunteers"
)

select
    id as volunteer_id,
	email,
    status,
    joined_date,
    employment_status,
    hours_per_month,
    state,
    timezone,
    coalesce(board_leadership_experience::boolean, false) as has_board_leadership_experience,
    coalesce(grant_writing_experience::boolean, false) as has_grant_writing_experience,
    created_time as airtable_created_at,
    last_modified as airtable_modified_at
from source