
    
    

with child as (
    select event_id as from_field
    from "openoakland"."stg_airtable_marts"."fct_attendance"
    where event_id is not null
),

parent as (
    select event_id as to_field
    from "openoakland"."stg_airtable_marts"."dim_event"
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null


