# NorthStar Retail - Environment Strategy

## 1. Overview

NorthStar Retail uses dbt as the transformation layer and DuckDB as the local analytical engine.

The project defines separate dbt targets for development and production:

- `dev`
- `prod`

The current implementation is intentionally lightweight because NorthStar is being developed and executed locally.

The environment strategy is designed so that the same dbt transformation code can later be promoted from development to production without changing the business transformation logic.

---

## 2. Current Local Environment

The current local architecture uses:

```text
Windows
  |
  +-- Python virtual environment
  |
  +-- dbt Core
  |
  +-- DuckDB
  |
  +-- data/
       |
       +-- bronze/
       +-- silver/
       +-- gold/
       +-- northstar.duckdb
```

The current DuckDB database is:

`data/northstar.duckdb`

The dbt project is located at:

`dbt/`

---

## 3. dbt Targets

The project currently defines two targets in the dbt profile:

```yaml
northstar:
  outputs:
    dev:
      type: duckdb
      path: C:\Users\USER\Desktop\Personal\northstar\data\northstar.duckdb
      threads: 4

    prod:
      type: duckdb
      path: C:\Users\USER\Desktop\Personal\northstar\data\northstar.duckdb
      threads: 4

  target: dev
```

The default target is:

`dev`

Therefore, running:

```bash
dbt run --project-dir dbt
```

uses the development target.

A production-target execution can be explicitly requested with:

```bash
dbt run --project-dir dbt --target prod
```

---

## 4. Why Dev and Prod Targets Exist

Even though the current local implementation points both targets to the same DuckDB database, maintaining separate targets establishes an environment boundary in the dbt configuration.

The intended workflow is:

```text
Development
     |
     | Validate transformations
     | Run data quality tests
     | Review changes
     v
Staging / CI
     |
     | Automated validation
     | dbt build
     v
Production
     |
     v
Production analytical data
```

This allows transformation logic to remain consistent while the execution environment changes.

---

## 5. Current Local Strategy

For the portfolio implementation, both environments currently use the same DuckDB database.

```text
dev  Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â
              Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬> data/northstar.duckdb
prod Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ
```

This is a deliberate simplification for local development. It avoids introducing unnecessary infrastructure before the required project functionality is complete.

The limitation is that development and production data are not physically isolated in the current local setup. Therefore, the current configuration should be considered a local development representation of environment separation, rather than a fully isolated production deployment.

---

## 6. Intended Production Strategy

In a production deployment, the environments should use separate storage and analytical resources.

A possible architecture is:

```text
Development
    |
    +--> Development object storage
    |
    +--> Development analytical database
    |
    +--> Development dbt target

Staging / CI
    |
    +--> Temporary validation environment
    |
    +--> Automated dbt tests

Production
    |
    +--> Production object storage
    |
    +--> Production analytical database
    |
    +--> Production dbt target
```

For example:

- `dev.northstar.duckdb`
- `staging.northstar.duckdb`
- `prod.northstar.duckdb`

or, in a cloud deployment:

```text
S3 / object storage
        |
        +-- dev/
        +-- staging/
        +-- prod/

Analytical warehouse
        |
        +-- development schema
        +-- staging schema
        +-- production schema
```

The exact production technology can change without requiring the business transformation models to be rewritten.

---

## 7. Environment-Specific Configuration

Environment-specific values should be controlled through dbt targets and variables rather than hard-coded throughout transformation models.

Examples include:

- database paths
- schemas
- object storage locations
- warehouse connections
- thread/concurrency settings
- environment-specific source locations

The transformation models should continue to use dbt abstractions such as:

```jinja
{{ ref('model_name') }}
```

and configuration variables where appropriate. This keeps business logic independent of deployment infrastructure.

---

## 8. Development Workflow

The intended development workflow is:

1. **Step 1 - Make a transformation change**  
   Modify a dbt model under: `dbt/models/`

2. **Step 2 - Parse the project**  
   ```bash
   dbt parse --project-dir dbt
   ```

3. **Step 3 - Run the affected model**  
   For example:  
   ```bash
   dbt run --project-dir dbt --select mart_sales_daily
   ```

4. **Step 4 - Run data quality tests**  
   ```bash
   dbt test --project-dir dbt
   ```

5. **Step 5 - Run the complete transformation build**  
   ```bash
   dbt build --project-dir dbt
   ```

6. **Step 6 - Commit validated changes**  
   Only tested transformation logic should be committed to version control.

---

## 9. CI/CD Strategy

