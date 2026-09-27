with source as (
    select * from "volunteer_data"."airtable"."project_volunteers"
),

with_indices as (
    select
        id,
        created_time,
        fields__join_id as join_id,
        fields__volunteer_id,
        fields__project_id,
        generate_subscripts(fields__volunteer_id, 1) as idx
    from source
    where fields__volunteer_id is not null
        and fields__project_id is not null
        and cardinality(fields__volunteer_id) > 0
)

select
    id,
    created_time,
    join_id,
    fields__volunteer_id[idx] as volunteer_id,
    fields__project_id[idx] as project_id
from with_indices
where idx <= least(cardinality(fields__volunteer_id), cardinality(fields__project_id))