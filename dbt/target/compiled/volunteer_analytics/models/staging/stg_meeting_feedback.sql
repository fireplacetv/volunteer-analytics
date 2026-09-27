with source as (
    select * from "volunteer_data"."airtable"."meeting_attendance"
)

select
    id,
    created_time,
    fields__date as date,
    fields__name as name,
    fields__email as email,
    fields__feedback as feedback,
    fields__notes as notes
from source