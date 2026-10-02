#!/usr/bin/env python3
"""Mirror the frozen CSVs as typed Parquet, for the Hub viewer and for DuckDB.

The type of a column is read from its name, not inferred from its values:
id and *ref are BIGINT, *_ft, *_khz, lighted and closed are INTEGER, *_deg,
*_degT and *_mhz are DOUBLE, and everything else stays the text of the CSV.
An inferrer would turn regions.local_code "02" into the number 2, because the
file writes it without quotes.

A value that does not fit its column stops the run. DuckDB's own cast would
not: it rounds '12.5' to 13 on the way to INTEGER, so integers are matched
against a pattern before they are cast.

Three changes are made and all are stated on the card:

  the header names lose the spaces airport-comments.csv puts after its commas
  airports and navaids gain a point geometry from longitude_deg, latitude_deg
  the rows are sorted by id (countries and regions by code)

No value is changed, and the CSV beside it is the byte-for-byte original.
"""

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "data" / "csv"
OUT = ROOT / "data" / "parquet"

FILES = [
    "airports", "runways", "navaids", "countries", "regions",
    "airport-frequencies", "airport-comments",
]  # fmt: skip
GEOMETRY = {"airports", "navaids"}
ORDER = {"countries": "code", "regions": "code"}


def column_type(name: str) -> str:
    """The SQL type of an OurAirports column, from its name alone."""
    low = name.lower()
    if low == "id" or low.endswith("ref"):
        return "BIGINT"
    if low.endswith(("_ft", "_khz")) or low in ("lighted", "closed"):
        return "INTEGER"
    if low.endswith(("_deg", "_degt", "_mhz")):
        return "DOUBLE"
    return "VARCHAR"


def csv_rows(path: Path) -> int:
    """Records in a CSV, counted without DuckDB (a quoted field may span lines)."""
    with open(path, newline="", encoding="utf-8") as f:
        return sum(1 for _ in csv.reader(f)) - 1


def select_sql(con, path: Path, geometry: bool = False) -> str:
    """A query reading one CSV with the types of column_type and trimmed names."""
    src = f"read_csv('{path}', header = true, all_varchar = true, strict_mode = true)"
    cols = []
    for n in con.sql(f"select * from {src} limit 0").columns:
        name, t = n.strip(), column_type(n.strip())
        if t == "VARCHAR":
            expr = f'"{n}"'
        elif t in ("BIGINT", "INTEGER"):
            expr = (
                f"""case when "{n}" is null or regexp_full_match("{n}", '-?[0-9]+') """
                f"""then cast("{n}" as {t}) """
                f"""else error('{path.name}: {name} is not an integer: ' || "{n}") end"""
            )
        else:
            expr = f'cast("{n}" as {t})'
        cols.append(f'{expr} as "{name}"')
    if geometry:
        cols.append(
            "st_point(cast(longitude_deg as double), cast(latitude_deg as double)) as geometry"
        )
    return f"select {', '.join(cols)} from {src}"


def main() -> int:
    import duckdb

    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("install spatial; load spatial")
    for name in FILES:
        f = CSV / f"{name}.csv"
        rows = csv_rows(f)
        p = OUT / f"{name.replace('-', '_')}.parquet"
        query = select_sql(con, f, name in GEOMETRY)
        con.execute(
            f"copy ({query} order by {ORDER.get(name, 'id')}) "
            f"to '{p}' (format parquet, compression zstd, write_bloom_filter false)"
        )
        got = con.sql(f"select count(*) from '{p}'").fetchone()[0]
        if got != rows:
            raise SystemExit(f"{p.name}: {got} rows, {f.name} has {rows}")
        print(f"{p.name:28} {got:>8,} rows {p.stat().st_size:>12,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
