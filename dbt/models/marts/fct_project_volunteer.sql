with source as (
    select * from {{ ref('stg_project_volunteers') }}
),

extracted as (
    select
        id as join_id,
        json_extract_string(json_blob, '$.volunteer_id[0]') as volunteer_id,
        json_extract_string(json_blob, '$.project_id[0]') as project_id,
        json_extract_string(json_blob, '$.role') as role,
        try_cast(json_extract_string(json_blob, '$.commitment_date') as date) as commitment_date,
        try_cast(json_extract_string(json_blob, '$.end_date') as date) as end_date,
        json_extract_string(json_blob, '$.status') as status,
        (
            (case when json_extract_string(json_blob, '$.outreach_1_date') is not null then 1 else 0 end) +
            (case when json_extract_string(json_blob, '$.outreach_2_date') is not null then 1 else 0 end) +
            (case when json_extract_string(json_blob, '$.outreach_3_date') is not null then 1 else 0 end)
        ) as outreach_attempt_count,
        try_cast(json_extract_string(json_blob, '$.outreach_1_date') as date) as first_outreach_date,
        try_cast(
            case
                when json_extract_string(json_blob, '$.outreach_3_date') is not null then json_extract_string(json_blob, '$.outreach_3_date')
                when json_extract_string(json_blob, '$.outreach_2_date') is not null then json_extract_string(json_blob, '$.outreach_2_date')
                else json_extract_string(json_blob, '$.outreach_1_date')
            end
        as date) as last_outreach_date,
        case
            when json_extract_string(json_blob, '$.outreach_3_date') is not null then json_extract_string(json_blob, '$.outreach_3_status')
            when json_extract_string(json_blob, '$.outreach_2_date') is not null then json_extract_string(json_blob, '$.outreach_2_status')
            else json_extract_string(json_blob, '$.outreach_1_status')
        end as last_outreach_status,
        coalesce(json_extract_string(json_blob, '$.is_declined')::boolean, false) as is_declined,
        json_extract_string(json_blob, '$.decline_reason') as decline_reason,
        created_time as airtable_created_at,
        last_modified as airtable_modified_at
    from source
)

select * from extracted
