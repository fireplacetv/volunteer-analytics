with source as (
    select * from "volunteer_data"."airtable"."event_attendance"
)

select
    id,
    created_time,
    fields__attendance_id as attendance_id,
    fields__event_id as event_id,
    fields__date as date,
    fields__name as name,
    fields__email as email
from source