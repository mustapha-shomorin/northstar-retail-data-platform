import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.transform_bronze_to_silver import normalize_order_status


def test_normalize_order_status():
    input_values = pd.Series([
        " delivered ",
        "SHIPPED",
        "  Canceled",
        "invoiced  ",
        None,
    ])

    result = normalize_order_status(input_values)

    expected = pd.Series([
        "delivered",
        "shipped",
        "canceled",
        "invoiced",
        pd.NA,
    ], dtype="string")

    pd.testing.assert_series_equal(
        result.reset_index(drop=True),
        expected.reset_index(drop=True),
        check_names=False,
    )