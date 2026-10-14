# NorthStar Retail — Data Lineage

## 1. Overview

Data lineage describes how data moves through the NorthStar Retail data platform, from the original source datasets through Bronze and Silver storage, the dbt transformation layer, Gold analytical models, and finally business-facing marts.

The lineage provides traceability from a dashboard metric back to its underlying source records.

The platform uses two complementary lineage layers:

1. **Physical data lineage** — traces data through the storage layers:
   Source CSV → Bronze Parquet → Silver Parquet → dbt models → Gold tables/marts

2. **Logical transformation lineage** — traces dependencies between dbt models using `ref()` relationships.

---

## 2. End-to-End Lineage

The overall data flow is:

```text
Olist CSV Dataset
       |
       v
Batch Ingestion
       |
       v
Bronze Parquet
       |
       v
Silver Parquet
       |
       v
dbt Staging Models
       |
       v
dbt Gold Dimensions / Facts
       |
       v
dbt Business Marts
       |
       v
DuckDB
       |
       v
BI / Analytics
```

Streaming data follows a parallel path:

```text
Synthetic Events
       |
       v
Redpanda
       |
       v
Streaming Bronze Parquet
       |
       v
Streaming Silver Parquet
       |
       v
dbt Staging
       |
       v
Analytical Models
```

---

## 3. Physical Storage Lineage

### 3.1 Historical Customer Data

```text
olist_customers_dataset.csv
        |
        v
data/bronze/olist/customers/
        |
        v
data/silver/customers/data.parquet
        |
        v
dbt stg_customers
        |
        v
dbt dim_customer
        |
        v
fact_orders.customer_key
```

The original customer dataset contains one record per Olist customer identifier.

The Silver layer standardizes the source data and preserves the customer attributes required by the analytical model.

The dbt staging model exposes the Silver data to the transformation layer.

`dim_customer` then changes the analytical grain to one row per `customer_unique_id`, providing the surrogate `customer_key` used by the fact table.

---

### 3.2 Historical Order Data

```text
olist_orders_dataset.csv
        |
        v
data/bronze/olist/orders/
        |
        v
data/silver/orders/data.parquet
        |
        v
dbt stg_orders
        |
        v
dbt fact_orders
        |
        +----------------------+
        |                      |
        v                      v
Order KPIs              mart_sales_daily
```

The order dataset supplies order identifiers, customer relationships, order status, and order lifecycle timestamps.

These fields are transformed into `fact_orders`, where date keys and order-processing duration metrics are derived.

---

### 3.3 Order Item Revenue Lineage

The primary revenue lineage used by the sales mart is:

```text
olist_order_items_dataset.csv
        |
        v
data/bronze/olist/order_items/
        |
        v
data/silver/order_items/data.parquet
        |
        v
dbt stg_order_items
        |
        v
dbt fact_order_items
        |
        v
fact_order_items.total_item_value
        |
        v
dbt mart_sales_daily
        |
        v
daily_revenue
        |
        v
rolling_7d_revenue
```

The `total_item_value` metric is calculated as:

```text
total_item_value = price + freight_value
```

The `mart_sales_daily` model aggregates `total_item_value` by order purchase date.

The seven-day rolling revenue metric is then calculated using a window function:

```sql
SUM(daily_revenue) OVER (
    ORDER BY full_date
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
)
```

This provides a continuous seven-day revenue measure across the calendar.

---

## 4. Product Lineage

```text
olist_products_dataset.csv
        |
        v
data/bronze/olist/products/
        |
        v
data/silver/products/data.parquet
        |
        v
dbt stg_products
        |
        v
dbt dim_product
        |
        v
fact_order_items.product_key
```

The staging model also standardizes source field names.

For example:

```text
product_name_lenght
        ↓
product_name_length

product_description_lenght
        ↓
product_description_length
```

The Gold product dimension provides the surrogate `product_key` used by `fact_order_items`.

---

## 5. Seller Lineage

```text
olist_sellers_dataset.csv
        |
        v
data/bronze/olist/sellers/
        |
        v
data/silver/sellers/data.parquet
        |
        v
dbt stg_sellers
        |
        v
dbt dim_seller
        |
        v
fact_order_items.seller_key
```

The seller dimension provides seller location attributes and the surrogate `seller_key`.

---

## 6. Geography Lineage

```text
olist_geolocation_dataset.csv
        |
        v
data/bronze/olist/geolocation/
        |
        v
data/silver/geolocation/data.parquet
        |
        v
dbt stg_geolocation
        |
        v
dbt dim_geography
```

The Silver geolocation layer contains standardized geolocation records.

The Gold geography dimension aggregates records by ZIP-code prefix and derives representative latitude and longitude values.

The Gold model uses:

- average latitude
- average longitude
- representative city
- representative state

for each ZIP-code prefix.

---

## 7. Payment Lineage

```text
olist_order_payments_dataset.csv
        |
        v
data/bronze/olist/order_payments/
        |
        v
data/silver/order_payments/data.parquet
        |
        v
dbt stg_order_payments
        |
        v
dbt fact_payments
```

`fact_payments` preserves the payment transaction grain:

```text
order_id + payment_sequential
```

This allows multiple payment records for the same order to be represented without collapsing individual transactions.

---

## 8. Customer-to-Order Lineage

The customer relationship is resolved through the source customer identifier and the analytical customer dimension:

```text
stg_orders.customer_id
        |
        v
stg_customers.customer_id
        |
        v
stg_customers.customer_unique_id
        |
        v
dim_customer.customer_unique_id
        |
        v
dim_customer.customer_key
        |
        v
fact_orders.customer_key
```

This design separates the source-level customer identifier from the analytical customer entity.

`dim_customer` uses `customer_unique_id` as its natural business key and generates a surrogate `customer_key`.

