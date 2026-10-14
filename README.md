# NorthStar Retail — End-to-End Data Engineering Platform

**An end-to-end retail data platform for batch ingestion, streaming data processing, analytical modeling, data quality, orchestration, and business intelligence.**

NorthStar Retail is a data engineering capstone project designed around the needs of a fictional multi-region retail business. It transforms historical e-commerce data and synthetic streaming events into structured, quality-checked datasets and business-facing analytics.

The platform combines data lake storage, analytical modeling, workflow orchestration, monitoring, and an interactive dashboard to demonstrate how data engineering systems can support operational visibility and informed business decisions.

## Project Highlights

- **Batch data processing:** Ingest and transform historical e-commerce datasets.
- **Streaming architecture:** Use Redpanda and synthetic events to demonstrate event-driven data ingestion.
- **Lakehouse-style storage:** Organize data into Bronze, Silver, and Gold layers using Parquet-based storage patterns.
- **Analytical modeling:** Use dbt and SQL to structure data for downstream analysis.
- **Analytical database:** Use DuckDB to query and analyze transformed data.
- **Workflow orchestration:** Use Apache Airflow to define and coordinate data pipeline tasks.
- **Data quality:** Apply Python validation scripts and dbt tests to check data reliability.
- **Monitoring and observability:** Integrate Prometheus and Grafana for infrastructure and pipeline visibility.
- **Business intelligence:** Provide an interactive Streamlit dashboard for exploring retail performance.

## Architecture

![NorthStar Retail Architecture](architecture/NorthStar%20Retail%20Architecture.png)

The architecture separates ingestion, storage, transformation, orchestration, monitoring, and serving into distinct components.

### Data flow

1. **Source:** Historical Olist e-commerce datasets provide the foundation for retail analytics. Synthetic events support the streaming workflow.
2. **Ingestion:** Python scripts and streaming components move data into the platform.
3. **Storage:** Data is organized into Bronze, Silver, and Gold layers, with Parquet used for analytical storage.
4. **Transformation:** dbt models and SQL transformations prepare data for analytical use.
5. **Analytics:** DuckDB supports analytical queries and downstream reporting.
6. **Orchestration:** Airflow coordinates scheduled pipeline activities.
7. **Quality assurance:** Python checks and dbt tests help identify data issues.
8. **Serving and monitoring:** Streamlit presents business-facing insights, while Prometheus and Grafana support monitoring.

The platform is developed locally using a combination of Python, SQL, Docker Compose, and supporting data infrastructure services.

## Platform Screenshots

### Business Intelligence Dashboard

The Streamlit dashboard presents NorthStar Retail's analytical outputs through an interactive business-facing interface.

![NorthStar Retail Dashboard](docs/demo/dashboard.png)

### Workflow Orchestration — Apache Airflow

The Airflow interface provides visibility into the orchestration of the platform's data pipeline workflows.

![Airflow Pipeline Orchestration](docs/screenshots/airflow_orchestration.png)

### Monitoring and Observability — Grafana

Grafana provides a monitoring interface for inspecting metrics and observing the status of the local data platform.

![NorthStar Retail Grafana Monitoring](docs/screenshots/grafana.png)

## Dashboard Demonstration

Watch the short screen recording to see the NorthStar Retail dashboard in action.

[▶ View the 24-second dashboard demonstration](docs/demo/dashboard.mp4)


## Technology Stack

| Area | Technologies |
|---|---|
| Programming | Python, SQL |
| Batch processing | Python, Parquet |
| Streaming | Redpanda |
| Object storage | SeaweedFS with an S3-compatible interface |
| Analytical database | DuckDB |
| Transformation | dbt |
| Orchestration | Apache Airflow |
| Data quality | Python validation scripts, dbt tests |
| Dashboard | Streamlit |
| Monitoring | Prometheus, Grafana |
| Infrastructure | Docker Compose |

## Repository Structure

```text
northstar/
├── architecture/             # Platform architecture diagram
├── dags/                     # Airflow DAG definitions
├── data_quality/             # Quality checks and generated reports
│   └── reports/
├── dbt/                      # dbt models, tests, and configuration
├── docs/                     # Technical documentation
│   └── demo/                 # Selected demonstration assets
├── infrastructure/           # Supporting infrastructure configuration
├── scripts/                  # Ingestion, profiling, and utility scripts
├── serving/                  # Streamlit dashboard
├── streaming/                # Streaming components
├── tests/                    # Project tests
├── .env.example              # Environment configuration template
├── .gitignore
├── docker-compose.yml        # Core local infrastructure
└── README.md
```

