from datetime import datetime, timedelta

from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.smtp.notifications.smtp import SmtpNotifier

PROJECT_DIR = "/opt/airflow/northstar"
DBT_PROFILES_DIR = "infrastructure/airflow/dbt_profiles"


default_args = {
    "owner": "northstar",
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=15),
    "on_failure_callback": SmtpNotifier(
        from_email="airflow@northstar.local",
        to="northstar-alerts@northstar.local",
        subject="[NorthStar] Pipeline Failure — {{ dag.dag_id }}",
        html_content="""
        <h3>NorthStar Retail Pipeline Failure</h3>
        <p><strong>DAG:</strong> {{ dag.dag_id }}</p>
        <p><strong>Task:</strong> {{ ti.task_id }}</p>
        <p><strong>Run:</strong> {{ run_id }}</p>
        <p><strong>Execution date:</strong> {{ logical_date }}</p>
        <p><strong>Log:</strong> <a href="{{ ti.log_url }}">View task log</a></p>
        """,
    ),
}

with DAG(
    dag_id="northstar_daily_pipeline",
    description="NorthStar Retail daily batch ingestion, transformation, and data quality pipeline",
    start_date=datetime(2026, 9, 28),
    schedule="0 2 * * *",
    catchup=False,
    default_args=default_args,
    max_active_runs=1,
    tags=["northstar", "retail", "batch", "dbt"],
    
) as dag:

    ingest_olist_bronze = BashOperator(
        task_id="ingest_olist_bronze",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python scripts/ingest_olist_bronze.py "
            "--ingestion-date {{ logical_date | ds }}"
        ),
    )

    transform_bronze_to_silver = BashOperator(
        task_id="transform_bronze_to_silver",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python scripts/transform_bronze_to_silver.py "
            "--batch-date {{ logical_date | ds }}"
        ),
    )

    validate_silver = BashOperator(
        task_id="validate_silver",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python scripts/validate_silver.py"
        ),
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "dbt build "
            "--project-dir dbt "
            f"--profiles-dir {DBT_PROFILES_DIR}"
        ),
    )

    ingest_olist_bronze >> transform_bronze_to_silver
    transform_bronze_to_silver >> validate_silver
    validate_silver >> dbt_build