# NorthStar Retail — Storage Design

## 1. Overview

NorthStar Retail uses a lakehouse-style storage architecture built around:

- Parquet for analytical data storage
- MinIO/S3-compatible object storage as the target storage architecture
- DuckDB as the local analytical query engine
- Bronze/Silver/Gold data layers
- date-based partitioning for ingestion-oriented Bronze data

The design prioritizes reproducibility, analytical performance, recoverability, and compatibility with local and cloud environments.

---

## 2. Storage Layers

### Bronze

Bronze contains source-faithful data with minimal transformation.

Historical Olist datasets are stored as Parquet under:

```text
data/bronze/olist/
```

The streaming Bronze layer is partitioned by ingestion date and hour:

```text
data/bronze/streaming/
└── ingestion_date=YYYY-MM-DD/
    └── ingestion_hour=HH/
        └── events.parquet
```

Bronze records retain ingestion metadata including:

- `_ingestion_timestamp`
- `_source_file`
- `_batch_id`
- `_source` for streaming events

This supports traceability and replay.

### Silver

Silver contains cleaned and conformed datasets.

The historical Silver datasets are organized by entity:

```text
data/silver/
├── customers/
├── sellers/
├── products/
├── orders/
├── order_items/
├── order_payments/
├── order_reviews/
├── geolocation/
└── order_events/
```

Silver processing performs:

- data type standardization
- string normalization
- deduplication
- timestamp normalization
- required-field validation
- referential-integrity validation
- event schema validation

Silver data is stored in Parquet format.

### Gold

Gold contains business-ready analytical datasets.

```text
data/gold/
├── dimensions/
│   ├── dim_customer.parquet
│   ├── dim_product.parquet
│   ├── dim_seller.parquet
│   ├── dim_geography.parquet
│   └── dim_date.parquet
│
└── facts/
    ├── fact_orders.parquet
    ├── fact_order_items.parquet
    └── fact_payments.parquet
```

Gold data is materialized because it contains dimensional transformations and business logic intended for repeated analytical use.

---

## 3. File Format

### Parquet

Parquet is the primary analytical storage format.

It was selected because it provides:

- **Columnar storage**: Analytical queries frequently access a subset of columns. Columnar storage avoids scanning unnecessary fields.
- **Compression**: Parquet provides efficient compression, reducing local and object-storage footprint.
- **Analytical performance**: DuckDB can query Parquet directly without requiring the data to be imported into a traditional database.
- **Interoperability**: Parquet is supported by DuckDB, Apache Spark, Python/Pandas, Polars, cloud data platforms, and BI and analytics ecosystems.

### Cloud compatibility

The same Parquet datasets can be stored locally in MinIO or remotely in Amazon S3 without changing the logical data model.

---

## 4. Partitioning Strategy

Partitioning is applied where it provides a clear operational benefit.

### Bronze streaming

Streaming Bronze data is partitioned by `ingestion_date` and `ingestion_hour`.

Example:

```text
ingestion_date=2026-09-30/
    ingestion_hour=15/
        events.parquet
```

This provides several benefits:

- efficient retrieval by ingestion time
- isolation of streaming batches
- easier replay and troubleshooting
- easier operational retention
- natural alignment with streaming processing windows

### Historical Bronze

Historical Olist data is partitioned by `ingestion_date`.

Example:

```text
orders/
└── ingestion_date=2026-09-28/
    └── data.parquet
```

The ingestion date represents when the dataset entered the platform rather than the business event date.

This distinction preserves the difference between:

- source/business timestamps
- platform ingestion timestamps

### Silver

The current project uses entity-level organization for Silver:

```text
data/silver/orders/
data/silver/customers/
data/silver/products/
```

The historical datasets are relatively small, so additional physical partitioning is not necessary at this stage.

Over-partitioning small datasets would create many small files and increase metadata and file-management overhead.

### Gold

Gold tables are currently stored as single Parquet files per table.

For the current project scale, this is intentional.

The largest Gold fact table contains approximately 112,650 rows, which is small for an analytical engine such as DuckDB.

Additional partitioning would introduce unnecessary complexity without providing a meaningful performance benefit at this scale.

---

## 5. Small File Considerations

Excessive partitioning can create many small Parquet files.

Small files can negatively affect:

- metadata operations
- file-open overhead
- query planning
- object-storage requests
- maintenance complexity

Therefore, NorthStar avoids partitioning solely for the sake of partitioning.

Partitioning is used when it aligns with an operational access pattern, particularly streaming ingestion.

---

## 6. Compaction Strategy

