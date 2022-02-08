{% macro athena__get_columns_in_relation(relation) -%}
  {% call statement('get_columns_in_relation', fetch_result=True) %}

      select
          column_name,
          data_type,
          null as character_maximum_length,
          null as numeric_precision,
          null as numeric_scale

      from {{ relation.information_schema('columns') }}
      where LOWER(table_name) = LOWER('{{ relation.identifier }}')
        {% if relation.schema %}
            and LOWER(table_schema) = LOWER('{{ relation.schema }}')
        {% endif %}
      order by ordinal_position

  {% endcall %}

  {% set table = load_result('get_columns_in_relation').table %}
  {% do return(sql_convert_columns_in_relation(table)) %}
{% endmacro %}


{% macro alter_relation_add_remove_columns(relation, add_columns = none, remove_columns = none) -%}
  {{ return(adapter.dispatch('alter_relation_add_remove_columns', 'dbt')(relation, add_columns, remove_columns)) }}
{% endmacro %}

{% macro athena__alter_relation_add_remove_columns(relation, add_columns, remove_columns) %}
  
  {% if add_columns is none %}
    {% set add_columns = [] %}
  {% endif %}
  {% if remove_columns is none %}
    {% set remove_columns = [] %}
  {% endif %}
  
  {% set sql -%}
     alter {{ relation.type }} {{ relation }}
            add columns
            (
              {% for column in add_columns %}
                  {{ column.name }} {%- if ('varchar' in column.data_type) or ('character varying' in column.data_type) %} {{ 'string'  }}
                  {%- elif ('integer' in column.data_type) %} {{ 'int'  }}
                  {%- else %} {{ column.data_type  }}
                  {%- endif %}{{ ',' if not loop.last }}
              {% endfor %}{{ ',' if add_columns and remove_columns }}
            )
            
            {% for column in remove_columns %}
                drop column {{ column.name }}{{ ',' if not loop.last }}
            {% endfor %}
  
  {%- endset -%}
  {% do log(sql) %}
  {% do run_query(sql) %}

{% endmacro %}
