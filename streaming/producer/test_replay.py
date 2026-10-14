import json
from pathlib import Path

import pandas as pd
from kafka import KafkaProducer


BOOTSTRAP_SERVERS = "localhost:19092"
TOPIC = "northstar-events"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BRONZE_DIR = PROJECT_ROOT / "data" / "bronze" / "streaming"


def get_existing_event():

    files = list(BRONZE_DIR.rglob("events.parquet"))

    if not files:
        raise FileNotFoundError(
            "No Bronze Parquet files found."
        )

    df = pd.concat(
        [pd.read_parquet(file) for file in files],
        ignore_index=True
    )

    return df.iloc[0].to_dict()


def main():

    event = get_existing_event()

    print("Replaying existing event:")
    print(f"event_id:   {event['event_id']}")
    print(f"event_type: {event['event_type']}")

    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda value: json.dumps(
            value
        ).encode("utf-8"),
        acks="all",
        retries=5,
    )

    metadata = producer.send(
        TOPIC,
        value=event
    ).get(timeout=10)

    producer.flush()
    producer.close()

    print()
    print(
        f"[REPLAYED] partition={metadata.partition} "
        f"offset={metadata.offset}"
    )


if __name__ == "__main__":
    main()