# ourairports-2026-08

Dataset: https://huggingface.co/datasets/yuiseki/ourairports-2026-08

OurAirports frozen at the last commit of August 2026, and the code that
fetches, checks and converts it. This repository holds the code; the data is
on the Hub.

## Where things are

```
scripts/01_download.sh        seven CSVs at commit 9e51f134, each checked against its git blob
scripts/02_verify.py          row counts, unique ids, every reference resolves
scripts/03_export_parquet.py  CSV -> Parquet, typed by column name, points for airports and navaids
src/publish.py                pushes the data and its card to the Hub
tests/                        the type rule and the export

data/README.md                the dataset card. Uploaded as-is
data/LICENSE                  the public domain statement and the changes the Parquet makes
data/provenance.yaml          the commit, the counts, and what was done
data/csv/                     generated, 24 MB, the commit's own files
data/parquet/                 generated, 8 MB
```

## Running it

```sh
./scripts/01_download.sh
uv run python scripts/02_verify.py
uv run python scripts/03_export_parquet.py
uv run python src/publish.py          # dry run; --push to upload
uv run pytest
```

Seconds. The whole of it is 24 MB.

## Why a commit and not a date

OurAirports rebuilds all seven files every night at the same URLs and no row
carries the date it changed, so a download names nothing. The commit of
davidmegginson/ourairports-data does. `01_download.sh` fetches from
raw.githubusercontent.com at that commit, never from the GitHub Pages copies,
and stops if a file's git blob is not the one the commit's tree names.

The month in the name is the month of the commit, 2026-08-31.

## Two traps

**DuckDB rounds instead of failing.** Casting `'12.5'` to INTEGER gives 13.
The export matches every integer column against a pattern before the cast,
so a value that does not fit stops the run rather than being rounded into
the data.

**One header has spaces.** `airport-comments.csv` writes `"id", "threadRef"`
with a space after each comma. The csv module then reads the names as
`' "threadRef"'`, quotes and all. `02_verify.py` cleans the header only; the
same option on the rows would also strip leading spaces inside the comments.

## Licence

The code here is MIT. The data it fetches is public domain, as OurAirports
states on its download page; credit is asked for and not required:

    Data from OurAirports (https://ourairports.com/)

See `data/LICENSE` for the statement and the three changes the Parquet makes.
