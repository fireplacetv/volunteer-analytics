
    
    

select
    id as unique_field,
    count(*) as n_records

from "openoakland"."raw_airtable"."event_attendance"
where id is not null
group by id
having count(*) > 1


