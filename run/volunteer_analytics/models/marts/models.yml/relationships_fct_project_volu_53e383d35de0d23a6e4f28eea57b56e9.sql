select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    

with child as (
    select volunteer_id as from_field
    from "openoakland"."stg_airtable_marts"."fct_project_volunteer"
    where volunteer_id is not null
),

parent as (
    select volunteer_id as to_field
    from "openoakland"."stg_airtable_marts"."dim_volunteer"
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null



      
    ) dbt_internal_test