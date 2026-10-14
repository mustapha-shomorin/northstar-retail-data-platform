import json
import random
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from kafka import KafkaProducer


# ============================================================
# Configuration
# ============================================================

BOOTSTRAP_SERVERS = "localhost:19092"
TOPIC = "northstar-events"

EVENTS_PER_SECOND = 2

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_SOURCE = PROJECT_ROOT / "data" / "source"

ORDERS_FILE = DATA_SOURCE / "olist_orders_dataset.csv"
CUSTOMERS_FILE = DATA_SOURCE / "olist_customers_dataset.csv"
PRODUCTS_FILE = DATA_SOURCE / "olist_products_dataset.csv"


# ============================================================
# Load sample IDs from Olist
# ============================================================

def load_ids():
    import pandas as pd

    orders = pd.read_csv(
        ORDERS_FILE,
        usecols=["order_id", "customer_id"]
    )

    products = pd.read_csv(
        PRODUCTS_FILE,
        usecols=["product_id"]
    )

    order_ids = orders["order_id"].dropna().tolist()
    customer_ids = orders["customer_id"].dropna().unique().tolist()
    product_ids = products["product_id"].dropna().tolist()

    return order_ids, customer_ids, product_ids


# ============================================================
# Event generation
# ============================================================

EVENT_TYPES = [
    "order_placed",
    "payment_received",
    "order_shipped",
    "order_delivered",
    "product_viewed",
    "cart_added",
    "cart_abandoned",
]


def generate_event(order_ids, customer_ids, product_ids):

    event_type = random.choice(EVENT_TYPES)

    event = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "event_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # --------------------------------------------------------
    # Order-related events
    # --------------------------------------------------------

    if event_type in {
        "order_placed",
        "payment_received",
        "order_shipped",
        "order_delivered",
    }:
        event["order_id"] = random.choice(order_ids)
        event["customer_id"] = random.choice(customer_ids)

    # --------------------------------------------------------
    # Product interaction events
    # --------------------------------------------------------

    elif event_type in {
        "product_viewed",
        "cart_added",
        "cart_abandoned",
    }:
        event["customer_id"] = random.choice(customer_ids)
        event["product_id"] = random.choice(product_ids)

    # --------------------------------------------------------
    # Event-specific attributes
    # --------------------------------------------------------

    if event_type == "payment_received":
        event["payment_value"] = round(random.uniform(10, 1000), 2)

    elif event_type == "product_viewed":
        event["device_type"] = random.choice([
            "mobile",
            "desktop",
            "tablet"
        ])

    elif event_type == "cart_added":
        event["quantity"] = random.randint(1, 5)

    return event


# ============================================================
# Kafka producer
# ============================================================

def create_producer():

    return KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        acks="all",
        retries=5,
    )


# ============================================================
# Main
# ============================================================

def main():

    print("Loading Olist IDs...")

    order_ids, customer_ids, product_ids = load_ids()

    print(f"Loaded {len(order_ids):,} order IDs")
    print(f"Loaded {len(customer_ids):,} customer IDs")
    print(f"Loaded {len(product_ids):,} product IDs")

    print()
    print(f"Connecting to Redpanda at {BOOTSTRAP_SERVERS}...")
    
    producer = create_producer()

    print(f"Connected. Producing events to '{TOPIC}'")
    print(f"Target rate: {EVENTS_PER_SECOND} events/sec")
    print("Press Ctrl+C to stop.")
    print()

    delay = 1 / EVENTS_PER_SECOND

    try:

        while True:

            event = generate_event(
                order_ids,
                customer_ids,
                product_ids
            )

            future = producer.send(
                TOPIC,
                value=event
            )

            metadata = future.get(timeout=10)

            print(
                f"[SENT] "
                f"{event['event_type']:<20} "
                f"event_id={event['event_id']} "
                f"partition={metadata.partition} "
                f"offset={metadata.offset}"
            )

            time.sleep(delay)

    except KeyboardInterrupt:

        print("\nStopping producer...")

    finally:

        producer.flush()
        producer.close()

        print("Producer stopped.")


if __name__ == "__main__":
    main()