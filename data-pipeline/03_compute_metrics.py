"""
Step 3: Compute derived goalkeeper metrics.

Reads intermediate parquet files from step 2, enriches individual events
with derived fields (shot zones, goal frame coords, pass categories), and
computes per-keeper aggregated statistics for every metric in the schema.

Output:
    {OUTPUT_DIR}/intermediate/shots_enriched.parquet
    {OUTPUT_DIR}/intermediate/passes_enriched.parquet
    {OUTPUT_DIR}/intermediate/sweeping.parquet
    {OUTPUT_DIR}/intermediate/keeper_summaries.parquet
    {OUTPUT_DIR}/intermediate/keeper_matches.parquet

Usage:
    python 03_compute_metrics.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (
    OUTPUT_DIR,
    PITCH_WIDTH,
    GOAL_Y_MIN,
    GOAL_WIDTH_YARDS,
    GOAL_HEIGHT_FEET,
    SHORT_PASS_MAX,
    MEDIUM_PASS_MAX,
    PROGRESSIVE_THRESHOLD,
    DIRECTION_LEFT_MAX,
    DIRECTION_RIGHT_MIN,
)


INTERMEDIATE_DIR = PROJECT_ROOT / OUTPUT_DIR / "intermediate"

# Goal frame: crossbar height in StatsBomb z-units (meters)
CROSSBAR_HEIGHT_M = 2.44

# GK event subtypes that count as sweeping/claiming actions
SWEEP_TYPES = {
    "Keeper Sweep", "Collected", "Smother",
    "Punch (One Hand)", "Punch (Two Hands)",
    "Clear", "Keeper Pick-Up",
}

# Outcomes considered successful for sweeping actions
SUCCESS_OUTCOMES = {
    "Success", "Won", "Claim", "Clear",
    "Touched Out", "Success In Play", "Success Out",
    "Collected Twice", "In Play Safe",
}

FAILURE_OUTCOMES = {
    "Lost", "In Play Danger", "Fail",
    "No Touch", "Missed",
}


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_intermediate() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    shots = pd.read_parquet(INTERMEDIATE_DIR / "shots_faced.parquet")
    gk_events = pd.read_parquet(INTERMEDIATE_DIR / "gk_events.parquet")
    passes = pd.read_parquet(INTERMEDIATE_DIR / "gk_passes.parquet")
    matches = pd.read_parquet(INTERMEDIATE_DIR / "matches.parquet")
    return shots, gk_events, passes, matches


# ---------------------------------------------------------------------------
# Shot enrichment
# ---------------------------------------------------------------------------

def classify_shot_zone(x: float, y: float) -> str:
    """Classify shot origin into a spatial zone (keeper's goal at x=0)."""
    if x <= 6:
        return "Six-Yard Box"
    if x <= 18:
        if 18 <= y <= 62:
            return "Box Central"
        return "Box Wide"
    return "Outside Box"


def compute_goal_frame_coords(
    end_y: float | None, end_z: float | None
) -> tuple[float | None, float | None]:
    """
    Map shot end location to goal frame coordinates.

    gf_x: 0-8 (left to right post, yards)
    gf_y: 0-8 (ground to crossbar, mapped from meters)
    """
    if end_y is None or pd.isna(end_y):
        return None, None

    gf_x = end_y - GOAL_Y_MIN
    gf_x = max(0.0, min(GOAL_WIDTH_YARDS, gf_x))

    if end_z is None or pd.isna(end_z):
        gf_y = None
    else:
        gf_y = (end_z / CROSSBAR_HEIGHT_M) * GOAL_HEIGHT_FEET
        gf_y = max(0.0, min(GOAL_HEIGHT_FEET, gf_y))

    return gf_x, gf_y


def classify_goal_frame_zone(gf_x: float | None, gf_y: float | None) -> str | None:
    """Classify into 2x3 goal frame grid."""
    if gf_x is None or gf_y is None:
        return None

    third = GOAL_WIDTH_YARDS / 3
    if gf_x < third:
        h = "Left"
    elif gf_x < 2 * third:
        h = "Center"
    else:
        h = "Right"

    v = "Bottom" if gf_y < GOAL_HEIGHT_FEET / 2 else "Top"
    return f"{v} {h}"


def enrich_shots(shots: pd.DataFrame, gk_events: pd.DataFrame) -> pd.DataFrame:
    """Add derived fields to each shot: zone, goal frame, GK action details."""
    df = shots.copy()

    # Shot zone
    df["shot_zone"] = [
        classify_shot_zone(r["shot_location_x"], r["shot_location_y"])
        for _, r in df.iterrows()
    ]

    # Goal frame coordinates (only for on-target shots)
    on_target_outcomes = {"Goal", "Saved", "Saved To Post", "Saved Off Target"}
    gf_x_list, gf_y_list, gf_zone_list = [], [], []
    for _, r in df.iterrows():
        if r["shot_outcome"] in on_target_outcomes:
            gf_x, gf_y = compute_goal_frame_coords(r["shot_end_y"], r["shot_end_z"])
            gf_zone = classify_goal_frame_zone(gf_x, gf_y)
        else:
            gf_x, gf_y, gf_zone = None, None, None
        gf_x_list.append(gf_x)
        gf_y_list.append(gf_y)
        gf_zone_list.append(gf_zone)

    df["gf_x"] = gf_x_list
    df["gf_y"] = gf_y_list
    df["goal_frame_zone"] = gf_zone_list

    # Join GK event details (technique, body part, position) onto shots.
    save_concede_types = {
        "Shot Saved", "Shot Saved Off Target", "Shot Saved to Post",
        "Goal Conceded", "Penalty Saved",
    }
    gk_save = gk_events[gk_events["gk_type"].isin(save_concede_types)].copy()

    df = df.merge(
        gk_save[["match_id", "minute", "player_id",
                  "gk_type", "gk_technique", "gk_body_part", "gk_position"]].rename(
            columns={
                "gk_type": "gk_action_type",
                "gk_technique": "_gk_technique",
                "gk_body_part": "_gk_body_part",
                "gk_position": "_gk_position",
            }
        ),
        left_on=["match_id", "minute", "keeper_player_id"],
        right_on=["match_id", "minute", "player_id"],
        how="left",
        suffixes=("", "_gk"),
    )
    df["gk_technique"] = df.get("_gk_technique")
    df["gk_body_part"] = df.get("_gk_body_part")
    df["gk_position"] = df.get("_gk_position")
    df.drop(columns=[c for c in df.columns if c.startswith("_gk_") or c == "player_id_gk"],
            errors="ignore", inplace=True)
    df = df.drop_duplicates(subset=["event_id"], keep="first")

    print(f"  Shots enriched: {len(df)} rows")
    print(f"  GK details joined: {df['gk_action_type'].notna().sum()} / {len(df)}")
    return df


# ---------------------------------------------------------------------------
# Pass enrichment
# ---------------------------------------------------------------------------

def enrich_passes(passes: pd.DataFrame) -> pd.DataFrame:
    df = passes.copy()

    df["pass_length_category"] = pd.cut(
        df["pass_length"],
        bins=[0, SHORT_PASS_MAX, MEDIUM_PASS_MAX, float("inf")],
        labels=["Short", "Medium", "Long"],
        right=True,
    )

    df["direction"] = pd.cut(
        df["end_y"],
        bins=[0, DIRECTION_LEFT_MAX, DIRECTION_RIGHT_MIN, PITCH_WIDTH],
        labels=["Left", "Center", "Right"],
        include_lowest=True,
    )

    # Progressive: advanced ball >= threshold toward opponent goal (increasing x)
    df["is_progressive"] = (df["end_x"] - df["start_x"]) >= PROGRESSIVE_THRESHOLD
    df["outcome"] = df["outcome"].fillna("Complete")

    print(f"  Passes enriched: {len(df)} rows")
    return df


# ---------------------------------------------------------------------------
# Sweeping extraction
# ---------------------------------------------------------------------------

def extract_sweeping(gk_events: pd.DataFrame) -> pd.DataFrame:
    df = gk_events[gk_events["gk_type"].isin(SWEEP_TYPES)].copy()

    df["action_type"] = df["gk_type"].replace({
        "Punch (One Hand)": "Punch",
        "Punch (Two Hands)": "Punch",
    })
    df["distance_from_goal"] = df["location_x"]

    def classify_outcome(outcome) -> bool:
        if outcome is None or (isinstance(outcome, float) and pd.isna(outcome)):
            return True
        return str(outcome) in SUCCESS_OUTCOMES or str(outcome) not in FAILURE_OUTCOMES

    df["outcome_success"] = df["gk_outcome"].apply(classify_outcome)

    print(f"  Sweeping actions extracted: {len(df)} rows")
    return df


# ---------------------------------------------------------------------------
# Keeper match appearances and minutes
# ---------------------------------------------------------------------------

def compute_keeper_matches(
    shots: pd.DataFrame,
    gk_events: pd.DataFrame,
    passes: pd.DataFrame,
    matches: pd.DataFrame,
) -> pd.DataFrame:
    # Match duration from max period in events
    all_periods = pd.concat([
        gk_events[["match_id", "period"]],
        shots[["match_id", "period"]],
        passes[["match_id", "period"]],
    ])
    match_has_et = all_periods.groupby("match_id")["period"].max() >= 3
    match_duration = match_has_et.map({True: 120, False: 90}).rename("match_duration")

    # Unique keeper-match pairs
    keeper_shots = shots[["keeper_player_id", "keeper_name", "keeper_team", "match_id"]].rename(
        columns={"keeper_player_id": "player_id", "keeper_name": "player_name", "keeper_team": "team_name"}
    )
    keeper_gk = gk_events[["player_id", "player_name", "team_name", "match_id"]]
    keeper_pass = passes[["player_id", "player_name", "team_name", "match_id"]]

    appearances = (
        pd.concat([keeper_shots, keeper_gk, keeper_pass])
        .drop_duplicates(subset=["player_id", "match_id"])
        .merge(match_duration, left_on="match_id", right_index=True)
    )

    keeper_matches = (
        appearances.groupby(["player_id", "player_name", "team_name"])
        .agg(matches_played=("match_id", "nunique"), minutes_played=("match_duration", "sum"))
        .reset_index()
    )

    # Clean sheets
    goals_per_match = (
        shots[shots["shot_outcome"] == "Goal"]
        .groupby(["keeper_player_id", "match_id"]).size()
        .reset_index(name="goals")
    )
    all_km = appearances[["player_id", "match_id"]].drop_duplicates()
    all_km = all_km.merge(
        goals_per_match, left_on=["player_id", "match_id"],
        right_on=["keeper_player_id", "match_id"], how="left",
    )
    all_km["goals"] = all_km["goals"].fillna(0)
    clean_sheets = (
        all_km[all_km["goals"] == 0].groupby("player_id").size().rename("clean_sheets")
    )
    keeper_matches = keeper_matches.merge(clean_sheets, left_on="player_id", right_index=True, how="left")
    keeper_matches["clean_sheets"] = keeper_matches["clean_sheets"].fillna(0).astype(int)

    print(f"  Keeper appearances computed: {len(keeper_matches)} keepers")
    return keeper_matches


# ---------------------------------------------------------------------------
# Per-keeper aggregation helpers
# ---------------------------------------------------------------------------

def safe_rate(num: int, denom: int) -> float | None:
    return num / denom if denom > 0 else None


def compute_shot_stopping(k_shots: pd.DataFrame, k_gk: pd.DataFrame) -> dict:
    n = len(k_shots)
    on_target = k_shots[k_shots["shot_outcome"].isin(["Goal", "Saved"])]
    n_on = len(on_target)
    goals = int((k_shots["shot_outcome"] == "Goal").sum())
    saves = int((k_shots["shot_outcome"] == "Saved").sum())
    xg = float(k_shots["statsbomb_xg"].sum())

    # Zone save rates
    zone_rates = {}
    for zone in ["Six-Yard Box", "Box Central", "Box Wide", "Outside Box"]:
        z = k_shots[k_shots["shot_zone"] == zone]
        z_on = z[z["shot_outcome"].isin(["Goal", "Saved"])]
        z_saves = int((z["shot_outcome"] == "Saved").sum())
        zone_rates[zone] = safe_rate(z_saves, len(z_on))

    # Goal frame zone save rates
    gf_rates = {}
    for zone in ["Top Left", "Top Center", "Top Right",
                  "Bottom Left", "Bottom Center", "Bottom Right"]:
        z = k_shots[k_shots["goal_frame_zone"] == zone]
        z_on = z[z["shot_outcome"].isin(["Goal", "Saved"])]
        z_saves = int((z["shot_outcome"] == "Saved").sum())
        gf_rates[zone] = safe_rate(z_saves, len(z_on))

    # Technique / body part / position from GK save events
    save_evts = k_gk[k_gk["gk_type"].str.contains("Saved", na=False)]
    tech = save_evts["gk_technique"].value_counts()
    bp = save_evts["gk_body_part"].value_counts()
    pos = save_evts["gk_position"].value_counts()

    saves_both = int(bp.get("Both Hands", 0))
    saves_left = int(bp.get("Left Hand", 0))
    saves_right = int(bp.get("Right Hand", 0))
    saves_feet = int(bp.get("Left Foot", 0)) + int(bp.get("Right Foot", 0))
    saves_other = max(0, saves - saves_both - saves_left - saves_right - saves_feet)

    return {
        "shots_faced": n,
        "shots_on_target_faced": n_on,
        "saves": saves,
        "goals_conceded": goals,
        "save_percentage": round(safe_rate(saves, n_on) or 0.0, 3),
        "xg_faced": round(xg, 2),
        "goals_minus_xg": round(goals - xg, 2),
        "save_rate_six_yard": zone_rates.get("Six-Yard Box"),
        "save_rate_box_central": zone_rates.get("Box Central"),
        "save_rate_box_wide": zone_rates.get("Box Wide"),
        "save_rate_outside_box": zone_rates.get("Outside Box"),
        "save_rate_top_left": gf_rates.get("Top Left"),
        "save_rate_top_center": gf_rates.get("Top Center"),
        "save_rate_top_right": gf_rates.get("Top Right"),
        "save_rate_bottom_left": gf_rates.get("Bottom Left"),
        "save_rate_bottom_center": gf_rates.get("Bottom Center"),
        "save_rate_bottom_right": gf_rates.get("Bottom Right"),
        "diving_saves": int(tech.get("Diving", 0)),
        "standing_saves": int(tech.get("Standing", 0)),
        "saves_both_hands": saves_both,
        "saves_left_hand": saves_left,
        "saves_right_hand": saves_right,
        "saves_feet": saves_feet,
        "saves_other": saves_other,
        "position_set": int(pos.get("Set", 0)),
        "position_moving": int(pos.get("Moving", 0)),
        "position_prone": int(pos.get("Prone", 0)),
    }


def compute_distribution(k_passes: pd.DataFrame) -> dict:
    total = len(k_passes)
    if total == 0:
        return {
            "total_passes": 0, "completion_rate": 0.0,
            "short_passes": 0, "short_accuracy": 0.0,
            "medium_passes": 0, "medium_accuracy": 0.0,
            "long_passes": 0, "long_accuracy": 0.0,
            "goal_kicks": 0, "goal_kick_avg_length": 0.0,
            "throws": 0, "throw_accuracy": 0.0,
            "open_play_passes": 0, "open_play_accuracy": 0.0,
            "pct_left": 0.0, "pct_center": 0.0, "pct_right": 0.0,
            "progressive_passes": 0, "progressive_pass_rate": 0.0,
        }

    complete = int((k_passes["outcome"] == "Complete").sum())

    length_stats = {}
    for cat in ["Short", "Medium", "Long"]:
        c = k_passes[k_passes["pass_length_category"] == cat]
        c_ok = int((c["outcome"] == "Complete").sum())
        length_stats[cat] = {"count": len(c), "accuracy": round(safe_rate(c_ok, len(c)) or 0.0, 3)}

    gk_kicks = k_passes[k_passes["pass_type"] == "Goal Kick"]
    throws = k_passes[k_passes["body_part"] == "Keeper Throw"]
    # Open play: no special pass_type
    open_play = k_passes[k_passes["pass_type"].isna() | (k_passes["pass_type"] == "")]

    throw_ok = int((throws["outcome"] == "Complete").sum())
    op_ok = int((open_play["outcome"] == "Complete").sum())

    dir_counts = k_passes["direction"].value_counts()
    dir_total = dir_counts.sum() or 1
    progressive = int(k_passes["is_progressive"].sum())

    return {
        "total_passes": total,
        "completion_rate": round(safe_rate(complete, total) or 0.0, 3),
        "short_passes": length_stats["Short"]["count"],
        "short_accuracy": length_stats["Short"]["accuracy"],
        "medium_passes": length_stats["Medium"]["count"],
        "medium_accuracy": length_stats["Medium"]["accuracy"],
        "long_passes": length_stats["Long"]["count"],
        "long_accuracy": length_stats["Long"]["accuracy"],
        "goal_kicks": len(gk_kicks),
        "goal_kick_avg_length": round(float(gk_kicks["pass_length"].mean()), 1) if len(gk_kicks) > 0 else 0.0,
        "throws": len(throws),
        "throw_accuracy": round(safe_rate(throw_ok, len(throws)) or 0.0, 3),
        "open_play_passes": len(open_play),
        "open_play_accuracy": round(safe_rate(op_ok, len(open_play)) or 0.0, 3),
        "pct_left": round(int(dir_counts.get("Left", 0)) / dir_total, 3),
        "pct_center": round(int(dir_counts.get("Center", 0)) / dir_total, 3),
        "pct_right": round(int(dir_counts.get("Right", 0)) / dir_total, 3),
        "progressive_passes": progressive,
        "progressive_pass_rate": round(safe_rate(progressive, total) or 0.0, 3),
    }


def compute_sweeping_profile(k_sweep: pd.DataFrame) -> dict:
    total = len(k_sweep)
    if total == 0:
        return {
            "total_actions": 0, "avg_distance_from_goal": 0.0,
            "max_distance_from_goal": 0.0, "success_rate": 0.0,
            "sweeps": 0, "collections": 0, "smothers": 0,
            "punches": 0, "clears": 0, "pick_ups": 0,
            "aerial_attempts": 0, "aerial_success_rate": 0.0,
        }

    distances = k_sweep["distance_from_goal"]
    successes = int(k_sweep["outcome_success"].sum())
    tc = k_sweep["action_type"].value_counts()

    aerial = k_sweep[k_sweep["action_type"].isin(["Collected", "Punch"])]
    aerial_ok = int(aerial["outcome_success"].sum())

    return {
        "total_actions": total,
        "avg_distance_from_goal": round(float(distances.mean()), 1),
        "max_distance_from_goal": round(float(distances.max()), 1),
        "success_rate": round(safe_rate(successes, total) or 0.0, 3),
        "sweeps": int(tc.get("Keeper Sweep", 0)),
        "collections": int(tc.get("Collected", 0)),
        "smothers": int(tc.get("Smother", 0)),
        "punches": int(tc.get("Punch", 0)),
        "clears": int(tc.get("Clear", 0)),
        "pick_ups": int(tc.get("Keeper Pick-Up", 0)),
        "aerial_attempts": len(aerial),
        "aerial_success_rate": round(safe_rate(aerial_ok, len(aerial)) or 0.0, 3),
    }


# ---------------------------------------------------------------------------
# Radar profiles (percentile ranks)
# ---------------------------------------------------------------------------

def compute_radar_profiles(summaries: list[dict]) -> list[dict]:
    """Percentile-rank radar values 0-1. Higher is always better."""
    df = pd.DataFrame(summaries)

    def pctile(series: pd.Series, higher_better: bool = True) -> pd.Series:
        if series.nunique() <= 1:
            return pd.Series(0.5, index=series.index)
        r = series.rank(pct=True, method="average")
        return r if higher_better else (1 - r)

    radar = pd.DataFrame({
        "save_percentage": pctile(df["save_percentage"]),
        "goals_minus_xg": pctile(df["goals_minus_xg"], higher_better=False),
        "short_pass_accuracy": pctile(df["short_accuracy"]),
        "long_pass_accuracy": pctile(df["long_accuracy"]),
        "progressive_pass_rate": pctile(df["progressive_pass_rate"]),
        "sweep_distance": pctile(df["avg_sweep_distance"]),
        "claiming_success": pctile(df["aerial_success_rate"]),
        "shot_stopping_rate_in_box": pctile(df["save_rate_in_box"]),
    })
    return radar.round(3).to_dict("records")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("Loading intermediate data...")
    shots, gk_events, passes, matches = load_intermediate()

    print("\nEnriching events:")
    shots = enrich_shots(shots, gk_events)
    passes = enrich_passes(passes)
    sweeping = extract_sweeping(gk_events)

    print("\nComputing keeper appearances...")
    keeper_matches = compute_keeper_matches(shots, gk_events, passes, matches)

    print("\nComputing per-keeper summaries...")
    summaries: list[dict] = []

    for _, km in keeper_matches.iterrows():
        pid = km["player_id"]

        k_shots = shots[shots["keeper_player_id"] == pid]
        k_gk = gk_events[gk_events["player_id"] == pid]
        k_passes = passes[passes["player_id"] == pid]
        k_sweep = sweeping[sweeping["player_id"] == pid]

        ss = compute_shot_stopping(k_shots, k_gk)
        dist = compute_distribution(k_passes)
        sw = compute_sweeping_profile(k_sweep)

        # In-box save rate for radar
        box_shots = k_shots[k_shots["shot_zone"].isin(["Six-Yard Box", "Box Central", "Box Wide"])]
        box_on = box_shots[box_shots["shot_outcome"].isin(["Goal", "Saved"])]
        box_saves = int((box_shots["shot_outcome"] == "Saved").sum())

        summaries.append({
            "player_id": pid,
            "player_name": km["player_name"],
            "team_name": km["team_name"],
            "matches_played": int(km["matches_played"]),
            "minutes_played": int(km["minutes_played"]),
            "clean_sheets": int(km["clean_sheets"]),
            "save_percentage": ss["save_percentage"],
            "goals_minus_xg": ss["goals_minus_xg"],
            "short_accuracy": dist["short_accuracy"],
            "long_accuracy": dist["long_accuracy"],
            "progressive_pass_rate": dist["progressive_pass_rate"],
            "avg_sweep_distance": sw["avg_distance_from_goal"],
            "aerial_success_rate": sw["aerial_success_rate"],
            "save_rate_in_box": safe_rate(box_saves, len(box_on)) or 0.0,
            "shot_stopping_json": json.dumps(ss),
            "distribution_json": json.dumps(dist),
            "sweeping_json": json.dumps(sw),
        })

    radar_profiles = compute_radar_profiles(summaries)
    for i, s in enumerate(summaries):
        s["radar_json"] = json.dumps(radar_profiles[i])

    summaries_df = pd.DataFrame(summaries)

    # Save
    shots.to_parquet(INTERMEDIATE_DIR / "shots_enriched.parquet", index=False)
    passes.to_parquet(INTERMEDIATE_DIR / "passes_enriched.parquet", index=False)
    sweeping.to_parquet(INTERMEDIATE_DIR / "sweeping.parquet", index=False)
    keeper_matches.to_parquet(INTERMEDIATE_DIR / "keeper_matches.parquet", index=False)
    summaries_df.to_parquet(INTERMEDIATE_DIR / "keeper_summaries.parquet", index=False)

    print(f"\nMetrics complete:")
    print(f"  Enriched shots:    {len(shots)}")
    print(f"  Enriched passes:   {len(passes)}")
    print(f"  Sweeping actions:  {len(sweeping)}")
    print(f"  Keeper summaries:  {len(summaries_df)}")

    # Print top keepers by goals_minus_xg
    top = summaries_df.nsmallest(5, "goals_minus_xg")
    print(f"\nTop 5 keepers by goals - xG (lower = better):")
    for _, row in top.iterrows():
        print(
            f"  {row['player_name']:25s} ({row['team_name']:15s}) "
            f"goals-xG: {row['goals_minus_xg']:+.2f}  "
            f"save%: {row['save_percentage']:.1%}  "
            f"minutes: {row['minutes_played']}"
        )


if __name__ == "__main__":
    main()