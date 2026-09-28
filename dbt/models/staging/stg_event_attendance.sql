with source as (
    select * from {{ source('airtable', 'event_attendance') }}
),

renamed as (
    select
        id,
        created_time,
        last_modified,
        json_extract_string(json_blob, '$.attendance_id') as attendance_id,
        json_extract_string(json_blob, '$.event_id') as event_id,
        try_cast(json_extract_string(json_blob, '$.Date') as date) as date,
        json_extract_string(json_blob, '$.Email') as email
    from source
),

-- Collapse repeat check-ins (same event, date and email), keeping the earliest.
-- Rows without an email fall back to their record id so they are never merged.
deduplicated as (
    {{ dbt_utils.deduplicate(
        relation='renamed',
        partition_by='event_id, date, coalesce(lower(trim(email)), id)',
        order_by='created_time, id'
    ) }}
)

select * from deduplicated
