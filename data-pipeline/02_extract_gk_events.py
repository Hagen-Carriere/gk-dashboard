"""
Step 2: Extract goalkeeper-relevant events from raw StatsBomb data.

Reads the match index from step 1, then for each match:
    1. Loads events and lineups JSON
    2. Identifies the goalkeeper(s) for each team
    3. Extracts three event categories:
       - Goal Keeper events (actions BY the keeper)
       - Shot events (shots AGAINST the keeper's team)
       - Pass events (passes BY the keeper)
    4. Normalizes coordinates so the keeper's goal is always at x=0
    5. Joins with lineup data for player names and team names

Output:
    {OUTPUT_DIR}/intermediate/gk_events.parquet   — all GK action events
    {OUTPUT_DIR}/intermediate/shots_faced.parquet  — all shots against each keeper
    {OUTPUT_DIR}/intermediate/gk_passes.parquet    — all passes by each keeper

Usage:
    python 02_extract_gk_events.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import COMPETITIONS, RAW_DATA_DIR, OUTPUT_DIR, PITCH_LENGTH, PITCH_WIDTH


def _sb_data_dir() -> Path:
    return PROJECT_ROOT / RAW_DATA_DIR / "open-data" / "data"


def load_events(match_id: int) -> list[dict[str, Any]]:
    path = _sb_data_dir() / "events" / f"{match_id}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_lineups(match_id: int) -> dict[str, Any]:
    path = _sb_data_dir() / "lineups" / f"{match_id}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def identify_keepers(
    lineups: list[dict[str, Any]],
) -> dict[int, list[dict[str, Any]]]:
    """
    Build a mapping of team_id -> list of keeper dicts with timing info.

    Each keeper dict contains:
        player_id, player_name, team_id, team_name,
        from_period (int or 1), to_period (int or None=end of match)

    Uses lineup position data to track when each keeper was on the pitch.
    """
    team_keepers: dict[int, list[dict[str, Any]]] = {}

    for team_lineup in lineups:
        team_id = team_lineup["team_id"]
        team_name = team_lineup["team_name"]
        keepers: list[dict[str, Any]] = []

        for player in team_lineup["lineup"]:
            positions = player.get("positions", [])
            for pos in positions:
                if pos.get("position") == "Goalkeeper" or pos.get("position_id") == 1:
                    keepers.append({
                        "player_id": player["player_id"],
                        "player_name": player["player_name"],
                        "team_id": team_id,
                        "team_name": team_name,
                        "from_period": pos.get("from_period", 1),
                        "to_period": pos.get("to_period"),  # None = played to end
                        "start_reason": pos.get("start_reason", ""),
                    })
                    break

        # Sort so the starter is first
        keepers.sort(key=lambda k: (0 if k["start_reason"] == "Starting XI" else 1))
        team_keepers[team_id] = keepers

    return team_keepers


def get_active_keeper(
    keepers: list[dict[str, Any]], period: int
) -> dict[str, Any] | None:
    """
    Return the keeper who was on the pitch during the given period.

    If timing data is missing or ambiguous, falls back to the first
    (starting) keeper. Returns None only if the team has no keepers at all.
    """
    if not keepers:
        return None

    for k in keepers:
        from_p = k.get("from_period", 1) or 1
        to_p = k.get("to_period")  # None means played to end
        if from_p <= period and (to_p is None or period <= to_p):
            return k

    # Fallback: return the starter
    return keepers[0]


def flip_x(x: float) -> float:
    """Flip x-coordinate to normalize keeper's goal to x=0."""
    return PITCH_LENGTH - x


def flip_y(y: float) -> float:
    """Flip y-coordinate when flipping orientation."""
    return PITCH_WIDTH - y


def normalize_location(
    loc: list[float] | None, needs_flip: bool
) -> tuple[float | None, float | None]:
    """Normalize a [x, y] location. Returns (x, y) or (None, None)."""
    if loc is None or len(loc) < 2:
        return None, None
    x, y = loc[0], loc[1]
    if needs_flip:
        x = flip_x(x)
        y = flip_y(y)
    return x, y


def normalize_location_3d(
    loc: list[float] | None, needs_flip: bool
) -> tuple[float | None, float | None, float | None]:
    """Normalize a [x, y, z] location. Returns (x, y, z) or Nones."""
    if loc is None or len(loc) < 2:
        return None, None, None
    x, y = loc[0], loc[1]
    z = loc[2] if len(loc) > 2 else None
    if needs_flip:
        x = flip_x(x)
        y = flip_y(y)
    return x, y, z


