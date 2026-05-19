"""
Output schemas for the goalkeeper analysis pipeline.

These dataclasses define the contract between the Python pipeline and the
Next.js frontend. Every JSON file the pipeline writes must conform to one
of these shapes. The matching TypeScript interfaces live in
frontend/src/lib/types.ts.

Coordinate convention (post-normalization):
    - The keeper's goal is always at x=0, y=40 (center of goal line).
    - The opponent's goal is at x=120.
    - Pitch dimensions: 120 x 80 (StatsBomb standard).
    - All coordinates in this file are NORMALIZED — the pipeline handles
      flipping raw StatsBomb coords when the keeper's team attacks
      right-to-left.

Goal frame convention:
    - Origin (0, 0) is the bottom-left post from the keeper's perspective
      (facing the field).
    - Width: 8 yards (approx 7.32m), mapped to range [0, 8].
    - Height: 8 feet (approx 2.44m), mapped to range [0, 8].
    - Derived from shot.end_location [x, y, z] where y gives horizontal
      position and z gives height. The pipeline maps these to goal-frame-
      relative coords.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# Enums — string values match what the frontend expects in filter controls
# ---------------------------------------------------------------------------

class ShotOutcome(str, Enum):
    GOAL = "Goal"
    SAVED = "Saved"
    OFF_TARGET = "Off Target"
    BLOCKED = "Blocked"
    POST = "Post"
    WAYWARD = "Wayward"


class ShotZone(str, Enum):
    """Spatial zone the shot was taken from, relative to the keeper's goal."""
    SIX_YARD_BOX = "Six-Yard Box"       # x: 0-6
    INSIDE_BOX_CENTRAL = "Box Central"   # x: 6-18, y: 18-62
    INSIDE_BOX_WIDE = "Box Wide"         # x: 6-18, y: 0-18 or 62-80
    OUTSIDE_BOX = "Outside Box"          # x: 18+


class GoalFrameZone(str, Enum):
    """Which sector of the goal the shot was aimed at (2x3 grid)."""
    TOP_LEFT = "Top Left"
    TOP_CENTER = "Top Center"
    TOP_RIGHT = "Top Right"
    BOTTOM_LEFT = "Bottom Left"
    BOTTOM_CENTER = "Bottom Center"
    BOTTOM_RIGHT = "Bottom Right"


class PlayPattern(str, Enum):
    REGULAR_PLAY = "Regular Play"
    FROM_CORNER = "From Corner"
    FROM_FREE_KICK = "From Free Kick"
    FROM_COUNTER = "From Counter"
    FROM_THROW_IN = "From Throw In"
    FROM_GOAL_KICK = "From Goal Kick"
    FROM_KEEPER = "From Keeper"
    OTHER = "Other"


class PassLength(str, Enum):
    SHORT = "Short"    # < 25 StatsBomb units
    MEDIUM = "Medium"  # 25-50
    LONG = "Long"      # > 50


class PassOutcome(str, Enum):
    COMPLETE = "Complete"
    INCOMPLETE = "Incomplete"
    OUT = "Out"
    INJURY_CLEARANCE = "Injury Clearance"
    UNKNOWN = "Unknown"


class SweepActionType(str, Enum):
    KEEPER_SWEEP = "Keeper Sweep"
    COLLECTED = "Collected"
    SMOTHER = "Smother"
    PUNCH = "Punch"
    CLEAR = "Clear"
    KEEPER_PICK_UP = "Keeper Pick-Up"


# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------

@dataclass
class Coord2D:
    x: float
    y: float


@dataclass
class Coord3D:
    x: float
    y: float
    z: float


@dataclass
class GoalFrameCoord:
    """Position on the goal frame. gf_x: 0-8 (left to right), gf_y: 0-8 (bottom to top)."""
    gf_x: float
    gf_y: float


@dataclass
class FreezeFramePlayer:
    player_id: int
    player_name: str
    position: str          # "Goalkeeper", "Centre Back", etc.
    location: Coord2D
    teammate: bool         # teammate of the SHOOTING team


# ---------------------------------------------------------------------------
# competitions.json — top-level index
# ---------------------------------------------------------------------------

