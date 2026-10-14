# NorthStar Retail — Data Quality & Testing

## 1. Overview

NorthStar Retail uses automated data-quality and testing controls across the
Silver, Gold, and transformation layers.

The Step 6 quality framework covers:

- Critical-field null checks
- Primary-key uniqueness
- Referential integrity between fact and dimension tables
- Fact-grain uniqueness
- Business-rule validation
- Unit testing of custom transformation logic
- Silver-layer structural validation
- Failure handling and recovery
- Streaming-record quarantine
- Automated pipeline alerts

The objective is to prevent invalid data from reaching downstream analytical
models while preserving sufficient raw data for investigation and recovery.

## 2. Data Quality Architecture

```text
Bronze
  │
  ▼
Bronze → Silver Transformation
  │
  ▼
Silver Validation
  │
  ├── Key validation
  ├── Referential integrity
  └── Required-column validation
  │
  ▼
dbt Build
  │
  ▼
dbt Data Tests
  │
  ├── Null checks
  ├── Uniqueness checks
  ├── Relationship checks
  ├── Grain checks
  └── Business-rule checks
  │
  ▼
Gold / Marts
```

Custom transformation logic is additionally covered by Python unit tests.

## 3. Silver Data Validation

The script `scripts/validate_silver.py` validates the historical Silver
datasets.

### Key validation

The following datasets are checked for null and duplicate keys:

- customers
- orders
- order_items
- order_payments
- order_reviews
- products
- sellers
- geolocation

Current result:

```text
20/20 CHECKS PASSED
STATUS: PASS
```

### Referential integrity

| Child dataset | Parent dataset | Result |
|---|---|---|
| orders | customers | PASS |
| order_items | orders | PASS |
| order_items | products | PASS |
| order_items | sellers | PASS |
| order_payments | orders | PASS |
| order_reviews | orders | PASS |

All currently contain zero orphan records.

### Required columns

Required-column checks confirm that expected structural fields exist in the
principal Silver datasets.

Current result: **PASS**.

## 4. dbt Data Tests

dbt provides the primary automated data-testing framework for the analytical
models.

The current project contains **65 data tests** covering:

- Critical-field null checks
- Primary-key and business-key uniqueness
- Fact-to-dimension referential integrity
- Fact-grain uniqueness
- Business-rule validation

### Critical-field null checks

Critical fields are tested using `not_null`, including customer, seller,
product, order, payment, event, dimensional-key, fact-key, and important
mart fields.

### Uniqueness checks

Uniqueness is enforced for primary and business keys including:

- `dim_customer.customer_key`
- `dim_customer.customer_unique_id`
- `dim_product.product_key`
- `dim_product.product_id`
- `dim_seller.seller_key`
- `dim_seller.seller_id`
- `dim_geography.geography_key`
- `dim_geography.geolocation_zip_code_prefix`
- `dim_date.date_key`
- `dim_date.full_date`
- `fact_orders.order_id`
- staging primary keys

### Referential integrity

Relationship tests include:

```text
fact_orders.customer_key → dim_customer.customer_key
fact_order_items.order_id → fact_orders.order_id
fact_order_items.product_key → dim_product.product_key
fact_order_items.seller_key → dim_seller.seller_key
fact_payments.order_id → fact_orders.order_id
```

### Fact grain

Custom singular tests verify:

```text
fact_order_items:
    order_id + order_item_id

fact_payments:
    order_id + payment_sequential
```

## 5. Business-Logic Validation

The test `assert_order_revenue_non_negative.sql` calculates total order
revenue from `fact_order_items` and returns orders whose calculated revenue
is negative.

Expected violating-record count: zero.

Current result:

```text
PASS
```

## 6. Transformation Unit Testing

Custom transformation logic is tested independently from database-level
tests.

The tested function is:

```text
normalize_order_status()
```

in `scripts/transform_bronze_to_silver.py`.

The unit test is:

```text
tests/unit/test_transformations.py
```

It verifies trimming, lowercase normalization, string handling, and
preservation of missing values.

Current result:

```text
1 passed
```

## 7. Streaming Data Quality

Streaming events are validated before being written to the Silver event
dataset.

Required fields include:

```text
event_id
event_type
event_timestamp
```

Expected event types are also validated.

Invalid events are written to:

```text
data/bronze/streaming/quarantine/
```

rather than silently discarded.

The schema-drift test demonstrated quarantine behavior for:

- a missing `event_type` field
- a renamed `event_type` field (`type`)

Both invalid events were quarantined.

## 8. Replay and Idempotency

Streaming records use `event_id` as the deduplication key.

Replay verification produced:

```text
Bronze rows:        54
Unique event IDs:   54
Duplicate IDs:       0
```

This confirms that replaying the tested events does not create duplicate
Bronze records.

## 9. Failure Behavior

NorthStar follows a fail-fast approach for critical data-quality failures.

### Critical batch quality failure

If a critical validation task fails:

1. The validation task is marked failed.
2. Downstream dependent tasks do not execute.
3. Airflow retries the failed task up to 3 times.
4. Retry delays use exponential backoff.
5. The maximum configured retry delay is 15 minutes.
6. Persistent failure triggers an SMTP notification.
7. Bronze/source data remains available for investigation and recovery.

### Invalid streaming records

Records that fail schema validation are quarantined while valid records
continue through the streaming pipeline.

### Recovery

Recovery options include:

- rerunning the failed transformation
- rerunning validation after correcting the issue
- replaying valid streaming events
- using Airflow backfill for historical processing windows

Bronze data is preserved so recovery does not require reacquiring the source.

## 10. Automated Alerting

Airflow uses SMTP-based failure notifications.

The local development environment uses Mailpit to capture and inspect
notification emails.

The alerting workflow was verified with an intentional Airflow task failure.
The resulting notification contained the DAG ID, task ID, run ID, execution
date, and task-log reference.

## 11. Data Quality Report

The automated report is generated by:

```text
data_quality/generate_quality_report.py
```

It executes:

```text
1. Silver validation
2. dbt data tests
3. Python transformation unit tests
```

The report is written to:

```text
data_quality/reports/data_quality_report.md
```

Latest result:

```text
Silver validation:          PASS
dbt data tests:             PASS
Transformation unit test:   PASS
Overall status:             PASS
```

Latest totals:

```text
Silver checks:              20/20 PASS
dbt tests:                  65/65 PASS
Unit tests:                  1/1 PASS
```

## 12. Quality Gates

| Quality gate | Expected behavior |
|---|---|
| Critical-field null check | Must pass |
| Primary-key uniqueness | Must pass |
| Referential integrity | Must pass |
| Fact-grain uniqueness | Must pass |
| Business-rule validation | Must pass |
| Silver validation | Must pass |
| Transformation unit test | Must pass |
| Invalid streaming schema | Quarantine |
| Persistent Airflow failure | Alert |

Critical failures prevent downstream processing.

## 13. Reproducibility

Primary local commands are:

```powershell
python scripts\\validate_silver.py

dbt test --project-dir dbt

pytest tests\\unit\\test_transformations.py -v

python data_quality\\generate_quality_report.py
```

The Airflow environment also executes the relevant validation stages as part
of the scheduled pipeline.

## 14. Current Quality Status

```text
SILVER VALIDATION: 20/20 CHECKS PASSED
DBT DATA TESTS:     65/65 PASS
UNIT TESTS:          1/1 PASS
OVERALL STATUS:      PASS
```

The NorthStar Retail pipeline therefore has automated structural,
referential, business-rule, transformation, and operational quality
controls covering the required Step 6 scope.
