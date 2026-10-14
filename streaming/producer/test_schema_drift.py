import json
import uuid
from datetime import datetime, timezone

from kafka import KafkaProducer


BOOTSTRAP_SERVERS = "localhost:19092"
TOPIC = "northstar-events"


def create_producer():

    return KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        acks="all",
        retries=5,
    )


def main():

    producer = create_producer()

    # --------------------------------------------------------
    # Drift 1: Missing required field
    # event_type is intentionally removed
    # --------------------------------------------------------

    missing_field_event = {
        "event_id": str(uuid.uuid4()),
        "event_timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "customer_id": "schema-drift-test-001",
    }

    # --------------------------------------------------------
    # Drift 2: Renamed required field
    # event_type → type
    # --------------------------------------------------------

    renamed_field_event = {
        "event_id": str(uuid.uuid4()),
        "type": "order_placed",
        "event_timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "customer_id": "schema-drift-test-002",
    }

    events = [
        ("missing_event_type", missing_field_event),
        ("renamed_event_type", renamed_field_event),
    ]

    for name, event in events:

        metadata = producer.send(
            TOPIC,
            value=event
        ).get(timeout=10)

        print(
            f"[SENT DRIFT] {name} | "
            f"partition={metadata.partition} | "
            f"offset={metadata.offset}"
        )

    producer.flush()
    producer.close()

    print("\nSchema-drift test events sent.")


if __name__ == "__main__":
    main()