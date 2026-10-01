#!/usr/bin/env python3
"""Push the frozen CSVs, their Parquet and the card to the Hugging Face Hub.

The CSVs go up as files rather than through datasets.push_to_hub, because
push_to_hub re-encodes. What makes this dataset worth anything is that the
bytes under csv/ are those of one named commit, so they are uploaded
unchanged and the manifest travels with them.

    uv run python src/publish.py             # dry run
    uv run python src/publish.py --push
"""

import argparse
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "yuiseki/ourairports-2026-08"

# Declared on the card, and therefore checked before anything moves.
CONFIGS = {
    "airports": "parquet/airports.parquet",
    "runways": "parquet/runways.parquet",
    "navaids": "parquet/navaids.parquet",
    "countries": "parquet/countries.parquet",
    "regions": "parquet/regions.parquet",
    "airport_frequencies": "parquet/airport_frequencies.parquet",
    "airport_comments": "parquet/airport_comments.parquet",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--push", action="store_true")
    a = ap.parse_args()

    card = (ROOT / "data" / "README.md").read_text(encoding="utf-8")
    for name, path in CONFIGS.items():
        if not re.search(rf"^- config_name: {re.escape(name)}$", card, re.M):
            raise SystemExit(f"the card declares no config named {name}")
        if not re.search(rf"^  data_files: {re.escape(path)}$", card, re.M):
            raise SystemExit(f"the card's data_files do not point at {path}")
        if not (ROOT / "data" / path).exists():
            raise SystemExit(f"missing {path}; run scripts/03 first")

    # The CSVs are the claim. A manifest that does not describe them means the
    # copy on the Hub is not the copy that was checked.
    csvdir = ROOT / "data" / "csv"
    listed = {}
    for line in (csvdir / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines():
        sha, _blob, _size, name = line.split("  ")
        listed[name] = sha
    on_disk = sorted(p.name for p in csvdir.glob("*.csv"))
    if sorted(listed) != on_disk:
        raise SystemExit("MANIFEST.sha256 and csv/ do not agree")
    for name, sha in sorted(listed.items()):
        got = hashlib.sha256((csvdir / name).read_bytes()).hexdigest()
        if got != sha:
            raise SystemExit(f"{name}: manifest says {sha}, file is {got}")
    print(f"{len(listed)} CSVs match the manifest")

    files = ["README.md", "LICENSE", "provenance.yaml", "csv/MANIFEST.sha256"]
    files += [f"csv/{n}" for n in on_disk]
    files += list(CONFIGS.values())
    total = sum((ROOT / "data" / f).stat().st_size for f in files)
    print(f"{a.repo}\n  {len(files)} files, {total / 1e6:.1f} MB")
    for f in files:
        print(f"  {f}")

    if not a.push:
        print("\ndry run. pass --push to upload")
        return 0

    from huggingface_hub import HfApi

    api = HfApi()
    api.create_repo(a.repo, repo_type="dataset", exist_ok=True, private=False)
    api.upload_folder(
        folder_path=str(ROOT / "data"),
        repo_id=a.repo,
        repo_type="dataset",
        allow_patterns=files,
    )
    print(f"\npushed to https://huggingface.co/datasets/{a.repo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