@dataclass
class CompetitionInfo:
    competition_id: int
    season_id: int
    competition_name: str  # "FIFA World Cup"
    season_name: str       # "2018"
    match_count: int
    keeper_count: int


@dataclass
class CompetitionsFile:
    """Shape of /data/competitions.json"""
    competitions: list[CompetitionInfo]


# ---------------------------------------------------------------------------
# keepers.json — one per competition, used by the overview table
# ---------------------------------------------------------------------------

@dataclass
class KeeperOverviewRow:
    player_id: int
    player_name: str
    team: str
    matches_played: int
    minutes_played: int
    shots_faced: int
    shots_on_target_faced: int
    saves: int
    goals_conceded: int
    save_percentage: float        # saves / shots_on_target_faced, 0-1
    xg_faced: float               # sum of statsbomb_xg for shots against
    goals_minus_xg: float         # goals_conceded - xg_faced (negative = outperforming)
    clean_sheets: int
    # Distribution summary (for overview sorting)
    pass_completion_pct: float    # 0-1
    # Sweeping summary
    sweeper_actions: int
    avg_sweep_distance: float     # avg distance from goal line in SB units


@dataclass
class KeepersFile:
    """Shape of /data/{competition_id}/keepers.json"""
    competition_id: int
    season_id: int
    competition_name: str
    season_name: str
    min_minutes_threshold: int    # keepers below this are excluded from rankings
    keepers: list[KeeperOverviewRow]


# ---------------------------------------------------------------------------
# shots.json — one per keeper, every shot faced
# ---------------------------------------------------------------------------

@dataclass
class ShotFaced:
    event_id: str                 # StatsBomb event UUID
    match_id: int
    match_label: str              # "France vs Croatia" — for display
    minute: int
    second: int
    period: int                   # 1 = first half, 2 = second half, 3/4 = extra time
    # Shot info (from the attacker's event)
    shot_location: Coord2D        # where the shot was taken (normalized)
    shot_end_location: Coord3D | None  # where the shot ended up (x, y, z)
    goal_frame_location: GoalFrameCoord | None  # mapped to goal frame (only for on-target shots)
    goal_frame_zone: GoalFrameZone | None
    shot_outcome: ShotOutcome
    shot_zone: ShotZone           # spatial zone of the shot origin
    statsbomb_xg: float
    shot_body_part: str           # "Right Foot", "Left Foot", "Head"
    shot_technique: str           # "Normal", "Volley", "Half Volley", etc.
    play_pattern: PlayPattern
    # GK action info (from the keeper's event, if present)
    gk_action_type: str | None    # "Shot Saved", "Goal Conceded", etc.
    gk_technique: str | None      # "Diving", "Standing"
    gk_body_part: str | None      # "Both Hands", "Right Hand", etc.
    gk_position: str | None       # "Set", "Moving", "Prone"
    # Freeze frame (optional — not all shots have it)
    keeper_location: Coord2D | None        # keeper's position at moment of shot
    freeze_frame: list[FreezeFramePlayer] | None


@dataclass
class ShotsFile:
    """Shape of /data/{competition_id}/{keeper_id}/shots.json"""
    player_id: int
    player_name: str
    team: str
    competition_id: int
    shots: list[ShotFaced]


# ---------------------------------------------------------------------------
# distribution.json — one per keeper, every pass
# ---------------------------------------------------------------------------

@dataclass
class KeeperPass:
    event_id: str
    match_id: int
    match_label: str
    minute: int
    second: int
    period: int
    start_location: Coord2D       # normalized
    end_location: Coord2D         # normalized
    pass_length: float            # StatsBomb units (Euclidean distance)
    pass_length_category: PassLength
    outcome: PassOutcome
    height: str                   # "Ground Pass", "Low Pass", "High Pass"
    body_part: str                # "Right Foot", "Left Foot", "Keeper Throw"
    pass_type: str | None         # "Goal Kick", "Kick Off", "Free Kick", or null for open play
    is_progressive: bool          # moved ball ≥10 units toward opponent's goal
    direction: str                # "Left", "Center", "Right" based on end_location.y


@dataclass
class DistributionFile:
    """Shape of /data/{competition_id}/{keeper_id}/distribution.json"""
    player_id: int
    player_name: str
    team: str
    competition_id: int
    passes: list[KeeperPass]


