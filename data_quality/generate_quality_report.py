from pathlib import Path
import subprocess
from datetime import datetime


# ============================================================
# Configuration
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

REPORT_DIR = (
    PROJECT_ROOT
    / "data_quality"
    / "reports"
)

REPORT_FILE = (
    REPORT_DIR
    / "data_quality_report.md"
)


# ============================================================
# Command execution
# ============================================================

def run_command(command, label):
    """Run a validation command and capture its output."""

    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    return {
        "label": label,
        "command": " ".join(command),
        "returncode": result.returncode,
        "output": result.stdout + result.stderr,
        "passed": result.returncode == 0,
    }


# ============================================================
# Result extraction
# ============================================================

def extract_silver_summary(output):
    """Extract the final Silver validation summary."""

    for line in output.splitlines():

        if "SILVER VALIDATION:" in line:
            return line.strip()

    return "Silver validation summary not found."


def extract_dbt_summary(output):
    """Extract the final dbt test summary."""

    for line in output.splitlines():

        if "PASS=" in line and "TOTAL=" in line:
            return line.strip()

    return "dbt test summary not found."


# ============================================================
# Report generation
# ============================================================

def generate_report(results):
    """Generate the Markdown data-quality report."""

    generated_at = (
        datetime.now()
        .astimezone()
        .strftime("%Y-%m-%d %H:%M:%S %Z")
    )

    silver = results[0]
    dbt = results[1]
    unit = results[2]

    overall_pass = all(
        result["passed"]
        for result in results
    )

    status = "PASS" if overall_pass else "FAIL"

    silver_status = (
        "PASS"
        if silver["passed"]
        else "FAIL"
    )

    dbt_status = (
        "PASS"
        if dbt["passed"]
        else "FAIL"
    )

    unit_status = (
        "PASS"
        if unit["passed"]
        else "FAIL"
    )

    silver_summary = extract_silver_summary(
        silver["output"]
    )

    dbt_summary = extract_dbt_summary(
        dbt["output"]
    )

    report = f"""# NorthStar Retail — Data Quality Report

## 1. Report Summary

| Field | Value |
|---|---|
| Generated | {generated_at} |
| Overall status | **{status}** |
| Silver validation | **{silver_status}** |
| dbt data tests | **{dbt_status}** |
| Transformation unit test | **{unit_status}** |

---

## 2. Validation Results

### Silver Data Validation

The existing Silver validation script checks:

- Primary and composite key null and uniqueness constraints
- Referential integrity between related datasets
- Required columns

**Result:** {silver_summary}

Command:

```text
{silver["command"]}

dbt Data Tests

dbt validates:

Critical-field null checks
Primary-key uniqueness
Fact-to-dimension referential integrity
Fact grain uniqueness
Business logic: order revenue must never be negative

Result: {dbt_summary}

Command:

{dbt["command"]}
Transformation Unit Test

A pytest unit test validates the custom
normalize_order_status() transformation logic.

Result: {unit_status}

Command:

{unit["command"]}
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
with an overall status of {status}.

The validation framework covers Silver structural
and integrity checks, Gold/dbt data tests,
business-rule validation, and a unit test for
custom transformation logic.
"""

    # --------------------------------------------------------
    # Save report
    # --------------------------------------------------------

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_FILE.write_text(
        report,
        encoding="utf-8",
    )

    return REPORT_FILE

#============================================================
# Main
#============================================================

def main():
    print("=" * 70)
    print("NORTHSTAR — DATA QUALITY REPORT GENERATION")
    print("=" * 70)

    commands = [
        (
            [
                "python",
                "scripts/validate_silver.py",
            ],
            "Silver data validation",
        ),
        (
            [
                "dbt",
                "test",
                "--project-dir",
                "dbt",
            ],
            "dbt data tests",
        ),
        (
            [
                "pytest",
                "tests/unit/test_transformations.py",
                "-v",
            ],
            "Transformation unit test",
        ),
    ]

    results = []

    # --------------------------------------------------------
    # Run all validation checks
    # --------------------------------------------------------

    for command, label in commands:

        print(f"\nRunning: {label}")

        result = run_command(
            command,
            label,
        )

        results.append(result)

        print(result["output"])

        print(
            f"{label}: "
            f"{'PASS' if result['passed'] else 'FAIL'}"
        )

    # --------------------------------------------------------
    # Generate report
    # --------------------------------------------------------

    report_file = generate_report(results)

    overall_status = (
        "PASS"
        if all(
            result["passed"]
            for result in results
        )
        else "FAIL"
    )

    print("\n" + "=" * 70)
    print(
        f"REPORT GENERATED: {report_file}"
    )
    print(
        f"OVERALL STATUS: {overall_status}"
    )
    print("=" * 70)



if __name__ == "__main__":
    main()