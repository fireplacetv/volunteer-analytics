with source as (
    select * from "volunteer_data"."airtable"."projects"
)

select
    id,
    created_time,
    fields__project_id as project_id
from source