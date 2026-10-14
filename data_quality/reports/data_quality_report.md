# NorthStar Retail — Data Quality Report

## 1. Report Summary

| Field | Value |
|---|---|
| Generated | 2026-10-03 06:23:31 W. Central Africa Standard Time |
| Overall status | **PASS** |
| Silver validation | **PASS** |
| dbt data tests | **PASS** |
| Transformation unit test | **PASS** |

---

## 2. Validation Results

### Silver Data Validation

The existing Silver validation script checks:

- Primary and composite key null and uniqueness constraints
- Referential integrity between related datasets
- Required columns

**Result:** SILVER VALIDATION: 20/20 CHECKS PASSED

Command:

```text
python scripts/validate_silver.py

dbt Data Tests

dbt validates:

Critical-field null checks
Primary-key uniqueness
Fact-to-dimension referential integrity
Fact grain uniqueness
Business logic: order revenue must never be negative

Result: 05:23:26  Done. PASS=65 WARN=0 ERROR=0 SKIP=0 NO-OP=0 REUSED=0 TOTAL=65

Command:

dbt test --project-dir dbt
Transformation Unit Test

A pytest unit test validates the custom
normalize_order_status() transformation logic.

Result: PASS

Command:

pytest tests/unit/test_transformations.py -v
3. Failure Behavior
Batch Pipeline

Critical data-quality failures cause the relevant
validation task to fail. Downstream pipeline tasks
do not continue when a required dependency fails.

Airflow automatically retries failed tasks up to
3 times using exponential backoff.

If the task continues to fail after the configured
retries, an SMTP failure notification is triggered.

Raw Bronze data is preserved so that the failed
transformation or validation can be investigated
and rerun without requiring the source data to be
reacquired.

Invalid Streaming Records

Streaming events that fail schema validation are
written to the Bronze quarantine area rather than
being silently discarded.

Valid events continue to be processed.

Streaming replay is protected through event_id
deduplication so that replaying an event does not
create duplicate Silver records.

Recovery

A failed historical batch can be rerun for the
relevant processing date.

Airflow backfills can also be used when a historical
date range needs to be reprocessed.

4. Quality Policy

NorthStar Retail follows these principles:

Critical failures stop downstream processing.
Invalid streaming records are quarantined.
Source and Bronze data are preserved for recovery.
Pipeline retries are automatic.
Persistent failures generate alerts.
Transformations are covered by both data-level and unit-level tests.
All quality checks are repeatable and version-controlled.
5. Overall Assessment

The Step 6 automated data-quality checks completed
with an overall status of PASS.

The validation framework covers Silver structural
and integrity checks, Gold/dbt data tests,
business-rule validation, and a unit test for
custom transformation logic.
