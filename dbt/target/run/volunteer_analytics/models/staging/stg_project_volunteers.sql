
  
  create view "volunteer_data"."airtable"."stg_project_volunteers__dbt_tmp" as (
    select
    id,
    created_time,
    fields__join_id as join_id
from "volunteer_data"."airtable"."project_volunteers"
  );
