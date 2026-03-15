"""
OpenPond — a data platform inspired by Databricks/Snowflake, powered by SmallPond.
"""

from openpond.catalog import Catalog, CatalogError, ColumnInfo, DatabaseInfo, SchemaInfo, TableInfo
from openpond.pipeline import Pipeline, PipelineError, PipelineResult, Step, StepResult
from openpond.platform import DataPlatform, PlatformError
from openpond.table import Table, TableError

__all__ = [
    # Platform
    "DataPlatform",
    "PlatformError",
    "init",
    # Catalog
    "Catalog",
    "CatalogError",
    "ColumnInfo",
    "DatabaseInfo",
    "SchemaInfo",
    "TableInfo",
    # Table
    "Table",
    "TableError",
    # Pipeline
    "Pipeline",
    "PipelineError",
    "PipelineResult",
    "Step",
    "StepResult",
]


def init(
    data_root=None,
    num_executors: int = 0,
    ray_address=None,
) -> DataPlatform:
    """
    Initialize an OpenPond :class:`DataPlatform`.

    This is the primary entry point for the OpenPond library, mirroring the
    ``smallpond.init()`` pattern.

    Parameters
    ----------
    data_root:
        Root directory for catalog metadata and data files.
        Defaults to ``~/.openpond``.
    num_executors:
        Number of SmallPond / Ray worker executors (``0`` = local mode).
    ray_address:
        Address of an existing Ray cluster (``None`` = start a local cluster).

    Returns
    -------
    DataPlatform

    Example::

        import openpond

        platform = openpond.init()
        platform.create_database("analytics")
        platform.create_schema("analytics", "sales")
        platform.shutdown()
    """
    return DataPlatform(
        data_root=data_root,
        num_executors=num_executors,
        ray_address=ray_address,
    )