*The structure above summarizes the main project components; individual files and supporting configuration may vary.*

## Documentation

The `docs/` directory contains supporting technical documentation, including:

- **Data lineage:** How data moves from source systems through the transformation layers to analytical outputs.
- **Data model:** The structure and relationships of analytical data.
- **Data quality:** Validation approach and quality controls.
- **Environment strategy:** Development environment and configuration approach.
- **Infrastructure:** Supporting services and local infrastructure.
- **Ingestion:** Source data ingestion and processing approach.
- **Orchestration:** Workflow scheduling and execution.
- **Stakeholder summary:** Business context and expected analytical value.
- **Storage design:** Data layer organization and storage decisions.

The project also includes an architecture diagram and a generated data quality report.

## Getting Started

### Prerequisites

Install or prepare the following:

- Python 3.12
- Git
- Docker Desktop with Docker Compose
- The project dependencies listed in the repository's dependency files
- Access to the source datasets required for ingestion

Some components, such as Airflow and Redpanda, use separate Compose configurations.

### 1. Clone the repository

```bash
git clone https://github.com/mustapha-shomorin/northstar-retail-data-platform.git
cd northstar-retail-data-platform
```


### 2. Create a Python virtual environment

On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies using the dependency file provided by the project. For example, if the repository contains `requirements.txt`:

```powershell
python -m pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Update `.env` with the local credentials and settings required by the services you intend to run. Use local values rather than committing credentials to Git.

### 4. Start the core infrastructure

From the repository root:

```powershell
docker compose up -d
```

Check the status of the services:

```powershell
docker compose ps
```

Airflow and Redpanda have separate Compose configurations. Consult the relevant project configuration and documentation before starting those components.

### 5. Launch the dashboard

With the Python environment configured and the required local data and database available, run:

```powershell
python -m streamlit run serving/app.py
```

Open the local URL printed by Streamlit, typically:

`http://localhost:8501`

The dashboard provides an interactive interface for exploring the project's available analytical outputs.

## Local Service Endpoints

When the corresponding services are running and configured, the following local endpoints are used:

| Service | Local endpoint |
|---|---|
| Streamlit dashboard | `http://localhost:8501` |
| Grafana | `http://localhost:3000` |
| Prometheus | `http://localhost:9090` |
| Airflow | `http://localhost:8081` |
| SeaweedFS S3-compatible endpoint | `http://localhost:8333` |
| Redpanda broker | `localhost:19092` |

These endpoints describe the local development configuration, not publicly hosted services.

## Data Quality and Reliability

Reliable analytics depend on more than successful data ingestion. NorthStar Retail incorporates data quality checks to help detect issues before they affect downstream analysis.

The project includes:

- Python-based data validation.
- dbt tests for modeled data.
- A generated data quality report.
- Separation of data into processing layers.
- Documentation describing lineage and quality controls.

The generated report is available at:

`data_quality/reports/data_quality_report.md`

These controls demonstrate a practical approach to data validation and traceability in an analytical pipeline.

## Engineering Considerations

The project demonstrates several important data engineering principles:

- **Separation of concerns:** Ingestion, transformation, storage, orchestration, and serving have distinct responsibilities.
- **Layered data architecture:** Data progresses through defined processing stages.
- **Reproducible development:** Local services and environment configuration are documented.
- **Data validation:** Quality checks and transformation tests help improve confidence in analytical outputs.
- **Operational visibility:** Monitoring tools provide a foundation for inspecting service health and pipeline behavior.
- **Business orientation:** Technical outputs are exposed through an interactive dashboard rather than remaining isolated in scripts.

NorthStar Retail is a portfolio and learning project. Its architecture demonstrates production-relevant patterns, but deployment hardening, security controls, scaling, and operational service-level guarantees would require additional work before production use.

## Future Improvements

Potential next steps include:

- Add automated CI checks for code quality and tests.
- Expand data quality monitoring and alerting.
- Improve pipeline recovery, retries, and idempotency.
- Add automated documentation and lineage generation.
- Extend analytical models and retail forecasting.
- Deploy the platform to a managed cloud environment.

## Author

**Mustapha O. Shomorin**  
Data Engineering | Data Science | Quantitative Analytics

This project demonstrates my practical approach to building data platforms that connect ingestion, transformation, quality assurance, orchestration, and business intelligence.

---

*NorthStar Retail is a fictional retail platform developed as a data engineering capstone project using public e-commerce data and synthetic streaming events.*
