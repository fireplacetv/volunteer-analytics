
    
    

select
    attendance_id as unique_field,
    count(*) as n_records

from "openoakland"."stg_airtable_marts"."fct_attendance"
where attendance_id is not null
group by attendance_id
having count(*) > 1


