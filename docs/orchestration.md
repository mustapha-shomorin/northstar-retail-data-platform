# NorthStar Retail — Orchestration

## 1. Overview

NorthStar Retail uses Apache Airflow as the orchestration layer for the batch analytics pipeline.

Airflow coordinates the movement of data through the following stages:

```text
Scheduled Trigger
      │
      ▼
Ingest Olist → Bronze
      │
      ▼
Bronze → Silver
      │
      ▼
Silver Validation
      │
      ▼
dbt Build
      │
      ▼
Pipeline Success
```

Failure at any task causes downstream tasks to remain blocked and triggers the configured failure notification.

Streaming ingestion is intentionally operated independently of the batch Airflow DAG:

```text
Synthetic Event Producer
        │
        ▼
     Redpanda
        │
        ▼
Streaming Consumer
        │
        ▼
Streaming Bronze
        │
        ▼
Streaming Silver
```

This separation prevents long-running streaming processes from being treated as finite Airflow batch tasks.

---

## 2. Technology

| Component | Technology |
| --- | --- |
| Orchestrator | Apache Airflow 3.3.2 |
| Executor | LocalExecutor |
| Metadata database | SQLite |
| Batch transformation | dbt Core 1.12.5 |
| Analytical engine | DuckDB |
| Batch storage | Parquet |
| Object-storage architecture | MinIO / S3-compatible |
| Streaming broker | Redpanda |
| Containerization | Docker Compose |
| Monitoring | Prometheus + Grafana |
| Alerting | Airflow SMTP provider + Mailpit for local development |

Airflow runs inside Docker so that the orchestration environment is reproducible.

---

## 3. DAG

The main production DAG is:

```text
northstar_daily_pipeline
```

Its purpose is to execute the complete historical/batch analytics workflow from raw ingestion through transformation and validation.

### DAG dependency graph

```text
ingest_olist_bronze
        │
        ▼
transform_bronze_to_silver
        │
        ▼
validate_silver
        │
        ▼
dbt_build
```

The dependencies are explicitly defined in the DAG:

```text
ingest_olist_bronze >> transform_bronze_to_silver
transform_bronze_to_silver >> validate_silver
validate_silver >> dbt_build
```

This ensures that:

1. Bronze ingestion completes before Silver transformation.
2. Silver transformation completes before validation.
3. Data-quality validation passes before dbt builds the analytical models.

---

## 4. Schedule

The DAG is scheduled to run daily at:

```text
02:00 UTC
```

The Airflow schedule expression is:

```text
0 2 * * *
```

The DAG uses:

```text
start_date=datetime(2026, 9, 28)
catchup=False
max_active_runs=1
```

`max_active_runs=1` prevents multiple instances of the same batch pipeline from running concurrently.

Airflow reports the next scheduled logical execution time according to the configured schedule.

---

## 5. Pipeline Tasks

### 5.1 Ingest Olist Bronze

Task:

```text
ingest_olist_bronze
```

Command:

```text
python scripts/ingest_olist_bronze.py --ingestion-date <logical_date>
```

The logical date is supplied dynamically by Airflow:

```text
{{ logical_date | ds }}
```

The ingestion task:

- reads the Olist source CSV files;
- calculates a deterministic batch identifier;
- adds ingestion metadata;
- writes Parquet files to Bronze;
- uses the ingestion date for partitioning;
- skips already-existing outputs to maintain idempotent reruns.

---

### 5.2 Transform Bronze to Silver

Task:

```text
transform_bronze_to_silver
```

Command:

```text
python scripts/transform_bronze_to_silver.py --batch-date <logical_date>
```

The transformation:

- standardizes data types;
- normalizes string fields;
- removes duplicate keys;
- applies Silver-layer metadata;
- writes cleaned Parquet datasets.

---

### 5.3 Validate Silver

Task:

```text
validate_silver
```

Command:

```text
python scripts/validate_silver.py
```

The validation checks:

- row counts;
- primary-key uniqueness;
- composite-key uniqueness;
- required columns;
- referential integrity.

The completed historical Silver validation produced:

```text
20/20 checks PASS
```

The pipeline is designed so that a critical validation failure prevents the dbt transformation stage from executing.

---

### 5.4 dbt Build

Task:

```text
dbt_build
```

Command:

```text
dbt build \
  --project-dir dbt \
  --profiles-dir infrastructure/airflow/dbt_profiles
```

The dbt build executes:

- staging models;
- Gold dimensions;
- Gold facts;
- analytical marts;
- dbt data-quality tests.

The validated dbt project completed with:

```text
82/82 PASS
```

This includes:

- 9 table models;
- 9 views;
- 64 tests.

---

## 6. Retry and Failure Handling

The DAG is configured with automatic retries:

```text
default_args = {
    "owner": "northstar",
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=15),
}
```

### Retry behavior

A failed task is automatically retried up to three times.

