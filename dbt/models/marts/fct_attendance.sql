with attendance as (
    select * from {{ ref('stg_event_attendance') }}
),

volunteers as (
	select * from {{ ref('dim_volunteer') }}
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
	left join volunteers v on lower(a.email) = lower(v.email)
)

select * from joined
