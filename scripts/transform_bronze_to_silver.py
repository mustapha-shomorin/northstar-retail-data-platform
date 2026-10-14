from pathlib import Path
from datetime import datetime, timezone
import argparse

import pandas as pd


# ============================================================
# Configuration
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"
SILVER_DIR = PROJECT_ROOT / "data" / "silver"

DEFAULT_BATCH_DATE = "2026-09-28"
BATCH_DATE = DEFAULT_BATCH_DATE

BRONZE_OLIST_DIR = BRONZE_DIR / "olist"


# ============================================================
# Helpers
# ============================================================

def get_bronze_file(dataset: str) -> Path:
    """Return the Bronze parquet file for a dataset."""
    path = (
        BRONZE_OLIST_DIR
        / dataset
        / f"ingestion_date={BATCH_DATE}"
        / "data.parquet"
    )

    if not path.exists():
        raise FileNotFoundError(f"Bronze file not found: {path}")

    return path


def write_silver(df: pd.DataFrame, dataset: str) -> None:
    """Write a transformed dataframe to Silver as Parquet."""

    output_dir = SILVER_DIR / dataset
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "data.parquet"

    df.to_parquet(
        output_file,
        index=False,
        engine="pyarrow"
    )

    print(f"  Wrote {len(df):,} rows → {output_file}")


def add_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """Add Silver transformation metadata."""

    df = df.copy()

    df["_silver_transformed_at"] = datetime.now(
        timezone.utc
    )

    df["_silver_batch_date"] = BATCH_DATE

    return df

def normalize_order_status(series: pd.Series) -> pd.Series:
    """Normalize order status values for Silver."""
    return (
        series
        .astype("string")
        .str.strip()
        .str.lower()
    )


# ============================================================
# Customers
# ============================================================

