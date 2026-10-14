import duckdb
from pathlib import Path


DB_PATH = Path("data/northstar.duckdb")

SILVER_TABLES = {
    "silver_customers": "data/silver/customers/data.parquet",
    "silver_sellers": "data/silver/sellers/data.parquet",
    "silver_products": "data/silver/products/data.parquet",
    "silver_orders": "data/silver/orders/data.parquet",
    "silver_order_items": "data/silver/order_items/data.parquet",
    "silver_order_payments": "data/silver/order_payments/data.parquet",
    "silver_order_reviews": "data/silver/order_reviews/data.parquet",
    "silver_geolocation": "data/silver/geolocation/data.parquet",
    "silver_order_events": "data/silver/order_events/data.parquet",
}


def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(DB_PATH))

    print(f"DuckDB database: {DB_PATH}")

    for table_name, parquet_path in SILVER_TABLES.items():
        if not Path(parquet_path).exists():
            raise FileNotFoundError(
                f"Silver Parquet file not found: {parquet_path}"
            )

        con.execute(
            f"""
            CREATE OR REPLACE VIEW {table_name} AS
            SELECT *
            FROM read_parquet('{parquet_path}')
            """
        )

        count = con.execute(
            f"SELECT COUNT(*) FROM {table_name}"
        ).fetchone()[0]

        print(f"{table_name}: {count:,} rows")

    con.close()

    print("\nDuckDB setup completed successfully.")


if __name__ == "__main__":
    main()