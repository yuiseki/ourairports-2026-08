#!/usr/bin/env bash
# Fetch the seven OurAirports CSVs as they were at the last commit of August
# 2026, and freeze exactly what arrived.
#
# OurAirports rebuilds these files every night at the same URLs, and the rows
# carry no update date, so the only way to name a version is the commit of
# davidmegginson/ourairports-data that holds it. The files are taken from
# raw.githubusercontent.com at that commit, never from the GitHub Pages URLs,
# whose content changes under them.
#
# Each file is checked against the git blob the commit's tree names for it:
# the same bytes, or the run stops.
set -euo pipefail
cd "$(dirname "$0")/.."

REPO=davidmegginson/ourairports-data
COMMIT=9e51f13487de777bdc473a37d271981a2d0b30ca   # 2026-08-31T01:53:13Z, "data update"
OUT=data/csv
FILES=(airports runways navaids countries regions airport-frequencies airport-comments)
mkdir -p "$OUT"

tree="$(curl -sSf --max-time 60 "https://api.github.com/repos/$REPO/git/trees/$COMMIT")"

: > "$OUT/MANIFEST.sha256"
for name in "${FILES[@]}"; do
  f="$OUT/$name.csv"
  curl -sSf --max-time 300 -o "$f" "https://raw.githubusercontent.com/$REPO/$COMMIT/$name.csv"
  want="$(printf '%s' "$tree" | python3 -c "
import json, sys
print(next(e['sha'] for e in json.load(sys.stdin)['tree'] if e['path'] == '$name.csv'))")"
  got="$(git hash-object "$f")"
  if [ "$got" != "$want" ]; then
    echo "$name.csv is blob $got, the commit says $want" >&2
    exit 1
  fi
  printf '%s  %s  %s  %s\n' "$(sha256sum "$f" | cut -d' ' -f1)" "$got" "$(stat -c %s "$f")" "$name.csv" \
    >> "$OUT/MANIFEST.sha256"
done
sort -k4 "$OUT/MANIFEST.sha256" -o "$OUT/MANIFEST.sha256"
cat "$OUT/MANIFEST.sha256"
