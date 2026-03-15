# OpenPond

> A lightweight data platform inspired by Databricks and Snowflake, powered by [SmallPond](https://github.com/deepseek-ai/smallpond) and [DuckDB](https://duckdb.org/).

[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](tests/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## Overview

**OpenPond** provides a developer-friendly data platform with concepts familiar from Databricks and Snowflake:

| OpenPond concept | Databricks equivalent | Snowflake equivalent |
|---|---|---|
| `DataPlatform` | Workspace | Account |
| Database | Catalog | Database |
| Schema | Schema | Schema |
| Table | Delta table | Table |
| `Catalog` | Unity Catalog | Information Schema |
| `Pipeline` | Delta Live Tables | Snowpark tasks |

Under the hood, data is stored as **Parquet files**, queries run on **DuckDB** via SmallPond, and distributed processing scales to PB-scale datasets through **Ray**.

---

## Installation

```bash
pip install openpond
```

Python 3.8–3.12 is supported.

---

## Quick Start

```python
import openpond
import pandas as pd

# 1. Initialize the platform (local mode)
platform = openpond.init()

# 2. Create a three-level namespace: database → schema → table
platform.create_database("analytics")
platform.create_schema("analytics", "sales")
platform.create_table("analytics", "sales", "orders")

# 3. Ingest data
data = pd.DataFrame({
    "order_id": [1, 2, 3],
    "amount": [100.0, 250.0, 75.0],
    "region": ["US", "EU", "US"],
})
platform.table("analytics", "sales", "orders").write(data)

# 4. Query with SQL
result = platform.sql(
    "SELECT region, sum(amount) AS total FROM {0} GROUP BY region ORDER BY total DESC",
    "analytics.sales.orders",
)
print(result.to_pandas())
#   region   total
# 0     US   175.0
# 1     EU   250.0

# 5. Clean up
platform.shutdown()
```

---

## Core Concepts

### DataPlatform

The single entry-point for all platform operations.

```python
platform = openpond.init(data_root="~/.openpond", num_executors=0)
```

| Parameter | Description |
|---|---|
| `data_root` | Directory for catalog metadata and data files (default `~/.openpond`) |
| `num_executors` | SmallPond / Ray workers (`0` = local mode) |
| `ray_address` | Connect to an existing Ray cluster |

### Catalog

Three-level namespace: **database** → **schema** → **table**.

```python
platform.create_database("finance")
platform.create_schema("finance", "market")
platform.create_table("finance", "market", "prices",
    columns=[
        openpond.ColumnInfo("ticker", "VARCHAR", nullable=False),
        openpond.ColumnInfo("close",  "DOUBLE"),
    ]
)

# Introspect
platform.list_databases()           # ["finance", ...]
platform.list_schemas("finance")    # ["market"]
platform.list_tables("finance", "market")  # ["prices"]

info = platform.catalog.get_table("finance", "market", "prices")
print(info.full_name)   # finance.market.prices
print(info.row_count)   # updated after each write
```

### Table

Read and write managed Parquet tables.

```python
tbl = platform.table("finance", "market", "prices")

# Read as SmallPond DataFrame (for distributed processing)
sp_df = tbl.read()

# Read as pandas
pdf = tbl.to_pandas()

# Write (pandas or SmallPond DataFrame)
tbl.write(my_dataframe)

# Table-scoped SQL
result = tbl.sql("SELECT ticker, max(close) FROM {table} GROUP BY ticker")
```

### Pipeline

Build multi-step ETL workflows with the fluent builder API.

```python
pipeline = (
    platform.pipeline("daily_etl")
    .add_step("extract",   lambda _: platform.read_parquet("/raw/orders/"))
    .add_step("transform", lambda df: platform.session.partial_sql(
        "SELECT *, amount * 1.1 AS amount_with_tax FROM {0}", df))
    .add_step("load",      lambda df: platform.table("dw", "fact", "orders").write(df))
)

result = pipeline.run()
print(result.success)            # True
print(result.total_duration_secs)
for step in result.steps:
    print(f"  {step.name}: {step.duration_secs:.2f}s, rows_out={step.rows_out}")
```

---

## CLI

```bash
# Manage databases and schemas
openpond create-database analytics
openpond create-schema analytics sales
openpond list-databases
openpond list-schemas analytics
openpond list-tables analytics sales

# Describe a table
openpond describe-table analytics sales orders

# Ingest data
openpond ingest --format parquet --src /data/orders/ analytics sales orders

# Run a SQL query
openpond query --table analytics.sales.orders \
    "SELECT region, sum(amount) FROM {0} GROUP BY region"
```

---

## Development

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest -v tests/
```

---

## License

MIT
