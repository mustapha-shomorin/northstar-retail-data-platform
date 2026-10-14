import json
import random
import time
import uuid
from datetime import datetime, timezone

from kafka import KafkaProducer


# ============================================================
# Configuration
# ============================================================

BOOTSTRAP_SERVERS = "localhost:19092"
TOPIC = "northstar-events"

EVENTS_PER_SECOND = 2

# Sample IDs from the Olist dataset
SAMPLE_ORDER_IDS = [
    "53cdb2fc8bc7dce0b6741e2150273451",
    "1505230f5f1d9b2f2e0e5a4e4f5f8e9a",
    "703f5f9a0b4f2c5e8a7d6b1c9e0f1234",
]

SAMPLE_CUSTOMER_IDS = [
    "861eff4711a542e4b93843c6dd7febb6",
    "290c77bc529b7ac8f6b1c9d8e7f6a5b4",
    "879864dab9bc3043f70c0f5f7f3e7f9a",
]

EVENT_TYPES = [
    "order_placed",
    "payment_received",
    "order_shipped",
    "order_delivered",
    "product_viewed",
    "cart_added",
    "cart_abandoned",
]


# ============================================================
# Kafka producer
# ============================================================

def create_producer():

    return KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )


# ============================================================
# Event generation
# ============================================================

def generate_event():

    event_type = random.choice(EVENT_TYPES)

    event = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "event_timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "customer_id": random.choice(SAMPLE_CUSTOMER_IDS),
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

        event["order_id"] = random.choice(
            SAMPLE_ORDER_IDS
        )

    # --------------------------------------------------------
    # Product/customer interaction events
    # --------------------------------------------------------

    if event_type in {
        "product_viewed",
        "cart_added",
    }:

        event["product_id"] = str(
            uuid.uuid4()
        )

    # --------------------------------------------------------
    # Additional attributes
    # --------------------------------------------------------

    if event_type == "payment_received":

        event["payment_value"] = round(
            random.uniform(20, 500),
            2,
        )

    if event_type == "product_viewed":

        event["device_type"] = random.choice(
            ["mobile", "desktop", "tablet"]
        )

    if event_type == "cart_added":

        event["quantity"] = random.randint(
            1,
            5,
        )

    return event


# ============================================================
# Producer loop
# ============================================================

def main():

    print("=" * 70)
    print("NORTHSTAR RETAIL — STREAMING EVENT PRODUCER")
    print("=" * 70)

    print(f"\nKafka broker: {BOOTSTRAP_SERVERS}")
    print(f"Topic:        {TOPIC}")
    print(f"Rate:         {EVENTS_PER_SECOND} events/second")

    print("\nConnecting to Kafka-compatible broker...")

    producer = create_producer()

    print("Connected.")
    print("\nGenerating events...\n")

    interval = 1 / EVENTS_PER_SECOND

    try:

        while True:

            event = generate_event()

            producer.send(
                TOPIC,
                value=event,
            )

            producer.flush()

            print(
                f"[{event['event_timestamp']}] "
                f"{event['event_type']:<20} "
                f"event_id={event['event_id']}"
            )

            time.sleep(interval)

    except KeyboardInterrupt:

        print("\nStopping producer...")

    finally:

        producer.flush()
        producer.close()

        print("Producer stopped.")


if __name__ == "__main__":
    main()