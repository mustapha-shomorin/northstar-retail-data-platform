import json
import signal
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from kafka import KafkaConsumer


# ============================================================
# Configuration
# ============================================================

BOOTSTRAP_SERVERS = "localhost:19092"
TOPIC = "northstar-events"
GROUP_ID = "northstar-bronze-consumer"

PROJECT_ROOT = Path(__file__).resolve().parents[2]

BRONZE_DIR = PROJECT_ROOT / "data" / "bronze" / "streaming"
QUARANTINE_DIR = BRONZE_DIR / "quarantine"

BATCH_SIZE = 10


# Required fields for every event
REQUIRED_FIELDS = {
    "event_id",
    "event_type",
    "event_timestamp",
}


# ============================================================
# Graceful shutdown
# ============================================================

running = True


def stop_consumer(signum, frame):
    global running
    print("\nStopping consumer...")
    running = False


signal.signal(signal.SIGINT, stop_consumer)
signal.signal(signal.SIGTERM, stop_consumer)


# ============================================================
# Validation
# ============================================================

def validate_event(event):

    if not isinstance(event, dict):
        return False, "Event is not a JSON object"

    missing_fields = REQUIRED_FIELDS - set(event.keys())

    if missing_fields:
        return False, (
            f"Missing required fields: "
            f"{sorted(missing_fields)}"
        )

    if not event["event_id"]:
        return False, "event_id is empty"

    if not event["event_type"]:
        return False, "event_type is empty"

    if not event["event_timestamp"]:
        return False, "event_timestamp is empty"

    return True, None


# ============================================================
# Bronze writer
# ============================================================

# def write_bronze(events):

#     if not events:
#         return

#     now = datetime.now(timezone.utc)

#     ingestion_date = now.strftime("%Y-%m-%d")
#     ingestion_hour = now.strftime("%H")

#     output_dir = (
#         BRONZE_DIR
#         / f"ingestion_date={ingestion_date}"
#         / f"ingestion_hour={ingestion_hour}"
#     )

#     output_dir.mkdir(parents=True, exist_ok=True)

#     output_file = output_dir / "events.parquet"

#     df = pd.DataFrame(events)

#     # Add ingestion metadata
#     df["_ingestion_timestamp"] = now.isoformat()
#     df["_source"] = "redpanda:northstar-events"

#     if output_file.exists():

#         existing = pd.read_parquet(output_file)

#         combined = pd.concat(
#             [existing, df],
#             ignore_index=True
#         )

#         # Idempotency protection
#         combined = combined.drop_duplicates(
#             subset=["event_id"],
#             keep="first"
#         )

#         combined.to_parquet(
#             output_file,
#             index=False
#         )

#     else:

#         df.to_parquet(
#             output_file,
#             index=False
#         )

#     print(
#         f"[BRONZE] Wrote {len(df)} event(s) → "
#         f"{output_file}"
#     )


def write_bronze(events):

    if not events:
        return

    now = datetime.now(timezone.utc)

    ingestion_date = now.strftime("%Y-%m-%d")
    ingestion_hour = now.strftime("%H")

    output_dir = (
        BRONZE_DIR
        / f"ingestion_date={ingestion_date}"
        / f"ingestion_hour={ingestion_hour}"
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "events.parquet"

    # --------------------------------------------------------
    # Create incoming DataFrame
    # --------------------------------------------------------

    df = pd.DataFrame(events)

    # --------------------------------------------------------
    # Global idempotency check
    #
    # Check ALL existing Bronze partitions for event_id.
    # --------------------------------------------------------

    existing_event_ids = set()

    existing_files = list(
        BRONZE_DIR.rglob("events.parquet")
    )

    for existing_file in existing_files:

        # Don't need to read the file we are about to rewrite
        # separately; it will be handled below.
        existing_df = pd.read_parquet(
            existing_file,
            columns=["event_id"]
        )

        existing_event_ids.update(
            existing_df["event_id"].dropna().astype(str)
        )

    # Remove events already present anywhere in Bronze
    df["event_id"] = df["event_id"].astype(str)

    before_count = len(df)

    df = df[
        ~df["event_id"].isin(existing_event_ids)
    ].copy()

    skipped_count = before_count - len(df)

    if skipped_count > 0:

        print(
            f"[DEDUP] Skipped {skipped_count} "
            f"already-processed event(s)"
        )

    # Nothing new to write
    if df.empty:

        print(
            "[BRONZE] No new events to write."
        )

        return

    # --------------------------------------------------------
    # Add ingestion metadata
    # --------------------------------------------------------

    df["_ingestion_timestamp"] = now.isoformat()
    df["_source"] = "redpanda:northstar-events"

    # --------------------------------------------------------
    # Write to the current partition
    # --------------------------------------------------------

    if output_file.exists():

        existing_df = pd.read_parquet(
            output_file
        )

        combined = pd.concat(
            [existing_df, df],
            ignore_index=True
        )

        # Final protection within this partition
        combined = combined.drop_duplicates(
            subset=["event_id"],
            keep="first"
        )

        combined.to_parquet(
            output_file,
            index=False
        )

    else:

        df.to_parquet(
            output_file,
            index=False
        )

    print(
        f"[BRONZE] Wrote {len(df)} new event(s) → "
        f"{output_file}"
    )
# ============================================================
# Quarantine writer
# ============================================================

def quarantine_event(event, reason):

    QUARANTINE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    now = datetime.now(timezone.utc)

    output_file = (
        QUARANTINE_DIR
        / f"quarantine_{now.strftime('%Y%m%d')}.jsonl"
    )

    record = {
        "_quarantine_timestamp": now.isoformat(),
        "_reason": reason,
        "event": event,
    }

    with open(
        output_file,
        "a",
        encoding="utf-8"
    ) as f:

        f.write(
            json.dumps(record) + "\n"
        )

    print(
        f"[QUARANTINE] {reason}"
    )


# ============================================================
# Kafka consumer
# ============================================================

def create_consumer():

    return KafkaConsumer(
        TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        group_id=GROUP_ID,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda value: json.loads(
            value.decode("utf-8")
        ),
    )


# ============================================================
# Main
# ============================================================

def main():

    print("Starting NorthStar Bronze consumer...")
    print(f"Broker: {BOOTSTRAP_SERVERS}")
    print(f"Topic: {TOPIC}")
    print(f"Consumer group: {GROUP_ID}")
    print()

    consumer = create_consumer()

    valid_events = []
    processed = 0
    quarantined = 0

    try:

        while running:

            records = consumer.poll(
                timeout_ms=1000,
                max_records=BATCH_SIZE
            )

            if not records:
                continue

            for _, messages in records.items():

                for message in messages:

                    event = message.value

                    valid, reason = validate_event(event)

                    if not valid:

                        quarantine_event(
                            event,
                            reason
                        )

                        quarantined += 1

                        # Offset can still be committed because
                        # the invalid record has been preserved.
                        continue

                    valid_events.append(event)
                    processed += 1

            # ------------------------------------------------
            # Write valid events before committing offsets
            # ------------------------------------------------

            if valid_events:

                write_bronze(valid_events)

                valid_events.clear()

            # ------------------------------------------------
            # Commit only after processing
            # ------------------------------------------------

            consumer.commit()

            print(
                f"[COMMITTED] "
                f"Processed={processed} "
                f"Quarantined={quarantined}"
            )

    finally:

        if valid_events:
            write_bronze(valid_events)

        consumer.close()

        print()
        print("Consumer stopped.")
        print(f"Total processed: {processed}")
        print(f"Total quarantined: {quarantined}")


if __name__ == "__main__":
    main()