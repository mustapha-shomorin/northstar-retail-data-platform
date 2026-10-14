{% macro silver_source(table_name) %}

    read_parquet(
        '{{ var("silver_path") }}/{{ table_name }}/data.parquet'
    )

{% endmacro %}