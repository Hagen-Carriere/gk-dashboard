"""
Step 1: Ingest raw StatsBomb open data.

Downloads or reads from a local clone of the statsbomb/open-data GitHub repo.
For each competition in config.COMPETITIONS, loads:
    - matches/{competition_id}/{season_id}.json  → match list
    - events/{match_id}.json                     → all events per match
    - lineups/{match_id}.json                    → player/team mappings

Output: raw DataFrames written to intermediate parquet files in config.RAW_DATA_DIR,
or returned in-memory for the next pipeline step.
"""

from __future__ import annotations


def main() -> None:
    raise NotImplementedError("TODO: Milestone 1")


if __name__ == "__main__":
    main()
