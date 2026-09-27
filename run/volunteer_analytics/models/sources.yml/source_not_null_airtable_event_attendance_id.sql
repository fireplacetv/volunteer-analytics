select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    



select id
from "openoakland"."raw_airtable"."event_attendance"
where id is null



      
    ) dbt_internal_test