{% macro generate_schema_name(custom_schema_name, node) -%}
	{#- 
		Check the output mode, defaulting to 'dev' if DBT_OUTPUT_MODE is
	    empty/not set
	-#}
    {%- set output_mode = env_var('DBT_OUTPUT_MODE', 'dev') -%}
    
    {%- if output_mode == 'production' -%}
        {#- Production mode: use the custom schema directly (e.g., 'marts') -#}
        {%- if custom_schema_name is none -%}
            {{ target.schema }}
        {%- else -%}
            {{ custom_schema_name }}
        {%- endif -%}
        
    {%- else -%}
		{#-
			Dev mode: get user, lowercase it, and replace dots, hyphens, or
			spaces with underscores
		-#}
        {%- set raw_user = env_var('USER', 'dev') -%}
        {%- set current_user = raw_user | lower | replace('.', '_') | replace('-', '_') | replace(' ', '_') -%}
        
        {%- if custom_schema_name is none -%}
            dbt_{{ current_user }}_{{ target.schema }}
        {%- else -%}
            dbt_{{ current_user }}_{{ custom_schema_name }}
        {%- endif -%}
    {%- endif -%}
{%- endmacro %}
