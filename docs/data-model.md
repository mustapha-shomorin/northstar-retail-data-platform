# NorthStar Retail — Data Model

## 1. Overview

NorthStar Retail uses a layered lakehouse-style architecture:

```text
Bronze → Silver → Gold
```

The Bronze layer preserves source data in an auditable, recoverable form. The Silver layer contains cleaned, standardized, deduplicated, and validated data. The Gold layer provides business-ready dimensional models for analytical workloads and BI.
The Gold layer is implemented using DuckDB tables and exported as compressed Parquet files.

## 2. Data Modeling Objectives
The Gold model is designed to:
- support retail sales and operational analytics
- provide consistent business definitions
- separate measurable business events from descriptive attributes
- support efficient analytical queries
- maintain clear fact-table grains
- provide reusable dimensions across multiple facts
- support BI tools and downstream analytical workloads
- remain reproducible in a local Docker/Python environment

## 3. Gold Dimensional Model
The Gold layer follows a dimensional modeling approach consisting of:

### Fact tables
| Table | Grain |
| --- | --- |
| fact_orders | One row per order |
| fact_order_items | One row per order item |
| fact_payments | One row per payment transaction |

### Dimension tables
| Table | Grain |
| --- | --- |
| dim_customer | One row per unique customer |
| dim_product | One row per product |
| dim_seller | One row per seller |
| dim_geography | One row per ZIP-code prefix |
| dim_date | One row per calendar date |

## 4. Dimension Tables

### 4.1 dim_customer
**Grain:** One row per customer_unique_id.

The source Olist dataset contains both customer_id and customer_unique_id. customer_id is associated with individual order records, while customer_unique_id represents the underlying customer.
Therefore, dim_customer is modeled at the unique-customer level.

**Columns**
| Column | Description |
| --- | --- |
| customer_key | Surrogate dimension key |
| customer_unique_id | Business identifier for the customer |
| customer_city | Customer city |
| customer_state | Customer state |
| customer_zip_code_prefix | Customer ZIP-code prefix |

**Row count:** 96,096 unique customers.

### 4.2 dim_product
**Grain:** One row per product.

**Columns**
| Column | Description |
| --- | --- |
| product_key | Surrogate dimension key |
| product_id | Source product identifier |
| product_category_name | Product category |
| product_name_length | Product name length |
| product_description_length | Product description length |
| product_photos_qty | Number of product photos |
| product_weight_g | Product weight in grams |
| product_length_cm | Product length |
| product_height_cm | Product height |
| product_width_cm | Product width |

The source column product_name_lenght is standardized to product_name_length in the Gold model. Likewise, product_description_lenght is standardized to product_description_length.

**Row count:** 32,951 products.

### 4.3 dim_seller
**Grain:** One row per seller.

**Columns**
| Column | Description |
| --- | --- |
| seller_key | Surrogate dimension key |
| seller_id | Source seller identifier |
| seller_city | Seller city |
| seller_state | Seller state |
| seller_zip_code_prefix | Seller ZIP-code prefix |

**Row count:** 3,095 sellers.

### 4.4 dim_geography
**Grain:** One row per ZIP-code prefix.

The source geolocation dataset contains multiple geographic observations for some ZIP-code prefixes. Therefore, individual raw geolocation records are not treated as individual Gold geography entities.
For each ZIP-code prefix:
- city and state are retained
- latitude is aggregated using the average latitude
- longitude is aggregated using the average longitude

This provides one standardized geography record per ZIP-code prefix.

**Columns**
| Column | Description |
| --- | --- |
| geography_key | Surrogate geography key |
| zip_code_prefix | ZIP-code prefix |
| city | City |
| state | State |
| latitude | Average latitude |
| longitude | Average longitude |

**Row count:** 19,015 ZIP-code prefixes.

### 4.5 dim_date
**Grain:** One row per calendar date.

The date dimension is generated independently rather than sourced from the Olist data. The calendar covers the date range required by the order dataset.

**Columns**
| Column | Description |
| --- | --- |
| date_key | Integer date key in YYYYMMDD format |
| full_date | Calendar date |
| year | Calendar year |
| quarter | Calendar quarter |
| month | Month number |
| month_name | Month name |
| week | Week number |
| day | Day of month |
| day_name | Day name |
| is_weekend | Weekend indicator |

**Row count:** 800 calendar dates.

## 5. Fact Tables

### 5.1 fact_orders
**Grain:** One row per order.
fact_orders is the central order-level fact table.

**Columns**
| Column | Description |
| --- | --- |
| order_id | Source order identifier |
| customer_key | Foreign key to dim_customer |
| order_date_key | Foreign key to dim_date |
| approved_date_key | Foreign key to dim_date |
| carrier_delivery_date_key | Foreign key to dim_date |
| customer_delivery_date_key | Foreign key to dim_date |
| estimated_delivery_date_key | Foreign key to dim_date |
| order_status | Order status |
| order_to_approval_days | Days from purchase to approval |
| approval_to_carrier_days | Days from approval to carrier handoff |
| carrier_to_customer_days | Days from carrier handoff to customer delivery |
| order_to_customer_delivery_days | Total days from order to customer delivery |
| delivery_delay_days | Difference between actual and estimated delivery |

