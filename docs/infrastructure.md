# NorthStar Retail — Infrastructure and Deployment

## 1. Overview
NorthStar Retail uses a containerized infrastructure to support data ingestion, analytical storage, orchestration, monitoring, and business intelligence. The infrastructure separates the main platform services into manageable components, making local development, testing, and demonstration easier to reproduce.

Docker Compose is used to run the core infrastructure services. Airflow and Redpanda are defined in separate Compose configurations to keep orchestration and streaming infrastructure independently manageable.

## 2. Infrastructure Architecture
The infrastructure supports the following components:

| Component | Technology | Responsibility |
| :--- | :--- | :--- |
| Object storage | SeaweedFS | S3-compatible storage for ingested data and object-storage demonstrations |
| Streaming platform | Redpanda | Kafka-compatible event streaming for synthetic retail activity |
| Orchestration | Apache Airflow | Scheduling and coordinating the batch data pipeline |
| Analytical database | DuckDB | Local analytical storage and SQL queries over modeled data |
| Transformation | dbt Core with dbt-duckdb | SQL-based transformation, modeling, and data tests |
| Business intelligence | Streamlit | Interactive dashboard for business users |
| Metrics collection | Prometheus | Collecting operational metrics from configured scrape targets |
| Monitoring dashboards | Grafana | Visualizing service health and pipeline-related metrics |
| Metrics exporter | Custom Python service | Exposing NorthStar application metrics to Prometheus |
| Container management | Docker Compose | Defining and managing containerized services |

## 3. Docker Compose Organization
The project uses separate Compose configurations for different infrastructure responsibilities.

### Core infrastructure
The root `docker-compose.yml` defines:
- SeaweedFS object storage
- Prometheus metrics collection
- Grafana monitoring dashboards
- The custom NorthStar metrics service

### Orchestration infrastructure
The Airflow stack is defined in:
`infrastructure/airflow/docker-compose.yml`

It runs the Airflow components required to process and schedule the daily pipeline. The pipeline coordinates ingestion, transformation, validation, and the dbt build.

### Streaming infrastructure
The Redpanda stack is defined in:
`infrastructure/redpanda/docker-compose.yml`

It provides the Kafka-compatible broker used by the event producer and consumer. The streaming consumer validates incoming events, writes valid events to Parquet, and sends invalid events to quarantine.

## 4. Service Access
The following local endpoints are used by the project:

| Service | Local URL or address | Purpose |
| :--- | :--- | :--- |
| Streamlit | `http://localhost:8501` | Executive analytics dashboard |
| Grafana | `http://localhost:3000` | Operational monitoring |
| Prometheus | `http://localhost:9090` | Metrics interface |
| Airflow | `http://localhost:8081` | Pipeline orchestration interface |
| SeaweedFS S3 endpoint | `http://localhost:8333` | S3-compatible object storage |
| Redpanda Kafka endpoint | `localhost:19092` | Streaming producer and consumer access |

These endpoints assume the project's documented local port mappings are unchanged.

## 5. Configuration and Secrets
Runtime configuration is maintained separately from source code where appropriate.

The project uses `.env` for local environment-specific settings and `.env.example` to document the expected configuration variables without exposing actual secret values.

Before publishing the repository:
- Exclude `.env` and other files containing credentials.
- Keep `.env.example` populated only with safe placeholders.
- Avoid committing passwords, access keys, tokens, or private connection strings.
- Document any required environment variables without disclosing their values.

Credentials should be changed through local configuration rather than hard-coded into application source files.

## 6. Deployment and Startup
Run the commands from the project root unless otherwise indicated.

### Start core infrastructure
```bash
docker compose up -d
docker compose ps
```

### Start Airflow
```bash
docker compose -f infrastructure/airflow/docker-compose.yml up -d
docker compose -f infrastructure/airflow/docker-compose.yml ps
```

### Start Redpanda
```bash
docker compose -f infrastructure/redpanda/docker-compose.yml up -d
docker compose -f infrastructure/redpanda/docker-compose.yml ps
```

### Start the Streamlit dashboard
Run the following command in a VS Code terminal with the project's virtual environment available:
```bash
.\.venv\Scripts\python.exe -m streamlit run serving\app.py
```

The dashboard queries the local DuckDB analytical database. The database and modeled tables must already be available for the dashboard to display its business metrics.

## 7. Monitoring and Observability
Prometheus collects metrics from configured targets, including the custom NorthStar metrics service. Grafana uses these metrics to provide visibility into operational health and processing activity.

The monitoring setup supports review of indicators such as:
- Pipeline status and failures
- Records processed
- Data freshness
- Metrics service availability

Monitoring coverage depends on the metrics implemented and exposed by the running services. A metric should not be interpreted as a direct measurement of end-to-end pipeline performance unless the instrumentation explicitly supports that conclusion.

## 8. Reliability and Operational Considerations
The platform incorporates reliability measures across its data-processing components:
- Airflow retries tasks after configured failures.
- Failure notifications are configured for the orchestration workflow.
- Streaming event IDs support duplicate detection and replay protection.
- Invalid streaming events are quarantined for investigation.
- Validation scripts and dbt tests help detect data-quality issues.

These controls improve processing reliability, but they do not by themselves guarantee production-grade availability or disaster recovery.

## 9. Security and Production Considerations
The current setup is designed for local development and demonstration. Before operating the platform for a real business, additional controls would be required, including:
- Managed secrets and access control
- Authentication and authorization for service interfaces
- TLS and secure network configuration
- Persistent, backed-up orchestration metadata
- Automated infrastructure deployment and environment separation
- Alert routing and incident-response procedures
- Recovery testing and documented service-level objectives

## 10. Summary
NorthStar Retail combines containerized infrastructure, orchestration, event streaming, analytical storage, data-quality controls, and monitoring into a cohesive data platform. Its modular structure supports reproducible local execution and provides a foundation for further deployment hardening and scaling as operational requirements grow.