with source as (
    select
        cast(json_extract_string(json_blob, '$.event_id') as integer) as event_id,
        id as airtable_record_id,
        json_extract_string(json_blob, '$.name') as event_name,
        json_extract_string(json_blob, '$.type') as event_type,
        event_date,
        json_extract_string(json_blob, '$.description') as description,
        created_time,
        last_modified
    from {{ ref('stg_events') }}
),

synthetic_monthly as (
    select
        0 as event_id,
        null::varchar as airtable_record_id,
        'Monthly meetings' as event_name,
        'Monthly meeting' as event_type,
        null::date as event_date,
        'Recurring monthly all-hands meeting' as description,
        current_timestamp as created_time,
        current_timestamp as last_modified
),

all_events as (
    select * from source
    union all
    select * from synthetic_monthly
    where not exists (select 1 from source where event_id = 0)
)

select
    event_id,
    airtable_record_id,
    event_name,
    event_type,
    event_date,
    description,
    created_time as airtable_created_at,
    last_modified as airtable_modified_at,
    (event_id = 0) as is_monthly_meeting
from all_events
