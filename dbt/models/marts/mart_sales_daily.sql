{{ config(materialized='table') }}

WITH daily_sales AS (

    SELECT
        fo.order_purchase_date_key AS date_key,

        SUM(foi.total_item_value) AS daily_revenue,

        COUNT(DISTINCT fo.order_id) AS daily_orders

    FROM {{ ref('fact_orders') }} fo

    INNER JOIN {{ ref('fact_order_items') }} foi
        ON fo.order_id = foi.order_id

    GROUP BY
        fo.order_purchase_date_key

),

calendar AS (

    SELECT
        date_key,
        full_date,
        year,
        quarter,
        month,
        month_name,
        week,
        day,
        day_name,
        is_weekend

    FROM {{ ref('dim_date') }}

),

daily_metrics AS (

    SELECT
        c.date_key,
        c.full_date,
        c.year,
        c.quarter,
        c.month,
        c.month_name,
        c.week,
        c.day,
        c.day_name,
        c.is_weekend,

        COALESCE(ds.daily_revenue, 0) AS daily_revenue,

        COALESCE(ds.daily_orders, 0) AS daily_orders

    FROM calendar c

    LEFT JOIN daily_sales ds
        ON c.date_key = ds.date_key

)

SELECT
    date_key,
    full_date,
    year,
    quarter,
    month,
    month_name,
    week,
    day,
    day_name,
    is_weekend,

    daily_revenue,

    daily_orders,

    SUM(daily_revenue) OVER (
        ORDER BY full_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS rolling_7d_revenue,

    SUM(daily_orders) OVER (
        ORDER BY full_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS rolling_7d_orders

FROM daily_metrics