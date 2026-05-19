/**
 * Coordinate transformation utilities for rendering StatsBomb data on SVG.
 *
 * All input coordinates use the normalized convention from the pipeline:
 *   - Keeper's goal at x=0, opponent's goal at x=120
 *   - Pitch: 120 × 80 units
 *
 * SVG rendering may use different coordinate systems depending on the
 * component (full pitch, half pitch, goal frame). These utilities handle
 * the mapping.
 */

// -- Pitch constants (StatsBomb units) ----------------------------------------

export const PITCH = {
  length: 120,
  width: 80,
  // Penalty area
  penaltyAreaLength: 18,  // extends 18 units from goal line
  penaltyAreaWidth: 44,   // 18 to 62 on y-axis
  penaltyAreaYMin: 18,
  penaltyAreaYMax: 62,
  // Six-yard box
  sixYardLength: 6,
  sixYardWidth: 20,       // 30 to 50 on y-axis
  sixYardYMin: 30,
  sixYardYMax: 50,
  // Goal
  goalYMin: 36,
  goalYMax: 44,
  goalWidth: 8,           // yards
  goalHeight: 8,          // feet (approx 2.44m)
  // Center
  centerX: 60,
  centerY: 40,
  centerCircleRadius: 10,
  // Penalty spot
  penaltySpotX: 12,
} as const;

// -- SVG coordinate mapping ---------------------------------------------------

export interface SVGViewport {
  width: number;
  height: number;
  /** Padding around the pitch in SVG units */
  padding: number;
}

/**
 * Map a StatsBomb (x, y) coordinate to SVG pixel position.
 * The pitch is rendered with (0, 0) at top-left of the SVG.
 */
export function pitchToSVG(
  sbX: number,
  sbY: number,
  viewport: SVGViewport
): { svgX: number; svgY: number } {
  const drawWidth = viewport.width - 2 * viewport.padding;
  const drawHeight = viewport.height - 2 * viewport.padding;

  return {
    svgX: viewport.padding + (sbX / PITCH.length) * drawWidth,
    svgY: viewport.padding + (sbY / PITCH.width) * drawHeight,
  };
}

/**
 * Map a StatsBomb distance to SVG pixel distance (x-axis).
 */
export function pitchDistanceToSVG(
  sbDistance: number,
  viewport: SVGViewport
): number {
  const drawWidth = viewport.width - 2 * viewport.padding;
  return (sbDistance / PITCH.length) * drawWidth;
}

// -- Goal frame mapping -------------------------------------------------------

export interface GoalFrameViewport {
  width: number;
  height: number;
  padding: number;
}

/**
 * Map goal frame coordinates (gf_x: 0-8, gf_y: 0-8) to SVG position.
 * Goal frame renders with (0, 0) at top-left:
 *   - gf_x=0 (left post) maps to left side of SVG
 *   - gf_y=0 (ground) maps to bottom of SVG
 *   - gf_y=8 (crossbar) maps to top of SVG
 */
export function goalFrameToSVG(
  gfX: number,
  gfY: number,
  viewport: GoalFrameViewport
): { svgX: number; svgY: number } {
  const drawWidth = viewport.width - 2 * viewport.padding;
  const drawHeight = viewport.height - 2 * viewport.padding;

  return {
    svgX: viewport.padding + (gfX / PITCH.goalWidth) * drawWidth,
    // Flip y-axis: ground (gf_y=0) at bottom, crossbar (gf_y=8) at top
    svgY: viewport.padding + ((PITCH.goalHeight - gfY) / PITCH.goalHeight) * drawHeight,
  };
}

// -- Shot zone classification (client-side, for filtering) --------------------

import type { ShotZone, Coord2D } from "./types";

/**
 * Classify a shot location into a zone. Matches the pipeline logic
 * in 03_compute_metrics.py for consistency.
 */
export function classifyShotZone(location: Coord2D): ShotZone {
  if (location.x <= 6) {
    return "Six-Yard Box";
  }
  if (location.x <= 18) {
    if (location.y >= 18 && location.y <= 62) {
      return "Box Central";
    }
    return "Box Wide";
  }
  return "Outside Box";
}
