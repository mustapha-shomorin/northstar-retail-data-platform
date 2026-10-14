{{ config(materialized='table') }}

WITH order_items AS (

    SELECT *
    FROM {{ ref('stg_order_items') }}

),

products AS (

    SELECT
        product_key,
        product_id
    FROM {{ ref('dim_product') }}

),

sellers AS (

    SELECT
        seller_key,
        seller_id
    FROM {{ ref('dim_seller') }}

)

SELECT
    oi.order_id,

    oi.order_item_id,

    dp.product_key,

    ds.seller_key,

    CAST(
        STRFTIME(
            CAST(oi.shipping_limit_date AS DATE),
            '%Y%m%d'
        )
        AS INTEGER
    ) AS shipping_limit_date_key,

    oi.price,

    oi.freight_value,

    oi.price + oi.freight_value AS total_item_value

FROM order_items oi

LEFT JOIN products dp
    ON oi.product_id = dp.product_id

LEFT JOIN sellers ds
    ON oi.seller_id = ds.seller_id