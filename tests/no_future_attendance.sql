select *
from {{ ref('fct_attendance') }}
where occasion_date > current_date
