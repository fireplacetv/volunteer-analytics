
    
    

select
    id as unique_field,
    count(*) as n_records

from "openoakland"."raw_airtable"."volunteers"
where id is not null
group by id
having count(*) > 1


