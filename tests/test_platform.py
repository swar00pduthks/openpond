"""
Integration tests for DataPlatform and Table.

These tests start a real SmallPond session (local mode) and exercise the full
platform stack: catalog, table read/write, SQL queries, and pipelines.
"""

import os

import pandas as pd
import pytest

import openpond
from openpond.catalog import ColumnInfo


@pytest.fixture(scope="module")
def platform(tmp_path_factory):
    """One SmallPond platform shared across tests in this module."""
    data_root = str(tmp_path_factory.mktemp("openpond"))
    p = openpond.init(data_root=data_root)
    yield p
    p.shutdown()


@pytest.fixture(scope="module", autouse=True)
def setup_catalog(platform):
    """Pre-populate the catalog used by tests."""
    platform.create_database("testdb")
    platform.create_schema("testdb", "public")


# ---------------------------------------------------------------------------
# DataPlatform init / catalog
# ---------------------------------------------------------------------------


class TestPlatformInit:
    def test_init_creates_data_root(self, platform):
        assert os.path.isdir(platform._data_root)

    def test_session_is_accessible(self, platform):
        assert platform.session is not None

    def test_catalog_is_accessible(self, platform):
        assert platform.catalog is not None

    def test_list_databases(self, platform):
        dbs = platform.list_databases()
        assert "testdb" in dbs

    def test_list_schemas(self, platform):
        schemas = platform.list_schemas("testdb")
        assert "public" in schemas

    def test_context_manager_enter(self, platform):
        # Verify __enter__ returns the platform itself.
        entered = platform.__enter__()
        assert entered is platform


# ---------------------------------------------------------------------------
# Table management
# ---------------------------------------------------------------------------


class TestTableManagement:
    def test_create_and_list_tables(self, platform):
        platform.create_table("testdb", "public", "orders")
        tables = platform.list_tables("testdb", "public")
        assert "orders" in tables

    def test_create_table_with_columns(self, platform):
        cols = [
            ColumnInfo("id", "INTEGER", nullable=False),
            ColumnInfo("amount", "DOUBLE"),
        ]
        platform.create_table("testdb", "public", "sales", columns=cols)
        info = platform.catalog.get_table("testdb", "public", "sales")
        assert len(info.columns) == 2
        assert info.columns[0].name == "id"

    def test_drop_table(self, platform):
        platform.create_table("testdb", "public", "temp_tbl")
        platform.drop_table("testdb", "public", "temp_tbl")
        tables = platform.list_tables("testdb", "public")
        assert "temp_tbl" not in tables


# ---------------------------------------------------------------------------
# Table read / write
# ---------------------------------------------------------------------------


class TestTableReadWrite:
    def test_write_and_read_parquet(self, platform):
        data = pd.DataFrame({"id": [1, 2, 3], "value": [10.0, 20.0, 30.0]})
        df = platform.from_pandas(data)

        tbl = platform.create_table("testdb", "public", "rw_test", replace=True)
        tbl.write(df)

        result_df = tbl.to_pandas()
        assert len(result_df) == 3
        assert set(result_df.columns) == {"id", "value"}

    def test_write_pandas_directly(self, platform):
        data = pd.DataFrame({"x": list(range(5))})
        tbl = platform.create_table("testdb", "public", "pandas_test", replace=True)
        tbl.write(data)

        result_df = tbl.to_pandas()
        assert len(result_df) == 5

    def test_table_count(self, platform):
        data = pd.DataFrame({"x": list(range(50))})
        df = platform.from_pandas(data)
        tbl = platform.create_table("testdb", "public", "count_test", replace=True)
        tbl.write(df)
        assert tbl.count() == 50

    def test_table_info_updated_after_write(self, platform):
        data = pd.DataFrame({"a": [1, 2]})
        df = platform.from_pandas(data)
        tbl = platform.create_table("testdb", "public", "stats_test", replace=True)
        tbl.write(df)
        info = tbl.info
        assert info.row_count == 2
        assert info.size_bytes > 0


# ---------------------------------------------------------------------------
# SQL queries
# ---------------------------------------------------------------------------


class TestSQL:
    def test_sql_via_platform(self, platform):
        data = pd.DataFrame(
            {"ticker": ["AAPL", "AAPL", "GOOG"], "price": [150.0, 155.0, 2800.0]}
        )
        tbl = platform.create_table("testdb", "public", "prices", replace=True)
        tbl.write(data)

        result = platform.sql(
            "SELECT ticker, max(price) AS max_price FROM {0} GROUP BY ticker ORDER BY ticker",
            "testdb.public.prices",
        )
        pdf = result.to_pandas()
        assert len(pdf) == 2
        assert list(pdf["ticker"]) == ["AAPL", "GOOG"]

    def test_table_sql_method(self, platform):
        data = pd.DataFrame({"id": [1, 2, 3, 4, 5], "score": [10, 20, 30, 40, 50]})
        tbl = platform.create_table("testdb", "public", "scores", replace=True)
        tbl.write(data)

        result = tbl.sql("SELECT * FROM {table} WHERE score > 25")
        pdf = result.to_pandas()
        assert len(pdf) == 3


# ---------------------------------------------------------------------------
# Pipelines via platform
# ---------------------------------------------------------------------------


class TestPlatformPipeline:
    def test_pipeline_via_platform(self, platform):
        data = pd.DataFrame({"val": [1, 2, 3]})

        pipeline = (
            platform.pipeline("test_pipe")
            .add_step("load", lambda _: platform.from_pandas(data))
            .add_step(
                "transform",
                lambda df: platform.session.partial_sql(
                    "SELECT val * 2 AS val FROM {0}", df
                ),
            )
        )
        result = pipeline.run()
        assert result.success
        assert len(result.steps) == 2
