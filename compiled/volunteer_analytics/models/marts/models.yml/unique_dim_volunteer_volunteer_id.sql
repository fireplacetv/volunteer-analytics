
    
    

select
    volunteer_id as unique_field,
    count(*) as n_records

from "openoakland"."stg_airtable_marts"."dim_volunteer"
where volunteer_id is not null
group by volunteer_id
having count(*) > 1


