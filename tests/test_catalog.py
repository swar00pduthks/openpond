"""Tests for the Catalog class."""

import os
import tempfile

import pytest

from openpond.catalog import (
    Catalog,
    CatalogError,
    ColumnInfo,
    TableInfo,
)


@pytest.fixture()
def catalog(tmp_path):
    """Return a fresh Catalog backed by a temporary directory."""
    return Catalog(str(tmp_path / "catalog"))


# ---------------------------------------------------------------------------
# Database tests
# ---------------------------------------------------------------------------


class TestDatabase:
    def test_create_and_list(self, catalog):
        catalog.create_database("db1")
        catalog.create_database("db2")
        names = [d.name for d in catalog.list_databases()]
        assert "db1" in names
        assert "db2" in names

    def test_create_duplicate_raises(self, catalog):
        catalog.create_database("dup")
        with pytest.raises(CatalogError, match="already exists"):
            catalog.create_database("dup", exist_ok=False)

    def test_create_duplicate_exist_ok(self, catalog):
        catalog.create_database("dup")
        info = catalog.create_database("dup", exist_ok=True)
        assert info.name == "dup"

    def test_get_database(self, catalog):
        catalog.create_database("mydb", comment="hello")
        info = catalog.get_database("mydb")
        assert info.name == "mydb"
        assert info.comment == "hello"

    def test_get_missing_raises(self, catalog):
        with pytest.raises(CatalogError):
            catalog.get_database("no_such_db")

    def test_drop_database(self, catalog):
        catalog.create_database("to_drop")
        catalog.drop_database("to_drop")
        assert not catalog.database_exists("to_drop")

    def test_drop_non_empty_raises(self, catalog):
        catalog.create_database("nonempty")
        catalog.create_schema("nonempty", "s1")
        with pytest.raises(CatalogError, match="not empty"):
            catalog.drop_database("nonempty", cascade=False)

    def test_drop_cascade(self, catalog):
        catalog.create_database("big")
        catalog.create_schema("big", "s1")
        catalog.drop_database("big", cascade=True)
        assert not catalog.database_exists("big")

    def test_persistence(self, tmp_path):
        """Catalog metadata survives a reload from disk."""
        path = str(tmp_path / "cat")
        c1 = Catalog(path)
        c1.create_database("persistent")
        c2 = Catalog(path)
        assert c2.database_exists("persistent")


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestSchema:
    def test_create_and_list(self, catalog):
        catalog.create_database("db")
        catalog.create_schema("db", "s1")
        catalog.create_schema("db", "s2")
        names = [s.name for s in catalog.list_schemas("db")]
        assert {"s1", "s2"} == set(names)

    def test_create_in_missing_db_raises(self, catalog):
        with pytest.raises(CatalogError):
            catalog.create_schema("ghost", "s1")

    def test_drop_schema(self, catalog):
        catalog.create_database("db")
        catalog.create_schema("db", "to_drop")
        catalog.drop_schema("db", "to_drop")
        assert not catalog.schema_exists("db", "to_drop")


# ---------------------------------------------------------------------------
# Table tests
# ---------------------------------------------------------------------------


class TestTable:
    def _populated_catalog(self, catalog):
        catalog.create_database("db")
        catalog.create_schema("db", "sc")
        return catalog

    def test_register_and_list(self, catalog):
        self._populated_catalog(catalog)
        info = TableInfo(
            database="db", schema="sc", name="t1", location="/tmp/t1"
        )
        catalog.register_table(info)
        tables = catalog.list_tables("db", "sc")
        assert len(tables) == 1
        assert tables[0].name == "t1"

    def test_register_with_columns(self, catalog):
        self._populated_catalog(catalog)
        cols = [
            ColumnInfo(name="id", dtype="INTEGER", nullable=False),
            ColumnInfo(name="name", dtype="VARCHAR"),
        ]
        info = TableInfo(
            database="db", schema="sc", name="t2",
            location="/tmp/t2", columns=cols,
        )
        catalog.register_table(info)
        retrieved = catalog.get_table("db", "sc", "t2")
        assert len(retrieved.columns) == 2
        assert retrieved.columns[0].name == "id"
        assert retrieved.columns[0].nullable is False

    def test_register_duplicate_raises(self, catalog):
        self._populated_catalog(catalog)
        info = TableInfo(database="db", schema="sc", name="t3", location="/tmp/t3")
        catalog.register_table(info)
        with pytest.raises(CatalogError, match="already exists"):
            catalog.register_table(info, replace=False)

    def test_register_replace(self, catalog):
        self._populated_catalog(catalog)
        info = TableInfo(database="db", schema="sc", name="t4", location="/tmp/t4")
        catalog.register_table(info)
        info2 = TableInfo(
            database="db", schema="sc", name="t4",
            location="/tmp/t4_new", comment="replaced",
        )
        catalog.register_table(info2, replace=True)
        got = catalog.get_table("db", "sc", "t4")
        assert got.comment == "replaced"

    def test_update_table_stats(self, catalog):
        self._populated_catalog(catalog)
        info = TableInfo(database="db", schema="sc", name="t5", location="/tmp/t5")
        catalog.register_table(info)
        catalog.update_table_stats("db", "sc", "t5", row_count=100, size_bytes=2048)
        got = catalog.get_table("db", "sc", "t5")
        assert got.row_count == 100
        assert got.size_bytes == 2048

    def test_drop_table(self, catalog):
        self._populated_catalog(catalog)
        info = TableInfo(database="db", schema="sc", name="t6", location="/tmp/t6")
        catalog.register_table(info)
        catalog.drop_table("db", "sc", "t6")
        assert not catalog.table_exists("db", "sc", "t6")

    def test_full_name(self, catalog):
        self._populated_catalog(catalog)
        info = TableInfo(database="db", schema="sc", name="t7", location="/tmp/t7")
        assert info.full_name == "db.sc.t7"