def extract_match_events(
    events: list[dict[str, Any]],
    team_keepers: dict[int, list[dict[str, Any]]],
    match_id: int,
    home_team: str,
    away_team: str,
    home_team_id: int,
    away_team_id: int,
) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Extract GK events, shots faced, and GK passes from a single match.

    Returns (gk_events, shots_faced, gk_passes) as lists of flat dicts.
    """
    match_label = f"{home_team} vs {away_team}"

    # Coordinate normalization:
    # StatsBomb normalizes every event so the acting team attacks toward x=120.
    # - GK events (keeper's team): keeper's goal is already at x=0. No flip.
    # - Shots (shooting team): keeper's goal is at x=120. Always flip.
    # - GK passes (keeper's team): keeper's goal at x=0. No flip.
    # No period-based inversion needed — StatsBomb handles halftime switching
    # within its per-event normalization.

    # Build a set of all keeper player_ids for quick lookup
    all_keeper_ids: set[int] = set()
    keeper_info: dict[int, dict[str, Any]] = {}  # player_id -> info
    for tid, keepers in team_keepers.items():
        for k in keepers:
            all_keeper_ids.add(k["player_id"])
            keeper_info[k["player_id"]] = k

    # Map team_id -> opposing team's keeper(s)
    opposing_keepers: dict[int, list[dict]] = {
        home_team_id: team_keepers.get(away_team_id, []),
        away_team_id: team_keepers.get(home_team_id, []),
    }

    gk_events: list[dict] = []
    shots_faced: list[dict] = []
    gk_passes: list[dict] = []

    for evt in events:
        evt_type = evt.get("type", {}).get("name", "")
        team_id = evt.get("team", {}).get("id")
        player_id = evt.get("player", {}).get("id")
        period = evt.get("period", 0)

        # ---- Goal Keeper events (type_id: 23) ----
        # Keeper's own events: goal at x=0, no flip needed.
        if evt_type == "Goal Keeper" and player_id in all_keeper_ids:
            gk = evt.get("goalkeeper", {})
            loc_x, loc_y = normalize_location(evt.get("location"), False)
            end_x, end_y = normalize_location(
                evt.get("end_location") or gk.get("end_location"), False
            )

            gk_events.append({
                "event_id": evt.get("id"),
                "match_id": match_id,
                "match_label": match_label,
                "player_id": player_id,
                "player_name": evt.get("player", {}).get("name"),
                "team_id": team_id,
                "team_name": evt.get("team", {}).get("name"),
                "minute": evt.get("minute", 0),
                "second": evt.get("second", 0),
                "period": period,
                "location_x": loc_x,
                "location_y": loc_y,
                "end_location_x": end_x,
                "end_location_y": end_y,
                "gk_type": gk.get("type", {}).get("name"),
                "gk_technique": gk.get("technique", {}).get("name"),
                "gk_body_part": gk.get("body_part", {}).get("name"),
                "gk_position": gk.get("position", {}).get("name"),
                "gk_outcome": gk.get("outcome", {}).get("name"),
            })

        # ---- Shot events (type_id: 16) ----
        # Shots are from the shooting team's perspective (attacking toward x=120).
        # The keeper's goal is at x=120, so we always flip to put it at x=0.
        elif evt_type == "Shot":
            shot = evt.get("shot", {})
            shooting_team_id = team_id
            target_keepers = opposing_keepers.get(shooting_team_id, [])
            if not target_keepers:
                continue

            shot_loc_x, shot_loc_y = normalize_location(
                evt.get("location"), True
            )
            end_x, end_y, end_z = normalize_location_3d(
                shot.get("end_location"), True
            )

            # Extract freeze frame (also flip all positions)
            freeze_frame_raw = shot.get("freeze_frame", [])
            freeze_frame: list[dict] | None = None
            keeper_ff_location: tuple[float | None, float | None] = (None, None)

            if freeze_frame_raw:
                freeze_frame = []
                for ff_player in freeze_frame_raw:
                    ff_loc = ff_player.get("location", [])
                    ff_x, ff_y = normalize_location(ff_loc, True)
                    ff_entry = {
                        "player_id": ff_player.get("player", {}).get("id"),
                        "player_name": ff_player.get("player", {}).get("name"),
                        "position": ff_player.get("position", {}).get("name"),
                        "location_x": ff_x,
                        "location_y": ff_y,
                        "teammate": ff_player.get("teammate", False),
                    }
                    freeze_frame.append(ff_entry)

                    # Find the keeper in the freeze frame
                    if ff_entry["position"] == "Goalkeeper" and not ff_entry["teammate"]:
                        keeper_ff_location = (ff_x, ff_y)

            for target_keeper in [get_active_keeper(target_keepers, period)]:
                if target_keeper is None:
                    continue
                shots_faced.append({
                    "event_id": evt.get("id"),
                    "match_id": match_id,
                    "match_label": match_label,
                    "keeper_player_id": target_keeper["player_id"],
                    "keeper_name": target_keeper["player_name"],
                    "keeper_team_id": target_keeper["team_id"],
                    "keeper_team": target_keeper["team_name"],
                    "minute": evt.get("minute", 0),
                    "second": evt.get("second", 0),
                    "period": period,
                    "shot_location_x": shot_loc_x,
                    "shot_location_y": shot_loc_y,
                    "shot_end_x": end_x,
                    "shot_end_y": end_y,
                    "shot_end_z": end_z,
                    "shot_outcome": shot.get("outcome", {}).get("name"),
                    "statsbomb_xg": shot.get("statsbomb_xg", 0.0),
                    "shot_body_part": shot.get("body_part", {}).get("name"),
                    "shot_technique": shot.get("technique", {}).get("name"),
                    "play_pattern": evt.get("play_pattern", {}).get("name"),
                    "shot_type": shot.get("type", {}).get("name"),
                    "keeper_ff_x": keeper_ff_location[0],
                    "keeper_ff_y": keeper_ff_location[1],
                    "freeze_frame_json": (
                        json.dumps(freeze_frame) if freeze_frame else None
                    ),
                })

        # ---- Pass events by goalkeepers ----
        # Keeper's own passes: goal at x=0, no flip needed.
        elif evt_type == "Pass" and player_id in all_keeper_ids:
            pass_data = evt.get("pass", {})
            start_x, start_y = normalize_location(evt.get("location"), False)
            end_loc = pass_data.get("end_location")
            end_x, end_y = normalize_location(end_loc, False)

            # Determine outcome — StatsBomb marks incomplete passes with
            # pass.outcome; complete passes have no outcome field.
            outcome_raw = pass_data.get("outcome", {}).get("name")
            outcome = outcome_raw if outcome_raw else "Complete"

            gk_passes.append({
                "event_id": evt.get("id"),
                "match_id": match_id,
                "match_label": match_label,
                "player_id": player_id,
                "player_name": evt.get("player", {}).get("name"),
                "team_id": team_id,
                "team_name": evt.get("team", {}).get("name"),
                "minute": evt.get("minute", 0),
                "second": evt.get("second", 0),
                "period": period,
                "start_x": start_x,
                "start_y": start_y,
                "end_x": end_x,
                "end_y": end_y,
                "pass_length": pass_data.get("length"),
                "outcome": outcome,
                "height": pass_data.get("height", {}).get("name"),
                "body_part": pass_data.get("body_part", {}).get("name"),
                "pass_type": pass_data.get("type", {}).get("name"),
            })

    return gk_events, shots_faced, gk_passes


def main() -> None:
    intermediate_dir = PROJECT_ROOT / OUTPUT_DIR / "intermediate"
    matches_path = intermediate_dir / "matches.parquet"

    if not matches_path.exists():
        print("ERROR: matches.parquet not found. Run 01_ingest.py first.")
        sys.exit(1)

    matches_df = pd.read_parquet(matches_path)
    print(f"Loaded {len(matches_df)} matches from index\n")

    all_gk_events: list[dict] = []
    all_shots_faced: list[dict] = []
    all_gk_passes: list[dict] = []

    for _, match in matches_df.iterrows():
        match_id = int(match["match_id"])

        try:
            events = load_events(match_id)
            lineups = load_lineups(match_id)
        except FileNotFoundError as e:
            print(f"  SKIP match {match_id}: {e}")
            continue

        team_keepers = identify_keepers(lineups)
        gk_evts, shots, passes = extract_match_events(
            events=events,
            team_keepers=team_keepers,
            match_id=match_id,
            home_team=match["home_team"],
            away_team=match["away_team"],
            home_team_id=int(match["home_team_id"]),
            away_team_id=int(match["away_team_id"]),
        )
        all_gk_events.extend(gk_evts)
        all_shots_faced.extend(shots)
        all_gk_passes.extend(passes)

        if (match.name + 1) % 10 == 0:
            print(f"  Processed {match.name + 1}/{len(matches_df)} matches...")

    # Convert to DataFrames and save
    gk_events_df = pd.DataFrame(all_gk_events)
    shots_df = pd.DataFrame(all_shots_faced)
    passes_df = pd.DataFrame(all_gk_passes)

    gk_events_df.to_parquet(intermediate_dir / "gk_events.parquet", index=False)
    shots_df.to_parquet(intermediate_dir / "shots_faced.parquet", index=False)
    passes_df.to_parquet(intermediate_dir / "gk_passes.parquet", index=False)

    print(f"\nExtraction complete:")
    print(f"  GK events:  {len(gk_events_df)}")
    print(f"  Shots faced: {len(shots_df)}")
    print(f"  GK passes:  {len(passes_df)}")

    # Quick summary of keepers found
    if not shots_df.empty:
        keeper_summary = (
            shots_df.groupby(["keeper_player_id", "keeper_name", "keeper_team"])
            .size()
            .reset_index(name="shots_faced")
            .sort_values("shots_faced", ascending=False)
        )
        print(f"\nKeepers found ({len(keeper_summary)}):")
        for _, row in keeper_summary.head(10).iterrows():
            print(
                f"  {row['keeper_name']:25s} ({row['keeper_team']:20s}) — "
                f"{row['shots_faced']} shots faced"
            )
        if len(keeper_summary) > 10:
            print(f"  ... and {len(keeper_summary) - 10} more")


if __name__ == "__main__":
    main()
