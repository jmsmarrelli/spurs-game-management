"""Fetch pinned public inputs and build indexed coaching-analysis cohorts."""

from pathlib import Path
import argparse, hashlib, json, sqlite3, tarfile, urllib.request
import pandas as pd
from .common import ROOT, shots


def fetch():
    manifest = json.loads((ROOT / "data/source_manifest.json").read_text())
    raw = ROOT / "data/raw"
    raw.mkdir(parents=True, exist_ok=True)
    for item in manifest["files"]:
        archive = raw / (item["name"] + ".tar.xz")
        if not archive.exists():
            with urllib.request.urlopen(item["url"], timeout=180) as r:
                archive.write_bytes(r.read())
        if hashlib.sha256(archive.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"Checksum mismatch: {archive.name}")
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                if member.isfile() and member.name.endswith(".csv"):
                    # Deliberately do not use extractall on a downloaded archive.
                    with tar.extractfile(member) as f:
                        (raw / Path(member.name).name).write_bytes(f.read())
        print(item["name"], "verified")


def database():
    with sqlite3.connect(ROOT / "data/research.sqlite") as con:
        for table in ["turnovers", "timeout_candidates", "quarter_attempts"]:
            pd.read_csv(ROOT / f"data/{table}.csv.gz").to_sql(
                table, con, if_exists="replace", index=False
            )
            con.execute(
                f"CREATE UNIQUE INDEX {table}_event ON {table}(game_id, event_id)"
            )
        con.executescript((ROOT / "sql/coaching_queries.sql").read_text())
        for view in ["turnover_windows", "quarter_clock_groups", "timeout_game_counts"]:
            pd.read_sql_query(f"SELECT * FROM {view}", con).to_csv(
                ROOT / f"results/sql_{view}.csv", index=False
            )
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["fetch", "sql"])
    args = parser.parse_args()
    if args.action == "fetch":
        fetch()
    else:
        database()
        print("SQL cohort summaries exported")