**Row count:** 99,441 orders.

### 5.2 fact_order_items
**Grain:** One row per order item.
The natural grain is: order_id + order_item_id

**Columns**
| Column | Description |
| --- | --- |
| order_id | Foreign key to the order |
| order_item_id | Item sequence within the order |
| product_key | Foreign key to dim_product |
| seller_key | Foreign key to dim_seller |
| shipping_limit_date_key | Shipping deadline date |
| price | Product price |
| freight_value | Freight/shipping cost |
| total_item_value | Price plus freight value |

**Row count:** 112,650 order items.

### 5.3 fact_payments
**Grain:** One row per payment transaction.
The natural grain is: order_id + payment_sequential

**Columns**
| Column | Description |
| --- | --- |
| order_id | Foreign key to the order |
| payment_sequential | Payment sequence within the order |
| payment_type | Payment method |
| payment_installments | Number of installments |
| payment_value | Payment amount |

**Row count:** 103,886 payment transactions.

## 6. Fact-to-Dimension Relationships
The primary relationships are:

```text
dim_customer
      │
      │ customer_key
      ▼
fact_orders
      │
      ├──────────────► dim_date
      │                order_date_key
      │
      └──────────────► dim_date
                       delivery date keys


fact_orders
      │
      │ order_id
      ▼
fact_order_items
      │
      ├──────────────► dim_product
      │                product_key
      │
      └──────────────► dim_seller
                       seller_key


fact_payments
      │
      │ order_id
      ▼
   orders
```

The dim_date dimension is role-playing in fact_orders. Different date keys represent different business events:
- order date
- approval date
- carrier delivery date
- customer delivery date
- estimated delivery date

## 7. Surrogate Keys
Surrogate integer keys are used for the main dimensions:
- customer_key
- product_key
- seller_key
- geography_key

These keys provide stable analytical identifiers independent of source-system identifiers.
Source/business identifiers such as customer_unique_id, product_id, and seller_id are retained alongside the surrogate keys.

## 8. Slowly Changing Dimensions
NorthStar uses Slowly Changing Dimension Type 1 (SCD Type 1) for the current Gold dimensional model.

Under Type 1:
- the latest attribute value replaces the previous value
- historical versions of dimension records are not maintained
- no effective-start or effective-end dates are required

**Rationale**
The Olist dataset does not provide reliable attribute-change history for most dimensions.
Implementing SCD Type 2 without genuine historical change events would require creating artificial historical states that are not present in the source data.
Therefore, Type 1 is appropriate for the current project scope.
If a production source later provides reliable change history, selected dimensions could be migrated to Type 2.

## 9. Bronze → Silver → Gold Transformation
The overall transformation process is:

```text
SOURCE DATA
    │
    ▼
┌─────────────┐
│   BRONZE    │
│             │
│ Raw source  │
│ data        │
└──────┬──────┘
       │
       │ Cleaning
       │ Standardization
       │ Deduplication
       │ Validation
       ▼
┌─────────────┐
│   SILVER    │
│             │
│ Conformed   │
│ datasets    │
└──────┬──────┘
       │
       │ Dimensional
       │ modeling
       │ Business logic
       ▼
┌─────────────┐
│    GOLD     │
│             │
│ Facts       │
│ Dimensions  │
│ Marts       │
└──────┬──────┘
       │
       ▼
DuckDB / BI / Analytics
```

## 10. DuckDB Analytical Layer
DuckDB is used as the local analytical query engine.
The architecture intentionally avoids unnecessary duplication of Silver data into DuckDB.
Silver Parquet files remain the primary Silver storage format, while DuckDB provides queryable views over those files.
The Gold dimensional tables are materialized in DuckDB because they represent transformed, business-ready analytical datasets.
Gold tables are also exported as Parquet files under:

```text
data/gold/
├── dimensions/
└── facts/
```

This provides both:
- a queryable analytical database
- portable analytical files for downstream tools

## 11. File Format
Parquet is used throughout the analytical storage layers because it provides:
- columnar storage
- efficient analytical scans
- compression
- predicate and column pruning
- interoperability with DuckDB and other analytical engines
- portability across local and cloud object storage

Gold Parquet files are written using Zstandard (ZSTD) compression.

## 12. Gold Model Validation
The Gold model was validated after construction.
The following checks passed:

| Validation | Result |
| --- | --- |
| fact_orders row count | 99,441 |
| Duplicate fact_orders.order_id | 0 |
| Duplicate fact_order_items grain | 0 |
| Duplicate fact_payments grain | 0 |
| Orders missing customer key | 0 |
| Order items missing product key | 0 |
| Order items missing seller key | 0 |
| Orders missing order date | 0 |

All eight Gold model validation checks passed.

## 13. Gold Model Summary
The completed Gold model contains:

**Dimensions**
- dim_customer — 96,096 rows
- dim_product — 32,951 rows
- dim_seller — 3,095 rows
- dim_geography — 19,015 rows
- dim_date — 800 rows

**Facts**
- fact_orders — 99,441 rows
- fact_order_items — 112,650 rows
- fact_payments — 103,886 rows

The model provides a consistent foundation for sales, customer, product, seller, regional, payment, and operational analytics.