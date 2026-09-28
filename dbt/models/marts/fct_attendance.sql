with attendance as (
    select * from {{ ref('stg_event_attendance') }}
),

-- Match check-ins to volunteers on the keyed email hash. This comes from
-- staging so the hash never has to appear in the marts.
volunteers as (
    select id as volunteer_id, email_hash
    from {{ ref('stg_volunteers') }}
    where email_hash is not null
),

events as (
    select * from {{ ref('dim_event') }}
),

joined as (
    select
        a.id as attendance_id,
        v.volunteer_id,
        cast(a.event_id as integer) as event_id,
        (cast(a.event_id as integer) = 0) as is_monthly_meeting,
        e.event_type as occasion_type,
        coalesce(a.date, e.event_date) as occasion_date,
        a.created_time as airtable_created_at,
        a.last_modified as airtable_modified_at
    from attendance a
    left join events e on cast(a.event_id as integer) = e.event_id
    left join volunteers v on a.email_hash = v.email_hash
)

select * from joined
