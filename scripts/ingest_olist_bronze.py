from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib

import pandas as pd


# ============================================================
# Configuration
# ============================================================

SOURCE_DIR = Path("data/source")
BRONZE_DIR = Path("data/bronze/olist")

DEFAULT_INGESTION_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# Source files that should be ingested
SOURCE_FILES = [
    "olist_customers_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "product_category_name_translation.csv",
]


# ============================================================
# Utility functions
# ============================================================

def get_dataset_name(file_name: str) -> str:
    """
    Convert source filename into a clean dataset name.
    """

    if file_name == "product_category_name_translation.csv":
        return "product_category_name_translation"

    return (
        file_name
        .replace("olist_", "")
        .replace("_dataset.csv", "")
    )


def generate_batch_id(file_path: Path) -> str:
    """
    Generate a deterministic batch ID from the source file.

    The same source file contents will produce the same
    batch ID, supporting idempotent ingestion.
    """

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:

        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            sha256.update(chunk)

    return sha256.hexdigest()[:16]


def get_output_path(
    dataset_name: str,
    ingestion_date: str,
) -> Path:

    output_dir = (
        BRONZE_DIR
        / dataset_name
        / f"ingestion_date={ingestion_date}"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    return output_dir / "data.parquet"


# ============================================================
# Ingestion
# ============================================================

def ingest_dataset(file_name: str) -> dict:

    source_path = SOURCE_DIR / file_name

    if not source_path.exists():
        raise FileNotFoundError(
            f"Source file not found: {source_path}"
        )

    dataset_name = get_dataset_name(file_name)

    batch_id = generate_batch_id(source_path)

    output_path = get_output_path(
        dataset_name,
        INGESTION_DATE,
    )

    print("\n" + "-" * 70)
    print(f"Dataset:      {dataset_name}")
    print(f"Source:       {source_path}")
    print(f"Batch ID:     {batch_id}")
    print(f"Output:       {output_path}")

    # --------------------------------------------------------
    # Idempotency check
    # --------------------------------------------------------

    if output_path.exists():

        print("Status:       SKIPPED")
        print("Reason:       Bronze file already exists")

        return {
            "dataset": dataset_name,
            "status": "SKIPPED",
            "rows": None,
            "batch_id": batch_id,
            "output": str(output_path),
        }

    # --------------------------------------------------------
    # Read source
    # --------------------------------------------------------

    print("Reading source CSV...")

    df = pd.read_csv(source_path)

    original_columns = list(df.columns)

    # --------------------------------------------------------
    # Add ingestion metadata
    # --------------------------------------------------------

    df["_ingestion_timestamp"] = INGESTION_TIMESTAMP
    df["_source_file"] = file_name
    df["_batch_id"] = batch_id

    # --------------------------------------------------------
    # Write Parquet
    # --------------------------------------------------------

    print("Writing Parquet...")

    df.to_parquet(
        output_path,
        engine="pyarrow",
        index=False,
    )

    print(f"Rows:         {len(df):,}")
    print(f"Columns:      {len(original_columns)}")
    print("Status:       INGESTED")

    return {
        "dataset": dataset_name,
        "status": "INGESTED",
        "rows": len(df),
        "batch_id": batch_id,
        "output": str(output_path),
    }


# ============================================================
# Main
# ============================================================

# def main():

#     print("=" * 80)
#     print("NORTHSTAR RETAIL — OLIST BATCH INGESTION")
#     print("=" * 80)

#     print(f"\nSource directory: {SOURCE_DIR.resolve()}")
#     print(f"Bronze directory: {BRONZE_DIR.resolve()}")
#     print(f"Ingestion date:   {INGESTION_DATE}")

#     results = []

#     for file_name in SOURCE_FILES:

#         try:

#             result = ingest_dataset(file_name)

#             results.append(result)

#         except Exception as error:

#             print("\nERROR")
#             print(f"Dataset: {file_name}")
#             print(f"Reason:  {error}")

#             results.append({
#                 "dataset": get_dataset_name(file_name),
#                 "status": "FAILED",
#                 "rows": None,
#                 "batch_id": None,
#                 "output": None,
#             })

#     # ========================================================
#     # Summary
#     # ========================================================

#     results_df = pd.DataFrame(results)

#     print("\n" + "=" * 80)
#     print("INGESTION SUMMARY")
#     print("=" * 80)

#     print(
#         results_df.to_string(index=False)
#     )

#     successful = (
#         results_df["status"] == "INGESTED"
#     ).sum()

#     skipped = (
#         results_df["status"] == "SKIPPED"
#     ).sum()

#     failed = (
#         results_df["status"] == "FAILED"
#     ).sum()

#     print("\n" + "=" * 80)

#     print(f"Successfully ingested: {successful}")
#     print(f"Skipped:               {skipped}")
#     print(f"Failed:                {failed}")

#     if failed > 0:
#         raise RuntimeError(
#             "Batch ingestion completed with failures."
#         )

#     print("\nBatch ingestion completed successfully.")


def main():

    parser = argparse.ArgumentParser(
        description="Ingest Olist source CSV files into Bronze Parquet."
    )

    parser.add_argument(
        "--ingestion-date",
        default=DEFAULT_INGESTION_DATE,
        help="Logical ingestion date in YYYY-MM-DD format.",
    )

    args = parser.parse_args()

    global INGESTION_DATE
    global INGESTION_TIMESTAMP

    INGESTION_DATE = args.ingestion_date
    INGESTION_TIMESTAMP = datetime.now(timezone.utc).isoformat()

    print("=" * 80)
    print("NORTHSTAR RETAIL - OLIST BATCH INGESTION")
    print("=" * 80)

    print(f"\nSource directory: {SOURCE_DIR.resolve()}")
    print(f"Bronze directory: {BRONZE_DIR.resolve()}")
    print(f"Ingestion date:   {INGESTION_DATE}")

    results = []

    for file_name in SOURCE_FILES:

        try:

            result = ingest_dataset(file_name)

            results.append(result)

        except Exception as error:

            print("\nERROR")
            print(f"Dataset: {file_name}")
            print(f"Reason:  {error}")

            results.append({
                "dataset": get_dataset_name(file_name),
                "status": "FAILED",
                "rows": None,
                "batch_id": None,
                "output": None,
            })

    # ========================================================
    # Summary
    # ========================================================

    results_df = pd.DataFrame(results)

    print("\n" + "=" * 80)
    print("INGESTION SUMMARY")
    print("=" * 80)

    print(
        results_df.to_string(index=False)
    )

    successful = (
        results_df["status"] == "INGESTED"
    ).sum()

    skipped = (
        results_df["status"] == "SKIPPED"
    ).sum()

    failed = (
        results_df["status"] == "FAILED"
    ).sum()

    print("\n" + "=" * 80)

    print(f"Successfully ingested: {successful}")
    print(f"Skipped:               {skipped}")
    print(f"Failed:                {failed}")

    if failed > 0:
        raise RuntimeError(
            "Batch ingestion completed with failures."
        )

    print("\nBatch ingestion completed successfully.")

if __name__ == "__main__":
    main()