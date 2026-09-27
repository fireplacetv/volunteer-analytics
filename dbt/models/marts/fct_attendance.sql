with attendance as (
    select * from {{ ref('stg_event_attendance') }}
),

events as (
    select * from {{ ref('dim_event') }}
),

joined as (
    select
        a.id as attendance_id,
        a.volunteer_id,
        cast(a.event_id as integer) as event_id,
        (cast(a.event_id as integer) = 0) as is_monthly_meeting,
        e.event_type as occasion_type,
        coalesce(a.date, e.event_date) as occasion_date,
        a.status,
        (a.status in ('Attended', 'Remote')) as is_present,
        a.created_time as airtable_created_at,
        a.last_modified as airtable_modified_at
    from attendance a
    left join events e on cast(a.event_id as integer) = e.event_id
)

select * from joined
