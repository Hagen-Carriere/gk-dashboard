"""
Step 2: Extract goalkeeper-relevant events from raw StatsBomb data.

Filters to three event categories:
    1. type_name == "Goal Keeper" — actions performed by the keeper
    2. type_name == "Shot" where the shot is against the keeper's team
    3. type_name == "Pass" where the passer is a goalkeeper

Joins with lineup data to resolve player names and teams.
Normalizes coordinates so the keeper's goal is always at x=0.

Output: cleaned DataFrames with all GK-relevant events, keyed by
(competition_id, keeper_id, match_id).
"""

from __future__ import annotations


def main() -> None:
    raise NotImplementedError("TODO: Milestone 1")


if __name__ == "__main__":
    main()
