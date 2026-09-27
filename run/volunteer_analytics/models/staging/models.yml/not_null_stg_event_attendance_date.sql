select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    



select date
from "openoakland"."stg_airtable_stg_airtable"."stg_event_attendance"
where date is null



      
    ) dbt_internal_test