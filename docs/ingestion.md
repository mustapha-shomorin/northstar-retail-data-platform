# NorthStar Retail — Ingestion Design

## 1. Overview

NorthStar Retail uses a hybrid ingestion architecture supporting both historical batch ingestion and near-real-time streaming ingestion.

The ingestion layer consists of:

* Historical Olist Brazilian E-Commerce Dataset
* Python batch ingestion
* Redpanda for event streaming
* Python Kafka-compatible producer
* Python streaming consumer
* Parquet-based Bronze storage
* Schema validation and quarantine
* Event-level idempotency using `event_id`

The overall flow is:

```text
Historical Olist Dataset
        |
        v
   Batch Ingestion
        |
        v
 Bronze Parquet
```

and:

```text
Synthetic Event Producer
        |
        v
     Redpanda
        |
        v
 Streaming Consumer
        |
        v
 Bronze Parquet
```

## 2. Batch Ingestion

The historical Olist dataset consists of nine source files:

* customers
* orders
* order_items
* order_payments
* order_reviews
* products
* sellers
* geolocation
* product_category_name_translation

The batch ingestion process reads the source CSV files and writes them to Parquet in the Bronze layer.

Each dataset receives the following ingestion metadata:

* `_ingestion_timestamp`
* `_source_file`
* `_batch_id`

The batch ID is generated deterministically using a SHA-256 hash of the source file contents.

### Batch storage layout

```text
data/bronze/olist/
├── customers/
│   └── ingestion_date=YYYY-MM-DD/
├── orders/
│   └── ingestion_date=YYYY-MM-DD/
├── order_items/
│   └── ingestion_date=YYYY-MM-DD/
├── order_payments/
│   └── ingestion_date=YYYY-MM-DD/
├── order_reviews/
│   └── ingestion_date=YYYY-MM-DD/
├── products/
│   └── ingestion_date=YYYY-MM-DD/
├── sellers/
│   └── ingestion_date=YYYY-MM-DD/
├── geolocation/
│   └── ingestion_date=YYYY-MM-DD/
└── product_category_name_translation/
    └── ingestion_date=YYYY-MM-DD/
```

The batch process is idempotent for the current project scope. If the target dataset partition already exists, the ingestion process skips rewriting it.

## 3. Streaming Ingestion

Streaming events are generated synthetically using identifiers from the Olist dataset.

Supported event types include:

* `order_placed`
* `payment_received`
* `order_shipped`
* `order_delivered`
* `product_viewed`
* `cart_added`
* `cart_abandoned`

The producer publishes JSON events to the Redpanda topic:

```text
northstar-events
```

Redpanda is Kafka-compatible and is used as the local streaming broker.

### Streaming event structure

Events contain a unique:

```text
event_id
```

and:

```text
event_type
event_timestamp
```

Additional fields depend on the event type, such as:

```text
customer_id
order_id
product_id
payment_value
device_type
quantity
```

## 4. Streaming Bronze Storage

The consumer reads events from Redpanda and writes valid events to Parquet.

Streaming Bronze data is partitioned by ingestion date and hour:

```text
data/bronze/streaming/
└── ingestion_date=YYYY-MM-DD/
    └── ingestion_hour=HH/
        └── events.parquet
```

Each event receives:

```text
_ingestion_timestamp
_source
```

The `_source` value identifies the originating stream:

```text
redpanda:northstar-events
```

## 5. Schema Validation and Drift Handling

The consumer validates the required fields:

```text
event_id
event_type
event_timestamp
```

### Additive fields

Additional fields are preserved rather than rejected.

For example, an event may contain:

```text
device_type
```

or:

```text
quantity
```

without causing the event to fail validation.

### Missing required fields

Events missing a required field are rejected from Bronze and written to the quarantine area.

### Renamed required fields

A renamed required field is treated as missing until the schema is explicitly updated.

For example:

```text
event_type
```

renamed to:

```text
type
```

is treated as a schema violation.

### Quarantine

Invalid events are preserved in:

```text
data/bronze/streaming/quarantine/
```

as JSON Lines files.

This prevents invalid records from silently disappearing while keeping them available for investigation and reprocessing.

## 6. Idempotency and Replay Strategy

Each streaming event has a globally unique:

```text
event_id
```

The consumer checks existing Bronze partitions before writing new events.

If an `event_id` already exists anywhere in the Bronze streaming layer, the event is skipped.

This protects the Bronze layer against duplicate delivery and replay.

The implementation follows an effectively at-least-once ingestion model:

```text
Redpanda
   |
   v
Consumer
   |
   v
Process event
   |
   v
Write Bronze
   |
   v
Commit offset
```

Offsets are committed only after processing.

Therefore, if processing fails before the offset is committed, the event can be replayed safely.

## 7. Replay Test

Idempotency was explicitly tested by replaying an existing valid event into Redpanda.

Before replay:

```text
Bronze rows: 54
Unique event IDs: 54
```

The same event was subsequently published again.

After replay and processing:

```text
Bronze rows: 54
Unique event IDs: 54
Duplicate event IDs: 0
```

This demonstrates that replaying an already-processed event does not create a duplicate Bronze record.

## 8. Schema Drift Test

Two malformed events were intentionally introduced:

1. An event with the required `event_type` field removed.
2. An event where `event_type` was renamed to `type`.

Both were rejected by the consumer and written to quarantine.

The result was:

```text
Total processed: 0
Total quarantined: 2
```

The original malformed payloads and validation reasons were preserved in the quarantine JSONL file.

## 9. Failure and Recovery Behavior

The streaming consumer uses manual Kafka offset commits.

The intended processing sequence is:

1. Read event from Redpanda.
2. Validate event.
3. Write valid event to Bronze or quarantine invalid event.
4. Commit the Kafka offset.

This provides safe recovery from processing failures.

If the consumer stops before committing an event, the event remains available for replay from Redpanda.

Duplicate events created by replay are handled through `event_id`-based idempotency.

## 10. Current Ingestion Architecture

```text
                 ┌───────────────────────┐
                 │ Olist Historical Data │
                 └───────────┬───────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Batch Ingestion │
                    └────────┬────────┘
                             │
                             ▼
                     Bronze Parquet


                 ┌───────────────────────┐
                 │ Synthetic Event       │
                 │ Producer              │
                 └───────────┬───────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    Redpanda     │
                    │ northstar-events│
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Streaming       │
                    │ Consumer        │
                    └────────┬────────┘
                             │
                 ┌───────────┴───────────┐
                 ▼                       ▼
          Valid Events              Invalid Events
                 │                       │
                 ▼                       ▼
        Bronze Parquet              Quarantine
```

## 11. Technology Choices

| Component          | Technology          | Purpose                          |
| ------------------ | ------------------- | -------------------------------- |
| Batch ingestion    | Python/Pandas       | Historical ingestion             |
| Streaming broker   | Redpanda            | Kafka-compatible event streaming |
| Streaming producer | Python/kafka-python | Event generation                 |
| Streaming consumer | Python/kafka-python | Event processing                 |
| Bronze storage     | Parquet             | Efficient columnar raw storage   |
| Containerization   | Docker              | Reproducible infrastructure      |

## 12. Step 2 Completion

The ingestion layer satisfies the project requirements for:

* batch ingestion
* streaming ingestion
* Bronze storage
* schema validation
* schema-drift handling
* quarantine
* idempotency
* replay
* safe offset processing
* failure recovery
