from pathlib import Path

import pandas as pd


# ============================================================
# Configuration
# ============================================================

SOURCE_DIR = Path("data/source")


# ============================================================
# Dataset profiling
# ============================================================

def profile_dataset(file_path: Path) -> dict:
    """Generate high-level profiling information for a dataset."""

    df = pd.read_csv(file_path)

    missing_values = df.isna().sum()

    return {
        "file_name": file_path.name,
        "rows": len(df),
        "columns": len(df.columns),
        "duplicate_rows": int(df.duplicated().sum()),
        "memory_mb": round(
            df.memory_usage(deep=True).sum() / (1024 ** 2),
            2
        ),
        "total_missing_values": int(missing_values.sum()),
        "columns_with_missing_values": int(
            (missing_values > 0).sum()
        ),
    }


# ============================================================
# Column profiling
# ============================================================

def profile_columns(file_path: Path) -> pd.DataFrame:
    """Generate column-level profiling information."""

    df = pd.read_csv(file_path)

    profile = pd.DataFrame({
        "column": df.columns,
        "dtype": df.dtypes.astype(str).values,
        "non_null": df.notna().sum().values,
        "null_count": df.isna().sum().values,
        "null_percentage": (
            df.isna().mean().mul(100).round(2).values
        ),
        "unique_values": df.nunique(dropna=True).values,
    })

    profile["is_unique"] = (
        profile["unique_values"] == len(df)
    )

    return profile


# ============================================================
# Categorical value profiling
# ============================================================

def profile_categorical_values(file_path: Path):
    """Display value frequencies for categorical columns."""

    df = pd.read_csv(file_path)

    print("\nCategorical value distributions:")

    categorical_columns = []

    for column in df.columns:

        # Treat object/string columns as categorical
        if df[column].dtype == "object" or str(df[column].dtype) == "str":
            categorical_columns.append(column)

    if not categorical_columns:
        print("  No categorical columns detected.")
        return

    for column in categorical_columns:

        print(f"\n  {column}")

        value_counts = (
            df[column]
            .value_counts(dropna=False)
            .head(20)
        )

        for value, count in value_counts.items():

            percentage = (count / len(df)) * 100

            print(
                f"    {str(value):<40} "
                f"{count:>8,} "
                f"({percentage:>6.2f}%)"
            )

        if df[column].nunique(dropna=True) > 20:
            print(
                f"    ... showing top 20 of "
                f"{df[column].nunique(dropna=True):,} unique values"
            )


# ============================================================
# Numeric profiling
# ============================================================

def profile_numeric_columns(file_path: Path):
    """Display statistics for numeric columns."""

    df = pd.read_csv(file_path)

    numeric_columns = df.select_dtypes(
        include=["number"]
    ).columns

    print("\nNumeric column ranges:")

    if len(numeric_columns) == 0:
        print("  No numeric columns detected.")
        return

    numeric_profile = pd.DataFrame({
        "column": numeric_columns,
        "min": [df[column].min() for column in numeric_columns],
        "max": [df[column].max() for column in numeric_columns],
        "mean": [df[column].mean() for column in numeric_columns],
        "median": [df[column].median() for column in numeric_columns],
    })

    print(
        numeric_profile.to_string(
            index=False,
            float_format=lambda x: f"{x:,.4f}"
        )
    )


# ============================================================
# Date profiling
# ============================================================

def profile_date_columns(file_path: Path):
    """Detect date/timestamp columns and report their ranges."""

    df = pd.read_csv(file_path)

    print("\nDate/timestamp ranges:")

    date_columns = []

    for column in df.columns:

        column_name = column.lower()

        # Detect likely date columns by name
        if any(
            keyword in column_name
            for keyword in [
                "date",
                "timestamp",
                "datetime",
            ]
        ):
            date_columns.append(column)

    if not date_columns:
        print("  No date/timestamp columns detected.")
        return

    for column in date_columns:

        converted = pd.to_datetime(
            df[column],
            errors="coerce"
        )

        valid_dates = converted.dropna()

        if len(valid_dates) == 0:
            print(f"  {column}: no valid dates detected")
            continue

        print(
            f"  {column:<40} "
            f"min={valid_dates.min()} | "
            f"max={valid_dates.max()} | "
            f"invalid={converted.isna().sum():,}"
        )


# ============================================================
# Potential key profiling
# ============================================================

