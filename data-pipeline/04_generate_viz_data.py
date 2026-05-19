"""
Step 4: Generate frontend-ready JSON files.

Serializes pipeline DataFrames into the JSON schema defined in schemas.py:
    - /data/competitions.json
    - /data/{competition_id}/keepers.json
    - /data/{competition_id}/{keeper_id}/shots.json
    - /data/{competition_id}/{keeper_id}/distribution.json
    - /data/{competition_id}/{keeper_id}/sweeping.json
    - /data/{competition_id}/{keeper_id}/summary.json

Validates output against schema contracts before writing.
"""

from __future__ import annotations


def main() -> None:
    raise NotImplementedError("TODO: Milestone 2")


if __name__ == "__main__":
    main()
