"""
DataPlatform — the main entry point for OpenPond.

Inspired by Databricks workspaces and Snowflake accounts: a single object
that provides catalog management, distributed query execution (via SmallPond),
and pipeline orchestration.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from openpond.catalog import Catalog, ColumnInfo, TableInfo
from openpond.pipeline import Pipeline
from openpond.table import Table


class PlatformError(Exception):
    """Raised when a platform-level operation fails."""


class DataPlatform:
    """
    The OpenPond data platform.

    A single workspace that combines:

    * A **catalog** for managing databases, schemas, and table metadata.
    * A **SmallPond session** for distributed data processing.
    * A **pipeline** factory for building ETL workflows.

    Parameters
    ----------
    data_root:
        Root directory for all platform data and catalog metadata.
        Defaults to ``~/.openpond``.
    num_executors:
        Number of SmallPond/Ray worker executors.  ``0`` runs everything
        locally (default).
    ray_address:
        Address of an existing Ray cluster.  ``None`` starts a local cluster.

    Example::

        import openpond

        platform = openpond.init()
        platform.create_database("analytics")
        platform.create_schema("analytics", "sales")
        platform.create_table("analytics", "sales", "orders", location="/data/orders/")

        # Load data
        df = platform.session.read_parquet("/data/raw/orders.parquet")
        platform.table("analytics", "sales", "orders").write(df)

        # Query
        result = platform.sql(
            "SELECT date, sum(amount) FROM {0} GROUP BY date",
            "analytics.sales.orders",
        )
        print(result.to_pandas())

        platform.shutdown()
    """

    def __init__(
        self,
        data_root: Optional[str] = None,
        num_executors: int = 0,
        ray_address: Optional[str] = None,
    ) -> None:
        self._data_root = data_root or os.path.join(
            os.path.expanduser("~"), ".openpond"
        )
        os.makedirs(self._data_root, exist_ok=True)

        catalog_root = os.path.join(self._data_root, "catalog")
        self._catalog = Catalog(catalog_root)

        self._session: Any = self._init_session(num_executors, ray_address)

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def _init_session(self, num_executors: int, ray_address: Optional[str]) -> Any:
        import smallpond

        data_dir = os.path.join(self._data_root, "smallpond")
        return smallpond.init(
            data_root=data_dir,
            num_executors=num_executors,
            ray_address=ray_address,
        )

    @property
    def session(self) -> Any:
        """The underlying SmallPond :class:`~smallpond.dataframe.Session`."""
        return self._session

    @property
    def catalog(self) -> Catalog:
        """The platform :class:`~openpond.catalog.Catalog`."""
        return self._catalog

    def shutdown(self) -> None:
        """Shut down the SmallPond / Ray cluster and release resources."""
        self._session.shutdown()

    def __enter__(self) -> "DataPlatform":
        return self

    def __exit__(self, *args: Any) -> None:
        self.shutdown()

    # ------------------------------------------------------------------
    # Database management (thin wrappers around Catalog)
    # ------------------------------------------------------------------

    def create_database(
        self,
        name: str,
        comment: str = "",
        properties: Optional[Dict[str, str]] = None,
        exist_ok: bool = True,
    ) -> None:
        """Create a database in the catalog."""
        self._catalog.create_database(
            name,
            location=os.path.join(self._data_root, "data", name),
            comment=comment,
            properties=properties,
            exist_ok=exist_ok,
        )

    def drop_database(self, name: str, cascade: bool = False) -> None:
        """Drop a database from the catalog."""
        self._catalog.drop_database(name, cascade=cascade)

    def list_databases(self) -> List[str]:
        """Return the names of all databases."""
        return [db.name for db in self._catalog.list_databases()]

    # ------------------------------------------------------------------
    # Schema management
    # ------------------------------------------------------------------

    def create_schema(
        self,
        database: str,
        name: str,
        comment: str = "",
        properties: Optional[Dict[str, str]] = None,
        exist_ok: bool = True,
    ) -> None:
        """Create a schema inside an existing database."""
        self._catalog.create_schema(
            database,
            name,
            comment=comment,
            properties=properties,
            exist_ok=exist_ok,
        )

    def drop_schema(
        self, database: str, name: str, cascade: bool = False
    ) -> None:
        """Drop a schema from the catalog."""
        self._catalog.drop_schema(database, name, cascade=cascade)

    def list_schemas(self, database: str) -> List[str]:
        """Return the names of all schemas in a database."""
        return [s.name for s in self._catalog.list_schemas(database)]

    # ------------------------------------------------------------------
    # Table management
    # ------------------------------------------------------------------

    def create_table(
        self,
        database: str,
        schema: str,
        name: str,
        columns: Optional[List[ColumnInfo]] = None,
        location: Optional[str] = None,
        format: str = "parquet",
        comment: str = "",
        properties: Optional[Dict[str, str]] = None,
        replace: bool = False,
    ) -> Table:
        """
        Register a new table in the catalog and return a :class:`Table` handle.

        Parameters
        ----------
        database, schema, name:
            Three-level table identifier (``database.schema.name``).
        columns:
            Optional list of :class:`~openpond.catalog.ColumnInfo` objects.
        location:
            Storage path for the table's data files.  Defaults to
            ``<data_root>/data/<database>/<schema>/<name>/``.
        format:
            Data file format.  ``"parquet"`` (default), ``"csv"``, or ``"json"``.
        replace:
            If ``True``, overwrite any existing catalog entry.
        """
        if location is None:
            location = os.path.join(
                self._data_root, "data", database, schema, name
            )
        os.makedirs(location, exist_ok=True)
        info = TableInfo(
            database=database,
            schema=schema,
            name=name,
            location=location,
            format=format,
            columns=columns or [],
            comment=comment,
            properties=properties or {},
        )
        self._catalog.register_table(info, replace=replace)
        return Table(self._catalog, self._session, database, schema, name)

    def table(self, database: str, schema: str, name: str) -> Table:
        """
        Return a :class:`Table` handle for an existing catalog entry.

        Raises :class:`~openpond.catalog.CatalogError` if the table does not exist.
        """
        # Validate existence
        self._catalog.get_table(database, schema, name)
        return Table(self._catalog, self._session, database, schema, name)

    def drop_table(self, database: str, schema: str, name: str) -> None:
        """Remove a table from the catalog (data files are not deleted)."""
        self._catalog.drop_table(database, schema, name)

    def list_tables(self, database: str, schema: str) -> List[str]:
        """Return the names of all tables in a schema."""
        return [t.name for t in self._catalog.list_tables(database, schema)]

    # ------------------------------------------------------------------
    # SQL
    # ------------------------------------------------------------------

    def sql(self, query: str, *table_refs: str) -> Any:
        """
        Execute a SQL query against one or more catalog tables.

        Table references are passed as positional arguments and substituted
        as ``{0}``, ``{1}``, … in the query template, following SmallPond
        conventions.

        Example::

            result = platform.sql(
                "SELECT ticker, max(price) FROM {0} GROUP BY ticker",
                "finance.market.prices",
            )
            print(result.to_pandas())
        """
        dfs = []
        for ref in table_refs:
            parts = ref.split(".")
            if len(parts) != 3:
                raise PlatformError(
                    f"Table reference must be 'database.schema.table', got '{ref}'."
                )
            tbl = self.table(*parts)
            dfs.append(tbl.read())
        return self._session.partial_sql(query, *dfs)

    # ------------------------------------------------------------------
    # Pipelines
    # ------------------------------------------------------------------

    def pipeline(self, name: str, description: str = "") -> Pipeline:
        """Create a new :class:`~openpond.pipeline.Pipeline` instance."""
        return Pipeline(name=name, description=description)

    # ------------------------------------------------------------------
    # Data loading helpers (mirrors Databricks read API)
    # ------------------------------------------------------------------

    def read_parquet(
        self,
        paths,
        recursive: bool = False,
        columns=None,
    ) -> Any:
        """Load Parquet files as a SmallPond DataFrame."""
        return self._session.read_parquet(
            paths, recursive=recursive, columns=columns
        )

    def read_csv(self, paths, schema: Dict[str, str], delim: str = ",") -> Any:
        """Load CSV files as a SmallPond DataFrame."""
        return self._session.read_csv(paths, schema, delim=delim)

    def read_json(self, paths, schema: Dict[str, str]) -> Any:
        """Load JSON files as a SmallPond DataFrame."""
        return self._session.read_json(paths, schema)

    def from_pandas(self, df) -> Any:
        """Create a SmallPond DataFrame from a pandas DataFrame."""
        return self._session.from_pandas(df)

    def from_items(self, items: list) -> Any:
        """Create a SmallPond DataFrame from a list of dicts or values."""
        return self._session.from_items(items)