The retry delay uses exponential backoff, with a maximum delay of 15 minutes.

Conceptually:

```text
Initial failure
      │
      ├── Retry 1
      │
      ├── Retry 2
      │
      └── Retry 3
             │
             ▼
       Failure notification
```

This allows transient failures to recover without requiring manual intervention.

---

## 7. Failure Alerting

NorthStar uses Airflow's SMTP notification provider for task failure alerts.

The notifier is:

```text
SmtpNotifier(
    from_email="airflow@northstar.local",
    to="northstar-alerts@northstar.local",
    subject="[NorthStar] Pipeline Failure — {{ dag.dag_id }}",
    ...
)
```

The local development environment uses Mailpit as the SMTP server.

Mailpit configuration:

```text
SMTP host: mailpit
SMTP port: 1025
```

The Airflow SMTP connection is:

```text
smtp_default
```

with:

```text
host: mailpit
port: 1025
disable_ssl: true
disable_tls: true
```

### Alert verification

Failure alerting was explicitly tested using a temporary DAG:

```text
northstar_alert_test
```

The test task intentionally exited with status code `1`.

Airflow generated the failure notification with:

```text
DAG: northstar_alert_test
Task: intentional_failure
Run: manual__2026-10-02T11:28:36.396412+00:00
```

The email was successfully received in Mailpit.

Subject:

```text
[NorthStar] Alert Test — northstar_alert_test
```

This verifies the complete notification path:

```text
Airflow Task Failure
        │
        ▼
SmtpNotifier
        │
        ▼
smtp_default
        │
        ▼
Mailpit SMTP
        │
        ▼
Failure Email
```

The temporary alert-test DAG is not part of the production pipeline.

---

## 8. Successful Scheduled Run

The NorthStar pipeline was successfully executed through its scheduled Airflow run.

Run:

```text
scheduled__2026-10-02T02:00:00+00:00
```

Final state:

```text
success
```

The successful run completed the complete dependency chain:

```text
ingest_olist_bronze
        ↓
transform_bronze_to_silver
        ↓
validate_silver
        ↓
dbt_build
```

The successful run provides evidence that the production DAG can execute automatically from the scheduler through the complete batch pipeline.

---

## 9. Backfill Procedure

Airflow 3.3 provides backfill through:

```text
airflow backfill create
```

The general NorthStar backfill command is:

```text
docker compose -f infrastructure\airflow\docker-compose.yml exec airflow-scheduler airflow backfill create `
  --dag-id northstar_daily_pipeline `
  --from-date YYYY-MM-DD `
  --to-date YYYY-MM-DD
```

For failed historical runs, the reprocessing behavior can be specified:

```text
docker compose -f infrastructure\airflow\docker-compose.yml exec airflow-scheduler airflow backfill create `
  --dag-id northstar_daily_pipeline `
  --from-date YYYY-MM-DD `
  --to-date YYYY-MM-DD `
  --reprocess-behavior failed
```

### Recommended dry run

Before executing a backfill, use:

```text
docker compose -f infrastructure\airflow\docker-compose.yml exec airflow-scheduler airflow backfill create `
  --dag-id northstar_daily_pipeline `
  --from-date YYYY-MM-DD `
  --to-date YYYY-MM-DD `
  --dry-run
```

The dry run allows the operator to inspect the backfill parameters before execution.

### Backfill considerations

Backfills should be used when:

- historical data needs to be reprocessed;
- a failed historical pipeline execution needs recovery;
- transformation logic has changed and historical partitions need rebuilding;
- a historical source extract becomes available.

The operator should first verify:

1. The requested date range is in the past.
2. The source data for the requested period is available.
3. Existing successful runs will not be unnecessarily reprocessed.
4. Sufficient storage is available.
5. Downstream analytical outputs can safely be rebuilt.

---

## 10. Static Dataset Limitation

The current NorthStar project uses the Olist Brazilian E-Commerce Dataset as a historical source snapshot.

The dataset is static rather than a continuously arriving historical source.

Therefore, backfilling multiple logical dates currently reprocesses the same underlying Olist snapshot unless date-specific source extracts are introduced.

For example:

```text
Logical date: 2026-09-30
        │
        └── Olist snapshot

Logical date: 2026-10-01
        │
        └── Olist snapshot

Logical date: 2026-10-02
        │
        └── Olist snapshot
```

In a production implementation, each execution date would normally correspond to the appropriate historical source extract or source partition.

This limitation does not affect the demonstration of Airflow orchestration, dependency management, retries, validation, alerting, or backfill mechanics.

---

## 11. Idempotency and Safe Reruns

The ingestion layer is designed to be idempotent.

The batch ingestion process:

- generates a deterministic batch identifier from the source content;
- writes data to date-partitioned Bronze storage;
- detects existing outputs;
- skips already-ingested datasets.

Therefore, rerunning the same ingestion task does not blindly append another copy of the same historical dataset.

The streaming pipeline separately uses `event_id` for deduplication.

Streaming replay verification produced:

```text
Bronze rows: 54
Unique event IDs: 54
Duplicate event IDs: 0
```

This allows the streaming consumer to safely replay events without creating duplicate business events.

---

## 12. Failure Recovery

When a task fails:

```text
Task failure
    │
    ▼
