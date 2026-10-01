import importlib.util
from pathlib import Path

import duckdb
import pytest

_spec = importlib.util.spec_from_file_location(
    "export", Path(__file__).parents[1] / "scripts" / "03_export_parquet.py"
)
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)


@pytest.mark.parametrize(
    ("name", "sql"),
    [
        ("id", "BIGINT"),
        ("airport_ref", "BIGINT"),
        ("threadRef", "BIGINT"),
        ("elevation_ft", "INTEGER"),
        ("frequency_khz", "INTEGER"),
        ("lighted", "INTEGER"),
        ("latitude_deg", "DOUBLE"),
        ("le_heading_degT", "DOUBLE"),
        ("frequency_mhz", "DOUBLE"),
        ("local_code", "VARCHAR"),
        ("iata_code", "VARCHAR"),
        ("date", "VARCHAR"),
    ],
)
def test_column_type(name, sql):
    assert m.column_type(name) == sql


def test_csv_rows_counts_records_not_lines(tmp_path):
    f = tmp_path / "c.csv"
    f.write_text('"id","body"\n1,"two\nlines"\n2,"x"\n', encoding="utf-8")
    assert m.csv_rows(f) == 2


def _rel(tmp_path, text: str, geometry: bool = False):
    f = tmp_path / "t.csv"
    f.write_text(text, encoding="utf-8")
    con = duckdb.connect()
    con.execute("install spatial; load spatial")
    return con.sql(m.select_sql(con, f, geometry))


def test_leading_zeros_survive_and_numbers_are_typed(tmp_path):
    rel = _rel(tmp_path, '"id","code","local_code","elevation_ft"\n302811,"AD-02",02,11\n')
    assert rel.fetchone() == (302811, "AD-02", "02", 11)
    assert dict(zip(rel.columns, rel.types, strict=True)) == {
        "id": "BIGINT", "code": "VARCHAR", "local_code": "VARCHAR", "elevation_ft": "INTEGER",
    }  # fmt: skip


def test_header_names_lose_their_spaces(tmp_path):
    rel = _rel(tmp_path, '"id", "threadRef", "body"\n1,2,"x"\n')
    assert rel.columns == ["id", "threadRef", "body"]


def test_a_point_geometry_is_added(tmp_path):
    rel = _rel(tmp_path, '"id","latitude_deg","longitude_deg"\n1,35.5,139.75\n2,,\n', True)
    got = rel.select("id, st_astext(geometry)").order("id").fetchall()
    assert got == [(1, "POINT (139.75 35.5)"), (2, None)]


def test_a_value_the_rule_does_not_fit_stops_the_run(tmp_path):
    # A plain cast would round 12.5 to 13 and carry on.
    rel = _rel(tmp_path, '"id","elevation_ft"\n1,12.5\n')
    with pytest.raises(duckdb.Error, match="elevation_ft is not an integer: 12.5"):
        rel.fetchall()
