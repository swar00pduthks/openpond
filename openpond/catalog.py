"""
Data catalog for OpenPond - manages metadata for databases, schemas, and tables.
Inspired by Databricks Unity Catalog and Snowflake Information Schema.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class ColumnInfo:
    """Metadata for a table column."""

    name: str
    dtype: str
    nullable: bool = True
    comment: str = ""


@dataclass
class TableInfo:
    """Metadata for a table in the catalog."""

    database: str
    schema: str
    name: str
    location: str
    format: str = "parquet"
    columns: List[ColumnInfo] = field(default_factory=list)
    row_count: Optional[int] = None
    size_bytes: Optional[int] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    comment: str = ""
    properties: Dict[str, str] = field(default_factory=dict)

    @property
    def full_name(self) -> str:
        return f"{self.database}.{self.schema}.{self.name}"


@dataclass
class SchemaInfo:
    """Metadata for a schema (namespace) in the catalog."""

    database: str
    name: str
    location: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    comment: str = ""
    properties: Dict[str, str] = field(default_factory=dict)

    @property
    def full_name(self) -> str:
        return f"{self.database}.{self.name}"


@dataclass
class DatabaseInfo:
    """Metadata for a database in the catalog."""

    name: str
    location: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    comment: str = ""
    properties: Dict[str, str] = field(default_factory=dict)


class CatalogError(Exception):
    """Raised when a catalog operation fails."""


class Catalog:
    """
    A data catalog that manages metadata for databases, schemas, and tables.

    Modeled after Databricks Unity Catalog and Snowflake Information Schema.
    Metadata is persisted as JSON files under ``catalog_root``.

    Example::

        catalog = Catalog("/path/to/catalog")
        catalog.create_database("analytics")
        catalog.create_schema("analytics", "sales")
        catalog.register_table(TableInfo(
            database="analytics", schema="sales", name="orders",
            location="/data/orders/", format="parquet",
        ))
        tables = catalog.list_tables("analytics", "sales")
    """

    _CATALOG_FILE = "catalog.json"

    def __init__(self, catalog_root: str) -> None:
        self._root = catalog_root
        os.makedirs(catalog_root, exist_ok=True)
        self._catalog_path = os.path.join(catalog_root, self._CATALOG_FILE)
        self._data: Dict = self._load()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _load(self) -> Dict:
        if os.path.exists(self._catalog_path):
            with open(self._catalog_path) as fh:
                return json.load(fh)
        return {"databases": {}}

    def _save(self) -> None:
        with open(self._catalog_path, "w") as fh:
            json.dump(self._data, fh, indent=2)

    # ------------------------------------------------------------------
    # Database operations
    # ------------------------------------------------------------------

    def create_database(
        self,
        name: str,
        location: str = "",
        comment: str = "",
        properties: Optional[Dict[str, str]] = None,
        exist_ok: bool = False,
    ) -> DatabaseInfo:
        """Create a new database in the catalog."""
        if name in self._data["databases"]:
            if exist_ok:
                return self.get_database(name)
            raise CatalogError(f"Database '{name}' already exists.")
        db_location = location or os.path.join(self._root, name)
        os.makedirs(db_location, exist_ok=True)
        info = DatabaseInfo(
            name=name,
            location=db_location,
            comment=comment,
            properties=properties or {},
        )
        self._data["databases"][name] = {"info": asdict(info), "schemas": {}}
        self._save()
        return info

    def get_database(self, name: str) -> DatabaseInfo:
        """Return metadata for a database."""
        self._require_database(name)
        return DatabaseInfo(**self._data["databases"][name]["info"])

    def drop_database(self, name: str, cascade: bool = False) -> None:
        """Drop a database from the catalog."""
        self._require_database(name)
        schemas = self._data["databases"][name]["schemas"]
        if schemas and not cascade:
            raise CatalogError(
                f"Database '{name}' is not empty. Use cascade=True to drop it."
            )
        del self._data["databases"][name]
        self._save()

    def list_databases(self) -> List[DatabaseInfo]:
        """List all databases."""
        return [DatabaseInfo(**v["info"]) for v in self._data["databases"].values()]

    def database_exists(self, name: str) -> bool:
        return name in self._data["databases"]

    # ------------------------------------------------------------------
    # Schema operations
    # ------------------------------------------------------------------

    def create_schema(
        self,
        database: str,
        name: str,
        location: str = "",
        comment: str = "",
        properties: Optional[Dict[str, str]] = None,
        exist_ok: bool = False,
    ) -> SchemaInfo:
        """Create a new schema inside a database."""
        self._require_database(database)
        schemas = self._data["databases"][database]["schemas"]
        if name in schemas:
            if exist_ok:
                return self.get_schema(database, name)
            raise CatalogError(
                f"Schema '{database}.{name}' already exists."
            )
        db_location = self._data["databases"][database]["info"]["location"]
        schema_location = location or os.path.join(db_location, name)
        os.makedirs(schema_location, exist_ok=True)
        info = SchemaInfo(
            database=database,
            name=name,
            location=schema_location,
            comment=comment,
            properties=properties or {},
        )
        schemas[name] = {"info": asdict(info), "tables": {}}
        self._save()
        return info

    def get_schema(self, database: str, name: str) -> SchemaInfo:
        """Return metadata for a schema."""
        self._require_schema(database, name)
        return SchemaInfo(**self._data["databases"][database]["schemas"][name]["info"])

    def drop_schema(
        self, database: str, name: str, cascade: bool = False
    ) -> None:
        """Drop a schema from the catalog."""
        self._require_schema(database, name)
        tables = self._data["databases"][database]["schemas"][name]["tables"]
        if tables and not cascade:
            raise CatalogError(
                f"Schema '{database}.{name}' is not empty. Use cascade=True."
            )
        del self._data["databases"][database]["schemas"][name]
        self._save()

    def list_schemas(self, database: str) -> List[SchemaInfo]:
        """List all schemas in a database."""
        self._require_database(database)
        return [
            SchemaInfo(**v["info"])
            for v in self._data["databases"][database]["schemas"].values()
        ]

    def schema_exists(self, database: str, name: str) -> bool:
        return (
            database in self._data["databases"]
            and name in self._data["databases"][database]["schemas"]
        )

    # ------------------------------------------------------------------
    # Table operations
    # ------------------------------------------------------------------

    def register_table(self, info: TableInfo, replace: bool = False) -> TableInfo:
        """Register a table in the catalog."""
        self._require_schema(info.database, info.schema)
        tables = self._data["databases"][info.database]["schemas"][info.schema]["tables"]
        if info.name in tables and not replace:
            raise CatalogError(
                f"Table '{info.full_name}' already exists. Use replace=True."
            )
        info.updated_at = datetime.now(timezone.utc).isoformat()
        tables[info.name] = asdict(info)
        self._save()
        return info

    def get_table(self, database: str, schema: str, name: str) -> TableInfo:
        """Return metadata for a table."""
        self._require_table(database, schema, name)
        raw = self._data["databases"][database]["schemas"][schema]["tables"][name]
        columns = [ColumnInfo(**c) for c in raw.pop("columns", [])]
        info = TableInfo(**raw, columns=columns)
        return info

    def update_table_stats(
        self,
        database: str,
        schema: str,
        name: str,
        row_count: Optional[int] = None,
        size_bytes: Optional[int] = None,
    ) -> None:
        """Update statistics for a registered table."""
        self._require_table(database, schema, name)
        entry = self._data["databases"][database]["schemas"][schema]["tables"][name]
        if row_count is not None:
            entry["row_count"] = row_count
        if size_bytes is not None:
            entry["size_bytes"] = size_bytes
        entry["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save()

    def drop_table(self, database: str, schema: str, name: str) -> None:
        """Remove a table from the catalog."""
        self._require_table(database, schema, name)
        del self._data["databases"][database]["schemas"][schema]["tables"][name]
        self._save()

    def list_tables(self, database: str, schema: str) -> List[TableInfo]:
        """List all tables in a schema."""
        self._require_schema(database, schema)
        result = []
        for raw in (
            self._data["databases"][database]["schemas"][schema]["tables"].values()
        ):
            raw = dict(raw)
            columns = [ColumnInfo(**c) for c in raw.pop("columns", [])]
            result.append(TableInfo(**raw, columns=columns))
        return result

    def table_exists(self, database: str, schema: str, name: str) -> bool:
        return (
            self.schema_exists(database, schema)
            and name
            in self._data["databases"][database]["schemas"][schema]["tables"]
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_database(self, name: str) -> None:
        if name not in self._data["databases"]:
            raise CatalogError(f"Database '{name}' does not exist.")

    def _require_schema(self, database: str, schema: str) -> None:
        self._require_database(database)
        if schema not in self._data["databases"][database]["schemas"]:
            raise CatalogError(f"Schema '{database}.{schema}' does not exist.")

    def _require_table(self, database: str, schema: str, name: str) -> None:
        self._require_schema(database, schema)
        if (
            name
            not in self._data["databases"][database]["schemas"][schema]["tables"]
        ):
            raise CatalogError(
                f"Table '{database}.{schema}.{name}' does not exist."
            )
