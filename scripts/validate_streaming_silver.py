from pathlib import Path
import pandas as pd


# ============================================================
# Configuration
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SILVER_FILE = (
    PROJECT_ROOT
    / "data"
    / "silver"
    / "order_events"
    / "data.parquet"
)


REQUIRED_COLUMNS = [
    "event_id",
    "event_type",
    "event_timestamp",
]


EXPECTED_EVENT_TYPES = {
    "order_placed",
    "payment_received",
    "order_shipped",
    "order_delivered",
    "product_viewed",
    "cart_added",
    "cart_abandoned",
}


# ============================================================
# Validation
# ============================================================

def main():

    print("=" * 70)
    print("NORTHSTAR — STREAMING SILVER VALIDATION")
    print("=" * 70)

    if not SILVER_FILE.exists():
        raise FileNotFoundError(
            f"Silver event file not found: {SILVER_FILE}"
        )

    df = pd.read_parquet(SILVER_FILE)

    print(
        f"\nTotal rows: {len(df):,}"
    )

    # --------------------------------------------------------
    # Required columns
    # --------------------------------------------------------

    print("\n" + "-" * 70)
    print("REQUIRED COLUMNS")
    print("-" * 70)

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        print(
            f"FAIL — Missing columns: {missing_columns}"
        )
        raise SystemExit(1)

    print("PASS — All required columns present")

    # --------------------------------------------------------
    # Event ID uniqueness
    # --------------------------------------------------------

    print("\n" + "-" * 70)
    print("EVENT ID UNIQUENESS")
    print("-" * 70)

    null_event_ids = df["event_id"].isna().sum()

    duplicate_event_ids = df.duplicated(
        subset=["event_id"]
    ).sum()

    print(
        f"Null event IDs: {null_event_ids}"
    )

    print(
        f"Duplicate event IDs: {duplicate_event_ids}"
    )

    event_id_pass = (
        null_event_ids == 0
        and duplicate_event_ids == 0
    )

    print(
        "PASS"
        if event_id_pass
        else "FAIL"
    )

    # --------------------------------------------------------
    # Event types
    # --------------------------------------------------------

    print("\n" + "-" * 70)
    print("EVENT TYPES")
    print("-" * 70)

    actual_event_types = set(
        df["event_type"]
        .dropna()
        .unique()
    )

    unexpected = (
        actual_event_types
        - EXPECTED_EVENT_TYPES
    )

    missing = (
        EXPECTED_EVENT_TYPES
        - actual_event_types
    )

    print(
        "Unexpected event types:",
        sorted(unexpected)
    )

    print(
        "Missing event types:",
        sorted(missing)
    )

    event_type_pass = len(unexpected) == 0

    print(
        "PASS"
        if event_type_pass
        else "FAIL"
    )

    # --------------------------------------------------------
    # Timestamp validation
    # --------------------------------------------------------

    print("\n" + "-" * 70)
    print("TIMESTAMP VALIDATION")
    print("-" * 70)

    event_timestamp = pd.to_datetime(
        df["event_timestamp"],
        errors="coerce",
        utc=True
    )

    invalid_timestamps = event_timestamp.isna().sum()

    print(
        f"Invalid/null event timestamps: "
        f"{invalid_timestamps}"
    )

    timestamp_pass = (
        invalid_timestamps == 0
    )

    print(
        "PASS"
        if timestamp_pass
        else "FAIL"
    )

    # --------------------------------------------------------
    # Source validation
    # --------------------------------------------------------

    print("\n" + "-" * 70)
    print("SOURCE VALIDATION")
    print("-" * 70)

    null_sources = df["_source"].isna().sum()

    print(
        f"Null source values: {null_sources}"
    )

    source_pass = null_sources == 0

    print(
        "PASS"
        if source_pass
        else "FAIL"
    )

    # --------------------------------------------------------
    # Event distribution
    # --------------------------------------------------------

    print("\n" + "-" * 70)
    print("EVENT DISTRIBUTION")
    print("-" * 70)

    print(
        df["event_type"]
        .value_counts()
        .to_string()
    )

    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    checks = [
        event_id_pass,
        event_type_pass,
        timestamp_pass,
        source_pass,
    ]

    passed = sum(checks)
    total = len(checks)

    print("\n" + "=" * 70)
    print(
        f"STREAMING SILVER VALIDATION: "
        f"{passed}/{total} CHECKS PASSED"
    )

    if passed == total:
        print("STATUS: PASS")
    else:
        print("STATUS: FAIL")

    print("=" * 70)

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()