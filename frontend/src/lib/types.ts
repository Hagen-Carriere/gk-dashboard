/**
 * Data type definitions for the goalkeeper analysis dashboard.
 *
 * These interfaces mirror the Python dataclasses in data-pipeline/schemas.py.
 * Every JSON file loaded by the frontend conforms to one of these shapes.
 *
 * Coordinate conventions (all data is pre-normalized by the pipeline):
 *   - Keeper's goal at x=0, center of goal line at (0, 40)
 *   - Opponent's goal at x=120
 *   - Pitch: 120 × 80 StatsBomb units
 *
 * Goal frame conventions:
 *   - (0, 0) = bottom-left post (keeper's perspective facing field)
 *   - Width 0–8 (yards), Height 0–8 (feet)
 */

// ---------------------------------------------------------------------------
// Enums (string unions matching Python Enum values)
// ---------------------------------------------------------------------------

export type ShotOutcome =
  | "Goal"
  | "Saved"
  | "Off Target"
  | "Blocked"
  | "Post"
  | "Wayward";

export type ShotZone =
  | "Six-Yard Box"
  | "Box Central"
  | "Box Wide"
  | "Outside Box";

export type GoalFrameZone =
  | "Top Left"
  | "Top Center"
  | "Top Right"
  | "Bottom Left"
  | "Bottom Center"
  | "Bottom Right";

export type PlayPattern =
  | "Regular Play"
  | "From Corner"
  | "From Free Kick"
  | "From Counter"
  | "From Throw In"
  | "From Goal Kick"
  | "From Keeper"
  | "Other";

export type PassLengthCategory = "Short" | "Medium" | "Long";

export type PassOutcome =
  | "Complete"
  | "Incomplete"
  | "Out"
  | "Injury Clearance"
  | "Unknown";

export type SweepActionType =
  | "Keeper Sweep"
  | "Collected"
  | "Smother"
  | "Punch"
  | "Clear"
  | "Keeper Pick-Up";

export type PassDirection = "Left" | "Center" | "Right";

// ---------------------------------------------------------------------------
// Shared primitives
// ---------------------------------------------------------------------------

export interface Coord2D {
  x: number;
  y: number;
}

export interface Coord3D {
  x: number;
  y: number;
  z: number;
}

export interface GoalFrameCoord {
  /** 0–8, left to right from keeper's perspective */
  gf_x: number;
  /** 0–8, bottom to top */
  gf_y: number;
}

export interface FreezeFramePlayer {
  player_id: number;
  player_name: string;
  position: string;
  location: Coord2D;
  /** Teammate of the SHOOTING team, not the keeper */
  teammate: boolean;
}

// ---------------------------------------------------------------------------
// competitions.json
// ---------------------------------------------------------------------------

export interface CompetitionInfo {
  competition_id: number;
  season_id: number;
  competition_name: string;
  season_name: string;
  match_count: number;
  keeper_count: number;
}

export interface CompetitionsFile {
  competitions: CompetitionInfo[];
}

// ---------------------------------------------------------------------------
// keepers.json — overview table for a competition
// ---------------------------------------------------------------------------

export interface KeeperOverviewRow {
  player_id: number;
  player_name: string;
  team: string;
  matches_played: number;
  minutes_played: number;
  shots_faced: number;
  shots_on_target_faced: number;
  saves: number;
  goals_conceded: number;
  /** saves / shots_on_target_faced, range 0–1 */
  save_percentage: number;
  /** Sum of statsbomb_xg for all shots against */
  xg_faced: number;
  /** goals_conceded - xg_faced. Negative = outperforming. */
  goals_minus_xg: number;
  clean_sheets: number;
  /** Overall pass completion, 0–1 */
  pass_completion_pct: number;
  sweeper_actions: number;
  avg_sweep_distance: number;
}

export interface KeepersFile {
  competition_id: number;
  season_id: number;
  competition_name: string;
  season_name: string;
  min_minutes_threshold: number;
  keepers: KeeperOverviewRow[];
}

// ---------------------------------------------------------------------------
// shots.json — every shot a keeper faced
// ---------------------------------------------------------------------------

