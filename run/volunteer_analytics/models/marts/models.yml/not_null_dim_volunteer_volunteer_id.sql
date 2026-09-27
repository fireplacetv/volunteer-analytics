select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    



select volunteer_id
from "openoakland"."stg_airtable_marts"."dim_volunteer"
where volunteer_id is null



      
    ) dbt_internal_test