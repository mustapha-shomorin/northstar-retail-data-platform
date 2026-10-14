{{ config(materialized='table') }}

WITH date_spine AS (

    SELECT
        date_value::DATE AS full_date

    FROM generate_series(
        DATE '2016-01-01',
        DATE '2018-03-31',
        INTERVAL '1 day'
    ) AS t(date_value)

)

SELECT
    CAST(
        STRFTIME(full_date, '%Y%m%d')
        AS INTEGER
    ) AS date_key,

    full_date,

    EXTRACT(YEAR FROM full_date)::INTEGER AS year,

    EXTRACT(QUARTER FROM full_date)::INTEGER AS quarter,

    EXTRACT(MONTH FROM full_date)::INTEGER AS month,

    STRFTIME(full_date, '%B') AS month_name,

    EXTRACT(WEEK FROM full_date)::INTEGER AS week,

    EXTRACT(DAY FROM full_date)::INTEGER AS day,

    STRFTIME(full_date, '%A') AS day_name,

    CASE
        WHEN DAYOFWEEK(full_date) IN (0, 6)
        THEN TRUE
        ELSE FALSE
    END AS is_weekend

FROM date_spine