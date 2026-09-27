
    
    

select
    id as unique_field,
    count(*) as n_records

from "openoakland"."stg_airtable_stg_airtable"."stg_volunteers"
where id is not null
group by id
having count(*) > 1


