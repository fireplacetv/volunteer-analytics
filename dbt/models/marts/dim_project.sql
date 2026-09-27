with source as (
    select * from {{ ref('stg_projects') }}
)

select
    cast(project_id as integer) as project_id,
    id as airtable_record_id,
    cast(project_number as integer) as project_number,
    project_name,
    status,
    stakeholder,
    description,
    start_date,
    end_date,
    created_time as airtable_created_at,
    last_modified as airtable_modified_at
from source
