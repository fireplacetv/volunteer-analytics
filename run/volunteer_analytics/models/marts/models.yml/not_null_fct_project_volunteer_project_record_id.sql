select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    



select project_record_id
from "openoakland"."stg_airtable_marts"."fct_project_volunteer"
where project_record_id is null



      
    ) dbt_internal_test