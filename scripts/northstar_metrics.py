import re
import time
from pathlib import Path

from prometheus_client import Gauge, start_http_server

PROJECT_ROOT = Path(__file__).resolve().parents[1]

pipeline_success = Gauge(
    "northstar_pipeline_success",
    "Whether the latest NorthStar pipeline validation passed.",
)

pipeline_failure = Gauge(
    "northstar_pipeline_failure",
    "Whether the latest NorthStar pipeline validation failed.",
)

pipeline_duration_seconds = Gauge(
    "northstar_pipeline_duration_seconds",
    "Latest NorthStar pipeline duration in seconds.",
)

records_processed = Gauge(
    "northstar_records_processed",
    "Number of records processed in the latest NorthStar data pipeline.",
)

data_freshness_seconds = Gauge(
    "northstar_data_freshness_seconds",
    "Age of the latest NorthStar Silver data in seconds.",
)

service_health = Gauge(
    "northstar_service_health",
    "Health status of the NorthStar metrics service.",
)


def get_pipeline_status() -> bool:
    """Read the latest data quality report and determine pipeline status."""

    report = (
        PROJECT_ROOT
        / "data_quality"
        / "reports"
        / "data_quality_report.md"
    )

    if not report.exists():
        return False

    text = report.read_text(encoding="utf-8").upper()

    # Accept common PASS formats used by the NorthStar report.
    pass_patterns = [
        r"OVERALL STATUS\s*:\s*PASS",
        r"OVERALL\s+STATUS\s*\|\s*PASS",
        r"STATUS\s*:\s*PASS",
        r"PASS=\d+.*ERROR=0",
    ]

    return any(re.search(pattern, text) for pattern in pass_patterns)


def get_records_processed() -> int:
    """
    Calculate the number of records currently represented
    in the Silver layer.
    """

    silver_dir = PROJECT_ROOT / "data" / "silver"

    if not silver_dir.exists():
        return 0

    total_records = 0

    try:
        import pyarrow.parquet as pq

        for parquet_file in silver_dir.rglob("*.parquet"):
            try:
                total_records += pq.ParquetFile(parquet_file).metadata.num_rows
            except Exception:
                continue

    except ImportError:
        return 0

    return total_records


def get_latest_data_timestamp() -> float:
    """Return the modification time of the newest Silver Parquet file."""

    silver_dir = PROJECT_ROOT / "data" / "silver"

    files = list(silver_dir.rglob("*.parquet"))

    if not files:
        return time.time()

    return max(file.stat().st_mtime for file in files)


def update_metrics() -> None:
    """Refresh all NorthStar Prometheus metrics."""

    pipeline_passed = get_pipeline_status()

    if pipeline_passed:
        pipeline_success.set(1)
        pipeline_failure.set(0)
    else:
        pipeline_success.set(0)
        pipeline_failure.set(1)

    records_processed.set(get_records_processed())

    data_timestamp = get_latest_data_timestamp()

    data_freshness_seconds.set(
        max(0, time.time() - data_timestamp)
    )

    # No reliable pipeline duration source is currently exposed.
    # Keep this at zero rather than publishing a misleading value.
    pipeline_duration_seconds.set(0)

    # Exporter is running successfully.
    service_health.set(1)


if __name__ == "__main__":

    start_http_server(8000)

    print(
        "NorthStar metrics exporter running on "
        "http://0.0.0.0:8000/metrics"
    )

    while True:
        try:
            update_metrics()
        except Exception as exc:
            print(f"Metrics update error: {exc}")

            # Keep service health visible even if one metric update fails.
            service_health.set(0)

        time.sleep(15)