GitHub Actions can later automate the validation process. A simplified CI workflow is:

```text
Git Push / Pull Request
        |
        v
Install Python dependencies
        |
        v
Install dbt
        |
        v
dbt parse
        |
        v
dbt build
        |
        v
Data quality tests
        |
        v
Pass / Fail
```

A failed transformation or data quality test should prevent the change from being promoted. This provides an automated quality gate for transformation logic.

---

## 10. Production Deployment Workflow

A production deployment can follow:

```text
Developer
    |
    v
Git Branch
    |
    v
Pull Request
    |
    v
CI Validation
    |
    +--> dbt parse
    +--> dbt build
    +--> data quality tests
    |
    v
Merge
    |
    v
Production Deployment
    |
    v
dbt build --target prod
```

Production execution should use production-specific credentials and storage locations rather than developer-local paths. Credentials should not be committed to Git.

---

## 11. Environment Separation Principles

The production implementation should follow these principles:

### Development
- **Purpose:**
  - build models
  - experiment with transformations
  - debug SQL
  - validate assumptions
- **Characteristics:**
  - developer-controlled
  - lower cost
  - isolated from production data where possible

### Staging / CI
- **Purpose:**
  - validate changes before production
  - execute automated tests
  - identify breaking schema or transformation changes
- **Characteristics:**
  - reproducible
  - automated
  - temporary or controlled

### Production
- **Purpose:**
  - provide trusted analytical data
  - support dashboards and downstream consumers
- **Characteristics:**
  - controlled access
  - monitored
  - backed up
  - isolated from development
  - scheduled and orchestrated

---

## 12. Environment Promotion

Transformation code should progress through environments rather than being independently rewritten.

```text
Development
     |
     v
CI / Staging
     |
     v
Production
```

The same dbt model logic should be tested before promotion. Environment-specific configuration should determine where the model executes. This reduces the risk of differences between development and production transformation logic.

---

## 13. Relationship with Airflow

Airflow is responsible for orchestration, while dbt is responsible for transformations.

The intended production workflow is:

```text
Airflow
   |
   +--> Ingestion
   |
   +--> Bronze
   |
   +--> Silver
   |
   +--> dbt build --target prod
   |
   +--> Data quality checks
   |
   +--> BI refresh
```

Airflow should not contain the business transformation SQL that belongs in dbt. Instead, Airflow schedules and coordinates the dbt execution.

---

## 14. Relationship with Docker

Docker provides reproducibility for the infrastructure components of NorthStar.

The intended environment includes:

```text
Docker
  |
  +-- Airflow
  +-- Redpanda
  +-- MinIO
  +-- PostgreSQL
  +-- Metabase
  +-- Monitoring
```

dbt can run within a controlled Python environment or a dedicated dbt container in a production deployment. The objective is to ensure that transformation and infrastructure dependencies are reproducible across environments.

---

## 15. Security Considerations

Production credentials should never be stored directly in `dbt_project.yml` or committed to Git.

Instead, production deployments should use:

- environment variables
- secret managers
- CI/CD secrets
- cloud IAM roles where available

The current local DuckDB implementation does not require external production credentials.

---

## 16. Current vs Intended Architecture

| Area | Current Project | Intended Production |
| :--- | :--- | :--- |
| **dbt** | dbt Core | dbt Core or managed dbt |
| **Analytical engine** | DuckDB | DuckDB, warehouse, or cloud analytical engine |
| **Dev target** | Local DuckDB | Isolated development database |
| **Prod target** | Same local DuckDB | Isolated production database |
| **Object storage** | Local filesystem / MinIO | S3-compatible object storage |
| **CI/CD** | GitHub Actions planned | Automated deployment pipeline |
| **Secrets** | Local environment | Secret manager / CI secrets |
| **Orchestration** | Airflow | Airflow |
| **Transformation** | dbt | dbt |
| **Version control** | Git | Git + CI/CD |

---

## 17. Environment Strategy Summary

NorthStar currently uses separate `dev` and `prod` dbt targets while keeping both targets on the same local DuckDB database.

This is appropriate for the current portfolio development stage because it demonstrates the environment abstraction without introducing unnecessary infrastructure.

For production deployment, the targets should be changed to physically isolated resources.

The core principle is:

$$\text{Same transformation logic} + \text{Environment-specific configuration} = \text{Controlled promotion from development to production}$$

This approach allows NorthStar to evolve from a reproducible local portfolio project into a production-oriented data platform without restructuring the transformation layer.