{{ config(materialized='table') }}

WITH orders AS (

    SELECT *
    FROM {{ ref('stg_orders') }}

),

customers AS (

    SELECT
        customer_id,
        customer_unique_id
    FROM {{ ref('stg_customers') }}

),

customer_dimension AS (

    SELECT
        customer_key,
        customer_unique_id
    FROM {{ ref('dim_customer') }}

)

SELECT
    o.order_id,

    dc.customer_key,

    CAST(
        STRFTIME(CAST(o.order_purchase_timestamp AS DATE), '%Y%m%d')
        AS INTEGER
    ) AS order_purchase_date_key,

    CAST(
        STRFTIME(CAST(o.order_approved_at AS DATE), '%Y%m%d')
        AS INTEGER
    ) AS order_approved_date_key,

    CAST(
        STRFTIME(CAST(o.order_delivered_carrier_date AS DATE), '%Y%m%d')
        AS INTEGER
    ) AS delivered_carrier_date_key,

    CAST(
        STRFTIME(CAST(o.order_delivered_customer_date AS DATE), '%Y%m%d')
        AS INTEGER
    ) AS delivered_customer_date_key,

    CAST(
        STRFTIME(CAST(o.order_estimated_delivery_date AS DATE), '%Y%m%d')
        AS INTEGER
    ) AS estimated_delivery_date_key,

    o.order_status,

    CASE
        WHEN o.order_purchase_timestamp IS NOT NULL
         AND o.order_approved_at IS NOT NULL
        THEN DATE_DIFF(
            'hour',
            o.order_purchase_timestamp,
            o.order_approved_at
        )
    END AS purchase_to_approval_hours,

    CASE
        WHEN o.order_approved_at IS NOT NULL
         AND o.order_delivered_carrier_date IS NOT NULL
        THEN DATE_DIFF(
            'hour',
            o.order_approved_at,
            o.order_delivered_carrier_date
        )
    END AS approval_to_carrier_hours,

    CASE
        WHEN o.order_delivered_carrier_date IS NOT NULL
         AND o.order_delivered_customer_date IS NOT NULL
        THEN DATE_DIFF(
            'hour',
            o.order_delivered_carrier_date,
            o.order_delivered_customer_date
        )
    END AS carrier_to_customer_hours,

    CASE
        WHEN o.order_purchase_timestamp IS NOT NULL
         AND o.order_delivered_customer_date IS NOT NULL
        THEN DATE_DIFF(
            'day',
            o.order_purchase_timestamp,
            o.order_delivered_customer_date
        )
    END AS purchase_to_customer_days,

    CASE
        WHEN o.order_purchase_timestamp IS NOT NULL
         AND o.order_estimated_delivery_date IS NOT NULL
        THEN DATE_DIFF(
            'day',
            o.order_purchase_timestamp,
            o.order_estimated_delivery_date
        )
    END AS purchase_to_estimated_days

FROM orders o

LEFT JOIN customers c
    ON o.customer_id = c.customer_id

LEFT JOIN customer_dimension dc
    ON c.customer_unique_id = dc.customer_unique_id