Automatic retry
    │
    ├── success → continue pipeline
    │
    └── repeated failure
            │
            ▼
       Failure alert
```

Because task dependencies are explicit, downstream tasks do not run when their upstream dependency has failed.

For example:

```text
ingest ❌
   │
   ▼
transform → upstream_failed
   │
   ▼
validate → upstream_failed
   │
   ▼
dbt → upstream_failed
```

This prevents downstream transformations from operating on an incomplete or invalid dataset.

---

## 13. Streaming Operations

The long-running streaming pipeline is intentionally outside the daily Airflow DAG.

The streaming architecture is:

```text
Producer
   │
   ▼
Redpanda
   │
   ▼
Consumer
   │
   ▼
Bronze Streaming
   │
   ▼
Silver Streaming
```

The streaming consumer:

- uses a Kafka consumer group;
- commits offsets after successful processing;
- validates required event fields;
- quarantines invalid events;
- deduplicates by `event_id`;
- supports replay.

Airflow therefore remains responsible for finite batch workflows while Redpanda and the streaming consumer handle continuous event processing.

---

## 14. Operational Commands

### Check DAGs

```text
docker compose -f infrastructure\airflow\docker-compose.yml exec airflow-scheduler airflow dags list
```

### Show DAG structure

```text
docker compose -f infrastructure\airflow\docker-compose.yml exec airflow-scheduler airflow dags show northstar_daily_pipeline
```

### List DAG runs

Airflow 3.3 uses the DAG ID as a positional argument:

```text
docker compose -f infrastructure\airflow\docker-compose.yml exec airflow-scheduler airflow dags list-runs northstar_daily_pipeline
```

### Check next execution

```text
docker compose -f infrastructure\airflow\docker-compose.yml exec airflow-scheduler airflow dags next-execution northstar_daily_pipeline
```

### Render a task

```text
docker compose -f infrastructure\airflow\docker-compose.yml exec airflow-scheduler airflow tasks render northstar_daily_pipeline ingest_olist_bronze 2026-10-01
```

### Trigger a manual run

```text
docker compose -f infrastructure\airflow\docker-compose.yml exec airflow-scheduler airflow dags trigger northstar_daily_pipeline
```

### Run the backfill help command

```text
docker compose -f infrastructure\airflow\docker-compose.yml exec airflow-scheduler airflow backfill --help
```

---

## 15. Airflow Web Interface

The local Airflow web interface is exposed at:

```text
http://localhost:8081
```

The interface can be used to inspect:

- DAG status;
- task dependencies;
- task execution history;
- task logs;
- retry attempts;
- successful and failed runs;
- execution duration.

The successful scheduled run should be captured as project evidence showing the DAG and its completed tasks.

---

## 16. Orchestration Architecture

The completed NorthStar orchestration architecture is:

```text
                         ┌──────────────────────┐
                         │   Airflow Scheduler   │
                         └──────────┬───────────┘
                                    │
                              Daily 02:00 UTC
                                    │
                                    ▼
                     ┌───────────────────────────┐
                     │ ingest_olist_bronze       │
                     └─────────────┬─────────────┘
                                   │
                                   ▼
                     ┌───────────────────────────┐
                     │ transform_bronze_to_silver│
                     └─────────────┬─────────────┘
                                   │
                                   ▼
                     ┌───────────────────────────┐
                     │ validate_silver           │
                     └─────────────┬─────────────┘
                                   │
                              PASS │
                                   ▼
                     ┌───────────────────────────┐
                     │ dbt_build                 │
                     └─────────────┬─────────────┘
                                   │
                                   ▼
                            Pipeline Success

       Any task failure
              │
              ▼
       Retry × 3 with
       exponential backoff
              │
              ▼
       SmtpNotifier
              │
              ▼
        Failure Email
```

---

## 17. Step 5 Completion Criteria

| Requirement | Status |
| --- | --- |
| Airflow orchestration implemented | PASS |
| Full batch dependency chain | PASS |
| Scheduled execution | PASS |
| Successful scheduled run | PASS |
| Retry logic | PASS |
| Exponential backoff | PASS |
| Failure alerting | PASS |
| Alert successfully received | PASS |
| Backfill command verified | PASS |
| Backfill procedure documented | PASS |
| Streaming kept independent | PASS |
| Operational commands documented | PASS |

Step 5 establishes Airflow as the orchestration layer for the NorthStar Retail batch analytics platform.

The resulting pipeline provides scheduled execution, explicit dependencies, automated retries, data-quality gating, failure alerting, idempotent processing, and a documented mechanism for historical backfills.
