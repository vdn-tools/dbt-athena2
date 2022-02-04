{% macro athena__create_table_as(temporary, relation, sql) -%}
  {%- set external_location = config.get('external_location', default=none) -%}
  {%- set partitioned_by = config.get('partitioned_by', default=none) -%}
  {%- set bucketed_by = config.get('bucketed_by', default=none) -%}
  {%- set bucket_count = config.get('bucket_count', default=none) -%}
  {%- set field_delimiter = config.get('field_delimiter', default=none) -%}
  {%- set format = config.get('format', default='parquet') -%}

  create table
    {{ relation }}

    with (
      external_location='{{ adapter.s3_table_location(relation.schema, relation.identifier) }}',
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