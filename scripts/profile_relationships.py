from pathlib import Path

import pandas as pd


# ============================================================
# Configuration
# ============================================================

SOURCE_DIR = Path("data/source")


# ============================================================
# Dataset loading
# ============================================================

def load_datasets() -> dict[str, pd.DataFrame]:
    """Load all Olist CSV datasets into memory."""

    datasets = {}

    csv_files = sorted(SOURCE_DIR.glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(
            f"No CSV files found in: {SOURCE_DIR.resolve()}"
        )

    for file_path in csv_files:
        dataset_name = file_path.stem.replace(
            "olist_", ""
        ).replace("_dataset", "")

        print(f"Loading: {file_path.name}")

        datasets[dataset_name] = pd.read_csv(file_path)

    return datasets


# ============================================================
# Primary-key profiling
# ============================================================

def profile_primary_key(
    df: pd.DataFrame,
    dataset_name: str,
    key_column: str,
) -> dict:
    """Profile uniqueness and nulls for a primary key."""

    if key_column not in df.columns:
        return {
            "dataset": dataset_name,
            "key": key_column,
            "rows": len(df),
            "null_count": None,
            "duplicate_count": None,
            "unique_count": None,
            "is_unique": False,
            "status": "COLUMN NOT FOUND",
        }

    null_count = int(df[key_column].isna().sum())
    duplicate_count = int(
        df[key_column].duplicated(keep=False).sum()
    )
    unique_count = int(df[key_column].nunique(dropna=True))

    is_unique = (
        null_count == 0
        and duplicate_count == 0
        and unique_count == len(df)
    )

    return {
        "dataset": dataset_name,
        "key": key_column,
        "rows": len(df),
        "null_count": null_count,
        "duplicate_count": duplicate_count,
        "unique_count": unique_count,
        "is_unique": is_unique,
        "status": "PASS" if is_unique else "CHECK",
    }


# ============================================================
# Foreign-key profiling
# ============================================================

def profile_foreign_key(
    child_df: pd.DataFrame,
    parent_df: pd.DataFrame,
    child_dataset: str,
    child_key: str,
    parent_dataset: str,
    parent_key: str,
) -> dict:
    """
    Check whether every non-null child foreign key
    exists in the parent table.
    """

    if child_key not in child_df.columns:
        return {
            "relationship": (
                f"{child_dataset}.{child_key} -> "
                f"{parent_dataset}.{parent_key}"
            ),
            "child_rows": len(child_df),
            "child_nulls": None,
            "distinct_child_keys": None,
            "parent_keys": None,
            "orphan_keys": None,
            "orphan_rows": None,
            "orphan_percentage": None,
            "status": "CHILD COLUMN NOT FOUND",
        }

    if parent_key not in parent_df.columns:
        return {
            "relationship": (
                f"{child_dataset}.{child_key} -> "
                f"{parent_dataset}.{parent_key}"
            ),
            "child_rows": len(child_df),
            "child_nulls": int(child_df[child_key].isna().sum()),
            "distinct_child_keys": int(
                child_df[child_key].nunique(dropna=True)
            ),
            "parent_keys": None,
            "orphan_keys": None,
            "orphan_rows": None,
            "orphan_percentage": None,
            "status": "PARENT COLUMN NOT FOUND",
        }

    child_keys = child_df[child_key].dropna()
    parent_keys = set(parent_df[parent_key].dropna().unique())

    orphan_mask = ~child_keys.isin(parent_keys)

    orphan_rows = int(orphan_mask.sum())
    orphan_keys = int(child_keys[orphan_mask].nunique())

    orphan_percentage = round(
        orphan_rows / len(child_keys) * 100,
        2
    ) if len(child_keys) > 0 else 0

    return {
        "relationship": (
            f"{child_dataset}.{child_key} -> "
            f"{parent_dataset}.{parent_key}"
        ),
        "child_rows": len(child_df),
        "child_nulls": int(child_df[child_key].isna().sum()),
        "distinct_child_keys": int(
            child_df[child_key].nunique(dropna=True)
        ),
        "parent_keys": len(parent_keys),
        "orphan_keys": orphan_keys,
        "orphan_rows": orphan_rows,
        "orphan_percentage": orphan_percentage,
        "status": "PASS" if orphan_rows == 0 else "CHECK",
    }


# ============================================================
# Composite-key profiling
# ============================================================

def profile_composite_key(
    df: pd.DataFrame,
    dataset_name: str,
    key_columns: list[str],
) -> dict:
    """Check uniqueness of a composite key."""

    missing_columns = [
        column
        for column in key_columns
        if column not in df.columns
    ]

    if missing_columns:
        return {
            "dataset": dataset_name,
            "key": " + ".join(key_columns),
            "rows": len(df),
            "duplicate_rows": None,
            "null_key_rows": None,
            "is_unique": False,
            "status": f"MISSING: {missing_columns}",
        }

    null_key_rows = int(
        df[key_columns].isna().any(axis=1).sum()
    )

    duplicate_rows = int(
        df.duplicated(subset=key_columns, keep=False).sum()
    )

    is_unique = (
        null_key_rows == 0
        and duplicate_rows == 0
    )

    return {
        "dataset": dataset_name,
        "key": " + ".join(key_columns),
        "rows": len(df),
        "duplicate_rows": duplicate_rows,
        "null_key_rows": null_key_rows,
        "is_unique": is_unique,
        "status": "PASS" if is_unique else "CHECK",
    }


# ============================================================
# Relationship configuration
# ============================================================

RELATIONSHIPS = [
    {
        "child_dataset": "orders",
        "child_key": "customer_id",
        "parent_dataset": "customers",
        "parent_key": "customer_id",
    },
    {
        "child_dataset": "order_items",
        "child_key": "order_id",
        "parent_dataset": "orders",
        "parent_key": "order_id",
    },
    {
        "child_dataset": "order_items",
        "child_key": "product_id",
        "parent_dataset": "products",
        "parent_key": "product_id",
    },
    {
        "child_dataset": "order_items",
        "child_key": "seller_id",
        "parent_dataset": "sellers",
        "parent_key": "seller_id",
    },
    {
        "child_dataset": "order_payments",
        "child_key": "order_id",
        "parent_dataset": "orders",
        "parent_key": "order_id",
    },
    {
        "child_dataset": "order_reviews",
        "child_key": "order_id",
        "parent_dataset": "orders",
        "parent_key": "order_id",
    },
]


PRIMARY_KEYS = [
    ("customers", "customer_id"),
    ("orders", "order_id"),
    ("products", "product_id"),
    ("sellers", "seller_id"),
]


COMPOSITE_KEYS = [
    ("order_items", ["order_id", "order_item_id"]),
    ("order_payments", ["order_id", "payment_sequential"]),
]


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 80)
    print("NORTHSTAR RETAIL — OLIST RELATIONSHIP & INTEGRITY PROFILER")
    print("=" * 80)

    # --------------------------------------------------------
    # Load datasets
    # --------------------------------------------------------

    datasets = load_datasets()

    print("\nDatasets loaded:")
    for name, df in datasets.items():
        print(f"  {name:<20} {len(df):>10,} rows")

    # --------------------------------------------------------
    # Primary-key checks
    # --------------------------------------------------------

    print("\n" + "=" * 80)
    print("PRIMARY KEY INTEGRITY")
    print("=" * 80)

    pk_results = []

    for dataset_name, key_column in PRIMARY_KEYS:

        result = profile_primary_key(
            datasets[dataset_name],
            dataset_name,
            key_column,
        )

        pk_results.append(result)

    pk_df = pd.DataFrame(pk_results)

    print(
        pk_df.to_string(index=False)
    )

    # --------------------------------------------------------
    # Composite-key checks
    # --------------------------------------------------------

    print("\n" + "=" * 80)
    print("COMPOSITE KEY INTEGRITY")
    print("=" * 80)

    composite_results = []

    for dataset_name, key_columns in COMPOSITE_KEYS:

        result = profile_composite_key(
            datasets[dataset_name],
            dataset_name,
            key_columns,
        )

        composite_results.append(result)

    composite_df = pd.DataFrame(composite_results)

    print(
        composite_df.to_string(index=False)
    )

    # --------------------------------------------------------
    # Foreign-key checks
    # --------------------------------------------------------

    print("\n" + "=" * 80)
    print("REFERENTIAL INTEGRITY")
    print("=" * 80)

    relationship_results = []

    for relationship in RELATIONSHIPS:

        result = profile_foreign_key(
            child_df=datasets[
                relationship["child_dataset"]
            ],
            parent_df=datasets[
                relationship["parent_dataset"]
            ],
            child_dataset=relationship["child_dataset"],
            child_key=relationship["child_key"],
            parent_dataset=relationship["parent_dataset"],
            parent_key=relationship["parent_key"],
        )

        relationship_results.append(result)

    relationship_df = pd.DataFrame(
        relationship_results
    )

    print(
        relationship_df.to_string(index=False)
    )

    # --------------------------------------------------------
    # Overall summary
    # --------------------------------------------------------

    print("\n" + "=" * 80)
    print("INTEGRITY SUMMARY")
    print("=" * 80)

    pk_pass = (pk_df["status"] == "PASS").sum()
    pk_total = len(pk_df)

    composite_pass = (
        composite_df["status"] == "PASS"
    ).sum()
    composite_total = len(composite_df)

    relationship_pass = (
        relationship_df["status"] == "PASS"
    ).sum()
    relationship_total = len(relationship_df)

    print(
        f"\nPrimary keys:       {pk_pass}/{pk_total} PASS"
    )
    print(
        f"Composite keys:     "
        f"{composite_pass}/{composite_total} PASS"
    )
    print(
        f"Relationships:      "
        f"{relationship_pass}/{relationship_total} PASS"
    )

    total_checks = (
        pk_total
        + composite_total
        + relationship_total
    )

    total_pass = (
        pk_pass
        + composite_pass
        + relationship_pass
    )

    print(
        f"\nOverall integrity:  "
        f"{total_pass}/{total_checks} checks PASS"
    )


if __name__ == "__main__":
    main()