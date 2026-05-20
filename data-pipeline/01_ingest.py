"""
Step 1: Ingest raw StatsBomb open data.

Clones the statsbomb/open-data GitHub repo (if not already present) and
builds a match index for each configured competition. Validates that all
expected data files exist.

Output:
    {RAW_DATA_DIR}/                         — cloned StatsBomb repo
    {OUTPUT_DIR}/intermediate/matches.parquet — match index with metadata

Usage:
    python 01_ingest.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

# Resolve paths relative to project root (one level up from data-pipeline/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import COMPETITIONS, CompetitionConfig, RAW_DATA_DIR, OUTPUT_DIR

STATSBOMB_REPO_URL = "https://github.com/statsbomb/open-data.git"

# Paths within the cloned repo
def _sb_data_dir() -> Path:
    return PROJECT_ROOT / RAW_DATA_DIR / "open-data" / "data"


def clone_repo() -> None:
    """Clone the StatsBomb open-data repo if not already present."""
    repo_dir = PROJECT_ROOT / RAW_DATA_DIR / "open-data"
    if repo_dir.exists():
        print(f"StatsBomb repo already exists at {repo_dir}")
        return

    print(f"Cloning StatsBomb open-data into {repo_dir} ...")
    (PROJECT_ROOT / RAW_DATA_DIR).mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "clone", "--depth", "1", STATSBOMB_REPO_URL, str(repo_dir)],
        check=True,
    )
    print("Clone complete.")


def load_matches(comp: CompetitionConfig) -> pd.DataFrame:
    """
    Load the match list for a single competition/season.

    Returns a DataFrame with columns:
        match_id, match_date, home_team, away_team, home_score, away_score,
        competition_id, season_id, competition_name, season_name
    """
    matches_path = (
        _sb_data_dir() / "matches" / str(comp.competition_id) / f"{comp.season_id}.json"
    )
    if not matches_path.exists():
        raise FileNotFoundError(
            f"No matches file for {comp.competition_name} {comp.season_name} "
            f"at {matches_path}"
        )

    with open(matches_path, encoding="utf-8") as f:
        raw_matches = json.load(f)

    rows: list[dict] = []
    for m in raw_matches:
        rows.append({
            "match_id": m["match_id"],
            "match_date": m["match_date"],
            "kick_off": m.get("kick_off"),
            "home_team_id": m["home_team"]["home_team_id"],
            "home_team": m["home_team"]["home_team_name"],
            "away_team_id": m["away_team"]["away_team_id"],
            "away_team": m["away_team"]["away_team_name"],
            "home_score": m["home_score"],
            "away_score": m["away_score"],
            "match_week": m.get("match_week"),
            "competition_stage": m.get("competition_stage", {}).get("name", "Unknown"),
            "competition_id": comp.competition_id,
            "season_id": comp.season_id,
            "competition_name": comp.competition_name,
            "season_name": comp.season_name,
        })

    df = pd.DataFrame(rows)
    print(
        f"  {comp.competition_name} {comp.season_name}: "
        f"{len(df)} matches loaded"
    )
    return df


def validate_data_files(match_ids: list[int]) -> dict[str, list[int]]:
    """
    Check that events and lineups JSON files exist for every match.

    Returns a dict with 'missing_events' and 'missing_lineups' lists.
    """
    sb_data = _sb_data_dir()
    missing: dict[str, list[int]] = {"missing_events": [], "missing_lineups": []}

    for mid in match_ids:
        if not (sb_data / "events" / f"{mid}.json").exists():
            missing["missing_events"].append(mid)
        if not (sb_data / "lineups" / f"{mid}.json").exists():
            missing["missing_lineups"].append(mid)

    return missing


def main() -> None:
    clone_repo()

    intermediate_dir = PROJECT_ROOT / OUTPUT_DIR / "intermediate"
    intermediate_dir.mkdir(parents=True, exist_ok=True)

    all_matches: list[pd.DataFrame] = []

    print("\nLoading match data:")
    for comp in COMPETITIONS:
        df = load_matches(comp)
        all_matches.append(df)

        # Validate that raw event/lineup files exist
        missing = validate_data_files(df["match_id"].tolist())

        if missing["missing_events"]:
            print(
                f"  WARNING: {len(missing['missing_events'])} matches missing "
                f"event files: {missing['missing_events'][:5]}..."
            )
        if missing["missing_lineups"]:
            print(
                f"  WARNING: {len(missing['missing_lineups'])} matches missing "
                f"lineup files: {missing['missing_lineups'][:5]}..."
            )

        if not missing["missing_events"] and not missing["missing_lineups"]:
            print("  All event and lineup files present.")

    # Combine and save
    matches_df = pd.concat(all_matches, ignore_index=True)
    out_path = intermediate_dir / "matches.parquet"
    matches_df.to_parquet(out_path, index=False)
    print(f"\nMatch index saved to {out_path}")
    print(f"Total: {len(matches_df)} matches across {len(COMPETITIONS)} competition(s)")


if __name__ == "__main__":
    main()
