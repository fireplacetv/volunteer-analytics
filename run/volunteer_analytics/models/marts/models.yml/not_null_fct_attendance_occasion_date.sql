select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    



select occasion_date
from "openoakland"."stg_airtable_marts"."fct_attendance"
where occasion_date is null



      
    ) dbt_internal_test