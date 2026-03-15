"""
Command-line interface for OpenPond.

Usage::

    openpond --help
    openpond list-databases
    openpond list-schemas <database>
    openpond list-tables <database> <schema>
    openpond describe-table <database> <schema> <table>
    openpond create-database <name>
    openpond create-schema <database> <schema>
    openpond ingest --format parquet --src /path/to/data \\
                    <database> <schema> <table>
    openpond query --table <database.schema.table> "<SQL>"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
from typing import List, Optional


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openpond",
        description="OpenPond data platform CLI — powered by SmallPond.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--data-root",
        default=None,
        metavar="PATH",
        help="Platform data root (default: ~/.openpond).",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ------------------------------------------------------------------ #
    # list-databases
    # ------------------------------------------------------------------ #
    sub.add_parser("list-databases", help="List all databases.")

    # ------------------------------------------------------------------ #
    # list-schemas
    # ------------------------------------------------------------------ #
    p = sub.add_parser("list-schemas", help="List schemas in a database.")
    p.add_argument("database")

    # ------------------------------------------------------------------ #
    # list-tables
    # ------------------------------------------------------------------ #
    p = sub.add_parser("list-tables", help="List tables in a schema.")
    p.add_argument("database")
    p.add_argument("schema")

    # ------------------------------------------------------------------ #
    # describe-table
    # ------------------------------------------------------------------ #
    p = sub.add_parser("describe-table", help="Show table metadata.")
    p.add_argument("database")
    p.add_argument("schema")
    p.add_argument("table")

    # ------------------------------------------------------------------ #
    # create-database
    # ------------------------------------------------------------------ #
    p = sub.add_parser("create-database", help="Create a new database.")
    p.add_argument("name")
    p.add_argument("--comment", default="")

    # ------------------------------------------------------------------ #
    # drop-database
    # ------------------------------------------------------------------ #
    p = sub.add_parser("drop-database", help="Drop a database.")
    p.add_argument("name")
    p.add_argument(
        "--cascade", action="store_true", help="Drop all schemas/tables too."
    )

    # ------------------------------------------------------------------ #
    # create-schema
    # ------------------------------------------------------------------ #
    p = sub.add_parser("create-schema", help="Create a new schema.")
    p.add_argument("database")
    p.add_argument("schema")
    p.add_argument("--comment", default="")

    # ------------------------------------------------------------------ #
    # drop-schema
    # ------------------------------------------------------------------ #
    p = sub.add_parser("drop-schema", help="Drop a schema.")
    p.add_argument("database")
    p.add_argument("schema")
    p.add_argument("--cascade", action="store_true")

    # ------------------------------------------------------------------ #
    # ingest
    # ------------------------------------------------------------------ #
    p = sub.add_parser(
        "ingest",
        help="Ingest data files into a table.",
        description=textwrap.dedent(
            """\
            Load data from FILES into a catalog table.

            Example:
              openpond ingest --format parquet --src /data/orders/ \\
                              analytics sales orders
            """
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("database")
    p.add_argument("schema")
    p.add_argument("table")
    p.add_argument("--src", required=True, metavar="PATH", help="Source data path.")
    p.add_argument(
        "--format",
        default="parquet",
        choices=["parquet", "csv", "json"],
        help="Source file format (default: parquet).",
    )
    p.add_argument(
        "--schema-json",
        metavar="JSON",
        default=None,
        help='Column schema as JSON, e.g. \'{"id":"INTEGER","name":"VARCHAR"}\'.',
    )
    p.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing table definition.",
    )

    # ------------------------------------------------------------------ #
    # query
    # ------------------------------------------------------------------ #
    p = sub.add_parser("query", help="Run a SQL query against catalog tables.")
    p.add_argument("sql", metavar="SQL", help="SQL query template.")
    p.add_argument(
        "--table",
        metavar="DB.SCHEMA.TABLE",
        dest="tables",
        action="append",
        default=[],
        help=(
            "Table reference substituted as {0}, {1}, … in the SQL template. "
            "Can be specified multiple times."
        ),
    )

    return parser


def _get_platform(data_root: Optional[str]):
    from openpond.platform import DataPlatform

    return DataPlatform(data_root=data_root, num_executors=0)


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    cmd = args.command

    # Commands that only need the catalog (no SmallPond session)
    catalog_only_commands = {
        "list-databases",
        "list-schemas",
        "list-tables",
        "describe-table",
        "create-database",
        "drop-database",
        "create-schema",
        "drop-schema",
    }

    if cmd in catalog_only_commands:
        from openpond.catalog import Catalog

        data_root = args.data_root or os.path.join(os.path.expanduser("~"), ".openpond")
        catalog = Catalog(os.path.join(data_root, "catalog"))

        if cmd == "list-databases":
            dbs = catalog.list_databases()
            if not dbs:
                print("(no databases)")
            for db in dbs:
                print(db.name)

        elif cmd == "list-schemas":
            schemas = catalog.list_schemas(args.database)
            if not schemas:
                print(f"(no schemas in '{args.database}')")
            for s in schemas:
                print(s.name)

        elif cmd == "list-tables":
            tables = catalog.list_tables(args.database, args.schema)
            if not tables:
                print(f"(no tables in '{args.database}.{args.schema}')")
            for t in tables:
                print(t.name)

        elif cmd == "describe-table":
            info = catalog.get_table(args.database, args.schema, args.table)
            print(f"Table:    {info.full_name}")
            print(f"Format:   {info.format}")
            print(f"Location: {info.location}")
            print(f"Rows:     {info.row_count}")
            print(f"Bytes:    {info.size_bytes}")
            print(f"Created:  {info.created_at}")
            print(f"Updated:  {info.updated_at}")
            if info.comment:
                print(f"Comment:  {info.comment}")
            if info.columns:
                print("Columns:")
                for col in info.columns:
                    nullable = "NULL" if col.nullable else "NOT NULL"
                    print(f"  {col.name:<24} {col.dtype:<16} {nullable}")
            if info.properties:
                print("Properties:")
                for k, v in info.properties.items():
                    print(f"  {k} = {v}")

        elif cmd == "create-database":
            catalog.create_database(
                args.name,
                location=os.path.join(data_root, "data", args.name),
                comment=args.comment,
                exist_ok=True,
            )
            print(f"Database '{args.name}' created.")

        elif cmd == "drop-database":
            catalog.drop_database(args.name, cascade=args.cascade)
            print(f"Database '{args.name}' dropped.")

        elif cmd == "create-schema":
            catalog.create_schema(
                args.database, args.schema, comment=args.comment, exist_ok=True
            )
            print(f"Schema '{args.database}.{args.schema}' created.")

        elif cmd == "drop-schema":
            catalog.drop_schema(
                args.database, args.schema, cascade=args.cascade
            )
            print(f"Schema '{args.database}.{args.schema}' dropped.")

        return 0

    # Commands that require a full SmallPond platform
    platform = _get_platform(args.data_root)
    try:
        if cmd == "ingest":
            col_schema = None
            if args.schema_json:
                from openpond.catalog import ColumnInfo

                raw = json.loads(args.schema_json)
                col_schema = [ColumnInfo(name=k, dtype=v) for k, v in raw.items()]

            tbl = platform.create_table(
                args.database,
                args.schema,
                args.table,
                columns=col_schema,
                location=None,
                format=args.format,
                replace=args.replace,
            )

            if args.format == "parquet":
                df = platform.read_parquet(args.src, recursive=True)
            elif args.format == "csv":
                if not col_schema:
                    print("--schema-json is required for CSV ingestion.", file=sys.stderr)
                    return 1
                schema_dict = {c.name: c.dtype for c in col_schema}
                df = platform.read_csv(args.src, schema=schema_dict)
            else:
                if not col_schema:
                    print("--schema-json is required for JSON ingestion.", file=sys.stderr)
                    return 1
                schema_dict = {c.name: c.dtype for c in col_schema}
                df = platform.read_json(args.src, schema=schema_dict)

            tbl.write(df)
            info = tbl.info
            print(
                f"Ingested '{args.src}' → {info.full_name} "
                f"({info.row_count} rows, {info.size_bytes} bytes)."
            )

        elif cmd == "query":
            result = platform.sql(args.sql, *args.tables)
            pdf = result.to_pandas()
            print(pdf.to_string(index=False))

    finally:
        platform.shutdown()

    return 0


if __name__ == "__main__":
    sys.exit(main())
