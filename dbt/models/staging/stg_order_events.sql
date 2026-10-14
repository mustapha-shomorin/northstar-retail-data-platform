{{ config(materialized='view') }}

SELECT
    event_id,
    event_type,
    event_timestamp,
    order_id,
    customer_id,
    payment_value,
    product_id,
    device_type,
    quantity,
    _ingestion_timestamp,
    _source
FROM {{ silver_source('order_events') }}