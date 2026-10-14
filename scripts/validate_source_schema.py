from pathlib import Path

import pandas as pd


# ============================================================
# Configuration
# ============================================================

SOURCE_DIR = Path("data/source")


# ============================================================
# Expected source schema
# ============================================================

EXPECTED_SCHEMA = {

    "customers": {
        "required_columns": [
            "customer_id",
            "customer_unique_id",
            "customer_zip_code_prefix",
            "customer_city",
            "customer_state",
        ],
    },

    "orders": {
        "required_columns": [
            "order_id",
            "customer_id",
            "order_status",
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ],
    },

    "order_items": {
        "required_columns": [
            "order_id",
            "order_item_id",
            "product_id",
            "seller_id",
            "shipping_limit_date",
            "price",
            "freight_value",
        ],
    },

    "order_payments": {
        "required_columns": [
            "order_id",
            "payment_sequential",
            "payment_type",
            "payment_installments",
            "payment_value",
        ],
    },

    "order_reviews": {
        "required_columns": [
            "review_id",
            "order_id",
            "review_score",
            "review_comment_title",
            "review_comment_message",
            "review_creation_date",
            "review_answer_timestamp",
        ],
    },

    "products": {
        "required_columns": [
            "product_id",
            "product_category_name",
            "product_name_lenght",
            "product_description_lenght",
            "product_photos_qty",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
        ],
    },

    "sellers": {
        "required_columns": [
            "seller_id",
            "seller_zip_code_prefix",
            "seller_city",
            "seller_state",
        ],
    },

    "geolocation": {
        "required_columns": [
            "geolocation_zip_code_prefix",
            "geolocation_lat",
            "geolocation_lng",
            "geolocation_city",
            "geolocation_state",
        ],
    },

    "product_category_name_translation": {
        "required_columns": [
            "product_category_name",
            "product_category_name_english",
        ],
    },
}


# ============================================================
# Dataset loader
# ============================================================

def load_dataset(file_path: Path) -> pd.DataFrame:
    """Load a CSV dataset."""

    print(f"Loading: {file_path.name}")

    return pd.read_csv(file_path)


# ============================================================
# Schema validation
# ============================================================

def validate_schema(
    df: pd.DataFrame,
    dataset_name: str,
    expected_columns: list[str],
) -> dict:

    actual_columns = set(df.columns)
    expected_columns_set = set(expected_columns)

    missing_columns = sorted(
        expected_columns_set - actual_columns
    )

    unexpected_columns = sorted(
        actual_columns - expected_columns_set
    )

    required_columns_present = len(missing_columns) == 0

    return {
        "dataset": dataset_name,
        "rows": len(df),
        "actual_columns": len(actual_columns),
        "expected_columns": len(expected_columns_set),
        "missing_columns": ", ".join(missing_columns) if missing_columns else "",
        "unexpected_columns": ", ".join(unexpected_columns) if unexpected_columns else "",
        "status": "PASS" if required_columns_present else "FAIL",
    }


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 80)
    print("NORTHSTAR RETAIL — SOURCE SCHEMA VALIDATION")
    print("=" * 80)

    results = []

    for dataset_name, config in EXPECTED_SCHEMA.items():

        # ----------------------------------------------------
        # Find matching file
        # ----------------------------------------------------

        if dataset_name == "product_category_name_translation":

            file_path = (
                SOURCE_DIR /
                "product_category_name_translation.csv"
            )

        else:

            file_path = (
                SOURCE_DIR /
                f"olist_{dataset_name}_dataset.csv"
            )

        # ----------------------------------------------------
        # Check file exists
        # ----------------------------------------------------

        if not file_path.exists():

            results.append({
                "dataset": dataset_name,
                "rows": None,
                "actual_columns": None,
                "expected_columns": len(
                    config["required_columns"]
                ),
                "missing_columns": "SOURCE FILE NOT FOUND",
                "unexpected_columns": "",
                "status": "FAIL",
            })

            continue

        # ----------------------------------------------------
        # Load dataset
        # ----------------------------------------------------

        df = load_dataset(file_path)

        # ----------------------------------------------------
        # Validate schema
        # ----------------------------------------------------

        result = validate_schema(
            df=df,
            dataset_name=dataset_name,
            expected_columns=config["required_columns"],
        )

        results.append(result)

    # ========================================================
    # Results
    # ========================================================

    results_df = pd.DataFrame(results)

    print("\n" + "=" * 80)
    print("SCHEMA VALIDATION RESULTS")
    print("=" * 80)

    print(
        results_df.to_string(index=False)
    )

    # ========================================================
    # Summary
    # ========================================================

    print("\n" + "=" * 80)
    print("SCHEMA VALIDATION SUMMARY")
    print("=" * 80)

    total = len(results_df)

    passed = (
        results_df["status"] == "PASS"
    ).sum()

    failed = (
        results_df["status"] == "FAIL"
    ).sum()

    print(f"\nDatasets checked: {total}")
    print(f"Passed:           {passed}")
    print(f"Failed:           {failed}")

    if failed == 0:

        print("\nOverall schema validation: PASS")

    else:

        print("\nOverall schema validation: FAIL")


if __name__ == "__main__":
    main()