def transform_customers():

    df = pd.read_parquet(get_bronze_file("customers"))

    df = df.drop_duplicates(
        subset=["customer_id"]
    )

    df["customer_zip_code_prefix"] = (
        pd.to_numeric(
            df["customer_zip_code_prefix"],
            errors="coerce"
        ).astype("Int64")
    )

    df["customer_city"] = (
        df["customer_city"]
        .astype("string")
        .str.strip()
    )

    df["customer_state"] = (
        df["customer_state"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    df = add_metadata(df)

    write_silver(df, "customers")


# ============================================================
# Sellers
# ============================================================

def transform_sellers():

    df = pd.read_parquet(get_bronze_file("sellers"))

    df = df.drop_duplicates(
        subset=["seller_id"]
    )

    df["seller_zip_code_prefix"] = (
        pd.to_numeric(
            df["seller_zip_code_prefix"],
            errors="coerce"
        ).astype("Int64")
    )

    df["seller_city"] = (
        df["seller_city"]
        .astype("string")
        .str.strip()
    )

    df["seller_state"] = (
        df["seller_state"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    df = add_metadata(df)

    write_silver(df, "sellers")


# ============================================================
# Products
# ============================================================

def transform_products():

    df = pd.read_parquet(get_bronze_file("products"))

    df = df.drop_duplicates(
        subset=["product_id"]
    )

    df["product_category_name"] = (
        df["product_category_name"]
        .astype("string")
        .str.strip()
    )

    numeric_columns = [
        "product_name_lenght",
        "product_description_lenght",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df = add_metadata(df)

    write_silver(df, "products")


# ============================================================
# Orders
# ============================================================

def transform_orders():

    df = pd.read_parquet(get_bronze_file("orders"))

    df = df.drop_duplicates(
        subset=["order_id"]
    )

    timestamp_columns = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]

    for column in timestamp_columns:
        df[column] = pd.to_datetime(
            df[column],
            errors="coerce"
        )

    df["order_status"] = normalize_order_status(
    df["order_status"]
    )

    df = add_metadata(df)

    write_silver(df, "orders")


# ============================================================
# Order Items
# ============================================================

def transform_order_items():

    df = pd.read_parquet(
        get_bronze_file("order_items")
    )

    df = df.drop_duplicates(
        subset=["order_id", "order_item_id"]
    )

    df["shipping_limit_date"] = pd.to_datetime(
        df["shipping_limit_date"],
        errors="coerce"
    )

    df["price"] = pd.to_numeric(
        df["price"],
        errors="coerce"
    )

    df["freight_value"] = pd.to_numeric(
        df["freight_value"],
        errors="coerce"
    )

    df = add_metadata(df)

    write_silver(df, "order_items")


# ============================================================
# Payments
# ============================================================

def transform_order_payments():

    df = pd.read_parquet(
        get_bronze_file("order_payments")
    )

    df = df.drop_duplicates(
        subset=["order_id", "payment_sequential"]
    )

    df["payment_type"] = (
        df["payment_type"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    df["payment_installments"] = pd.to_numeric(
        df["payment_installments"],
        errors="coerce"
    )

    df["payment_value"] = pd.to_numeric(
        df["payment_value"],
        errors="coerce"
    )

    df = add_metadata(df)

    write_silver(df, "order_payments")


# ============================================================
# Reviews
# ============================================================

def transform_order_reviews():

    df = pd.read_parquet(
        get_bronze_file("order_reviews")
    )

    df = df.drop_duplicates(
        subset=["review_id", "order_id"]
    )

    df["review_comment_title"] = (
        df["review_comment_title"]
        .astype("string")
        .str.strip()
    )

    df["review_comment_message"] = (
        df["review_comment_message"]
        .astype("string")
        .str.strip()
    )

    df["review_score"] = pd.to_numeric(
        df["review_score"],
        errors="coerce"
    )

    df = add_metadata(df)

    write_silver(df, "order_reviews")


# ============================================================
# Geolocation
# ============================================================

def transform_geolocation():

    df = pd.read_parquet(
        get_bronze_file("geolocation")
    )

    df = df.drop_duplicates()

    df["geolocation_zip_code_prefix"] = (
        pd.to_numeric(
            df["geolocation_zip_code_prefix"],
            errors="coerce"
        ).astype("Int64")
    )

    df["geolocation_lat"] = pd.to_numeric(
        df["geolocation_lat"],
        errors="coerce"
    )

    df["geolocation_lng"] = pd.to_numeric(
        df["geolocation_lng"],
        errors="coerce"
    )

    df["geolocation_city"] = (
        df["geolocation_city"]
        .astype("string")
        .str.strip()
    )

    df["geolocation_state"] = (
        df["geolocation_state"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    df = add_metadata(df)

    write_silver(df, "geolocation")


# ============================================================
# Main
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description="Transform NorthStar Bronze data into Silver."
    )

    parser.add_argument(
        "--batch-date",
        default=DEFAULT_BATCH_DATE,
        help="Bronze ingestion date to transform, in YYYY-MM-DD format.",
    )

    args = parser.parse_args()

    global BATCH_DATE
    BATCH_DATE = args.batch_date

    print("=" * 60)
    print("NORTHSTAR - BRONZE -> SILVER TRANSFORMATION")
    print("=" * 60)

    print(f"Batch date: {BATCH_DATE}")

    transformations = [
        ("customers", transform_customers),
        ("sellers", transform_sellers),
        ("products", transform_products),
        ("orders", transform_orders),
        ("order_items", transform_order_items),
        ("order_payments", transform_order_payments),
        ("order_reviews", transform_order_reviews),
        ("geolocation", transform_geolocation),
    ]

    for name, transform in transformations:

        print(f"\nTransforming: {name}")

        try:
            transform()
            print(f"  {name} completed")

        except Exception as exc:
            print(f"  {name} failed: {exc}")
            raise

    print("\n" + "=" * 60)
    print("SILVER TRANSFORMATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()