Compaction is the process of combining small files into larger files.

### Streaming Bronze

Streaming ingestion can naturally generate multiple small files because data arrives continuously.

A production implementation would periodically compact files within an ingestion partition.

Before:

```text
ingestion_date=2026-09-30/
├── ingestion_hour=15/
│   ├── part-001.parquet
│   ├── part-002.parquet
│   └── part-003.parquet
└── ingestion_hour=16/
    ├── part-001.parquet
    └── part-002.parquet
```

After compaction:

```text
ingestion_date=2026-09-30/
├── ingestion_hour=15/
│   └── events.parquet
└── ingestion_hour=16/
    └── events.parquet
```

The current implementation already consolidates processed streaming events into partition-level Parquet output.

### Silver

Silver transformations currently produce one consolidated Parquet file per entity.

At the current dataset scale, further compaction is unnecessary.

If the platform grows substantially, Silver files can be compacted based on:

- file size
- partition size
- ingestion frequency
- query workload

### Gold

Gold tables are materialized as consolidated Parquet files.

Because the current Gold tables are relatively small, no additional compaction process is required.

---

## 7. Target File Size

In a larger production deployment, the platform would target reasonably sized Parquet files rather than extremely small files.

A practical target range is approximately: **128 MB – 512 MB per Parquet file**.

The exact target would depend on:

- query patterns
- storage platform
- ingestion frequency
- table growth
- number of concurrent analytical queries

The target is a guideline rather than a rigid requirement.

---

## 8. DuckDB Storage Architecture

DuckDB serves as the local analytical engine.

The architecture separates:

```text
Persistent analytical storage
        │
        ▼
     Parquet
        │
        ▼
      DuckDB
        │
        ▼
   SQL analytics
```

DuckDB can query Silver Parquet files directly. This avoids unnecessarily duplicating Silver data inside the DuckDB database.

Gold tables are materialized in DuckDB because they contain reusable business transformations.

The DuckDB database is stored at: `data/northstar.duckdb`

---

## 9. Local and Production Storage

### Local development

The project uses local filesystem storage and MinIO-compatible architecture.

```text
Local filesystem
      │
      ├── Bronze
      ├── Silver
      └── Gold
```

MinIO is used as the local S3-compatible object-storage option for the broader platform architecture.

### Production

The same logical architecture can migrate to Amazon S3:

```text
AWS S3
  │
  ├── Bronze
  ├── Silver
  └── Gold
```

Because the analytical datasets use Parquet and the storage architecture follows object-storage conventions, the transition does not require redesigning the data model.

---

## 10. Storage Design Trade-offs

| Decision | Benefit | Trade-off |
|---|---|---|
| **Parquet** | Efficient analytical storage | Less convenient for frequent row-level updates |
| **Date partitioning** | Efficient time-based access | Too many partitions can create small files |
| **Single Gold files** | Simple and efficient at current scale | Requires repartitioning as data grows |
| **DuckDB** | Fast, lightweight local analytics | Not intended to replace a distributed warehouse at very large scale |
| **MinIO** | Local S3-compatible development | Additional infrastructure compared with filesystem-only storage |
| **S3-compatible design** | Easy cloud migration | Object storage introduces network/storage-management considerations |

---

## 11. Scaling Strategy

As NorthStar grows, the storage strategy can evolve without changing the logical Bronze/Silver/Gold architecture.

Potential scaling changes include:

- Increase Bronze partition granularity when ingestion volume requires it.
- Introduce automated compaction for streaming partitions.
- Partition large Silver and Gold fact tables by business date.
- Introduce a table format such as Apache Iceberg if ACID table operations, schema evolution, and large-scale concurrent workloads become necessary.
- Move object storage from local MinIO to Amazon S3.
- Use a distributed analytical engine if DuckDB becomes insufficient for workload size or concurrency.

These technologies are deliberately not introduced at the current project scale because they would add complexity without providing a demonstrated requirement.

---

## 12. Storage Design Conclusion

The NorthStar storage design uses:

```text
Bronze
  │
  │ Parquet
  │ date/time partitioning where useful
  ▼
Silver
  │
  │ Parquet
  │ entity-oriented organization
  ▼
Gold
  │
  │ DuckDB + Parquet
  ▼
Analytics / BI
```

The design balances analytical performance, reproducibility, simplicity, and scalability.

Partitioning is applied where it provides an operational benefit, while avoiding unnecessary partitions for relatively small datasets.

Parquet provides the common storage format across the analytical layers, while DuckDB provides the local SQL analytical engine.