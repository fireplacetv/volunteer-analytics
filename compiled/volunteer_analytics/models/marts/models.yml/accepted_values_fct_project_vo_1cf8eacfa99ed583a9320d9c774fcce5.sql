
    
    

with all_values as (

    select
        status as value_field,
        count(*) as n_records

    from "openoakland"."stg_airtable_marts"."fct_project_volunteer"
    group by status

)

select *
from all_values
where value_field not in (
    'Active','Completed','Departed'
)


