"""
Pipeline configuration.

Competition/season IDs come from StatsBomb's competitions.json.
Add entries here to process additional competitions — the pipeline
scripts iterate over COMPETITIONS and produce output for each.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CompetitionConfig:
    competition_id: int
    season_id: int
    competition_name: str
    season_name: str


# ---- Competitions to process ------------------------------------------------

COMPETITIONS: list[CompetitionConfig] = [
    CompetitionConfig(
        competition_id=43,
        season_id=3,
        competition_name="FIFA World Cup",
        season_name="2018",
    ),
    # Uncomment to add 2022 World Cup in Milestone 7:
    # CompetitionConfig(
    #     competition_id=43,
    #     season_id=106,
    #     competition_name="FIFA World Cup",
    #     season_name="2022",
    # ),
]

# ---- Paths ------------------------------------------------------------------

# Root of the cloned statsbomb/open-data repo (relative to project root)
RAW_DATA_DIR = Path("data-pipeline/raw")

# Pipeline output — these JSONs get copied to frontend/public/data/
OUTPUT_DIR = Path("data-pipeline/output")

# Frontend data directory (for CI copy step)
FRONTEND_DATA_DIR = Path("frontend/public/data")

# ---- Thresholds -------------------------------------------------------------

# Keepers with fewer minutes than this are excluded from the overview rankings.
# Two full matches = 180 min. This filters out keepers who only appeared as
# late substitutes or in a single group-stage dead rubber.
MIN_MINUTES_THRESHOLD = 180

# ---- Coordinate constants ---------------------------------------------------

PITCH_LENGTH = 120.0  # StatsBomb x-axis
PITCH_WIDTH = 80.0    # StatsBomb y-axis

GOAL_WIDTH_YARDS = 8.0
GOAL_HEIGHT_FEET = 8.0

# Goal center in normalized coords (keeper's goal at x=0)
GOAL_CENTER_Y = 40.0  # center of pitch width
GOAL_Y_MIN = 36.0     # left post (from keeper's perspective facing field)
GOAL_Y_MAX = 44.0     # right post

# Pass length thresholds (StatsBomb units)
SHORT_PASS_MAX = 25.0
MEDIUM_PASS_MAX = 50.0

# Progressive pass: must advance ball >= this many units toward opponent goal
PROGRESSIVE_THRESHOLD = 10.0

# Direction buckets (by y-coordinate of end location)
# Left third: y < 26.67, Center: 26.67-53.33, Right: > 53.33
DIRECTION_LEFT_MAX = PITCH_WIDTH / 3
DIRECTION_RIGHT_MIN = 2 * PITCH_WIDTH / 3
