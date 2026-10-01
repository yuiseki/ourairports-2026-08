---
license: other
license_name: public-domain
license_link: https://ourairports.com/data/
language:
- en
task_categories:
- table-question-answering
- question-answering
tags:
- airports
- aviation
- geospatial
- gazetteer
- geoparquet
- frozen-snapshot
size_categories:
- 10K<n<100K
configs:
- config_name: airports
  data_files: parquet/airports.parquet
  default: true
- config_name: runways
  data_files: parquet/runways.parquet
- config_name: navaids
  data_files: parquet/navaids.parquet
- config_name: countries
  data_files: parquet/countries.parquet
- config_name: regions
  data_files: parquet/regions.parquet
- config_name: airport_frequencies
  data_files: parquet/airport_frequencies.parquet
- config_name: airport_comments
  data_files: parquet/airport_comments.parquet
---

# ourairports-2026-08

OurAirports as it was at the last commit of August 2026: 86,002 airports,
heliports and airfields around the world, with their runways, radio
frequencies and navigation aids, their IATA and ICAO codes, and whether they
have scheduled service.

Public domain. OurAirports asks for credit and does not require it.

## Why a frozen copy exists

OurAirports rebuilds its seven files every night at the same URLs, and no row
says when it last changed. An analysis run on Tuesday and again on Friday
reads different data and cannot tell. The only name a version has is the
commit of [davidmegginson/ourairports-data](https://github.com/davidmegginson/ourairports-data)
that holds it, and this dataset is one such commit:

    9e51f13487de777bdc473a37d271981a2d0b30ca   2026-08-31T01:53:13Z

The month in the name is the month the data is from, not the month it was
fetched.

## What is here

| config | rows | |
|---|---:|---|
| `airports` | 86,002 | one per place, with a point `geometry` |
| `runways` | 48,203 | length, width, surface, and both ends |
| `navaids` | 11,008 | VOR, NDB, DME and the rest, with a point `geometry` |
| `countries` | 249 | |
| `regions` | 3,987 | first-level subdivisions, ISO 3166-2 style codes |
| `airport_frequencies` | 30,343 | |
| `airport_comments` | 16,406 | members' comments on airports |

`csv/` holds the commit's seven files byte for byte, each checked against the
git blob the commit names for it. `csv/MANIFEST.sha256` records the sha256,
the blob and the size.

## Most of it is not airports

| type | rows |
|---|---:|
| small_airport | 42,707 |
| heliport | 23,196 |
| closed | 13,482 |
| medium_airport | 4,109 |
| seaplane_base | 1,273 |
| large_airport | 1,172 |
| balloonport | 63 |

Heliports and closed fields are 43% of the rows. In Japan it is starker:
3,040 of the 3,747 rows are heliports and 419 are closed, and 85 have
scheduled service. Filter on `type` and `scheduled_service` before counting
anything called an airport.

The United States is 32,643 rows, 38% of the whole.

## Types are by name, not inferred

| column name | type |
|---|---|
| `id`, `*ref` | BIGINT |
| `*_ft`, `*_khz`, `lighted`, `closed` | INTEGER |
| `*_deg`, `*_degT`, `*_mhz` | DOUBLE |
| anything else | the text of the CSV |

`regions.local_code` is written without quotes, so an inferrer turns `02`
into the number 2. Here it stays `02`. A value that did not fit its column
would have stopped the export; none did.

```python
from datasets import load_dataset

airports = load_dataset("yuiseki/ourairports-2026-08", "airports", split="train")
```

```sql
-- DuckDB, straight off the Parquet
SELECT ident, iata_code, name, municipality
FROM 'hf://datasets/yuiseki/ourairports-2026-08/parquet/airports.parquet'
WHERE iso_country = 'JP' AND scheduled_service = 'yes'
ORDER BY iata_code;
```

## What it is good for, and what it is not

It is the one open list that has the codes: 9,057 rows carry an IATA code and
10,473 an ICAO code, with scheduled service marked. Natural Earth has under a
thousand airports; OpenStreetMap has their shapes but attaches codes
unevenly.

It has no shapes. An airport is a point; a runway is two ends and a heading.
For aprons, terminals and runway polygons use OpenStreetMap.

It is crowd-sourced. Codes are not all confirmed against IATA's own register,
and some rows are stale. Treat a code as a lead rather than an authority.

## Reproducing it

```bash
git clone https://github.com/yuiseki/ourairports-2026-08
cd ourairports-2026-08
./scripts/01_download.sh                  # seven files at the commit, blob-checked
uv run python scripts/02_verify.py        # counts, unique ids, every reference resolves
uv run python scripts/03_export_parquet.py
```

## Licence

Public domain. The OurAirports download page says: "All data is released to
the Public Domain, and comes with no guarantee of accuracy or fitness for
use." Credit is asked for and not required; if you give it:

    Data from OurAirports (https://ourairports.com/)

The repository's own LICENSE is The Unlicense, which speaks only of software.
The statement for the data is the site's. `LICENSE` beside this file lists
the three changes the Parquet makes; the CSVs are unchanged.
