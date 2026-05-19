/**
 * Client-side metric utilities for filtering and re-aggregating data.
 *
 * The pipeline pre-computes all aggregated stats, but the frontend needs
 * to recalculate some metrics when the user applies filters (e.g., "show
 * only open play shots" or "first half only"). These functions handle
 * that filtered re-aggregation.
 */

import type {
  ShotFaced,
  ShotOutcome,
  PlayPattern,
  KeeperPass,
  PassLengthCategory,
  SweepAction,
} from "./types";

// -- Shot filtering -----------------------------------------------------------

export interface ShotFilters {
  period?: number[];              // [1], [2], [1,2], [3,4] for extra time
  playPattern?: PlayPattern[];
  shotBodyPart?: string[];
  shotZone?: string[];
}

export function filterShots(
  shots: ShotFaced[],
  filters: ShotFilters
): ShotFaced[] {
  return shots.filter((s) => {
    if (filters.period && !filters.period.includes(s.period)) return false;
    if (filters.playPattern && !filters.playPattern.includes(s.play_pattern))
      return false;
    if (filters.shotBodyPart && !filters.shotBodyPart.includes(s.shot_body_part))
      return false;
    if (filters.shotZone && !filters.shotZone.includes(s.shot_zone))
      return false;
    return true;
  });
}

/**
 * Compute summary stats from a filtered shot array.
 */
export function computeShotStats(shots: ShotFaced[]) {
  const onTarget = shots.filter(
    (s) => s.shot_outcome === "Goal" || s.shot_outcome === "Saved"
  );
  const saves = shots.filter((s) => s.shot_outcome === "Saved");
  const goals = shots.filter((s) => s.shot_outcome === "Goal");

  return {
    total: shots.length,
    onTarget: onTarget.length,
    saves: saves.length,
    goals: goals.length,
    savePercentage:
      onTarget.length > 0 ? saves.length / onTarget.length : null,
    xgFaced: shots.reduce((sum, s) => sum + s.statsbomb_xg, 0),
    goalsMinusXg:
      goals.length -
      shots.reduce((sum, s) => sum + s.statsbomb_xg, 0),
  };
}

// -- Pass filtering -----------------------------------------------------------

export interface PassFilters {
  lengthCategory?: PassLengthCategory[];
  passType?: string[];            // "Goal Kick", null (open play), etc.
  bodyPart?: string[];
  outcome?: string[];
}

export function filterPasses(
  passes: KeeperPass[],
  filters: PassFilters
): KeeperPass[] {
  return passes.filter((p) => {
    if (
      filters.lengthCategory &&
      !filters.lengthCategory.includes(p.pass_length_category)
    )
      return false;
    if (filters.passType) {
      const passType = p.pass_type ?? "Open Play";
      if (!filters.passType.includes(passType)) return false;
    }
    if (filters.bodyPart && !filters.bodyPart.includes(p.body_part))
      return false;
    if (filters.outcome && !filters.outcome.includes(p.outcome))
      return false;
    return true;
  });
}

// -- Sweep filtering ----------------------------------------------------------

export interface SweepFilters {
  actionType?: string[];
  period?: number[];
}

export function filterSweepActions(
  actions: SweepAction[],
  filters: SweepFilters
): SweepAction[] {
  return actions.filter((a) => {
    if (filters.actionType && !filters.actionType.includes(a.action_type))
      return false;
    if (filters.period && !filters.period.includes(a.period)) return false;
    return true;
  });
}
