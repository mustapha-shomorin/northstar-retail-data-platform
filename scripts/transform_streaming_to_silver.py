from pathlib import Path
from datetime import datetime, timezone
import pandas as pd


# ============================================================
# Configuration
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

BRONZE_STREAMING_DIR = (
    PROJECT_ROOT / "data" / "bronze" / "streaming"
)

SILVER_DIR = PROJECT_ROOT / "data" / "silver"

OUTPUT_DIR = SILVER_DIR / "order_events"
OUTPUT_FILE = OUTPUT_DIR / "data.parquet"


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
# Load Bronze streaming data
# ============================================================

def load_bronze_events():

    files = list(
        BRONZE_STREAMING_DIR.rglob("events.parquet")
    )

    if not files:
        raise FileNotFoundError(
            "No Bronze streaming events found."
        )

    print(f"Bronze event files found: {len(files)}")

    frames = []

    for file in files:

        df = pd.read_parquet(file)

        print(
            f"  {file.relative_to(PROJECT_ROOT)}: "
            f"{len(df):,} rows"
        )

        frames.append(df)

    return pd.concat(
        frames,
        ignore_index=True
    )


# ============================================================
# Validate events
# ============================================================

def validate_events(df):

    print("\nValidating event schema...")

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    invalid_event_types = set(
        df["event_type"].dropna().unique()
    ) - EXPECTED_EVENT_TYPES

    if invalid_event_types:
        raise ValueError(
            f"Unexpected event types: "
            f"{sorted(invalid_event_types)}"
        )

    null_required = df[
        REQUIRED_COLUMNS
    ].isna().any(axis=1).sum()

    if null_required:
        raise ValueError(
            f"{null_required} events have null "
            f"required fields."
        )

    print("  ✓ Required columns present")
    print("  ✓ Event types valid")
    print("  ✓ Required fields contain no nulls")


# ============================================================
# Transform
# ============================================================

def transform_events(df):

    df = df.copy()

    # --------------------------------------------------------
    # Deduplicate by event_id
    # --------------------------------------------------------

    before = len(df)

    df = df.drop_duplicates(
        subset=["event_id"],
        keep="first"
    )

    duplicates_removed = before - len(df)

    print(
        f"\nDuplicate events removed: "
        f"{duplicates_removed:,}"
    )

    # --------------------------------------------------------
    # Timestamp normalization
    # --------------------------------------------------------

    df["event_timestamp"] = pd.to_datetime(
        df["event_timestamp"],
        errors="coerce",
        utc=True
    )

    df["_ingestion_timestamp"] = pd.to_datetime(
        df["_ingestion_timestamp"],
        errors="coerce",
        utc=True
    )

    # --------------------------------------------------------
    # Standardize strings
    # --------------------------------------------------------

    df["event_id"] = (
        df["event_id"]
        .astype("string")
        .str.strip()
    )

    df["event_type"] = (
        df["event_type"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    df["_source"] = (
        df["_source"]
        .astype("string")
        .str.strip()
    )

    # --------------------------------------------------------
    # IDs
    # --------------------------------------------------------

    id_columns = [
        "order_id",
        "customer_id",
        "product_id",
        "device_type",
    ]

    for column in id_columns:

        if column in df.columns:

            df[column] = (
                df[column]
                .astype("string")
                .str.strip()
            )

    # --------------------------------------------------------
    # Numeric fields
    # --------------------------------------------------------

    df["payment_value"] = pd.to_numeric(
        df["payment_value"],
        errors="coerce"
    )

    df["quantity"] = pd.to_numeric(
        df["quantity"],
        errors="coerce"
    )

    # --------------------------------------------------------
    # Silver metadata
    # --------------------------------------------------------

    df["_silver_transformed_at"] = datetime.now(
        timezone.utc
    )

    df["_silver_batch_date"] = (
        datetime.now(timezone.utc)
        .date()
        .isoformat()
    )

    # --------------------------------------------------------
    # Column ordering
    # --------------------------------------------------------

    columns = [
        "event_id",
        "event_type",
        "event_timestamp",
        "order_id",
        "customer_id",
        "product_id",
        "payment_value",
        "quantity",
        "device_type",
        "_ingestion_timestamp",
        "_source",
        "_silver_transformed_at",
        "_silver_batch_date",
    ]

    df = df[
        [column for column in columns if column in df.columns]
    ]

    return df


# ============================================================
# Write Silver
# ============================================================

def write_silver(df):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_parquet(
        OUTPUT_FILE,
        index=False,
        engine="pyarrow"
    )

    print(
        f"\nWrote {len(df):,} rows → "
        f"{OUTPUT_FILE}"
    )


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 70)
    print("NORTHSTAR — STREAMING BRONZE → SILVER")
    print("=" * 70)

    df = load_bronze_events()

    print(
        f"\nTotal Bronze events: {len(df):,}"
    )

    validate_events(df)

    silver_df = transform_events(df)

    write_silver(silver_df)

    print("\nEvent distribution:")

    print(
        silver_df["event_type"]
        .value_counts()
        .to_string()
    )

    print("\n" + "=" * 70)
    print("STREAMING SILVER TRANSFORMATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()