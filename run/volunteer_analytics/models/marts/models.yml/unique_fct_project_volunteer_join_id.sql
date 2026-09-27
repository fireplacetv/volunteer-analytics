select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    

select
    join_id as unique_field,
    count(*) as n_records

from "openoakland"."stg_airtable_marts"."fct_project_volunteer"
where join_id is not null
group by join_id
having count(*) > 1



      
    ) dbt_internal_test