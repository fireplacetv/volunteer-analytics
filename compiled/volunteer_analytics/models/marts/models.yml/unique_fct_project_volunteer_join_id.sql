
    
    

select
    join_id as unique_field,
    count(*) as n_records

from "openoakland"."stg_airtable_marts"."fct_project_volunteer"
where join_id is not null
group by join_id
having count(*) > 1


