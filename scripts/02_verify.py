#!/usr/bin/env python3
"""Check that the frozen CSVs are the commit they claim and hang together.

Read with the csv module only, so nothing here shares a parser with the
Parquet export. A file that had lost rows, or a reference that pointed at
nothing, would still look like a large correct CSV.

The figures are those of commit 9e51f134 (2026-08-31). A different figure
means the files are not that commit, or every count on the card is wrong.
"""

import csv
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "data" / "csv"

ROWS = {
    "airports.csv": 86002,
    "runways.csv": 48203,
    "navaids.csv": 11008,
    "countries.csv": 249,
    "regions.csv": 3987,
    "airport-frequencies.csv": 30343,
    "airport-comments.csv": 16406,
}
JAPAN = {
    "airports": 3747,
    "heliport": 3040,
    "closed": 419,
    "scheduled_service": 85,
}


def read(name: str) -> list[dict]:
    with open(CSV / name, newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        # airport-comments.csv writes '"id", "threadRef", ...': the space after
        # each comma keeps the csv module from seeing the quotes, so the names
        # come out as ' "threadRef"'. Only the header is cleaned; the same
        # option on the rows would also eat leading spaces inside the text.
        header = [h.strip().strip('"') for h in next(r)]
        return [dict(zip(header, row, strict=True)) for row in r]


def main() -> int:
    failures = []

    def check(ok: bool, what: str) -> None:
        print(("ok    " if ok else "FAIL  ") + what)
        if not ok:
            failures.append(what)

    listed = {}
    for line in (CSV / "MANIFEST.sha256").read_text().splitlines():
        sha, blob, size, name = line.split("  ")
        listed[name] = (sha, int(size))
    check(sorted(listed) == sorted(ROWS), "MANIFEST.sha256 lists the seven files")
    for name, (sha, size) in sorted(listed.items()):
        data = (CSV / name).read_bytes()
        check(
            hashlib.sha256(data).hexdigest() == sha and len(data) == size,
            f"{name} matches the manifest",
        )

    t = {name: read(name) for name in ROWS}
    for name, n in ROWS.items():
        check(len(t[name]) == n, f"{name}: {len(t[name]):,} rows, expected {n:,}")
        ids = [r["id"] for r in t[name]]
        check(len(set(ids)) == len(ids), f"{name}: id is unique")

    airports = t["airports.csv"]
    ids = {r["id"] for r in airports}
    idents = {r["ident"] for r in airports}
    check(len(idents) == len(airports), "airports.ident is unique")
    for name, col in [
        ("runways.csv", "airport_ref"),
        ("airport-frequencies.csv", "airport_ref"),
        ("airport-comments.csv", "airportRef"),
    ]:
        orphans = sum(r[col] not in ids for r in t[name])
        check(orphans == 0, f"{name}: every {col} is an airport ({orphans} are not)")
    orphans = sum(
        r["associated_airport"] not in idents for r in t["navaids.csv"] if r["associated_airport"]
    )
    check(
        orphans == 0,
        f"navaids.csv: every associated_airport is an airport ident ({orphans} are not)",
    )
    countries = {r["code"] for r in t["countries.csv"]}
    regions = {r["code"] for r in t["regions.csv"]}
    check(all(r["iso_country"] in countries for r in airports), "every airport's country is listed")
    check(all(r["iso_region"] in regions for r in airports), "every airport's region is listed")

    bad = [
        r["id"]
        for r in airports
        if not (-90 <= float(r["latitude_deg"]) <= 90 and -180 <= float(r["longitude_deg"]) <= 180)
    ]
    check(not bad, f"every airport has a coordinate on the globe ({len(bad)} do not)")

    jp = [r for r in airports if r["iso_country"] == "JP"]
    got = {
        "airports": len(jp),
        "heliport": sum(r["type"] == "heliport" for r in jp),
        "closed": sum(r["type"] == "closed" for r in jp),
        "scheduled_service": sum(r["scheduled_service"] == "yes" for r in jp),
    }
    for k, v in JAPAN.items():
        check(got[k] == v, f"Japan {k}: {got[k]:,}, expected {v:,}")

    if failures:
        print(f"\n{len(failures)} checks failed")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
