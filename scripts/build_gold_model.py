import duckdb
from pathlib import Path


DB_PATH = Path("data/northstar.duckdb")

GOLD_DIMENSIONS = Path("data/gold/dimensions")
GOLD_FACTS = Path("data/gold/facts")


def main():
    GOLD_DIMENSIONS.mkdir(parents=True, exist_ok=True)
    GOLD_FACTS.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(DB_PATH))

    print("Building Gold dimensional model...")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. DIM_CUSTOMER
    # Grain: one row per customer_unique_id
    # ------------------------------------------------------------------
    con.execute("""
        CREATE OR REPLACE TABLE dim_customer AS
        SELECT
            ROW_NUMBER() OVER (
                ORDER BY customer_unique_id
            ) AS customer_key,
            customer_unique_id,
            MAX(customer_city) AS customer_city,
            MAX(customer_state) AS customer_state,
            MAX(customer_zip_code_prefix) AS customer_zip_code_prefix
        FROM silver_customers
        GROUP BY customer_unique_id
    """)

    # ------------------------------------------------------------------
    # 2. DIM_PRODUCT
    # Grain: one row per product
    # ------------------------------------------------------------------
    con.execute("""
        CREATE OR REPLACE TABLE dim_product AS
        SELECT
            ROW_NUMBER() OVER (
                ORDER BY product_id
            ) AS product_key,
            product_id,
            product_category_name,
            product_name_lenght AS product_name_length,
            product_description_lenght AS product_description_length,
            product_photos_qty,
            product_weight_g,
            product_length_cm,
            product_height_cm,
            product_width_cm
        FROM silver_products
    """)

    # ------------------------------------------------------------------
    # 3. DIM_SELLER
    # Grain: one row per seller
    # ------------------------------------------------------------------
    con.execute("""
        CREATE OR REPLACE TABLE dim_seller AS
        SELECT
            ROW_NUMBER() OVER (
                ORDER BY seller_id
            ) AS seller_key,
            seller_id,
            seller_city,
            seller_state,
            seller_zip_code_prefix
        FROM silver_sellers
    """)

    # ------------------------------------------------------------------
    # 4. DIM_GEOGRAPHY
    # Grain: one row per ZIP-code prefix
    # ------------------------------------------------------------------
    con.execute("""
        CREATE OR REPLACE TABLE dim_geography AS
        SELECT
            ROW_NUMBER() OVER (
                ORDER BY geolocation_zip_code_prefix
            ) AS geography_key,
            geolocation_zip_code_prefix AS zip_code_prefix,
            ANY_VALUE(geolocation_city) AS city,
            ANY_VALUE(geolocation_state) AS state,
            AVG(geolocation_lat) AS latitude,
            AVG(geolocation_lng) AS longitude
        FROM silver_geolocation
        GROUP BY geolocation_zip_code_prefix
    """)

    # ------------------------------------------------------------------
    # 5. DIM_DATE
    # Grain: one row per calendar date
    # ------------------------------------------------------------------
    con.execute("""
        CREATE OR REPLACE TABLE dim_date AS
        WITH date_range AS (
            SELECT
                CAST(MIN(order_purchase_timestamp) AS DATE) AS min_date,
                CAST(
                    GREATEST(
                        MAX(order_purchase_timestamp),
                        MAX(order_estimated_delivery_date)
                    ) AS DATE
                ) AS max_date
            FROM silver_orders
        ),
        calendar AS (
            SELECT
                unnest(
                    generate_series(
                        min_date,
                        max_date,
                        INTERVAL 1 DAY
                    )
                )::DATE AS full_date
            FROM date_range
        )
        SELECT
            CAST(STRFTIME(full_date, '%Y%m%d') AS INTEGER) AS date_key,
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
        FROM calendar
        ORDER BY full_date
    """)

    # # ------------------------------------------------------------------
    # # 6. FACT_ORDERS
    # # Grain: one row per order
    # # ------------------------------------------------------------------
    # con.execute("""
    #     CREATE OR REPLACE TABLE fact_orders AS
    #     SELECT
    #         o.order_id,

    #         c.customer_key,

    #         CAST(
    #             STRFTIME(CAST(o.order_purchase_timestamp AS DATE), '%Y%m%d')
    #             AS INTEGER
    #         ) AS order_date_key,

    #         CASE
    #             WHEN o.order_approved_at IS NOT NULL THEN
    #                 CAST(
    #                     STRFTIME(CAST(o.order_approved_at AS DATE), '%Y%m%d')
    #                     AS INTEGER
    #                 )
    #         END AS approved_date_key,

    #         CASE
    #             WHEN o.order_delivered_carrier_date IS NOT NULL THEN
    #                 CAST(
    #                     STRFTIME(
    #                         CAST(o.order_delivered_carrier_date AS DATE),
    #                         '%Y%m%d'
    #                     )
    #                     AS INTEGER
    #                 )
    #         END AS carrier_delivery_date_key,

    #         CASE
    #             WHEN o.order_delivered_customer_date IS NOT NULL THEN
    #                 CAST(
    #                     STRFTIME(
    #                         CAST(o.order_delivered_customer_date AS DATE),
    #                         '%Y%m%d'
    #                     )
    #                     AS INTEGER
    #                 )
    #         END AS customer_delivery_date_key,

    #         CASE
    #             WHEN o.order_estimated_delivery_date IS NOT NULL THEN
    #                 CAST(
    #                     STRFTIME(
    #                         CAST(o.order_estimated_delivery_date AS DATE),
    #                         '%Y%m%d'
    #                     )
    #                     AS INTEGER
    #                 )
    #         END AS estimated_delivery_date_key,

    #         o.order_status,

    #         CASE
    #             WHEN o.order_approved_at IS NOT NULL THEN
    #                 DATE_DIFF(
    #                     'day',
    #                     CAST(o.order_purchase_timestamp AS DATE),
    #                     CAST(o.order_approved_at AS DATE)
    #                 )
    #         END AS order_to_approval_days,

    #         CASE
    #             WHEN o.order_approved_at IS NOT NULL
    #                  AND o.order_delivered_carrier_date IS NOT NULL THEN
    #                 DATE_DIFF(
    #                     'day',
    #                     CAST(o.order_approved_at AS DATE),
    #                     CAST(o.order_delivered_carrier_date AS DATE)
    #                 )
    #         END AS approval_to_carrier_days,

    #         CASE
    #             WHEN o.order_delivered_carrier_date IS NOT NULL
    #                  AND o.order_delivered_customer_date IS NOT NULL THEN
    #                 DATE_DIFF(
    #                     'day',
    #                     CAST(o.order_delivered_carrier_date AS DATE),
    #                     CAST(o.order_delivered_customer_date AS DATE)
    #                 )
    #         END AS carrier_to_customer_days,

    #         CASE
    #             WHEN o.order_delivered_customer_date IS NOT NULL THEN
    #                 DATE_DIFF(
    #                     'day',
    #                     CAST(o.order_purchase_timestamp AS DATE),
    #                     CAST(o.order_delivered_customer_date AS DATE)
    #                 )
    #         END AS order_to_customer_delivery_days,

    #         CASE
    #             WHEN o.order_delivered_customer_date IS NOT NULL
    #                  AND o.order_estimated_delivery_date IS NOT NULL THEN
    #                 DATE_DIFF(
    #                     'day',
    #                     CAST(o.order_estimated_delivery_date AS DATE),
    #                     CAST(o.order_delivered_customer_date AS DATE)
    #                 )
    #         END AS delivery_delay_days

    #     FROM silver_orders o
    #     LEFT JOIN dim_customer c
    #         ON o.customer_id IN (
    #             SELECT customer_id
    #             FROM silver_customers sc
    #             WHERE sc.customer_unique_id = c.customer_unique_id
    #         )
    # """)



    # ------------------------------------------------------------------
    # 6. FACT_ORDERS
    # Grain: one row per order
    # ------------------------------------------------------------------
    con.execute("""
        CREATE OR REPLACE TABLE fact_orders AS
        SELECT
            o.order_id,

            c.customer_key,

            CAST(
                STRFTIME(
                    CAST(o.order_purchase_timestamp AS DATE),
                    '%Y%m%d'
                ) AS INTEGER
            ) AS order_date_key,

            CASE
                WHEN o.order_approved_at IS NOT NULL THEN
                    CAST(
                        STRFTIME(
                            CAST(o.order_approved_at AS DATE),
                            '%Y%m%d'
                        ) AS INTEGER
                    )
            END AS approved_date_key,

            CASE
                WHEN o.order_delivered_carrier_date IS NOT NULL THEN
                    CAST(
                        STRFTIME(
                            CAST(o.order_delivered_carrier_date AS DATE),
                            '%Y%m%d'
                        ) AS INTEGER
                    )
            END AS carrier_delivery_date_key,

            CASE
                WHEN o.order_delivered_customer_date IS NOT NULL THEN
                    CAST(
                        STRFTIME(
                            CAST(o.order_delivered_customer_date AS DATE),
                            '%Y%m%d'
                        ) AS INTEGER
                    )
            END AS customer_delivery_date_key,

            CASE
                WHEN o.order_estimated_delivery_date IS NOT NULL THEN
                    CAST(
                        STRFTIME(
                            CAST(o.order_estimated_delivery_date AS DATE),
                            '%Y%m%d'
                        ) AS INTEGER
                    )
            END AS estimated_delivery_date_key,

            o.order_status,

            CASE
                WHEN o.order_approved_at IS NOT NULL THEN
                    DATE_DIFF(
                        'day',
                        CAST(o.order_purchase_timestamp AS DATE),
                        CAST(o.order_approved_at AS DATE)
                    )
            END AS order_to_approval_days,

            CASE
                WHEN o.order_approved_at IS NOT NULL
                    AND o.order_delivered_carrier_date IS NOT NULL THEN
                    DATE_DIFF(
                        'day',
                        CAST(o.order_approved_at AS DATE),
                        CAST(o.order_delivered_carrier_date AS DATE)
                    )
            END AS approval_to_carrier_days,

            CASE
                WHEN o.order_delivered_carrier_date IS NOT NULL
                    AND o.order_delivered_customer_date IS NOT NULL THEN
                    DATE_DIFF(
                        'day',
                        CAST(o.order_delivered_carrier_date AS DATE),
                        CAST(o.order_delivered_customer_date AS DATE)
                    )
            END AS carrier_to_customer_days,

            CASE
                WHEN o.order_delivered_customer_date IS NOT NULL THEN
                    DATE_DIFF(
                        'day',
                        CAST(o.order_purchase_timestamp AS DATE),
                        CAST(o.order_delivered_customer_date AS DATE)
                    )
            END AS order_to_customer_delivery_days,

            CASE
                WHEN o.order_delivered_customer_date IS NOT NULL
                    AND o.order_estimated_delivery_date IS NOT NULL THEN
                    DATE_DIFF(
                        'day',
                        CAST(o.order_estimated_delivery_date AS DATE),
                        CAST(o.order_delivered_customer_date AS DATE)
                    )
            END AS delivery_delay_days

        FROM silver_orders o

        LEFT JOIN silver_customers sc
            ON o.customer_id = sc.customer_id

        LEFT JOIN dim_customer c
            ON sc.customer_unique_id = c.customer_unique_id
    """)

    # ------------------------------------------------------------------
    # 7. FACT_ORDER_ITEMS
    # Grain: one row per order item
    # ------------------------------------------------------------------
    con.execute("""
        CREATE OR REPLACE TABLE fact_order_items AS
        SELECT
            oi.order_id,
            oi.order_item_id,
            p.product_key,
            s.seller_key,

            CASE
                WHEN oi.shipping_limit_date IS NOT NULL THEN
                    CAST(
                        STRFTIME(
                            CAST(oi.shipping_limit_date AS DATE),
                            '%Y%m%d'
                        )
                        AS INTEGER
                    )
            END AS shipping_limit_date_key,

            oi.price,
            oi.freight_value,

            COALESCE(oi.price, 0)
                + COALESCE(oi.freight_value, 0)
                AS total_item_value

        FROM silver_order_items oi

        LEFT JOIN dim_product p
            ON oi.product_id = p.product_id

        LEFT JOIN dim_seller s
            ON oi.seller_id = s.seller_id
    """)

    # ------------------------------------------------------------------
    # 8. FACT_PAYMENTS
    # Grain: one row per payment transaction
    # ------------------------------------------------------------------
    con.execute("""
        CREATE OR REPLACE TABLE fact_payments AS
        SELECT
            order_id,
            payment_sequential,
            payment_type,
            payment_installments,
            payment_value
        FROM silver_order_payments
    """)

    # ------------------------------------------------------------------
    # Export Gold tables to Parquet
    # ------------------------------------------------------------------
    dimension_tables = [
        "dim_customer",
        "dim_product",
        "dim_seller",
        "dim_geography",
        "dim_date",
    ]

    fact_tables = [
        "fact_orders",
        "fact_order_items",
        "fact_payments",
    ]

    print("\nExporting dimensions...")

    for table in dimension_tables:
        output = GOLD_DIMENSIONS / f"{table}.parquet"

        con.execute(
            f"""
            COPY {table}
            TO '{output.as_posix()}'
            (FORMAT PARQUET, COMPRESSION ZSTD)
            """
        )

        count = con.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        print(f"{table}: {count:,} rows")

    print("\nExporting facts...")

    for table in fact_tables:
        output = GOLD_FACTS / f"{table}.parquet"

        con.execute(
            f"""
            COPY {table}
            TO '{output.as_posix()}'
            (FORMAT PARQUET, COMPRESSION ZSTD)
            """
        )

        count = con.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        print(f"{table}: {count:,} rows")

    con.close()

    print("\nGold dimensional model built successfully.")


if __name__ == "__main__":
    main()