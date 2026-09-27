
    
    

select
    project_id as unique_field,
    count(*) as n_records

from "openoakland"."stg_airtable_marts"."dim_project"
where project_id is not null
group by project_id
having count(*) > 1


