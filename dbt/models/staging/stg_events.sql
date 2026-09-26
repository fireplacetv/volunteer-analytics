with source as (
    select * from {{ source('airtable', 'events') }}
)

select
    id,
    created_time,
    fields__event_id as event_id,
    fields__name as name,
    fields__event_date as event_date,
    fields__description as description,
    fields__location as location,
    fields__event_status as event_status,
    fields__check_in_url as check_in_url,
    fields__qr_code as qr_code,
    fields__created_by__id as created_by_id,
    fields__created_by__email as created_by_email,
    fields__created_by__name as created_by_name
from source