---

## 9. Date Dimension Lineage

The date dimension is generated within dbt rather than directly copied from a source dataset.

```text
dbt generate_series()
        |
        v
dbt dim_date
        |
        +----------------------+
        |          |           |
        v          v           v
fact_orders   mart_sales   Other marts
date keys     daily dates
```

`dim_date` covers:

```text
2016-01-01 → 2018-03-31
```

and provides:

- date key
- full date
- year
- quarter
- month
- month name
- week
- day
- day name
- weekend indicator

This allows analytical models to use consistent calendar attributes.

---

## 10. Streaming Event Lineage

Streaming events have a separate ingestion path:

```text
Synthetic Event Producer
        |
        v
Redpanda
        |
        v
northstar-events topic
        |
        v
Streaming Consumer
        |
        v
data/bronze/streaming/
        |
        v
data/silver/order_events/data.parquet
        |
        v
dbt stg_order_events
```

The streaming Bronze layer preserves ingestion metadata such as:

- `_ingestion_timestamp`
- `_source`

The Silver transformation validates:

- required event identifiers
- event types
- timestamps
- duplicate event IDs
- numeric fields

Invalid events are quarantined rather than silently discarded.

---

## 11. dbt Logical Lineage

The dbt transformation layer establishes dependencies using `ref()`.

### Staging

```text
Silver Parquet
    |
    +--> stg_customers
    +--> stg_sellers
    +--> stg_products
    +--> stg_orders
    +--> stg_order_items
    +--> stg_order_payments
    +--> stg_order_reviews
    +--> stg_geolocation
    +--> stg_order_events
```

### Dimensions

```text
stg_customers
    |
    v
dim_customer

stg_products
    |
    v
dim_product

stg_sellers
    |
    v
dim_seller

stg_geolocation
    |
    v
dim_geography

generate_series()
    |
    v
dim_date
```

### Facts

```text
stg_orders
    +------------------+
    |                  |
    v                  v
stg_customers      dim_customer
    |                  |
    +--------+---------+
             |
             v
       fact_orders


stg_order_items
    |             |
    v             v
dim_product    dim_seller
    |             |
    +------+------+
           |
           v
   fact_order_items


stg_order_payments
           |
           v
    fact_payments
```

### Business Mart

```text
fact_orders
      |
      +------------------+
      |                  |
      v                  v
fact_order_items     dim_date
      |                  |
      +--------+---------+
               |
               v
       mart_sales_daily
```

---

## 12. Dashboard KPI Traceability Example

A dashboard KPI such as **7-Day Rolling Revenue** can be traced through the following chain:

```text
Dashboard KPI
    |
    v
mart_sales_daily.rolling_7d_revenue
    |
    v
mart_sales_daily.daily_revenue
    |
    v
fact_order_items.total_item_value
    |
    +-------------------+
    |                   |
    v                   v
price             freight_value
    |                   |
    +---------+---------+
              |
              v
      stg_order_items
              |
              v
data/silver/order_items/data.parquet
              |
              v
data/bronze/olist/order_items/
              |
              v
olist_order_items_dataset.csv
```

This provides a clear audit path from the business metric to the original source data.

---

## 13. Example: Customer KPI Traceability

A customer-related KPI can follow:

```text
Dashboard
    |
    v
fact_orders.customer_key
    |
    v
dim_customer.customer_key
    |
    v
dim_customer.customer_unique_id
    |
    v
stg_customers.customer_unique_id
    |
    v
data/silver/customers/data.parquet
    |
    v
data/bronze/olist/customers/
    |
    v
olist_customers_dataset.csv
```

This makes it possible to identify the source record and transformation path behind a customer-level analytical result.

---

## 14. Lineage and Data Quality

Lineage is supported by data quality checks at multiple stages.

### Bronze

The ingestion process records:

- source file
- ingestion timestamp
- batch ID

### Silver

Validation checks include:

- primary key uniqueness
- composite key uniqueness
- required columns
- referential integrity
- streaming event validation
- duplicate event detection

### dbt

The transformation layer currently contains 64 automated data tests covering:

- not-null constraints
- uniqueness
- fact grain
- dimension keys
- referential relationships
- mart metrics
- streaming event identifiers

Latest validation:

```text
PASS=64
WARN=0
ERROR=0
SKIP=0
TOTAL=64
```

This means the current dbt transformation graph passes all configured data quality tests.

---

## 15. Lineage Limitations

The current dbt staging models read Silver Parquet files through the `silver_source` macro.

The project also maintains a `sources.yml` file describing the nine Silver datasets.

Because the staging macro directly invokes DuckDB's `read_parquet()` function, the physical Parquet source is documented separately from the dbt model dependency graph.

Therefore:

- `ref()` dependencies provide logical dbt lineage between transformation models.
- `docs/data-lineage.md` provides the physical source-to-storage lineage.
- The combination provides end-to-end traceability for the current local architecture.

This approach keeps the current implementation simple while maintaining explicit lineage documentation.

---

## 16. Lineage Summary

| Layer | Example | Lineage Role |
|---|---|---|
| Source | Olist CSV | Original source |
| Bronze | Parquet | Raw, auditable ingestion |
| Silver | Cleaned Parquet | Standardized/conformed data |
| dbt Staging | `stg_orders` | Transformation entry point |
| dbt Dimensions | `dim_customer` | Analytical entities |
| dbt Facts | `fact_order_items` | Business events/measures |
| dbt Marts | `mart_sales_daily` | Business metrics |
| DuckDB | Analytical database | Query/serving layer |
| BI | Dashboard | Business consumption |

The resulting lineage enables NorthStar Retail to trace analytical outputs from business metrics back through Gold, Silver, and Bronze to the original source datasets.
