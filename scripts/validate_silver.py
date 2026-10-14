from pathlib import Path
import pandas as pd


# ============================================================
# Configuration
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SILVER_DIR = PROJECT_ROOT / "data" / "silver"


# ============================================================
# Dataset configuration
# ============================================================

DATASETS = {
    "customers": {
        "file": "customers/data.parquet",
        "keys": ["customer_id"],
    },
    "orders": {
        "file": "orders/data.parquet",
        "keys": ["order_id"],
    },
    "order_items": {
        "file": "order_items/data.parquet",
        "keys": ["order_id", "order_item_id"],
    },
    "order_payments": {
        "file": "order_payments/data.parquet",
        "keys": ["order_id", "payment_sequential"],
    },
    "order_reviews": {
        "file": "order_reviews/data.parquet",
        "keys": ["review_id", "order_id"],
    },
    "products": {
        "file": "products/data.parquet",
        "keys": ["product_id"],
    },
    "sellers": {
        "file": "sellers/data.parquet",
        "keys": ["seller_id"],
    },
    "geolocation": {
        "file": "geolocation/data.parquet",
        "keys": [],
    },
}


# ============================================================
# Helpers
# ============================================================

def load_dataset(dataset_name, config):
    path = SILVER_DIR / config["file"]

    if not path.exists():
        raise FileNotFoundError(
            f"Silver dataset not found: {path}"
        )

    return pd.read_parquet(path)


def check_key_uniqueness(df, keys):
    if not keys:
        return True, "N/A"

    null_count = df[keys].isna().any(axis=1).sum()

    duplicate_count = df.duplicated(
        subset=keys
    ).sum()

    passed = (
        null_count == 0
        and duplicate_count == 0
    )

    details = (
        f"null keys={null_count}, "
        f"duplicate keys={duplicate_count}"
    )

    return passed, details


def check_foreign_key(
    child_df,
    child_column,
    parent_df,
    parent_column
):
    child_values = set(
        child_df[child_column]
        .dropna()
        .astype(str)
    )

    parent_values = set(
        parent_df[parent_column]
        .dropna()
        .astype(str)
    )

    orphan_count = len(
        child_values - parent_values
    )

    return orphan_count == 0, orphan_count


# ============================================================
# Main validation
# ============================================================

def main():

    print("=" * 70)
    print("NORTHSTAR - SILVER DATA VALIDATION")
    print("=" * 70)

    datasets = {}

    # --------------------------------------------------------
    # Load datasets
    # --------------------------------------------------------

    for name, config in DATASETS.items():

        df = load_dataset(name, config)

        datasets[name] = df

        print(
            f"\n{name:<20} "
            f"{len(df):>10,} rows"
        )

    # --------------------------------------------------------
    # Key validation
    # --------------------------------------------------------

    print("\n" + "-" * 70)
    print("KEY VALIDATION")
    print("-" * 70)

    key_results = []

    for name, config in DATASETS.items():

        df = datasets[name]

        passed, details = check_key_uniqueness(
            df,
            config["keys"]
        )

        status = "PASS" if passed else "FAIL"

        print(
            f"{name:<20} "
            f"{status:<6} "
            f"{details}"
        )

        key_results.append(passed)

    # --------------------------------------------------------
    # Referential integrity
    # --------------------------------------------------------

    print("\n" + "-" * 70)
    print("REFERENTIAL INTEGRITY")
    print("-" * 70)

    relationships = [
        (
            "orders -> customers",
            "orders",
            "customer_id",
            "customers",
            "customer_id",
        ),
        (
            "order_items -> orders",
            "order_items",
            "order_id",
            "orders",
            "order_id",
        ),
        (
            "order_items -> products",
            "order_items",
            "product_id",
            "products",
            "product_id",
        ),
        (
            "order_items -> sellers",
            "order_items",
            "seller_id",
            "sellers",
            "seller_id",
        ),
        (
            "order_payments -> orders",
            "order_payments",
            "order_id",
            "orders",
            "order_id",
        ),
        (
            "order_reviews -> orders",
            "order_reviews",
            "order_id",
            "orders",
            "order_id",
        ),
    ]

    fk_results = []

    for (
        relationship,
        child_name,
        child_column,
        parent_name,
        parent_column,
    ) in relationships:

        passed, orphan_count = check_foreign_key(
            datasets[child_name],
            child_column,
            datasets[parent_name],
            parent_column,
        )

        status = "PASS" if passed else "FAIL"

        print(
            f"{relationship:<30} "
            f"{status:<6} "
            f"orphans={orphan_count}"
        )

        fk_results.append(passed)

    # --------------------------------------------------------
    # Required columns
    # --------------------------------------------------------

    print("\n" + "-" * 70)
    print("REQUIRED COLUMN VALIDATION")
    print("-" * 70)

    required_columns = {
        "customers": [
            "customer_id",
            "customer_unique_id",
        ],
        "orders": [
            "order_id",
            "customer_id",
            "order_status",
        ],
        "order_items": [
            "order_id",
            "order_item_id",
            "product_id",
            "seller_id",
        ],
        "order_payments": [
            "order_id",
            "payment_sequential",
            "payment_type",
        ],
        "products": [
            "product_id",
        ],
        "sellers": [
            "seller_id",
        ],
    }

    column_results = []

    for dataset_name, columns in required_columns.items():

        df = datasets[dataset_name]

        missing = [
            column
            for column in columns
            if column not in df.columns
        ]

        passed = len(missing) == 0

        status = "PASS" if passed else "FAIL"

        print(
            f"{dataset_name:<20} "
            f"{status:<6} "
            f"missing={missing}"
        )

        column_results.append(passed)

    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    total_checks = (
        len(key_results)
        + len(fk_results)
        + len(column_results)
    )

    passed_checks = sum(
        key_results
        + fk_results
        + column_results
    )

    print("\n" + "=" * 70)

    print(
        f"SILVER VALIDATION: "
        f"{passed_checks}/{total_checks} CHECKS PASSED"
    )

    if passed_checks == total_checks:
        print("STATUS: PASS")
    else:
        print("STATUS: FAIL")

    print("=" * 70)


if __name__ == "__main__":
    main()