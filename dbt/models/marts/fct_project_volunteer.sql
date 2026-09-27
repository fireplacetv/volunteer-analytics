with source as (
    select * from {{ ref('stg_project_volunteers') }}
),

with_derived as (
    select
        join_id,
        volunteer_id,
        project_record_id,
        role,
        commitment_date,
        end_date,
        status,
        (
            (case when outreach_1_date is not null then 1 else 0 end) +
            (case when outreach_2_date is not null then 1 else 0 end) +
            (case when outreach_3_date is not null then 1 else 0 end)
        ) as outreach_attempt_count,
        outreach_1_date as first_outreach_date,
        case
            when outreach_3_date is not null then outreach_3_date
            when outreach_2_date is not null then outreach_2_date
            else outreach_1_date
        end as last_outreach_date,
        case
            when outreach_3_date is not null then outreach_3_status
            when outreach_2_date is not null then outreach_2_status
            else outreach_1_status
        end as last_outreach_status,
        coalesce(cast(declined as boolean), false) as is_declined,
        decline_reason,
        airtable_created_at,
        airtable_modified_at
    from source
)

select * from with_derived