export interface ShotFaced {
  event_id: string;
  match_id: number;
  match_label: string;
  minute: number;
  second: number;
  period: number;
  shot_location: Coord2D;
  shot_end_location: Coord3D | null;
  goal_frame_location: GoalFrameCoord | null;
  goal_frame_zone: GoalFrameZone | null;
  shot_outcome: ShotOutcome;
  shot_zone: ShotZone;
  statsbomb_xg: number;
  shot_body_part: string;
  shot_technique: string;
  play_pattern: PlayPattern;
  gk_action_type: string | null;
  gk_technique: string | null;
  gk_body_part: string | null;
  gk_position: string | null;
  keeper_location: Coord2D | null;
  freeze_frame: FreezeFramePlayer[] | null;
}

export interface ShotsFile {
  player_id: number;
  player_name: string;
  team: string;
  competition_id: number;
  shots: ShotFaced[];
}

// ---------------------------------------------------------------------------
// distribution.json — every pass by the keeper
// ---------------------------------------------------------------------------

export interface KeeperPass {
  event_id: string;
  match_id: number;
  match_label: string;
  minute: number;
  second: number;
  period: number;
  start_location: Coord2D;
  end_location: Coord2D;
  /** Raw StatsBomb distance units */
  pass_length: number;
  pass_length_category: PassLengthCategory;
  outcome: PassOutcome;
  height: string;
  body_part: string;
  pass_type: string | null;
  /** Moved ball ≥10 units toward opponent's goal */
  is_progressive: boolean;
  direction: PassDirection;
}

export interface DistributionFile {
  player_id: number;
  player_name: string;
  team: string;
  competition_id: number;
  passes: KeeperPass[];
}

// ---------------------------------------------------------------------------
// sweeping.json — off-line actions
// ---------------------------------------------------------------------------

export interface SweepAction {
  event_id: string;
  match_id: number;
  match_label: string;
  minute: number;
  second: number;
  period: int;
  location: Coord2D;
  action_type: SweepActionType;
  outcome_success: boolean;
  /** x-coordinate after normalization (goal at x=0) */
  distance_from_goal: number;
}

export interface SweepingFile {
  player_id: number;
  player_name: string;
  team: string;
  competition_id: number;
  actions: SweepAction[];
}

// ---------------------------------------------------------------------------
// summary.json — pre-aggregated stats
// ---------------------------------------------------------------------------

export interface ShotStoppingProfile {
  shots_faced: number;
  shots_on_target_faced: number;
  saves: number;
  goals_conceded: number;
  save_percentage: number;
  xg_faced: number;
  goals_minus_xg: number;
  save_rate_six_yard: number | null;
  save_rate_box_central: number | null;
  save_rate_box_wide: number | null;
  save_rate_outside_box: number | null;
  save_rate_top_left: number | null;
  save_rate_top_center: number | null;
  save_rate_top_right: number | null;
  save_rate_bottom_left: number | null;
  save_rate_bottom_center: number | null;
  save_rate_bottom_right: number | null;
  diving_saves: number;
  standing_saves: number;
  saves_both_hands: number;
  saves_left_hand: number;
  saves_right_hand: number;
  saves_feet: number;
  saves_other: number;
  position_set: number;
  position_moving: number;
  position_prone: number;
}

export interface DistributionProfile {
  total_passes: number;
  completion_rate: number;
  short_passes: number;
  short_accuracy: number;
  medium_passes: number;
  medium_accuracy: number;
  long_passes: number;
  long_accuracy: number;
  goal_kicks: number;
  goal_kick_avg_length: number;
  throws: number;
  throw_accuracy: number;
  open_play_passes: number;
  open_play_accuracy: number;
  pct_left: number;
  pct_center: number;
  pct_right: number;
  progressive_passes: number;
  progressive_pass_rate: number;
}

export interface SweepingProfile {
  total_actions: number;
  avg_distance_from_goal: number;
  max_distance_from_goal: number;
  success_rate: number;
  sweeps: number;
  collections: number;
  smothers: number;
  punches: number;
  clears: number;
  pick_ups: number;
  aerial_attempts: number;
  aerial_success_rate: number;
}

export interface RadarProfile {
  /** All values 0–1, percentile rank within competition */
  save_percentage: number;
  goals_minus_xg: number;
  short_pass_accuracy: number;
  long_pass_accuracy: number;
  progressive_pass_rate: number;
  sweep_distance: number;
  claiming_success: number;
  shot_stopping_rate_in_box: number;
}

export interface SummaryFile {
  player_id: number;
  player_name: string;
  team: string;
  competition_id: number;
  matches_played: number;
  minutes_played: number;
  clean_sheets: number;
  shot_stopping: ShotStoppingProfile;
  distribution: DistributionProfile;
  sweeping: SweepingProfile;
  radar: RadarProfile;
}
