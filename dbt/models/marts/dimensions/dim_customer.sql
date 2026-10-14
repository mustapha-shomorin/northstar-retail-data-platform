{{ config(materialized='table') }}

SELECT
    ROW_NUMBER() OVER (
        ORDER BY customer_unique_id
    ) AS customer_key,

    customer_unique_id,

    ANY_VALUE(customer_id) AS customer_id,

    ANY_VALUE(customer_zip_code_prefix) AS customer_zip_code_prefix,

    ANY_VALUE(customer_city) AS customer_city,

    ANY_VALUE(customer_state) AS customer_state

FROM {{ ref('stg_customers') }}

GROUP BY customer_unique_id