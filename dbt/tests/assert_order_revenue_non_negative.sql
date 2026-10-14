SELECT
    order_id,
    SUM(total_item_value) AS order_revenue
FROM {{ ref('fact_order_items') }}
GROUP BY order_id
HAVING SUM(total_item_value) < 0