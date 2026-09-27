select
    id,
    created_time,
    fields__join_id as join_id
from "volunteer_data"."airtable"."project_volunteers"