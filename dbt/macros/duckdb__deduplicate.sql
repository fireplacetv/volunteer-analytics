{#
-- dbt_utils has no DuckDB implementation, and its default natural-joins on
-- every column, which silently drops any row containing a null. DuckDB
-- supports QUALIFY, so use the same approach as dbt_utils' Snowflake version.
#}
{%- macro duckdb__deduplicate(relation, partition_by, order_by) -%}

    select *
    from {{ relation }}
    qualify
        row_number() over (
            partition by {{ partition_by }}
            order by {{ order_by }}
        ) = 1

{%- endmacro -%}
