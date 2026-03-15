"""
Table abstraction for OpenPond.  Wraps SmallPond DataFrames with catalog-aware
read/write helpers, SQL support, and schema introspection.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import pandas as pd

if TYPE_CHECKING:
    import smallpond
    from openpond.catalog import Catalog, ColumnInfo, TableInfo


class TableError(Exception):
    """Raised when a table operation fails."""


class Table:
    """
    A managed table in the OpenPond platform.

    Backed by Parquet files on local storage (or any path-accessible store).
    Metadata is tracked in the :class:`~openpond.catalog.Catalog`.

    Example::

        table = platform.table("analytics", "sales", "orders")
        df = table.read()
        table.write(df)
        print(table.schema())
    """

    def __init__(
        self,
        catalog: "Catalog",
        session: Any,
        database: str,
        schema: str,
        name: str,
    ) -> None:
        self._catalog = catalog
        self._session = session
        self._database = database
        self._schema = schema
        self._name = name

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def full_name(self) -> str:
        return f"{self._database}.{self._schema}.{self._name}"

    @property
    def info(self) -> "TableInfo":
        return self._catalog.get_table(self._database, self._schema, self._name)

    @property
    def location(self) -> str:
        return self.info.location

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def read(
        self,
        columns: Optional[List[str]] = None,
    ) -> Any:
        """
        Read the table as a SmallPond DataFrame.

        Parameters
        ----------
        columns:
            Optional list of columns to project.
        """
        info = self.info
        if not os.path.exists(info.location):
            raise TableError(
                f"Table location '{info.location}' does not exist."
            )
        parquets = self._find_parquet_files(info.location)
        if not parquets:
            raise TableError(
                f"No parquet files found in '{info.location}'. "
                "Write data to the table first."
            )
        if info.format == "parquet":
            return self._session.read_parquet(parquets, columns=columns)
        if info.format == "csv":
            schema = {c.name: c.dtype for c in info.columns}
            return self._session.read_csv(info.location, schema=schema)
        if info.format == "json":
            schema = {c.name: c.dtype for c in info.columns}
            return self._session.read_json(info.location, schema=schema)
        raise TableError(f"Unsupported table format: '{info.format}'")

    def to_pandas(self, columns: Optional[List[str]] = None) -> pd.DataFrame:
        """Read the table into a pandas DataFrame."""
        info = self.info
        if not os.path.exists(info.location):
            raise TableError(
                f"Table location '{info.location}' does not exist."
            )
        parquets = self._find_parquet_files(info.location)
        if not parquets:
            raise TableError(
                f"No parquet files found in '{info.location}'."
            )
        import pyarrow.parquet as pq

        arrow_table = pq.read_table(parquets, columns=columns)
        return arrow_table.to_pandas()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def write(self, df: Any, mode: str = "overwrite") -> "Table":
        """
        Write a SmallPond DataFrame to the table's storage location.

        The DataFrame is materialised via pandas/PyArrow and persisted as
        Parquet files under the table's ``location`` directory, making the
        data immediately readable by DuckDB and SmallPond alike.

        Parameters
        ----------
        df:
            A SmallPond ``DataFrame`` (or pandas ``DataFrame``) to write.
        mode:
            Write mode.  ``"overwrite"`` replaces existing data (default).
            ``"append"`` is not yet supported.
        """
        info = self.info
        if mode not in ("overwrite",):
            raise TableError(f"Unsupported write mode: '{mode}'. Use 'overwrite'.")
        os.makedirs(info.location, exist_ok=True)

        # Collect the data locally and write with pyarrow for portability.
        import pyarrow as pa
        import pyarrow.parquet as pq

        if isinstance(df, pd.DataFrame):
            arrow_table = pa.Table.from_pandas(df)
        else:
            # SmallPond DataFrame -> pyarrow Table
            arrow_table = df.to_arrow()

        # Remove previous data files before overwriting.
        for fn in os.listdir(info.location):
            if fn.endswith(".parquet"):
                os.remove(os.path.join(info.location, fn))

        out_file = os.path.join(info.location, "data.parquet")
        pq.write_table(arrow_table, out_file)

        # Update statistics
        row_count = len(arrow_table)
        size_bytes = os.path.getsize(out_file)
        self._catalog.update_table_stats(
            self._database, self._schema, self._name,
            row_count=row_count, size_bytes=size_bytes,
        )
        return self

    # ------------------------------------------------------------------
    # SQL
    # ------------------------------------------------------------------

    def sql(self, query: str) -> Any:
        """
        Run a SQL query against this table and return a SmallPond DataFrame.

        The table is referenced as ``{table}`` in the query template.

        Example::

            df = table.sql("SELECT id, amount FROM {table} WHERE amount > 100")
        """
        df = self.read()
        query = query.replace("{table}", "{0}")
        return self._session.partial_sql(query, df)

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def schema(self) -> List["ColumnInfo"]:
        """Return the column schema of the table."""
        return self.info.columns

    def count(self) -> int:
        """Return the number of rows in the table."""
        info = self.info
        if info.row_count is not None:
            return info.row_count
        return self.read().count()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_parquet_files(location: str) -> List[str]:
        """Return sorted list of .parquet files in ``location``."""
        result = []
        for fn in sorted(os.listdir(location)):
            if fn.endswith(".parquet"):
                result.append(os.path.join(location, fn))
        return result