def profile_keys(file_path: Path):
    """
    Check likely Olist primary/composite keys.

    These are profiling checks only.
    They do not declare the keys as valid until
    we inspect the results.
    """

    df = pd.read_csv(file_path)

    file_name = file_path.name

    key_candidates = {
        "olist_customers_dataset.csv": [
            ["customer_id"],
            ["customer_unique_id"],
        ],

        "olist_orders_dataset.csv": [
            ["order_id"],
            ["customer_id"],
        ],

        "olist_order_items_dataset.csv": [
            ["order_id", "order_item_id"],
        ],

        "olist_order_payments_dataset.csv": [
            ["order_id", "payment_sequential"],
        ],

        "olist_order_reviews_dataset.csv": [
            ["review_id"],
            ["order_id"],
        ],

        "olist_products_dataset.csv": [
            ["product_id"],
        ],

        "olist_sellers_dataset.csv": [
            ["seller_id"],
        ],

        "olist_geolocation_dataset.csv": [
            [
                "geolocation_zip_code_prefix",
                "geolocation_lat",
                "geolocation_lng",
                "geolocation_city",
                "geolocation_state",
            ],
        ],

        "product_category_name_translation.csv": [
            ["product_category_name"],
            ["product_category_name_english"],
        ],
    }

    candidates = key_candidates.get(file_name, [])

    print("\nPotential key checks:")

    if not candidates:
        print("  No predefined key checks for this dataset.")
        return

    for key_columns in candidates:

        missing_columns = [
            column
            for column in key_columns
            if column not in df.columns
        ]

        if missing_columns:
            print(
                f"  {key_columns}: "
                f"missing columns {missing_columns}"
            )
            continue

        duplicate_count = int(
            df.duplicated(subset=key_columns).sum()
        )

        null_count = int(
            df[key_columns].isna().any(axis=1).sum()
        )

        total_rows = len(df)

        if duplicate_count == 0 and null_count == 0:
            status = "PASS"
        else:
            status = "CHECK"

        print(
            f"  [{status}] "
            f"{' + '.join(key_columns)} | "
            f"duplicates={duplicate_count:,} | "
            f"null_rows={null_count:,} | "
            f"rows={total_rows:,}"
        )


# ============================================================
# Profile a single dataset
# ============================================================

def profile_single_dataset(file_path: Path):
    """Run all profiling checks for one dataset."""

    print("\n" + "=" * 80)
    print(f"DATASET: {file_path.name}")
    print("=" * 80)

    # --------------------------------------------------------
    # Load dataset
    # --------------------------------------------------------

    df = pd.read_csv(file_path)

    # --------------------------------------------------------
    # Dataset summary
    # --------------------------------------------------------

    profile = profile_dataset(file_path)

    print("\nDataset summary:")
    print(f"  Rows:                         {profile['rows']:,}")
    print(f"  Columns:                      {profile['columns']:,}")
    print(f"  Duplicate rows:               {profile['duplicate_rows']:,}")
    print(f"  Memory usage:                 {profile['memory_mb']:.2f} MB")
    print(f"  Total missing values:         {profile['total_missing_values']:,}")
    print(
        f"  Columns with missing values:  "
        f"{profile['columns_with_missing_values']:,}"
    )

    # --------------------------------------------------------
    # Column profile
    # --------------------------------------------------------

    print("\nColumn profile:")

    column_profile = profile_columns(file_path)

    print(
        column_profile.to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # Categorical values
    # --------------------------------------------------------

    profile_categorical_values(file_path)

    # --------------------------------------------------------
    # Numeric columns
    # --------------------------------------------------------

    profile_numeric_columns(file_path)

    # --------------------------------------------------------
    # Date columns
    # --------------------------------------------------------

    profile_date_columns(file_path)

    # --------------------------------------------------------
    # Key checks
    # --------------------------------------------------------

    profile_keys(file_path)

    return profile


# ============================================================
# Main
# ============================================================

def main():
    """Profile all CSV files in the source directory."""

    csv_files = sorted(
        SOURCE_DIR.glob("*.csv")
    )

    if not csv_files:
        raise FileNotFoundError(
            f"No CSV files found in: {SOURCE_DIR.resolve()}"
        )

    print("=" * 80)
    print("NORTHSTAR RETAIL — OLIST SOURCE DATA PROFILING")
    print("=" * 80)

    print(
        f"\nSource directory: {SOURCE_DIR.resolve()}"
    )

    print(
        f"CSV files found: {len(csv_files)}"
    )

    profiles = []

    # --------------------------------------------------------
    # Profile each dataset
    # --------------------------------------------------------

    for file_path in csv_files:

        profile = profile_single_dataset(
            file_path
        )

        profiles.append(profile)

    # --------------------------------------------------------
    # Final dataset summary
    # --------------------------------------------------------

    profile_df = pd.DataFrame(
        profiles
    )

    print("\n" + "=" * 80)
    print("FINAL DATASET SUMMARY")
    print("=" * 80)

    print(
        profile_df.to_string(
            index=False
        )
    )


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    main()