{% macro athena__create_table_as(temporary, relation, sql) -%}
  {%- set s3_data_dir = adapter.s3_table_location(relation.schema, relation.identifier) -%}
  {%- set partitioned_by = config.get('partitioned_by', default=none) -%}
  {%- set bucketed_by = config.get('bucketed_by', default=none) -%}
  {%- set bucket_count = config.get('bucket_count', default=none) -%}
  {%- set field_delimiter = config.get('field_delimiter', default=none) -%}
  {%- set format = config.get('format', default='parquet') -%}

  create table
    {{ relation }}

    with (
      {%- if adapter.get_creds().work_group is none %}
        {# Ensure s3_data_dir is empty to avoid Athena exception HIVE_PATH_ALREADY_EXISTS #}
        {%- do adapter.delete_s3_object(s3_data_dir) %}
        external_location = '{{ s3_data_dir }}',
      {%- endif %}

      {%- if partitioned_by is not none %}
        partitioned_by=ARRAY{{ partitioned_by | tojson | replace('\"', '\'') }},
      {%- endif %}

      {%- if bucketed_by is not none %}
        bucketed_by=ARRAY{{ bucketed_by | tojson | replace('\"', '\'') }},
      {%- endif %}

      {%- if bucket_count is not none %}
        bucket_count={{ bucket_count }},
      {%- endif %}

      {%- if field_delimiter is not none %}
        field_delimiter='{{ field_delimiter }}',
      {%- endif %}

        format='{{ format }}'
    )
  as
    {{ sql }}
{% endmacro %}
