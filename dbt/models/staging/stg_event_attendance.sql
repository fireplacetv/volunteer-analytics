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
        -- Keyed hash of the normalized email, set at ingestion (dlt/airtable_pipeline/pii.py)
        json_extract_string(json_blob, '$.email_hash') as email_hash
    from source
),

-- Collapse repeat check-ins (same event, date and email), keeping the earliest.
-- Rows without an email fall back to their record id so they are never merged.
-- The hash is already case- and whitespace-normalized.
deduplicated as (
    {{ dbt_utils.deduplicate(
        relation='renamed',
        partition_by='event_id, date, coalesce(email_hash, id)',
        order_by='created_time, id'
    ) }}
)

select * from deduplicated