# ---------------------------------------------------------------------------
# sweeping.json — one per keeper, off-line actions
# ---------------------------------------------------------------------------

@dataclass
class SweepAction:
    event_id: str
    match_id: int
    match_label: str
    minute: int
    second: int
    period: int
    location: Coord2D             # normalized
    action_type: SweepActionType
    outcome_success: bool
    distance_from_goal: float     # x-coordinate = distance from goal line (since goal is at x=0)


@dataclass
class SweepingFile:
    """Shape of /data/{competition_id}/{keeper_id}/sweeping.json"""
    player_id: int
    player_name: str
    team: str
    competition_id: int
    actions: list[SweepAction]


# ---------------------------------------------------------------------------
# summary.json — one per keeper, pre-aggregated stats for the detail views
# ---------------------------------------------------------------------------

@dataclass
class ShotStoppingProfile:
    shots_faced: int
    shots_on_target_faced: int
    saves: int
    goals_conceded: int
    save_percentage: float
    xg_faced: float
    goals_minus_xg: float
    # By zone
    save_rate_six_yard: float | None     # null if 0 shots from that zone
    save_rate_box_central: float | None
    save_rate_box_wide: float | None
    save_rate_outside_box: float | None
    # By goal frame zone (save rates)
    save_rate_top_left: float | None
    save_rate_top_center: float | None
    save_rate_top_right: float | None
    save_rate_bottom_left: float | None
    save_rate_bottom_center: float | None
    save_rate_bottom_right: float | None
    # Technique breakdown (counts)
    diving_saves: int
    standing_saves: int
    # Body part breakdown (counts)
    saves_both_hands: int
    saves_left_hand: int
    saves_right_hand: int
    saves_feet: int
    saves_other: int              # chest, head, etc.
    # Position at shot (counts)
    position_set: int
    position_moving: int
    position_prone: int


@dataclass
class DistributionProfile:
    total_passes: int
    completion_rate: float        # 0-1
    # By length
    short_passes: int
    short_accuracy: float
    medium_passes: int
    medium_accuracy: float
    long_passes: int
    long_accuracy: float
    # By type
    goal_kicks: int
    goal_kick_avg_length: float
    throws: int
    throw_accuracy: float
    open_play_passes: int
    open_play_accuracy: float
    # Direction (percentages, 0-1)
    pct_left: float
    pct_center: float
    pct_right: float
    # Progressive
    progressive_passes: int
    progressive_pass_rate: float  # progressive / total


@dataclass
class SweepingProfile:
    total_actions: int
    avg_distance_from_goal: float
    max_distance_from_goal: float
    success_rate: float           # 0-1
    # By type (counts)
    sweeps: int
    collections: int
    smothers: int
    punches: int
    clears: int
    pick_ups: int
    # Claiming (aerial: collections + punches)
    aerial_attempts: int
    aerial_success_rate: float


@dataclass
class RadarProfile:
    """Normalized 0-1 values for radar chart, percentile rank within the competition."""
    save_percentage: float
    goals_minus_xg: float         # inverted so higher = better
    short_pass_accuracy: float
    long_pass_accuracy: float
    progressive_pass_rate: float
    sweep_distance: float         # avg distance from goal, higher = more aggressive
    claiming_success: float
    shot_stopping_rate_in_box: float


@dataclass
class SummaryFile:
    """Shape of /data/{competition_id}/{keeper_id}/summary.json"""
    player_id: int
    player_name: str
    team: str
    competition_id: int
    matches_played: int
    minutes_played: int
    clean_sheets: int
    shot_stopping: ShotStoppingProfile
    distribution: DistributionProfile
    sweeping: SweepingProfile
    radar: RadarProfile


# ---------------------------------------------------------------------------
# Helpers for serialization
# ---------------------------------------------------------------------------

def _serialize(obj: object) -> dict | list | str | int | float | bool | None:
    """Recursively convert dataclasses/enums to JSON-serializable dicts."""
    if isinstance(obj, Enum):
        return obj.value
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _serialize(v) for k, v in obj.__dict__.items()}
    if isinstance(obj, list):
        return [_serialize(item) for item in obj]
    return obj
